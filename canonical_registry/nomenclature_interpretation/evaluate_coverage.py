"""Run the frozen coverage cohorts and summarize against independent reference facets."""

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from .contracts import Category
from .cosing_preview_adapter import COSMETICS_FUNCTIONS, adapt_cosing_preview
from .framework import InterpretationFramework
from .preview import ChemicalEligibilityPreview
from providers import Bridge

EVALUATION = Path(__file__).with_name("evaluation") / "coverage_v1"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prediction(row, framework, preview):
    item = adapt_cosing_preview(row)
    result = framework.interpret(item)
    chemical = preview.evaluate(result)
    def claim(assertion):
        value = assertion.value
        if assertion.category == Category.STRUCTURAL:
            value = {k: value[k] for k in ("smiles", "inchikey", "components", "charge", "stereo")}
        return {**asdict(assertion), "value": value}

    return {
        "inci_id": row["inci_id"], "source_reference": result.designation.source_reference, "name": row["inci"],
        "stratum": row["stratum"], "stratum_n": int(row["stratum_n"]), "sample_rank": int(row["sample_rank"]),
        "state": result.state, "modules": {module.module: module.state for module in result.modules},
        "routed": any(module.module != "generic_ingredient" for module in result.modules),
        "fallback": any(module.module == "generic_ingredient" for module in result.modules),
        "assertions": [claim(a) for a in result.assertions],
        "withheld_assertions": [claim(a) for a in result.withheld_assertions],
        "graph_comparisons": [asdict(c) for c in result.graph_comparisons],
        "issues": [asdict(i) for i in result.issues], "functions": [asdict(r) for r in result.functions],
        "chemical_preview": asdict(chemical),
    }


def counts(rows):
    routed = [r for r in rows if r["routed"]]
    reviewed = [r for r in routed if r.get("review") in {"AGREES", "MIXED", "INCORRECT"}]
    return {
        "records": len(rows), "routed": len(routed),
        "useful_interpretations": sum(bool(r.get("useful")) for r in rows),
        "reviewed_routed_records": len(reviewed),
        "agrees": sum(r["review"] == "AGREES" for r in reviewed),
        "mixed_or_incorrect": sum(r["review"] != "AGREES" for r in reviewed),
        "unadjudicated_routed": len(routed) - len(reviewed),
        "reference_facet_hits": sum(bool(r.get("reference_hit")) for r in rows),
        "reference_facets_expected": sum(bool(r.get("reference_predicates")) for r in rows),
        "substance_eligible": sum(r["chemical_preview"]["route"] == "SUBSTANCE" for r in rows),
        "concept_eligible": sum(r["chemical_preview"]["route"] == "CHEMICAL_CONCEPT" for r in rows),
        "fallback": sum(r["fallback"] for r in rows),
        "state_counts": dict(Counter(r["state"] for r in rows)),
        "function_qualification_counts": dict(Counter(
            f["qualification"] for r in rows for f in r["functions"]
        )),
        "preview_block_reasons": dict(Counter(code for r in rows for code in r["chemical_preview"]["reasons"])),
    }


def summarize(rows, references, reviews):
    by_key = {(r["stratum"], r["sample_rank"]): r for r in rows}
    if len(by_key) != len(rows) or len({r["inci_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate sampled record")
    if set(by_key) != set(references) or set(by_key) != set(reviews):
        raise ValueError("Missing or unexpected reference or review records")
    for key, row in by_key.items():
        predicates, reference_note = references[key]
        status, useful, review_note = reviews[key]
        observed = {a["predicate"] for a in row["assertions"]}
        row.update(reference_predicates=predicates, reference_note=reference_note, review=status,
                   useful=useful, review_note=review_note,
                   reference_hit=bool(predicates and observed.intersection(predicates)))
    module_names = sorted({m for r in rows for m in r["modules"] if m != "generic_ingredient"})
    strata = {}
    for stratum in sorted({r["stratum"] for r in rows}):
        selected = [r for r in rows if r["stratum"] == stratum]
        strata[stratum] = {"population": selected[0]["stratum_n"], **counts(selected)}
    per_module = {}
    for module in module_names:
        selected = [r for r in rows if module in r["modules"]]
        per_module[module] = counts(selected)
    denominator = sum(s["population"] for s in strata.values())
    weighted = {
        metric: sum(s["population"] * s[metric] / s["records"] for s in strata.values()) / denominator
        for metric in ("routed", "useful_interpretations", "substance_eligible", "concept_eligible", "fallback")
    }
    return {
        **counts(rows), "strata": strata, "by_module_overlapping_record_counts": per_module,
        "stratified_population_represented": denominator, "weighted_point_estimates": weighted,
    }


def labels(path):
    # Rows are manually keyed by the deterministic stratum and sample rank.
    return {(stratum, int(rank)): value for stratum, group in load(path).items() for rank, value in group.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cohort", choices=("development", "holdout", "correction_holdout"))
    parser.add_argument("--tag", choices=("corrected",), help="Use separate outputs and reviews for a diagnostic replay")
    parser.add_argument("--score", action="store_true", help="Score already recorded predictions against review files")
    args = parser.parse_args()
    prefix = EVALUATION / args.cohort
    source_path = prefix.with_suffix(".json")
    output_prefix = prefix.name + ("." + args.tag if args.tag else "")
    predictions_path = EVALUATION / (output_prefix + ".predictions.json")
    if args.score:
        rows = load(predictions_path)
        summary = summarize(rows, labels(prefix.with_suffix(".reference.json")),
                            labels(EVALUATION / (output_prefix + ".review.json")))
        summary["source_sha256"] = sha256(source_path.read_bytes()).hexdigest()
        summary["predictions_sha256"] = sha256(predictions_path.read_bytes()).hexdigest()
        write(EVALUATION / (output_prefix + ".summary.json"), summary)
        print(json.dumps({k: v for k, v in summary.items() if not isinstance(v, dict)}, indent=2))
        return

    if predictions_path.exists() and args.cohort in {"development", "holdout"} and not args.tag:
        raise SystemExit("The frozen first release predictions exist. Use --tag corrected for a replay.")
    source_rows = load(source_path)
    bridge = Bridge()
    try:
        framework = InterpretationFramework(name_parser=bridge, function_vocabularies={"cosmetics": COSMETICS_FUNCTIONS})
        preview = ChemicalEligibilityPreview(bridge)
        rows = [prediction(row, framework, preview) for row in source_rows]
    finally:
        bridge.close()
    write(predictions_path, rows)
    print(f"Recorded {len(rows)} {args.cohort} predictions.")


if __name__ == "__main__":
    main()
