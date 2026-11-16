"""Run the frozen authority-backed study and the unchanged legacy reference suite."""

import argparse
from collections import Counter
from contextlib import ExitStack
from dataclasses import asdict, replace
from itertools import groupby
import json
from pathlib import Path
import platform
from time import perf_counter

from rdkit import rdBase
from canonical_registry.nomenclature_interpretation import InterpretationFramework
from canonical_registry.nomenclature_interpretation.contracts import Evidence, ReportedIdentifier, StructureKind, TypedStructure
from chemistry import describe

from .contracts import Facet, Family, Ingredient, MolecularBinding, Qualification, Scope, Verdict
from .engine import compare
from .evaluate import DATA as LEGACY, _real_ingredients, _synthetic_pairs, digest
from .qualification import AuthorityClaim, ClaimKind, Origin, qualify
from .retrieval import CandidateIndex, keys

STUDY = Path(__file__).with_name("evidence_validation")
LIMITS = (1, 5, 10, 25, 50)


def read(folder, name):
    return json.loads((folder / name).read_text(encoding="utf-8"))


def claim_from_record(item, record):
    return AuthorityClaim(
        subject=item.reference, designation=item.label, native_scope=item.scope,
        kind=ClaimKind(record["kind"]), origin=Origin(record.get("origin", "ORIGINAL_AUTHORITY")),
        authority=record["authority"], scheme=record["scheme"], revision=record["revision"],
        locator=record["locator"], source=record["source"], definition=record["definition"],
        referent=record["referent"], conditions=tuple(record.get("conditions", ())),
        comparison_scope=Scope(**record["comparison_scope"]) if "comparison_scope" in record else None,
        covers=frozenset(map(Family, record.get("covers", item.families))),
        field=record.get("field"), partition=record.get("partition"),
        allowed_values=frozenset(record.get("allowed_values", ())),
    )


def load_study(bridge):
    records = read(STUDY, "authority_inputs.json")
    proof_sources = {claim["source"] for r in records.values() for claim in r["claims"]
                     if claim["kind"] == "WHOLE_DESIGNATION"}
    full, independent = {}, {}
    parsed = Counter()
    for reference, r in records.items():
        identifiers = [ReportedIdentifier(kind, Evidence(value, kind, reference))
                       for kind, value in r.get("identifiers", ())]
        if bridge and set(r["families"]) == {"molecular"}:
            parsed["attempted"] += 1
            raw = bridge.opsin(r["label"])
            if raw.get("smiles"):
                try:
                    key = describe(raw["smiles"])["inchikey"]
                except (ValueError, RuntimeError):
                    pass
                else:
                    parsed["strictly_parsed"] += 1
                    identifiers.append(ReportedIdentifier("name parsed InChIKey", Evidence(
                        key, "candidate-only OPSIN structure from original label", reference, "OPSIN",
                    )))
        item = Ingredient(reference, r["label"], Scope(**r["scope"]), frozenset(map(Family, r["families"])),
                          reported_identifiers=tuple(identifiers))
        if graph := r.get("graph"):
            item = replace(item, molecular=MolecularBinding(reference, TypedStructure(
                StructureKind.SMILES, Evidence(graph["smiles"], "structure transcription", graph["source"]),
            ), Evidence(graph["definition"], "reviewed graph binding", graph["source"])))
        facets = tuple(Facet(reference, f["field"], f["scheme"], f["value"], Qualification.DESCRIPTIVE,
                             Evidence(f["value"], "independently sourced descriptor", f["source"]))
                       for f in r.get("independent_facets", ()))
        item = replace(item, facets=facets)
        claims = tuple(claim_from_record(item, c) for c in r["claims"])
        full[reference] = qualify(item, claims)
        # Withhold the equivalence document, including descriptors copied from the same
        # document anywhere in the pool. This is stricter than dropping the designation key.
        raw = replace(item, facets=tuple(f for f in facets if f.evidence.source_reference not in proof_sources),
                      reported_identifiers=tuple(i for i in identifiers
                                                 if i.evidence.source_reference not in proof_sources),
                      molecular=item.molecular if not item.molecular or
                      item.molecular.structure.evidence.source_reference not in proof_sources else None)
        independent[reference] = qualify(raw, tuple(c for c in claims if c.source not in proof_sources))
        assert not independent[reference].designations
    return full, independent, sorted(proof_sources), dict(parsed)


def score(rows):
    observed = Counter((r["expected"], r["prediction"]["verdict"]) for r in rows)
    expected = Counter(r["expected"] for r in rows)
    predicted = Counter(r["prediction"]["verdict"] for r in rows)
    e, d, u = Verdict.EQUIVALENT, Verdict.DISTINCT, Verdict.UNRESOLVED

    def ratio(n, den):
        return {"n": n, "denominator": den, "rate": n / den if den else None}

    return {
        "pairs": len(rows),
        "matrix": {a: {b: observed[a, b] for b in Verdict} for a in Verdict},
        "equivalence_precision": ratio(observed[e, e], predicted[e]),
        "equivalence_recall": ratio(observed[e, e], expected[e]),
        "false_equivalence": ratio(predicted[e] - observed[e, e], len(rows) - expected[e]),
        "distinctness_precision": ratio(observed[d, d], predicted[d]),
        "distinctness_recall": ratio(observed[d, d], expected[d]),
        "unresolved": ratio(predicted[u], len(rows)),
        "agreement": ratio(sum(observed[v, v] for v in Verdict), len(rows)),
        "order_invariance": ratio(sum(r["symmetric"] for r in rows), len(rows)),
        "repeat_determinism": ratio(sum(r["deterministic"] for r in rows), len(rows)),
        "relationship_agreement": ratio(sum(r["relationship_pass"] for r in rows), len(rows)),
    }


def adjudicate(references, pairs):
    results = []
    for ref, (left, right) in zip(references, pairs, strict=True):
        decision = compare(left, right)
        results.append({
            **ref, "labels": [left.label, right.label], "prediction": asdict(decision),
            "symmetric": decision == compare(right, left), "deterministic": decision == compare(left, right),
            "relationship_pass": set(ref["relationships"]) <= {r.kind for r in decision.relationships},
        })
    return results


def retrieval(items, refs, threshold, *, detail=False, name_tokens=True):
    start = perf_counter()
    index = CandidateIndex(items.values(), max_bucket=threshold, name_tokens=name_tokens)
    ready = perf_counter()
    results = {ref: index.find(item, limit=LIMITS[-1]) for ref, item in items.items()}
    finished = perf_counter()
    ranks = {ref: {match: j for j, (match, _) in enumerate(result.matches, 1)}
             for ref, result in results.items()}
    positives = [r for r in refs if r["expected"] == Verdict.EQUIVALENT]
    traces = []
    for case in positives:
        a, b = case["left"], case["right"]
        ar, br = ranks[a].get(b), ranks[b].get(a)
        shared = keys(items[a], name_tokens=name_tokens) & keys(items[b], name_tokens=name_tokens)
        suppressed = {key for key, _ in results[a].skipped}
        if not shared:
            cause = "NO_SHARED_DISCOVERY_KEY"
        elif shared <= suppressed:
            cause = "ALL_SHARED_POSTINGS_SUPPRESSED"
        elif ar is None or br is None:
            cause = "RANK_OUTSIDE_TOP_50"
        else:
            cause = None
        traces.append({
            "pair": case["id"], "ranks": [ar, br], "miss_cause": cause,
            "different_native_nomenclatures": items[a].scope.nomenclature != items[b].scope.nomenclature,
            "shared_literal_name": any(k[0] == "label" for k in shared),
            "shared_reported_cas_or_ec": any(k[0] == "reported" and k[1] in {"cas", "ec"} for k in shared),
            "shared_keys": sorted(shared) if detail else [],
        })
    return {
        "threshold": threshold, "concepts": len(items), "candidate_pairs": sum(r.candidate_count for r in results.values()) // 2,
        "postings_visited": sum(r.postings_visited for r in results.values()),
        "queries_with_suppression": sum(bool(r.skipped) for r in results.values()),
        "build_seconds": round(ready - start, 6), "query_seconds": round(finished - ready, 6),
        "recall": {
            limit: {"pairs_both_directions": sum(all(rank is not None and rank <= limit for rank in t["ranks"]) for t in traces),
                    "pairs_either_direction": sum(any(rank is not None and rank <= limit for rank in t["ranks"]) for t in traces),
                    "pairs": len(positives)}
            for limit in LIMITS
        },
        "miss_causes_at_50": dict(Counter(t["miss_cause"] for t in traces if t["miss_cause"])),
        "positive_traces": traces if detail else [],
    }


def crowded_posting_probe():
    scope = Scope("synthetic fixture", "benchmark", "specified ingredient")
    item_ids = ("left", "right", *(f"nuisance:{i:03d}" for i in range(126)))
    items = {}
    for ref in item_ids:
        identifier = ReportedIdentifier("fixture material key", Evidence("shared", "retrieval-only identifier", ref))
        items[ref] = Ingredient(ref, ref, scope, reported_identifiers=(identifier,))
    refs = [{"id": "crowded-posting-control", "left": "left", "right": "right", "expected": Verdict.EQUIVALENT}]
    return [retrieval(items, refs, threshold) for threshold in (64, 128)]


def prior_replay(bridge, archived):
    warehouse = _real_ingredients(InterpretationFramework(name_parser=bridge))
    refs = read(LEGACY, "real_reference.json")
    baseline = adjudicate(refs, ((warehouse[r["left"]], warehouse[r["right"]]) for r in refs))
    augmented = dict(warehouse)
    for label, (_, value, url, locator, definition, partition) in read(STUDY, "legacy_evidence.json").items():
        item = warehouse[label]
        claim = AuthorityClaim(
            item.reference, item.label, item.scope, ClaimKind.IDENTITY_SPECIFICATION, Origin.ORIGINAL_SOURCE_RECORD,
            "CosIng with corroborating authority", "CosIng ingredient definition", "captured-2026-11-11",
            locator, url, definition, value, ("Profile applies to the whole CosIng ingredient definition",),
            field="defining_referent", partition=partition, allowed_values=frozenset({value}),
        )
        augmented[label] = qualify(item, (claim,))
    reviewed = adjudicate(refs, ((augmented[r["left"]], augmented[r["right"]]) for r in refs))
    synthetic_pairs = list(_synthetic_pairs())
    controls = adjudicate((r for r, _, _ in synthetic_pairs), ((a, b) for _, a, b in synthetic_pairs))
    archived_by_id = {r["id"]: r["comparison"]["verdict"] for r in archived["real"]["pairs"] + archived["synthetic"]["pairs"]}
    for r in baseline + reviewed + controls:
        r["prior_verdict"] = archived_by_id[r["id"]]
    return {
        "prior_unaugmented": {"summary": score(baseline), "rows": baseline},
        "prior_with_documented_new_evidence": {"summary": score(reviewed), "rows": reviewed},
        "synthetic": {"summary": score(controls), "rows": controls},
    }


def run():
    freeze = read(STUDY, "freeze.json")
    for name, sha in freeze["inputs"].items():
        if digest(STUDY / name) != sha:
            raise ValueError(f"Frozen input changed: {name}")
    if digest(LEGACY / "results.json") != freeze["prior_predictions"]:
        raise ValueError("Archived predictions changed")
    prior_inputs = read(LEGACY, "reference_freeze.json")["reference_inputs_sha256"]
    if any(digest(LEGACY / name) != sha for name, sha in prior_inputs.items()):
        raise ValueError("A frozen legacy reference input changed")
    refs = read(STUDY, "reference.json")
    with ExitStack() as stack:
        from providers import Bridge
        bridge = Bridge()
        stack.callback(bridge.close)
        start = perf_counter()
        full, ablated, removed, parsed = load_study(bridge)
        preparation_seconds = round(perf_counter() - start, 6)
        start = perf_counter()
        rows = adjudicate(refs, ((full[r["left"]], full[r["right"]]) for r in refs))
        adjudication_seconds = round(perf_counter() - start, 6)
        legacy = prior_replay(bridge, read(LEGACY, "results.json"))
        jar = bridge.digest
    guard = {name: digest(Path(name)) == sha for name, sha in freeze["protected_sha256_before"].items()}
    return {
        "freeze_sha256": digest(STUDY / "freeze.json"),
        "runtime": {"python": platform.python_version(), "rdkit": rdBase.rdkitVersion, "opsin_jar_sha256": jar,
                    "input_preparation_seconds": preparation_seconds, "adjudication_seconds_three_replays": adjudication_seconds},
        "summary": score(rows),
        "by_category": {key: score(list(group)) for key, group in groupby(sorted(rows, key=lambda r: r["category"]),
                                                                           key=lambda r: r["category"])},
        "by_context": {key: score(list(group)) for key, group in groupby(sorted(rows, key=lambda r: r["context"]),
                                                                          key=lambda r: r["context"])},
        "predictions": rows,
        "retrieval": {
            "with_all": retrieval(full, refs, 64, detail=True),
            "binding_documents_withheld": retrieval(ablated, refs, 64, detail=True),
            "binding_documents_withheld_without_name_tokens": retrieval(ablated, refs, 64, name_tokens=False),
            "threshold_sweep": {name: [retrieval(pool, refs, t) for t in (2, 8, 16, 32, 128)]
                                for name, pool in (("with_all", full), ("binding_documents_withheld", ablated))},
            "removed_documents": removed, "candidate_only_name_parses": parsed,
            "synthetic_crowded_posting_probe": crowded_posting_probe(),
        },
        "regression": legacy,
        "protected_paths_total": len(guard), "changed_protected_paths": [p for p, same in guard.items() if not same],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=STUDY / "predictions.json")
    args = parser.parse_args()
    results = run()
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=sorted) + "\n", encoding="utf-8")
    print(json.dumps(results["summary"], indent=2))
    if results["changed_protected_paths"]:
        raise SystemExit("A protected path changed during the study")


if __name__ == "__main__":
    main()
