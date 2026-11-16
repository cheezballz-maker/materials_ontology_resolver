"""Replay frozen ingredient-pair references and emit auditable comparison results."""

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
from dataclasses import asdict
from hashlib import file_digest
import json
from pathlib import Path
import platform
from time import perf_counter

from rdkit import rdBase

from canonical_registry.nomenclature_interpretation import InterpretationFramework
from canonical_registry.nomenclature_interpretation.contracts import (
    Evidence, Issue, ReportedIdentifier, StructureKind, TypedStructure,
)
from canonical_registry.nomenclature_interpretation.cosing_preview_adapter import ALIASES, PARENT

from .adapters import from_cosing
from .contracts import (
    ChemicalTarget, Facet, Family, Ingredient, MolecularBinding, Qualification, RegistryType,
    Scope, ScopedDesignation, Verdict,
)
from .engine import compare
from .retrieval import CandidateIndex

DATA = Path(__file__).with_name("evaluation")
COSMETIC = Scope("INCI/CosIng", "cosmetics", "ingredient-designation")
CONTROL = Scope("synthetic-formulary", "development", "ingredient-designation")


def read(filename):
    return json.loads((DATA / filename).read_text(encoding="utf-8"))


def digest(path):
    if path.is_file():
        with path.open("rb") as stream:
            return file_digest(stream, "sha256").hexdigest()
    return None


def _real_ingredients(framework):
    aliases_by_id = {}
    aliases_by_parent = defaultdict(list)
    for alias in read("aliases.json"):
        aliases_by_id[alias["inci_alias_id"]] = alias
        aliases_by_parent[alias["inci_id"]].append(alias)
    reviews = read("real_review.json")
    ingredients = {}
    for row in read("warehouse.json"):
        reference = f"{PARENT}:{row['inci_id']}"

        def proof(source, value, field):
            if source in {"description", "inci"}:
                return Evidence(row[source], source, reference)
            return Evidence(value, field, source, reference)

        review = reviews.get(row["inci"], {})
        families = frozenset(map(Family, review.get("families", ())))
        facets = tuple(Facet(reference, f["field"], f["scheme"], f["value"], Qualification(f["qualification"]),
                             proof(f["source"], f["value"], f["field"])) for f in review.get("facets", ()))
        designations = ()
        if d := review.get("designation"):
            designations = (ScopedDesignation(reference, d["authority"], d["revision"], d["referent"],
                            frozenset(map(Family, d["covers"])),
                            proof(d["source"], d["justification"], "authority_designation_review")),)
        graph = None
        if claim := review.get("graph"):
            alias = aliases_by_id[claim["alias_id"]]
            if alias["inci_id"] != row["inci_id"]:
                raise ValueError("Reviewed graph is attached to the wrong source ingredient")
            structure = TypedStructure(StructureKind(alias["alias_type"].lower()), Evidence(
                alias["alias"], "original_typed_alias", f"{ALIASES}:{alias['inci_alias_id']}", alias["source"],
            ))
            graph = MolecularBinding(reference, structure,
                                     proof(claim["source"], claim["justification"], "graph_binding_review"))
        ingredients[row["inci"]] = from_cosing(
            row, aliases_by_parent[row["inci_id"]], COSMETIC, framework,
            families=families, facets=facets, designations=designations, molecular=graph,
        )
    return ingredients


def _synthetic_ingredient(reference, spec):
    def proof(field, value):
        return Evidence(value, field, "fixture:" + reference)

    families = frozenset(map(Family, spec.get("families", ())))
    scope = Scope(CONTROL.nomenclature, CONTROL.application, spec.get("specificity", CONTROL.specificity))
    designations = tuple(ScopedDesignation(
        reference, "synthetic-authority:" + reference.split("/")[0], "fixture-v1",
        d["referent"], frozenset(map(Family, d["covers"])),
        proof("whole_ingredient_authority", d["referent"]),
    ) for d in spec.get("designations", ()))
    facets = tuple(Facet(reference, f["field"], f["scheme"], f["value"], Qualification(f["qualification"]),
                         proof(f["field"], f["value"])) for f in spec.get("facets", ()))
    target = None
    if c := spec.get("target"):
        target = ChemicalTarget(reference, RegistryType(c["registry_type"]), "fixture-registry", "frozen-fixture",
                                c["id"], proof("synthetic_registry_target", c["id"]))
    molecular = None
    if smiles := spec.get("graph"):
        molecular = MolecularBinding(reference, TypedStructure(StructureKind.SMILES, proof("smiles", smiles)),
                                     proof("qualified_whole_ingredient_graph", smiles))
    issues = ()
    if conflict := spec.get("conflict"):
        issues = (Issue(conflict, (proof("reported_source_conflict", conflict),), conflict=True),)
    return Ingredient(reference, spec.get("label", reference), scope, families, designations, facets, target,
                      molecular, reported_identifiers=tuple(
                          ReportedIdentifier(scheme, proof(scheme, value)) for scheme, value in spec.get("ids", ())
                      ), search_aliases=tuple(proof("alias", value) for value in spec.get("aliases", ())), issues=issues)


def _synthetic_pairs():
    definitions = {case["id"]: case for case in read("synthetic_inputs.json")}
    for case in read("synthetic_reference.json"):
        spec = definitions[case["id"]]
        yield case, *(_synthetic_ingredient(case["id"] + "/" + side, spec[side]) for side in ("left", "right"))


def _fraction(count, total):
    return {"numerator": count, "denominator": total, "value": count / total if total else None}


def metrics(results):
    counts = Counter((row["expected"], row["comparison"]["verdict"]) for row in results)
    expected = Counter(row["expected"] for row in results)
    actual = Counter(row["comparison"]["verdict"] for row in results)
    equal, distinct, unresolved = Verdict.EQUIVALENT, Verdict.DISTINCT, Verdict.UNRESOLVED
    tp = counts[equal, equal]
    positives = [row for row in results if row["expected"] == equal]
    overlaps = [row for row in results if row["overlapping_families"]]
    material_cases = [row for row in results if row["relationships"]]
    return {
        "pairs": len(results),
        "expected_counts": {v: expected[v] for v in Verdict},
        "actual_counts": {v: actual[v] for v in Verdict},
        "confusion_matrix": {v: {k: counts[v, k] for k in Verdict} for v in Verdict},
        "equivalence_precision": _fraction(tp, actual[equal]),
        "equivalence_recall": _fraction(tp, expected[equal]),
        "false_equivalence_rate": _fraction(actual[equal] - tp, len(results) - expected[equal]),
        "distinctness_precision": _fraction(counts[distinct, distinct], actual[distinct]),
        "unresolved_rate": _fraction(actual[unresolved], len(results)),
        "outcome_agreement": _fraction(sum(counts[v, v] for v in Verdict), len(results)),
        "candidate_recall_equivalence": _fraction(sum(r["retrieved"] for r in positives), len(positives)),
        "candidate_retrieval_all_reviewed_pairs": _fraction(sum(r["retrieved"] for r in results), len(results)),
        "candidate_recall_without_authority_keys": _fraction(
            sum(r["retrieved_without_authority_keys"] for r in positives), len(positives)),
        "repeat_determinism": _fraction(sum(r["deterministic"] for r in results), len(results)),
        "order_invariance": _fraction(sum(r["order_invariant"] for r in results), len(results)),
        "overlap_agreement": _fraction(sum(r["comparison"]["verdict"] == r["expected"] for r in overlaps), len(overlaps)),
        "expected_relationships_found": _fraction(sum(r["relationship_pass"] for r in material_cases), len(material_cases)),
    }


def _run(pairs, ingredients):
    ingredients = tuple(ingredients)
    index = CandidateIndex(ingredients)
    output = []
    for case, left, right in pairs:
        comparison = compare(left, right)
        result = index.find(left)
        hits = dict(result.matches).get(right.reference, ())
        assert hits == dict(index.find(right).matches).get(left.reference, ())
        output.append({
            **case,
            "labels": [left.label, right.label],
            "comparison": asdict(comparison),
            "overlapping_families": len(left.families | right.families) > 1 and bool(
                len(left.families) > 1 or len(right.families) > 1),
            "deterministic": comparison == compare(left, right),
            "order_invariant": comparison == compare(right, left),
            "retrieved": bool(hits),
            "retrieved_without_authority_keys": any(key[0] != "designation" for key in hits),
            "retrieval_keys": hits,
            "skipped_keys": result.skipped,
            "relationship_pass": set(case["relationships"]) <= {r.kind for r in comparison.relationships},
        })
    candidate_lists = [index.find(item) for item in ingredients]
    return {
        "metrics": metrics(output),
        "index": {"concepts": len(ingredients),
                  "candidate_pairs": sum(len(x.matches) for x in candidate_lists) // 2,
                  "possible_pairs": len(ingredients) * (len(ingredients) - 1) // 2,
                  "queries_with_skipped_keys": sum(bool(x.skipped) for x in candidate_lists)},
        "pairs": output,
    }


def _scale_probe():
    count = 30_360
    def records():
        for k in range(count):
            yield Ingredient(f"scale:{k}", f"Synthetic label {k // 2}", CONTROL,
                             reported_identifiers=(ReportedIdentifier("CAS", Evidence(
                                 "broad-shared-id", "reported_cas", f"scale:{k}")),))
    started = perf_counter()
    index = CandidateIndex(records())
    indexed = perf_counter()
    candidates = [index.find(item) for item in records()]
    return {
        "synthetic_concepts": count,
        "possible_pairs": count * (count - 1) // 2,
        "candidate_pairs": sum(len(x.matches) for x in candidates) // 2,
        "queries_with_skipped_keys": sum(bool(x.skipped) for x in candidates),
        "build_seconds": round(indexed - started, 3),
        "all_queries_seconds": round(perf_counter() - indexed, 3),
    }


def evaluate(*, opsin=False):
    freeze = read("reference_freeze.json")
    if any(digest(DATA / name) != sha for name, sha in freeze["reference_inputs_sha256"].items()):
        raise ValueError("Frozen reference input changed")
    with ExitStack() as stack:
        bridge = None
        if opsin:
            from providers import Bridge
            bridge = Bridge()
            stack.callback(bridge.close)
        warehouse = _real_ingredients(InterpretationFramework(name_parser=bridge))
        jar = bridge.digest if bridge else None
    real_cases = read("real_reference.json")
    real = _run(((c, warehouse[c["left"]], warehouse[c["right"]]) for c in real_cases), warehouse.values())
    controls = list(_synthetic_pairs())
    synthetic = _run(controls, (item for _, a, b in controls for item in (a, b)))
    scale = _scale_probe()
    guard = {path: digest(Path(path)) == sha for path, sha in freeze["protected_sha256_before"].items()}
    return {"environment": {"python": platform.python_version(), "rdkit": rdBase.rdkitVersion, "opsin_jar_sha256": jar},
            "reference_freeze_sha256": digest(DATA / "reference_freeze.json"),
            "real": real, "synthetic": synthetic, "scale_probe": scale,
            "protected_paths_unchanged": sum(guard.values()), "protected_paths_total": len(guard),
            "changed_protected_paths": [p for p, same in guard.items() if not same]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opsin", action="store_true", help="Enable the existing local Java name interpreter")
    parser.add_argument("--output", type=Path, help="Write machine-readable results to this file")
    args = parser.parse_args()
    text = json.dumps(evaluate(opsin=args.opsin), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
