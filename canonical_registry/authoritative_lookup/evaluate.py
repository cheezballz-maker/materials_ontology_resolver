"""Reproduce the bounded read-only authority lookup pilot from frozen captures."""

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import json
from time import perf_counter

from rdkit import rdBase

from canonical_registry.chemistry import describe
from canonical_registry.cosing_pilot.staged_assessment import _bridge
from canonical_registry.identity_sufficiency.contract import Evaluator
from canonical_registry.identity_sufficiency.evaluate import _guards
from identity_comparator import compare as compare_forms
from .lookup import IdentityLookup, normalize
from .matching import ABSENT, AMBIGUOUS, EXACT, CanonicalMatching
from .protection import current_baseline
from .sources import (DATA, authority_records, capture_archives, cosing_input, gsrs_controls,
                      gsrs_input, read, warehouse, write)

OUTSIDE = "OUTSIDE_SUPPORTED_SCOPE"


def evaluate():
    start = perf_counter()
    cohort, retrieved, shards = warehouse()
    gsrs, companions = gsrs_controls()
    capture = read(DATA / "authority_cache.json")
    authorities, supplemental, archive_rejections = authority_records(capture["providers"])
    before, derived_changes = current_baseline()
    by_key, by_name = defaultdict(list), defaultdict(list)
    for record in supplemental:
        if record["inchikey"]:
            by_key[record["inchikey"]].append(record)
        for name in record["names"]:
            if name:
                by_name[normalize(name)].append(record)

    def supporting(row, candidates):
        found = {}
        keys = set(row["queries"]["INCHIKEY"]) | {c.get("inchikey") for c in candidates}
        names = set(row["queries"]["NAME"]) | {a["alias"] for a in row["aliases"]
                                                if a["alias_type"] in {"IUPAC", "INN_ISO_AN"} and a.get("alias")}
        for records in [*(by_key[k] for k in keys), *(by_name[normalize(n)] for n in names)]:
            for item in records:
                found[(item["authority"], item["entity"], item["capture"]["sha256"])] = item
        return [found[k] for k in sorted(found)]

    outputs, aliases, admissions = [], [], []
    timings = Counter()
    with ExitStack() as stack, rdBase.BlockLogs():
        bridge = _bridge(stack)
        service = IdentityLookup(Evaluator(bridge.official), authorities)
        matcher = CanonicalMatching(bridge)

        def resolve(source, group, stratum, candidates, total, extra=(), authority_source=False):
            tick = perf_counter()
            decision, receipt, outcomes = service.evaluate(source, candidates, total, authority_source=authority_source)
            status = decision["eligibility"]
            timings["qualification_seconds"] += perf_counter() - tick
            if status == "NOT_APPLICABLE_TO_EXACT_MOLECULAR_RESOLUTION" or (
                authority_source and candidates[0]["ingredient_type"] in {"IONIC MOIETY", "MOLECULAR FRAGMENT"}
            ):
                match = {"outcome": OUTSIDE, "reasons": decision["reasons"]}
            elif "COMPETING_AUTHORITY_STRUCTURAL_FORMS" in decision["reasons"] or (
                    "ALTERNATE_FORM_NAME_CANDIDATE_UNRESOLVED" in decision["reasons"]):
                match = {"outcome": AMBIGUOUS, "reasons": decision["reasons"]}
            else:
                tick = perf_counter()
                match = matcher.match(decision, receipt)
                if status == "CANDIDATE_READY":
                    timings["matching_seconds"] += perf_counter() - tick
            ref = {"source": source.evidence.source_reference, "revision": source.evidence.source_revision,
                   "referent": source.evidence.referent, "designation": source.evidence.designation}
            if match["outcome"] == EXACT and receipt and receipt["assertion_type"] in {
                "PREFERRED_NAME_AND_TYPED_IDENTIFIER", "SOURCE_DEFINITION_AND_TYPED_IDENTIFIER",
                "SOURCE_UNII_CROSS_REFERENCE", "SOURCE_NATIVE_STRUCTURE_WHOLE",
            }:
                aliases.append({**ref, "type": "EXACT_CHEMICAL_ALIAS", "alias": source.evidence.designation,
                                "target": match["proposal"], "receipt_sha256": receipt["receipt_sha256"]})
                if authority_source:
                    aliases.append({**ref, "type": "EXACT_CHEMICAL_ALIAS", "namespace": "UNII",
                                    "identifier": source.identifiers["UNII"][0], "target": match["proposal"],
                                    "receipt_sha256": receipt["receipt_sha256"]})
                else:
                    for namespace, values in receipt["supporting_source_evidence"]["matching_identifiers"].items():
                        aliases.append({**ref, "type": "EXACT_CHEMICAL_ALIAS", "namespace": namespace,
                                        "identifier": values[0], "target": match["proposal"],
                                        "receipt_sha256": receipt["receipt_sha256"]})
            if match["outcome"] == ABSENT:
                admissions.append({**ref, "type": "REVIEW_ONLY", "structure": decision["specificity"],
                                   "receipt_sha256": receipt["receipt_sha256"] if receipt else None,
                                   "registry": match["registry"], "proof": match["proof"]})
            lookup_labels = []
            for candidate in candidates:
                relation = {"name": candidate["chemical_name"], "type": "CANDIDATE_ALIAS",
                            "record": candidate["source_id"]}
                if receipt and candidate["chemical_id"] != receipt["warehouse_candidate"]["chemical_id"] and candidate.get("smiles"):
                    try:
                        comparison = compare_forms(describe(receipt["specificity"]["smiles"]), describe(candidate["smiles"]))
                    except (ValueError, RuntimeError):
                        comparison = None
                    if comparison and comparison["assessment"] == "DISTINCT" and comparison["relations"]:
                        relation.update(type="RELATED_BUT_DISTINCT", form_comparison=comparison)
                lookup_labels.append(relation)
            if match["outcome"] in {OUTSIDE, AMBIGUOUS} or (total > 1 and match["outcome"] != EXACT):
                lookup_labels.append({"name": source.evidence.designation, "type": "BROADER_OR_AMBIGUOUS_DESIGNATION",
                                      "record": source.evidence.referent, "scope": "REVIEW_DIAGNOSTIC"})
            outputs.append({**ref, "group": group, "stratum": stratum, "warehouse_count": total,
                            "warehouse_returned": len(candidates), "qualification": decision, "receipt": receipt,
                            "candidate_results": outcomes, "supplemental_candidates": extra,
                            "name_relationships": lookup_labels, "matching": match})

        for row in cohort:
            total, candidates = retrieved.get(row["concept_id"], (0, []))
            resolve(cosing_input(row), row["group"], row["stratum"], candidates, total,
                    supporting(row, candidates))
        for row in gsrs:
            resolve(gsrs_input(row, companions.get(row["chemical_id"], {})), "GSRS", row["cohort"],
                    [{**row, "routes": ["ORIGINAL_RECORD:UNII:" + row["source_id"]]}], 1, authority_source=True)
        matcher.verify()
    if _guards() != before:
        raise ValueError("Protected ontology, registry or source artifact changed")
    validation = validate_results(outputs, aliases)
    if validation["critical_violations"]:
        raise ValueError(f"Unsafe pilot result: {validation['critical_violations']}")
    by_group = {}
    for group in ("development", "fresh", "GSRS"):
        rows = [row for row in outputs if row["group"] == group]
        by_group[group] = {"rows": len(rows), "retrieved": sum(bool(r["warehouse_count"]) for r in rows),
                           "candidate_pairs": sum(r["warehouse_count"] for r in rows),
                           "review": sum(r["qualification"]["eligibility"] in {"NEEDS_MORE_EVIDENCE", "REVIEW_HOLD"} for r in rows),
                           "qualification": dict(Counter(r["qualification"]["eligibility"] for r in rows)),
                           "matching": dict(Counter(r["matching"]["outcome"] for r in rows))}
    metrics = {
        "groups": by_group, "snapshots": matcher.pins, "substance_integrity": matcher.registry.sqlite_integrity,
        "active_chemical_concepts": len(matcher.concepts), "trino_shards": shards,
        "archive_records": {k: sum(len(e["records"]) for e in v) if isinstance(v, list) else len(v["records"])
                            for k, v in capture["providers"].items()},
        "archived_native_rejections": archive_rejections, "archive_diagnostics": capture["archive_diagnostics"],
        "alias_proposals": len(aliases), "admission_proposals": len(admissions), "protected_before_after_equal": True,
        "protected_file_count": len(before), "local_seconds": round(perf_counter() - start, 3),
        "derived_cache_changes_since_cohort_freeze": derived_changes,
        "stage_seconds": dict(timings),
        "reference_checks": validation,
        "canonical_substances_in_snapshot": len(matcher.registry.entries),
        "distinct_authority_matches_executed": len(matcher.authority_matches),
        "authority_cache_bytes": (DATA / "authority_cache.json").stat().st_size,
        "external_availability": read(DATA / "external_availability.json"),
        "peak_python_working_set_bytes": peak_memory(),
    }
    write(DATA / "results.json", outputs)
    write(DATA / "alias_proposals.json", aliases)
    write(DATA / "admission_proposals.json", admissions)
    write(DATA / "metrics.json", metrics)
    print(json.dumps(metrics["groups"], indent=2))


def validate_results(outputs, aliases):
    known_targets = read(DATA / "freeze.json")["reference"]["positive_targets"]
    controls = {r["designation"]: r for r in outputs if r["group"] == "development"}
    expected = {name: {"expected": target, "actual": controls[name]["matching"].get("proposal", {}).get("id"),
                       "candidate_retrieved": bool(controls[name]["warehouse_count"])}
                for name, target in known_targets.items()}
    violations = []
    for row in outputs:
        match = row["matching"]
        if match["outcome"] == EXACT and (
            row["qualification"]["eligibility"] != "CANDIDATE_READY" or not row["receipt"]
            or not match["proof"]["search_complete"] or not match["proof"]["admission_eligible"]
        ):
            violations.append(row["referent"])
    for name, result in expected.items():
        if result["actual"] and result["actual"] != result["expected"]:
            violations.append(name)
    forbidden = {"ALCOHOL DENAT.", "GLUTAMIC ACID", "MAGNESIUM SULFATE", "TITANIUM DIOXIDE",
                 "LAVANDULA ANGUSTIFOLIA FLOWER EXTRACT", "LACTIC ACID"}
    unsafe = [r["referent"] for r in outputs if (r["group"] == "development" and r["designation"] in forbidden
              and r["matching"]["outcome"] == EXACT) or (r["group"] == "GSRS" and
              r["stratum"] in {"component", "polymer", "mixture", "structurallyDiverse"} and
              r["matching"]["outcome"] == EXACT)]
    safe_receipts = {r["receipt"]["receipt_sha256"] for r in outputs
                     if r["receipt"] and r["matching"]["outcome"] == EXACT}
    orphan_aliases = [r["referent"] for r in aliases if r["receipt_sha256"] not in safe_receipts]
    return {"known_positive_targets": expected, "named_negative_controls": sorted(forbidden & controls.keys()),
            "critical_violations": sorted(set(violations + unsafe + orphan_aliases)),
            "population_accuracy_estimated": False}


def peak_memory():
    try:
        from psutil import Process
    except ImportError:
        return None
    return getattr(Process().memory_info(), "peak_wset", None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-archives", action="store_true", help="Rebuild the bounded cache from existing snapshots")
    args = parser.parse_args()
    if args.capture_archives:
        cohort, results, _ = warehouse()
        controls, _ = gsrs_controls()
        capture_archives(cohort, results, controls)
    else:
        evaluate()


if __name__ == "__main__":
    main()
