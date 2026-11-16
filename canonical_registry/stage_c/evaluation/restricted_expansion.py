"""Freeze bounded acquisition and summarize the verified expansion checkpoints."""

import argparse
from collections import Counter
from contextlib import closing
import json
from math import ceil
from statistics import median

from canonical_registry.authoritative_lookup.sources import file_digest, read, write
from canonical_registry.chemistry import describe
from identity_comparator import compare
from ..captures import inputs
from ..cohort import DATA
from ..fixture import open_fixture, reader

ROOT = DATA / "restricted_expansion"


def seal(fresh_limit, phase=1, run=None):
    path = ROOT / ("acquisition_freeze.json" if phase == 1 else f"phase_{phase}_freeze.json")
    if path.exists():
        raise FileExistsError(path)
    inputs(ROOT, fresh_limit=fresh_limit)
    names = ["gsrs_capture.json", "gsrs_queue.json", "pubchem_capture.json", "chebi_capture.json",
             "provider_queue.json", "identifier_reference.json", "identifier_queue.json", "reference_plan.json",
             "reference_capture.json"]
    names.extend(f"lookup_{i:02}.json" for i in range(ceil(fresh_limit / 60)))
    batch = {"fresh_limit": fresh_limit, "sha256": {name: file_digest(ROOT / name) for name in names}}
    authority = ROOT / f"phase_{phase}_authority"
    if authority.is_dir():
        batch["authority_directory"] = authority.name
        for name in ("gsrs_capture.json", "gsrs_queue.json", "pubchem_capture.json", "chebi_capture.json",
                     "provider_queue.json", "identifier_reference.json", "identifier_queue.json"):
            relative = f"{authority.name}/{name}"
            batch["sha256"][relative] = file_digest(ROOT / relative)
    if phase > 1:
        prior = read(run / "run.json")
        if prior.get("expansion_phase") != phase-1:
            raise ValueError("Previous phase has not finished")
        batch.update(fresh_begin=sum(read(ROOT / "freeze.json")["phase_sizes"][:phase-1]),
                     previous_manifest=file_digest(run / "manifest.json"))
    write(path, batch)


def stats(values):
    ordered = sorted(values)
    return {"count": len(ordered), "median": median(ordered) if ordered else None,
            "p95": ordered[ceil(.95 * len(ordered))-1] if ordered else None, "sum": sum(ordered)}


def summarize(run):
    permit, _, fixture = open_fixture(run)
    fresh = {r["concept_id"]: r for r in read(ROOT / "fresh.json")}
    plan = {r["referent"]: r for r in read(ROOT / "reference_plan.json")}
    sources = read(ROOT / "reference_capture.json")
    if (run / "supplemental_reference_capture.json").exists():
        sources.update(read(run / "supplemental_reference_capture.json"))
    operational = read(ROOT / "identifier_reference.json")
    run_stats = read(run / "run.json")
    phase_reference = ROOT / f"phase_{run_stats['expansion_phase']}_authority" / "identifier_reference.json"
    if phase_reference.is_file():
        operational.update(read(phase_reference))
    with closing(reader(permit.path)) as db:
        decisions = {r["referent"]: r for (raw,) in db.execute("SELECT result_json FROM stage_c_request")
                     for r in [json.loads(raw)]}
        aliases = dict(db.execute("SELECT source_key,alias FROM stage_c_exact_alias"))
        compressed = db.execute("SELECT count(*),sum(length(compressed)) FROM resolution_audit_payload").fetchone()
        targets = dict(db.execute("SELECT substance_id,structure_value FROM substance_structure WHERE structure_type='SMILES'"))
    observed = {key: row for key, row in decisions.items() if key in fresh}
    selected = {key for key in plan if key in observed} | {key for key, row in observed.items() if row["status"] == "RESOLVED_SUBSTANCE"}
    review = []
    for key in sorted(selected):
        row = observed[key]
        parent = fresh[key]["parent"]
        cas = fresh[key]["queries"]["CAS"]
        ref = sources.get(cas[0], {}) if len(cas) == 1 else {}
        captured = ref.get("status") == "STRUCTURAL_REFERENCE"
        scope = row["eligibility"]["source_identity_safety"]
        target = row.get("target")
        external = "UNAVAILABLE"
        if captured:
            external = "REFERENCE_FOR_UNRESOLVED" if not target else (
                "STANDARD_KEY_AGREES" if row["eligibility"]["specificity"]["inchikey"] == ref["inchikey"] else "STANDARD_KEY_DIFFERS")
        source_scope = "SOURCE_SCOPE_REVIEW_REQUIRED"
        if parent["description"] and any(
            word in parent["description"].lower() for word in (" is the extract ", " is an extract ", " is the volatile oil ", " is a copolymer ")
        ):
            source_scope = "PROVISIONAL_WITHHOLD_FROM_SOURCE_DEFINITION"
        review.append({"referent": key, "revision": row["revision"], "designation": row["designation"],
                       "source_definition": parent["description"], "identifiers": fresh[key]["queries"],
                       "status": row["status"], "target": target, "graph": targets.get(target), "authority": row.get("receipt"),
                       "source_scope": scope, "alias": aliases.get(row["source"]), "reference": ref,
                       "reference_overlaps_operational_capture": bool(cas and cas[0] in operational),
                       "structural_comparison": external, "provisional_scope_assessment": source_scope,
                       "whole_referent_independently_adjudicated": False})
    diagnostic = {}
    for row in decisions.values():
        name = row["designation"]
        if row["referent"] in fresh or name not in {"ISOPROPYL ALCOHOL", "RETINYL PALMITATE", "SODIUM CHLORIDE"}:
            continue
        match = row.get("match") or {}
        possible = match.get("unresolved_possible_candidate_ids", [])
        graph = row["eligibility"].get("specificity")
        comparison = {sid: compare(describe(graph["smiles"]), describe(targets[sid])) for sid in possible if graph}
        diagnostic[name] = {"referent": row["referent"], "status": row["status"], "eligibility": row["eligibility"],
                            "admission": row.get("admission"), "uniqueness": match.get("uniqueness"),
                            "possible_duplicates": possible, "direct_comparison": comparison}
    write(run / "reference_packets.json", review)
    write(run / "diagnostic_controls.json", diagnostic)
    write(run / "expansion_metrics.json", {
        "fresh": dict(Counter(r["status"] for r in observed.values())),
        "fresh_by_stratum": {s: dict(Counter(r["status"] for k, r in observed.items() if fresh[k]["stratum"] == s))
                             for s in sorted({fresh[k]["stratum"] for k in observed})},
        "fresh_warehouse_candidates": sum(bool(r["candidate_total"]) for r in observed.values()),
        "scope_reasons": dict(Counter(reason for r in decisions.values() for reason in r["eligibility"]["source_identity_safety"]["reasons"])),
        "primary_authorities": dict(Counter(r["receipt"]["authority"] for r in decisions.values() if r["status"] == "RESOLVED_SUBSTANCE")),
        "performance": {k: stats(r["timings"][k] for r in decisions.values() if k in r["timings"])
                        for k in ("qualification_seconds", "source_identity_safety_seconds", "canonical_transaction_seconds", "elapsed_seconds")},
        "compressed_audit_growth_bytes": compressed[1] - fixture["compaction"]["compressed_payload_bytes"],
        "fixture_growth_bytes": permit.path.stat().st_size - run_stats["initial_fixture_bytes"],
        "compressed_audit_payloads": compressed[0], "reference_packets": len(review),
        "reference_comparisons": dict(Counter(r["structural_comparison"] for r in review)),
        "disagreements": [{k: r[k] for k in ("referent", "designation", "target", "reference", "reference_overlaps_operational_capture")}
                          for r in review if r["structural_comparison"] == "STANDARD_KEY_DIFFERS"],
        "provisional_scope_assessments": dict(Counter(r["provisional_scope_assessment"] for r in review)),
        "scope_contradictions": [r["referent"] for r in review if r["status"] == "RESOLVED_SUBSTANCE"
                                 and r["provisional_scope_assessment"] == "PROVISIONAL_WITHHOLD_FROM_SOURCE_DEFINITION"],
        "independent_structure_comparisons": dict(Counter(r["structural_comparison"] for r in review
                                                       if not r["reference_overlaps_operational_capture"])),
    })


def additional_reference_queue(run):
    permit, _, _ = open_fixture(run)
    with closing(reader(permit.path)) as db:
        targets = {json.loads(raw)["referent"] for (raw,) in db.execute(
            "SELECT result_json FROM stage_c_request WHERE status='RESOLVED_SUBSTANCE'")}
    earlier = read(ROOT / "reference_capture.json")
    seen = set(earlier)
    queue = []
    for row in read(ROOT / "fresh.json"):
        cas = row["queries"]["CAS"]
        if row["concept_id"] in targets and len(cas) == 1 and cas[0] not in seen:
            if not all(part.isascii() and part.isdecimal() for part in cas[0].split("-")):
                continue
            queue.append({"cas": cas[0]})
            seen.add(cas[0])
    write(run / "supplemental_reference_queue.json", queue)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seal", "summarize", "reference-queue"))
    parser.add_argument("--run", default="pilot-expansion")
    parser.add_argument("--fresh-limit", type=int, default=200)
    parser.add_argument("--phase", type=int, choices=(1, 2, 3), default=1)
    args = parser.parse_args()
    if not args.run.isascii() or not args.run.replace("-", "").isalnum():
        parser.error("Use a simple run name")
    if args.action == "seal":
        seal(args.fresh_limit, args.phase, DATA / args.run)
    elif args.action == "reference-queue":
        additional_reference_queue(DATA / args.run)
    else:
        summarize(DATA / args.run)
