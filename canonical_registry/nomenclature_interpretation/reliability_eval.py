"""Capture frozen evaluations and score source and adversarial reliability."""

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
from itertools import chain
import json
from math import sqrt
from pathlib import Path
import platform
import random
import subprocess
import sys
from datetime import datetime, timezone

import rdkit
from rdkit import Chem

from .contracts import Category
from .cosing_preview_adapter import COSMETICS_FUNCTIONS, adapt_cosing_preview
from .framework import InterpretationFramework
from .preview import ChemicalEligibilityPreview
from .reliability_controls import CONFIRMATION_CONTROLS, CONTROLS, duplicate_evidence, equivalent_variant
from .reliability_reference import BASE, DATA, MODULES, annotate
from providers import Bridge, DEFAULT_JAR, ROOT

PACKAGE = Path(__file__).parent
REPETITIONS = 10
DETERMINISM_KEYS = (
    "open_stereochemistry", "smiles_inchi_conflict", "carbonate_graph_serializations", "wrong_inchikey",
    "multiple_botanical_parts", "ferment_constituent_graph", "copolymer_segments", "chain_distribution",
    "colour_five_digits", "unknown_designation", "context_and_unknown_role", "wrong_formula",
)
SCOPE = {
    "molecular_graph": "TYPED_CANDIDATE_GRAPH", "reported_taxon_text": "UNVERIFIED_TAXON_TEXT",
    "reported_plant_part": "REPORTED_SOURCE_PART", "source_anatomical_structure": "REPORTED_SOURCE_PART",
    "reported_source_preparation": "REPORTED_SOURCE_DEFINITION", "ColourIndex": "CANDIDATE_INDEX_DESIGNATION",
    "ColourIndexGenericName": "CANDIDATE_INDEX_DESIGNATION",
}
SCORED = {
    "molecular_chemical": {"molecular_graph"},
    "inorganic_mineral": {"reported_mineral_name", "reported_oxide_name", "reported_inorganic_salt_name",
                          "reported_inorganic_multimetal_oxide", "reported_hydration_qualifier"},
    "botanical": {"reported_taxon_text", "reported_plant_part", "source_anatomical_structure",
                  "reported_botanical_preparation"},
    "biological_biotechnological": {"reported_biological_category"},
    "polymer_silicone": {"reported_polymer_category", "reported_polyether_grade"},
    "lipid_surfactant": {"reported_lipid_surfactant_qualifier"},
    "colorant": {"ColourIndex", "ColourIndexGenericName", "reported_colorant_qualifier"},
    "preparation_mixture": {"reported_preparation_qualifier", "reported_source_preparation"},
}


def load(name):
    return json.loads((DATA / (name + ".json")).read_text(encoding="utf-8"))


def write(name, data):
    path = DATA / (name + ".json")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def signature(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def freeze(tag, files):
    import chemistry
    import identity_comparator
    import charge_comparison_attribution
    import name_interpretation
    import composition_constraints
    import canonical_registry.chemical_concept_registry.unified_chemical as unified
    import canonical_registry.enrichment.chemical_qualification as qualification
    paths = list(PACKAGE.glob("*.py"))
    paths.extend(Path(mod.__file__) for mod in (chemistry, identity_comparator, charge_comparison_attribution,
                                               name_interpretation, composition_constraints, unified, qualification))
    paths.extend([ROOT / "RegistryBridge.java", DEFAULT_JAR, *files])
    java = subprocess.run(["java", "-version"], text=True, capture_output=True, check=True).stderr.splitlines()
    write(tag + ".freeze", {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "rdkit": rdkit.__version__, "java": java,
        "opsin_jar": DEFAULT_JAR.name, "external_providers": "OFFLINE",
        "sha256": {str(p.resolve().relative_to(ROOT.parent.resolve())).replace("\\", "/"): sha(p) for p in sorted(set(paths))},
    })


def reference(tag, files):
    seen, records = set(), []
    for file in files:
        for row in load(file):
            if row["inci_id"] in seen:
                continue
            seen.add(row["inci_id"])
            if int(row["typed_count"]) != len(json.loads(row.get("alias_claims") or "[]")):
                raise ValueError("Sampled typed aliases were truncated")
            records.append({"cohort": "population" if file == "population" else file, "row": row,
                            "reference": annotate(row)})
    write(tag + ".reference", records)
    freeze(tag, [DATA / (n + ".json") for n in (*files, tag + ".reference")])
    print("Frozen reference records:", len(records))


def engine(bridge, interpreters=None):
    return InterpretationFramework(name_parser=bridge, interpreters=interpreters,
                                   function_vocabularies={"cosmetics": COSMETICS_FUNCTIONS})


def predict(tag, reference_tag, bridge):
    records = load(reference_tag + ".reference")
    framework, preview = engine(bridge), ChemicalEligibilityPreview(bridge)
    results = []
    for record in records:
        item = adapt_cosing_preview(record["row"])
        result = framework.interpret(item)
        results.append({"id": record["row"]["inci_id"], "cohort": record["cohort"],
                        "interpretation": asdict(result), "preview": asdict(preview.evaluate(result))})
    write(tag + ".predictions", results)
    print("Predictions:", len(results))


def normalized(result, preview):
    """Compare multisets of distinct evidence, without erasing distinct source pointers."""
    def unique(values):
        return sorted({signature(v) for v in values})

    def pair(obj):
        left, right = signature(obj["left"]), signature(obj["right"])
        if left > right:
            left, right = right, left
            direction = {"LEFT_MORE_SPECIFIC": "RIGHT_MORE_SPECIFIC", "RIGHT_MORE_SPECIFIC": "LEFT_MORE_SPECIFIC"}
            obj["relation"] = direction.get(obj["relation"], obj["relation"])
        return left, right, obj["relation"]

    def issue(obj):
        # Endpoint-specific direction is compared in graph comparisons.
        if obj["code"] in {"LEFT_MORE_SPECIFIC", "RIGHT_MORE_SPECIFIC"}:
            obj["code"] = "STEREO_SPECIFICITY_DIFFERS"
        obj["evidence"] = unique(obj["evidence"])
        return obj

    data = asdict(result)
    for module in data["modules"]:
        module["conventions"] = sorted(set(module["conventions"]))
        module["assertions"] = unique(module["assertions"])
        module["issues"] = unique(issue(x) for x in module["issues"])
    data["modules"] = unique(data["modules"])
    for key in ("assertions", "withheld_assertions", "functions"):
        data[key] = unique(data[key])
    data["issues"] = unique(issue(x) for x in data["issues"])
    data["graph_comparisons"] = unique(pair(x) for x in data["graph_comparisons"] if x["left"] != x["right"])
    data["preview"] = {"route": preview.route, "reasons": sorted(set(preview.reasons))}
    return data


def adversarial(bridge, controls=CONTROLS):
    framework, preview = engine(bridge), ChemicalEligibilityPreview(bridge)
    results = []
    for control in controls:
        result = framework.interpret(control.sample)
        eligibility = preview.evaluate(result)
        kept = [(a.predicate, a.value) for a in result.assertions]
        issues = {i.code for i in result.issues}
        checks = {
            "route": eligibility.route == control.route,
            "required_assertions": all((key, value) in kept for key, value in control.must),
            "forbidden_assertions": not (set(control.forbid) & {k for k, _ in kept}),
            "required_issue": not control.issue or control.issue in issues,
            "role_states": control.role_states is None or tuple(r.qualification for r in result.functions) == control.role_states,
            "designation_preserved": result.designation == control.sample.designation,
            "generic_when_expected": control.family != "fallback" or any(m.module == "generic_ingredient" for m in result.modules),
            "carbonate_serializations_compatible": control.key != "carbonate_graph_serializations" or any(
                p.left.field == "alias:0" and p.right.field == "alias:1" and p.relation == "COMPATIBLE"
                for p in result.graph_comparisons),
        }
        results.append({"control": asdict(control), "pass": all(checks.values()), "checks": checks,
                        "result": asdict(result), "preview": asdict(eligibility)})
    return results


def determinism(bridge):
    framework, preview = engine(bridge), ChemicalEligibilityPreview(bridge)
    samples = {c.key: c.sample for c in CONTROLS if c.key in DETERMINISM_KEYS}
    counts, failures, baselines = Counter(), [], {}
    for key, item in samples.items():
        base = framework.interpret(item)
        expected = normalized(base, preview.evaluate(base))
        baselines[key] = sha256(signature(expected).encode()).hexdigest()
        for kind in ("repeat", "module_order", "evidence_order", "duplicate"):
            for run in range(REPETITIONS):
                tested, reordered = item, framework
                if kind == "module_order":
                    modules = list(framework.interpreters)
                    if run == 0:
                        modules.reverse()
                    else:
                        random.Random(726019 + run).shuffle(modules)
                    reordered = engine(bridge, tuple(modules))
                if kind == "evidence_order":
                    tested = equivalent_variant(item, run)
                if kind == "duplicate":
                    tested = duplicate_evidence(equivalent_variant(item, run))
                got = reordered.interpret(tested)
                actual = normalized(got, preview.evaluate(got))
                counts[kind] += 1
                trace = trace_preserved(tested, got)
                changed = [k for k in expected if expected[k] != actual[k]]
                if changed or not trace:
                    failures.append({"case": key, "kind": kind, "repetition": run, "fields": changed,
                                     "trace_preserved": trace})
    return {"repetitions_per_case": REPETITIONS, "comparison_counts": counts,
            "baseline_hashes": baselines, "failures": failures}


def trace_preserved(item, result):
    functions = Counter(r.evidence for r in result.functions)
    identifiers = Counter(a.evidence for a in chain(result.assertions, result.withheld_assertions)
                          if a.method == "REPORTED_IDENTIFIER")
    molecular = [m for m in result.modules if m.module == "molecular_chemical"]
    structures = Counter(a.evidence for m in molecular for a in m.assertions if a.method == "STRICT_RDKIT_STRUCTURE")
    structures.update(e for m in molecular for i in m.issues if i.code == "TYPED_STRUCTURE_NOT_VALIDATED" for e in i.evidence)
    return (functions == Counter(x.evidence for x in item.functions)
            and identifiers == Counter(x.evidence for x in item.identifiers)
            and structures == Counter(x.evidence for x in item.structures))


def independent_fingerprints(bridge):
    framework, preview = engine(bridge), ChemicalEligibilityPreview(bridge)
    outcomes = {}
    for control in CONTROLS:
        if control.key in DETERMINISM_KEYS:
            result = framework.interpret(control.sample)
            outcomes[control.key] = sha256(signature(normalized(result, preview.evaluate(result))).encode()).hexdigest()
    return outcomes


def ratio(num, den):
    if not den:
        return {"n": num, "d": den, "rate": None, "wilson95": None}
    p = num / den
    z = 1.959963984540054
    middle = (p + z*z/(2*den))/(1 + z*z/den)
    half = z*sqrt((p*(1-p)+z*z/(4*den))/den)/(1+z*z/den)
    return {"n": num, "d": den, "rate": p, "wilson95": [max(0, middle-half), min(1, middle+half)]}


def confusion(want, got):
    return "UNKNOWN" if want is None else "TP" if want and got else "FN" if want else "FP" if got else "TN"


def rates(counts):
    c = Counter(counts)
    return {"precision": ratio(c["TP"], c["TP"]+c["FP"]), "recall": ratio(c["TP"], c["TP"]+c["FN"]),
            "false_positive_rate": ratio(c["FP"], c["FP"]+c["TN"]),
            "false_negative_rate": ratio(c["FN"], c["FN"]+c["TP"])}


def atom(predicate, value, role=None):
    if predicate == "molecular_graph":
        value = value["smiles"] if isinstance(value, dict) else value
        return predicate, value, SCOPE[predicate] if role in (None, "CANDIDATE_ONLY") else "INCORRECTLY_PROMOTED"
    scope = SCOPE.get(predicate, "LABEL_FACET")
    if predicate in {"reported_taxon_text", "ColourIndex", "ColourIndexGenericName"} and role not in (None, "CANDIDATE_ONLY"):
        scope = "INCORRECTLY_PROMOTED"
    return predicate, " ".join(str(value).casefold().split()), scope


def score(tag, ref_tag):
    records = load(ref_tag + ".reference")
    predictions = {p["id"]: p for p in load(tag + ".predictions")}
    if set(predictions) != {r["reference"]["id"] for r in records}:
        raise ValueError("Prediction and reference coverage differ")
    groups = {"all": records, "population": [r for r in records if r["cohort"] == "population"],
              "challenge": [r for r in records if r["cohort"] != "population"]}
    output = {}
    for group, selected in groups.items():
        if not selected:
            continue
        modules = {name: {"routing": Counter(), "assertions": Counter(), "scope": Counter()} for name in MODULES}
        totals, errors, strata = Counter(), [], {}
        for record in selected:
            ref = record["reference"]
            predicted = predictions[ref["id"]]
            result = predicted["interpretation"]
            routed = {m["module"]: m for m in result["modules"]}
            useful = False
            totals["records"] += 1
            totals["routed"] += any(m in routed for m in MODULES)
            totals["fallback"] += "generic_ingredient" in routed
            totals["fallback_"+confusion(ref["fallback"], "generic_ingredient" in routed)] += 1
            route = predicted["preview"]["route"]
            totals[route or "ineligible"] += 1
            retained = {signature(a) for a in result["assertions"]}
            for m, counts in modules.items():
                expectation = ref["routes"][m]
                actual = routed.get(m)
                counts["routing"][confusion(expectation, actual is not None)] += 1
                if expectation is None:
                    continue
                want = {atom(p, v) if SCOPE.get(p, "LABEL_FACET") == scope else (p, str(v), scope)
                        for p, v, scope in ref["assertions"][m] if p in SCORED[m]}
                eligible_assertions = [a for a in (actual or {}).get("assertions", []) if a["predicate"] in SCORED[m]
                                       and (a["predicate"] != "molecular_graph" or a["method"] == "STRICT_RDKIT_STRUCTURE")]
                got = {atom(a["predicate"], a["value"], a["evidence_role"]) for a in eligible_assertions}
                kept = {atom(a["predicate"], a["value"], a["evidence_role"])
                        for a in eligible_assertions if signature(a) in retained}
                useful |= bool(want & kept)
                for outcome, values in (("TP", want & got), ("FN", want - got), ("FP", got - want)):
                    counts["assertions"][outcome] += len(values)
                    if outcome != "TP" and values:
                        errors.append({"id": ref["id"], "name": ref["name"], "module": m, "type": outcome,
                                       "assertions": sorted(values)})
                if m in ref["scope_hold_modules"]:
                    counts["scope"]["expected_hold"] += 1
                    if route is None and not any(a["category"] == "STRUCTURAL" for a in result["assertions"]):
                        counts["scope"]["correct_hold"] += 1
                    else:
                        errors.append({"id": ref["id"], "name": ref["name"], "module": m, "type": "WHOLE_SCOPE_LEAK",
                                       "route": route})
            totals["useful"] += useful
            role = [{**{k: r[k] for k in ("reported_function", "application_context", "qualification", "qualified_vocabulary_labels")},
                     "field": r["evidence"]["field"]} for r in result["functions"]]
            totals["role_rows"] += len(ref["roles"])
            totals["role_rows_agree"] += sum((Counter(map(signature, role)) & Counter(map(signature, ref["roles"]))).values())
            totals["role_records_exact"] += role == ref["roles"]
            if record["cohort"] == "population":
                row = record["row"]
                s = strata.setdefault(row["stratum"], {"size": int(row["stratum_n"]), "counts": Counter()})["counts"]
                s.update(records=1, routed=int(any(m in routed for m in MODULES)), useful=int(useful),
                         fallback=int("generic_ingredient" in routed), substance=int(route == "SUBSTANCE"),
                         concept=int(route == "CHEMICAL_CONCEPT"))
        for counts in modules.values():
            counts["routing_metrics"] = rates(counts["routing"])
            a = counts["assertions"]
            counts["assertion_precision"] = ratio(a["TP"], a["TP"]+a["FP"])
            counts["assertion_recall"] = ratio(a["TP"], a["TP"]+a["FN"])
            counts["whole_referent_accuracy"] = ratio(counts["scope"]["correct_hold"], counts["scope"]["expected_hold"])
        aggregate = {}
        for family in ("routing", "assertions"):
            summed = sum((c[family] for c in modules.values()), Counter())
            metrics = rates(summed) if family == "routing" else {
                "precision": ratio(summed["TP"], summed["TP"]+summed["FP"]),
                "recall": ratio(summed["TP"], summed["TP"]+summed["FN"]),
            }
            macro = {}
            for metric in metrics:
                items = [(c["routing_metrics"][metric] if family == "routing" else c["assertion_"+metric])["rate"]
                         for c in modules.values()]
                items = [n for n in items if n is not None]
                macro[metric] = sum(items)/len(items) if items else None
            aggregate[family] = {"micro_counts": summed, "micro_metrics": metrics, "macro_rates": macro}
        population = sum(s["size"] for s in strata.values())
        weighted = {k: sum(s["size"]*s["counts"][k]/s["counts"]["records"] for s in strata.values())/population
                    for k in ("routed", "useful", "fallback", "substance", "concept")} if population else {}
        output[group] = {"totals": totals, "modules": modules, "aggregate": aggregate, "errors": errors,
                         "weighted": weighted, "strata": strata, "frame_population": population}
    write(tag + ".scores", output)
    print("Scored:", {group: dict(result["totals"]) for group, result in output.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("reference", "predict", "score", "controls", "fingerprint", "processes", "freeze"))
    parser.add_argument("--tag", default="initial")
    parser.add_argument("--reference-tag", default="initial")
    parser.add_argument("--files", nargs="+", default=BASE)
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(args.tag, [])
        return
    if args.action == "reference":
        reference(args.tag, args.files)
        return
    if args.action == "score":
        score(args.tag, args.reference_tag)
        return
    if args.action == "processes":
        fingerprints = []
        for _ in range(REPETITIONS):
            result = subprocess.run([sys.executable, "-B", "-m", __spec__.name, "fingerprint"],
                                    capture_output=True, text=True, check=True, timeout=75)
            fingerprints.append(json.loads(result.stdout))
        write(args.tag + ".processes", {"runs": len(fingerprints), "fingerprints": fingerprints,
                                      "identical": all(x == fingerprints[0] for x in fingerprints)})
        return
    bridge = Bridge()
    try:
        if args.action == "predict":
            predict(args.tag, args.reference_tag, bridge)
        elif args.action == "controls":
            result = adversarial(bridge)
            write(args.tag + ".adversarial", result)
            write(args.tag + ".determinism", determinism(bridge))
            if args.tag != "initial":
                fresh = adversarial(bridge, CONFIRMATION_CONTROLS)
                write(args.tag + ".confirmation_controls", fresh)
                print("Novel controls failed:", [r["control"]["key"] for r in fresh if not r["pass"]])
            print("Adversarial failed:", [r["control"]["key"] for r in result if not r["pass"]])
        else:
            print(json.dumps(independent_fingerprints(bridge)))
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
