"""Verify a completed Stage C run and export its durable, measured outcomes."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import json
from pathlib import Path
from statistics import median
from xml.etree.ElementTree import parse

from rdkit import rdBase
from canonical_registry.authoritative_lookup.sources import file_digest, read, write
from canonical_registry.chemistry import describe
from canonical_registry.identity_sufficiency.contract import digest, structure_signature
from canonical_registry.identity_sufficiency.evaluate import _guards
from audit_payload import decode
from identity_comparator import compare
from ..cohort import DATA
from ..fixture import open_fixture, reader


def verify(directory):
    permit, concepts, fixture = open_fixture(directory)
    run = read(directory / "run.json")
    manifest = read(directory / "manifest.json")
    from ..run import _source_guards_match
    if not _source_guards_match(manifest, v4="v4_inputs" in manifest["evidence"]):
        raise ValueError("Original registry, source or ontology digest changed")
    safety_closure = "safety_closure_freeze" in manifest["evidence"]
    expansion = "expansion_freeze" in manifest["evidence"]
    v4 = "v4_inputs" in manifest["evidence"]
    v5_phase = manifest.get("v5_phase")
    evidence_root = (DATA / "v5" if v5_phase else DATA / "v4" if v4 else DATA / "restricted_expansion" if expansion else DATA / "safety_closure" if safety_closure else DATA / "v3" if "v3_freeze" in manifest["evidence"] else
                     DATA / "v2" if "v2_freeze" in manifest["evidence"] else DATA)
    fresh_ids = {i["concept_id"] for i in read(evidence_root / "fresh.json")}
    v3 = evidence_root == DATA / "v3"
    review_holds = read(evidence_root / "review_holds.json") if v3 else {}
    if v3:
        for name in ("gsrs_capture.json", "pubchem_capture.json", "chebi_capture.json", "provider_queue.json",
                     "review_holds.json"):
            if manifest["evidence"].get(name) != file_digest(evidence_root / name):
                raise ValueError("Frozen authority evidence changed: " + name)
    if safety_closure:
        phase = run.get("expansion_phase", 1)
        reference = (manifest["v5_seal_path"] if v5_phase else "acquisition_freeze.json" if v4 else
                     ("acquisition_freeze.json" if phase == 1 else f"phase_{phase}_freeze.json") if expansion
                     else "reference_judgments.json")
        pin = "v4_inputs" if v4 else "expansion_freeze" if expansion else "blind_reference_plan"
        if manifest["evidence"][pin] != file_digest(evidence_root / reference):
            raise ValueError("Frozen reference judgments changed")
        authority_root = evidence_root / read(evidence_root / reference).get("authority_directory", "") if expansion else evidence_root
        if v5_phase:
            authority_root = (evidence_root / reference).parent
            if Path(reference).name == "retry_seal.json":
                authority_root /= "retry"
            if any(file_digest(evidence_root / p) != sha for p, sha in read(evidence_root / reference).items()):
                raise ValueError("Sealed v5 phase evidence changed")
        for name in ("gsrs_capture.json", "pubchem_capture.json", "chebi_capture.json", "provider_queue.json",
                     "identifier_reference.json", "identifier_queue.json"):
            if manifest["evidence"].get(name) != file_digest(authority_root / name):
                raise ValueError("Frozen safety closure evidence changed: " + name)
    test_file = evidence_root / ("tests.xml" if evidence_root != DATA else "tests_final.xml")
    with closing(reader(permit.path)) as db, closing(reader(concepts.path)) as cc:
        for conn in (db, cc):
            if conn.execute("PRAGMA integrity_check").fetchone() != ("ok",) or conn.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Isolated SQLite integrity check failed")
        if fixture.get("compaction"):
            from ..compact_history import verify_history
            verify_history(db, fixture["compaction"])
        decisions = [json.loads(r[0]) for r in db.execute("SELECT result_json FROM stage_c_request ORDER BY rowid")]
        if len(decisions) != run["expected_checkpoints"]:
            raise ValueError("Incomplete run")
        if v5_phase:
            from .v5 import BOUNDARIES
            start, end = BOUNDARIES[v5_phase - 1:v5_phase + 1]
            expected = {r["concept_id"] for r in read(evidence_root / "fresh.json")[start:end]}
            if {r["referent"] for r in decisions} & fresh_ids != expected:
                raise ValueError("Checkpoint membership differs from the frozen v5 phase")
        if v4 and not v5_phase and not manifest["v4_controls_only"] and {r["referent"] for r in decisions} & fresh_ids != fresh_ids:
            raise ValueError("Missing v4 fresh checkpoints")
        if expansion and run.get("expansion_phase", 1) > 1:
            boundary = read(evidence_root / f"phase_{run['expansion_phase']}_freeze.json")["fresh_limit"]
            expected = {r["concept_id"] for r in read(evidence_root / "fresh.json")[:boundary]}
            if {r["referent"] for r in decisions} & fresh_ids != expected:
                raise ValueError("Checkpoint membership differs from the frozen phase")
        if fixture.get("compaction"):
            for (payload,) in db.execute("SELECT decision_json FROM concept_resolution_event ORDER BY rowid LIMIT -1 OFFSET ?",
                                        (fixture["compaction"]["events"],)):
                json.loads(decode(db, payload))
        mappings = db.execute("""SELECT s.source_key,s.source_revision,s.substance_id,s.event_id,
                    s.mapping_predicate,e.concept_id,e.source_revision_id,r.source_revision,
                    a.substance_id,a.validated_revision_id
            FROM stage_c_request s
            JOIN concept_resolution_event e ON e.event_id=s.event_id
            JOIN source_concept_revision r ON r.revision_id=e.source_revision_id
            JOIN current_exact_association a ON a.concept_id=e.concept_id
            WHERE s.status='RESOLVED_SUBSTANCE' ORDER BY s.source_key""").fetchall()
        by_source = {r[0]: r for r in mappings}
        alias_rows = db.execute("SELECT source_key,substance_id,alias,evidence_digest FROM stage_c_exact_alias").fetchall()
        structure_rows = db.execute("SELECT substance_id,structure_value FROM substance_structure WHERE structure_type='SMILES'").fetchall()
        structures = dict(structure_rows)
        expected_count = fixture["baseline_counts"]["Substance"]
        created = dict(db.execute("SELECT substance_id,event_id FROM substance_creation_record WHERE event_id IN "
                                  "(SELECT event_id FROM stage_c_request)"))
        if len(structures) != expected_count + len(created):
            raise ValueError("New identity count does not reconcile")
        active = {r[0] for r in cc.execute("SELECT concept_id FROM concept_alignment WHERE status='ACTIVE'")}
        partial_mappings = set(cc.execute("SELECT source_system,record_id,concept_id FROM source_mapping"))
        identity_count = db.execute("SELECT count(*) FROM substance_identity").fetchone()[0]
        if identity_count != len(structures) or len(structure_rows) != len(structures):
            raise ValueError("A canonical Substance lacks exactly one SMILES")
    groups = Counter()
    by_source_eligibility = Counter()
    source_reasons = Counter()
    outcomes, eligibilities, pathways = Counter(), Counter(), Counter()
    registry_signature = defaultdict(list)
    authoritative_targets = defaultdict(set)
    resolved = []
    issues = []
    seen_review_holds = set()
    with rdBase.BlockLogs():
        for target, raw in structures.items():
            registry_signature[structure_signature(describe(raw))].append(target)
        for row in decisions:
            system = "GSRS" if row["source"].startswith("mse_dwd.dwd_mse_chemicals_inventory:") else "CosIng"
            groups[system] += 1
            elig = row["eligibility"]
            outcomes[row["outcome"]] += 1
            eligibilities[elig["eligibility"]] += 1
            by_source_eligibility[f"{system}:{elig['eligibility']}"] += 1
            source_reasons.update(elig["reasons"])
            if row["referent"] in review_holds:
                reviewed = review_holds[row["referent"]]
                seen_review_holds.add(row["referent"])
                if (row["status"] != "UNRESOLVED" or row["revision"] != reviewed["revision"] or
                        reviewed["reason"] not in elig["reasons"]):
                    issues.append(["DOCUMENTED_SCOPE_OR_FORM_HOLD_BYPASSED", row["source"]])
            if elig["evidence_pathway"]:
                pathways[elig["evidence_pathway"]] += 1
            receipt = row.get("receipt")
            if safety_closure and manifest.get("safety_enabled"):
                scope = elig.get("source_identity_safety", {})
                if (scope.get("source_revision") != row["revision"] or
                        (row["status"] == "RESOLVED_SUBSTANCE" and
                         (scope.get("scope") != "EXACT_MOLECULAR_REFERENT" or not scope.get("positive_binding") or
                          scope.get("reasons")))):
                    issues.append(["MISSING_OR_INVALID_SOURCE_SCOPE_PROOF", row["source"]])
                if v4 and row["status"] == "RESOLVED_SUBSTANCE" and (
                        scope.get("chemical_form", {}).get("assessment") != "EXACT_FORM_ESTABLISHED"):
                    issues.append(["MISSING_EXACT_FORM_PROOF", row["source"]])
            if receipt and receipt["receipt_sha256"] != digest({k:v for k,v in receipt.items() if k != "receipt_sha256"}):
                issues.append(["RECEIPT_DIGEST", row["source"]])
            if row["status"] == "RESOLVED_CHEMICAL_CONCEPT":
                namespace, _, record = row["source"].partition(":")
                if row["target"] not in active or (namespace, record, row["target"]) not in partial_mappings:
                    issues.append(["ORPHAN_CONCEPT_MAPPING", row["source"]])
            if row["status"] != "RESOLVED_SUBSTANCE":
                continue
            target = row["target"]
            proof = by_source.get(row["source"])
            if not proof or proof[1] != proof[7] or proof[2] != proof[8] or proof[6] != proof[9]:
                issues.append(["ASSOCIATION_REVISION_OR_TARGET_MISMATCH", row["source"]])
            if elig["eligibility"] != "CANDIDATE_READY" or not row["association"]["exact_current"]:
                issues.append(["UNSUPPORTED_RESOLUTION", row["source"]])
            given = describe(elig["specificity"]["smiles"])
            actual = describe(structures[target])
            if compare(given, actual)["assessment"] != "EXACT":
                issues.append(["CHEMICALLY_INCORRECT_TARGET", row["source"]])
            authoritative_targets[structure_signature(given)].add(target)
            resolved.append({"source": row["source"], "revision": row["revision"], "designation": row["designation"],
                             "target": target, "outcome": row["outcome"], "receipt": receipt["receipt_sha256"] if receipt else None})
    added_duplicates = [ids for ids in registry_signature.values() if len(ids) > 1 and set(ids).intersection(created)]
    splits = [sorted(ids) for ids in authoritative_targets.values() if len(ids) > 1]
    for source_key, target, alias, receipt_digest in alias_rows:
        row = next(r for r in decisions if r["source"] == source_key)
        if target != row.get("target") or alias != row["designation"].strip() or (
            not row["receipt"] or row["receipt"]["receipt_sha256"] != receipt_digest
        ):
            issues.append(["UNQUALIFIED_ALIAS", source_key])
    if len(mappings) != len(resolved):
        issues.append(["MAPPING_COUNT_MISMATCH", len(mappings)])
    if seen_review_holds != set(review_holds):
        issues.append(["REVIEW_SCOPE_RECEIPT_NOT_EVALUATED", sorted(set(review_holds) - seen_review_holds)])
    if added_duplicates or splits or issues:
        raise ValueError({"duplicates": added_duplicates, "splits": splits, "integrity_issues": issues})
    proposals = [r["timings"]["canonical_transaction_seconds"] for r in decisions
                 if "canonical_transaction_seconds" in r["timings"]]
    qualifications = [r["timings"]["qualification_seconds"] for r in decisions]
    summary = {
        "groups": dict(groups), "outcomes": dict(outcomes), "eligibility": dict(eligibilities), "pathways": dict(pathways),
        "eligibility_by_source": dict(by_source_eligibility), "qualification_reasons": dict(source_reasons),
        "gsrs_cos_ing_candidate_pairs": sum(r["candidate_total"] for r in decisions
                                          if not r["source"].startswith("mse_dwd.dwd_mse_chemicals_inventory:")),
        "records_with_candidates": sum(bool(r["candidate_total"]) for r in decisions),
        "ambiguous_retrieval": sum(r["candidate_total"] > 1 for r in decisions),
        "cosing_with_candidates": sum(bool(r["candidate_total"]) for r in decisions
                                     if not r["source"].startswith("mse_dwd.dwd_mse_chemicals_inventory:")),
        "cosing_qualified": sum(r["eligibility"]["eligibility"] == "CANDIDATE_READY" for r in decisions
                              if not r["source"].startswith("mse_dwd.dwd_mse_chemicals_inventory:")),
        "fresh_cosing_qualified": sum(r["eligibility"]["eligibility"] == "CANDIDATE_READY" for r in decisions
                                    if r["referent"] in fresh_ids),
        "resolved_substance": len(resolved), "distinct_substances": len({r["target"] for r in resolved}),
        "reused_baseline": len({r["target"] for r in resolved} - set(created)), "created": len(created),
        "chemical_concept_resolutions": sum(r["status"] == "RESOLVED_CHEMICAL_CONCEPT" for r in decisions),
        "aliases_distinct": len({(r[1], r[2]) for r in alias_rows}), "alias_assertions": len(alias_rows),
        "documented_review_holds_verified": len(seen_review_holds),
        "unresolved": sum(r["status"] == "UNRESOLVED" for r in decisions),
        "transaction_count": len(proposals), "transaction_median_seconds": median(proposals) if proposals else None,
        "transaction_total_seconds": sum(proposals), "duplicates_created": len(added_duplicates),
        "qualification_total_seconds": sum(qualifications),
        "detected_splits": len(splits), "integrity_issues": issues, "protected_paths_verified": len(manifest["protected"]) - int(v4),
        "fixture_database_bytes": permit.path.stat().st_size,
        "database_growth_vs_pinned_source_bytes": permit.path.stat().st_size -
        Path(manifest["pins"]["Substance"]["path"]).stat().st_size,
        "fixture_database_sha256": file_digest(permit.path),
        "chemical_concept_database_sha256": file_digest(concepts.path),
        "tests": parse(test_file).getroot().find("testsuite").attrib if test_file.exists() else None,
    }
    write(directory / "resolved.json", resolved)
    write(directory / "alias_associations.json", [
        {"source": key, "target": sid, "alias": alias, "receipt_sha256": receipt}
        for key, sid, alias, receipt in sorted(alias_rows)
    ])
    write(directory / "metrics.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    options = parser.parse_args()
    if not options.run.isascii() or not options.run.replace("-", "").isalnum():
        raise ValueError("Use a simple run name")
    verify(DATA / options.run)
