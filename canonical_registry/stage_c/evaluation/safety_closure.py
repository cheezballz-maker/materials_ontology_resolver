"""Freeze provisional reference judgments, then compare isolated decisions."""

import argparse
from collections import Counter
from contextlib import closing
import json
import re
from statistics import median

from canonical_registry.authoritative_lookup.lookup import normalize
from canonical_registry.authoritative_lookup.sources import file_digest, read, write
from ..cohort import DATA
from ..fixture import open_fixture, reader

ROOT = DATA / "safety_closure"

# A narrow assessment from original source definitions alone. This is an
# evaluation rubric, separate from qualification and deliberately incomplete.
PREPARATION = re.compile(r"\b(?:extract|hydrolysate) (?:of|from)\b|\b(?:oil|powder) (?:obtained|expressed) from\b|"
                         r"\b(?:steam distillates|formed by reacting|polymer with)\b", re.I)


def freeze_reference():
    target = ROOT / "reference_judgments.json"
    if target.exists():
        raise FileExistsError("Reference judgments are already frozen")
    operational = read(ROOT / "identifier_reference.json")
    references = read(ROOT / "nist_reference.json")
    rows = []
    for item in read(ROOT / "reference_cohort.json"):
        cas = item["cas"]
        ref = references.get(cas, {})
        shared = cas in operational
        definition = item.get("definition") or ""
        scope = "UNADJUDICATED"
        exact_key = None
        if PREPARATION.search(definition):
            scope = "WITHHOLD_PREPARATION_OR_DISTRIBUTION"
        elif ref.get("status") == "STRUCTURAL_REFERENCE" and (
            normalize(ref["title"]) == normalize(item["designation"])
            and not shared and (not definition or normalize(definition.rstrip(".")) == normalize(item["designation"]))
        ):
            scope, exact_key = "PROVISIONAL_EXACT", ref["inchikey"]
        rows.append({**item, "reference": ref, "reference_used_by_engine": shared,
                     "provisional_scope_judgment": scope, "expected_key": exact_key})
    write(target, rows)
    print(Counter(r["provisional_scope_judgment"] for r in rows))


def decisions(run):
    permit, _, _ = open_fixture(run)
    with closing(reader(permit.path)) as db:
        return {r["referent"]: r for raw, in db.execute("SELECT result_json FROM stage_c_request") for r in [json.loads(raw)]}


def compare_runs(run, baseline):
    rows = decisions(run)
    base = decisions(baseline)
    manifest, baseline_manifest = (read(p / "manifest.json") for p in (run, baseline))
    if rows.keys() != base.keys() or {k: v for k, v in manifest.items() if k != "safety_enabled"} != {
        k: v for k, v in baseline_manifest.items() if k != "safety_enabled"
    } or not manifest.get("safety_enabled") or baseline_manifest.get("safety_enabled"):
        raise ValueError("Paired run membership differs")
    review = []
    supplementary = read(ROOT / "reference_review_notes.json")
    for item in read(ROOT / "reference_judgments.json"):
        r = rows[item["referent"]]
        if r["revision"] != item["source_revision"]:
            raise ValueError("Reference source revision differs")
        exact = r["status"] == "RESOLVED_SUBSTANCE"
        key = (r["eligibility"]["specificity"] or {}).get("inchikey")
        ref_key = item["reference"].get("inchikey")
        structure = ("AGREES" if key == ref_key else "DIFFERS") if exact and ref_key else (
            "REFERENCE_WITHOUT_EXACT_PREDICTION" if ref_key else "REFERENCE_UNAVAILABLE")
        note = supplementary.get(item["referent"])
        scope = item["provisional_scope_judgment"]
        expected_key = item["expected_key"]
        if note:
            if note["designation"] != item["designation"]:
                raise ValueError("Supplementary reference does not match frozen designation")
            scope = note["scope"]
            expected_key = ref_key if scope == "PROVISIONAL_EXACT" else None
        result = "UNADJUDICATED"
        if scope == "WITHHOLD_PREPARATION_OR_DISTRIBUTION":
            result = "FALSE_WHOLE_REFERENT" if exact else "CORRECT_WITHHOLD"
        elif scope == "PROVISIONAL_EXACT":
            result = ("CORRECT_EXACT" if key == expected_key else "FALSE_EXACT") if exact else "POSSIBLE_FALSE_REJECTION"
        review.append({**item, "decision": r["status"], "target": r.get("target"), "key": key,
                       "reason": r["eligibility"]["reasons"], "structural_comparison": structure,
                       "supplementary_source_review": note, "effective_scope_judgment": scope,
                       "effective_expected_key": expected_key, "provisional_comparison": result})

    def timings(records, label):
        values = [r["timings"][label] for r in records if label in r["timings"]]
        return {"count": len(values), "median_seconds": median(values) if values else None, "total_seconds": sum(values)}

    paired = []
    for label, records in (("baseline", base), ("safety", rows)):
        matched = [records[k] for k in rows if rows[k]["status"] == base[k]["status"] == "RESOLVED_SUBSTANCE"]
        scope = [r["timings"]["source_identity_safety_seconds"] for r in records.values()
                 if "source_identity_safety_seconds" in r["timings"]]
        paired.append({"mode": label, "all_qualification": timings(records.values(), "qualification_seconds"),
                       "matched_transactions": timings(matched, "canonical_transaction_seconds"),
                       "matched_end_to_end": timings(matched, "elapsed_seconds"),
                       "creation_transactions": timings((r for r in records.values() if r["outcome"] == "NEW_SUBSTANCE_CREATED"),
                                                        "canonical_transaction_seconds"),
                       "all_elapsed": timings(records.values(), "elapsed_seconds"),
                       "scope_seconds": {"count": len(scope), "median": median(scope) if scope else None, "total": sum(scope)}})
    controls = read(DATA / "v3" / "review_holds.json")
    fresh = {r["concept_id"] for r in read(ROOT / "fresh.json")}
    first_stats, second_stats = (read(p / "run.json") for p in (run, baseline))
    safety_metrics, baseline_metrics = (read(p / "metrics.json") for p in (run, baseline))
    write(run / "closure_results.json", {"reference_sha256": file_digest(ROOT / "reference_judgments.json"),
          "supplementary_review_sha256": file_digest(ROOT / "reference_review_notes.json"),
          "specialist_reviewed": 0, "references": review,
          "reference_comparisons": dict(Counter(r["provisional_comparison"] for r in review)),
          "frozen_scope_labels": dict(Counter(r["provisional_scope_judgment"] for r in review)),
          "scope_judgments_after_supplement": dict(Counter(r["effective_scope_judgment"] for r in review)),
          "structure_comparisons": dict(Counter(r["structural_comparison"] for r in review if not r["reference_used_by_engine"])),
          "overlapping_reference_cas": sum(r["reference_used_by_engine"] for r in review),
          "historical_failures": [{"referent": key, "name": rows[key]["designation"], "before": base[key]["status"],
                                   "after": rows[key]["status"], "safety": rows[key]["eligibility"]["source_identity_safety"]}
                                  for key in controls],
          "fresh_outcomes": dict(Counter(r["status"] for key, r in rows.items() if key in fresh)),
          "safety_reasons": dict(Counter(reason for r in rows.values() for reason in r["eligibility"]["source_identity_safety"]["reasons"])),
          "decisions_changed": [{"referent": k, "designation": v["designation"], "before": base[k]["status"],
                                 "after": v["status"], "reasons": v["eligibility"]["reasons"]}
                                for k, v in rows.items() if v["status"] != base[k]["status"]],
          "identifier_assessments": dict(Counter(a["category"] for r in rows.values() for a in
                                                r["eligibility"]["source_identity_safety"]["identifier_observations"])),
          "batch": {"baseline": {"elapsed_seconds": second_stats["elapsed_seconds"],
                                  "fixture_bytes": baseline_metrics["fixture_database_bytes"],
                                  "peak_working_set_bytes": second_stats["peak_working_set_bytes"]},
                    "safety": {"elapsed_seconds": first_stats["elapsed_seconds"],
                               "fixture_bytes": safety_metrics["fixture_database_bytes"],
                               "peak_working_set_bytes": first_stats["peak_working_set_bytes"]}},
          "paired": paired})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "compare"))
    parser.add_argument("--run", default="pilot-safety-final")
    parser.add_argument("--baseline", default="pilot-safety-final-baseline")
    args = parser.parse_args()
    if any(not name.isascii() or not name.replace("-", "").isalnum() for name in (args.run, args.baseline)):
        parser.error("Use simple run names")
    if args.action == "freeze":
        freeze_reference()
    else:
        compare_runs(DATA / args.run, DATA / args.baseline)
