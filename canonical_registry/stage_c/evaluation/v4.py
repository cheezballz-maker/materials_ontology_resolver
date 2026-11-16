"""Stage C v4 input seals and historical controls for the isolated runner."""

import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
from xml.etree.ElementTree import parse

from canonical_registry.authoritative_lookup.sources import file_digest, read, write
from canonical_registry.chemistry import describe
from identity_comparator import compare
from fixture_registry import registry_digest
from ..captures import inputs
from ..cohort import DATA
from ..fixture import open_fixture, reader
from .restricted_expansion import stats

ROOT = DATA / "v4"
CONTROL_NAMES = {
    "PYRIDOXINE SALICYLATE", "ETHYLCYCLOHEXENE-1-CARBOXYLATE", "TRIDECYL ISONONANOATE",
    "BUTYLENE GLYCOL DIISONONANOATE", "2-TERT-BUTYLHYDROQUINONE METHYL ETHER",
    "CITRIC ACID", "MAGNESIUM SULFATE", "GLUTAMIC ACID", "ALCOHOL DENAT.", "SODIUM CHLORIDE",
    "ISOPROPYL ALCOHOL", "WATER", "AQUA", "GLYCERIN", "ALCOHOL", "HYDROGEN PEROXIDE",
    "ACETONE", "TRIPALMITIN", "PHENYLPARABEN", "SODIUM ACETATE",
}
UNRESOLVED = {
    "PYRIDOXINE SALICYLATE", "ETHYLCYCLOHEXENE-1-CARBOXYLATE", "TRIDECYL ISONONANOATE",
    "BUTYLENE GLYCOL DIISONONANOATE", "2-TERT-BUTYLHYDROQUINONE METHYL ETHER", "CITRIC ACID",
    "MAGNESIUM SULFATE", "GLUTAMIC ACID", "ALCOHOL DENAT.", "SODIUM CHLORIDE",
}
POSITIVE = CONTROL_NAMES - UNRESOLVED - {"SODIUM ACETATE"}

def capture_diagnostics():
    from datetime import datetime

    base = DATA / "restricted_expansion/phase_3_authority"
    output = {}
    for name in ("pubchem_capture", "chebi_capture", "gsrs_capture", "identifier_reference", "reference_capture"):
        path = ROOT / (name + ".json")
        current = read(path)
        old = read(base / path.name) if (base / path.name).exists() else {}
        if name == "gsrs_capture":
            current, old = current["records"], old["records"]
        additional = {k: v for k, v in current.items() if k not in old}
        timestamps = [datetime.fromisoformat(v["retrieved_at"]) for v in additional.values()]
        output[name] = {"retained": len(current) - len(additional), "new": len(additional),
                        "new_outcomes": dict(Counter(v["status"] for v in additional.values())),
                        "receipt_span_seconds": (max(timestamps) - min(timestamps)).total_seconds()}
    return output


def historical_controls(rows, warehouse, root):
    fresh_ids = {r["concept_id"] for r in read(root / "fresh.json")}
    controls = {}
    safety_candidates = {}
    for prior in ("v3", "safety_closure", "restricted_expansion"):
        old, candidates, _ = inputs(DATA / prior)
        if prior == "safety_closure":
            safety_candidates = candidates
        for row in old:
            if row["parent"]["inci"] in CONTROL_NAMES:
                key = row["concept_id"]
                if key not in controls or key in candidates and key not in warehouse:
                    controls[key] = {**row, "group": "historical_control"}
                    if key in candidates:
                        warehouse[key] = candidates[key]
    if {r["parent"]["inci"] for r in controls.values()} != CONTROL_NAMES:
        raise ValueError("Incomplete historical regression controls")
    if set(controls) & fresh_ids:
        raise ValueError("Historical control overlaps the fresh v4 cohort")
    for key in controls.keys() & safety_candidates.keys():
        warehouse[key] = safety_candidates[key]
    return list(controls.values()) + [r for r in rows if r["concept_id"] in fresh_ids], warehouse


def historical_checkpoint_packet():
    """Read the old failed fixture and verify checkpoint, alias and audit bytes."""
    from audit_payload import decode
    from ..compact_history import verify_history as verify_archive

    directory = DATA / "pilot-expansion"
    permit, concepts, metadata = open_fixture(directory)
    metrics = read(directory / "metrics.json")
    assert file_digest(permit.path) == metrics["fixture_database_sha256"]
    assert file_digest(concepts.path) == metrics["chemical_concept_database_sha256"]
    with closing(reader(permit.path)) as db:
        verify_archive(db, metadata["compaction"])
        quarantined = db.execute("SELECT status,substance_id,event_id,result_json FROM stage_c_request "
                                 "WHERE designation='PYRIDOXINE SALICYLATE'").fetchone()
        status, target, event, result = quarantined
        (decision,) = db.execute("SELECT decision_json FROM concept_resolution_event WHERE event_id=?", (event,)).fetchone()
        json.loads(decode(db, decision))
        assert (status, target) == ("RESOLVED_SUBSTANCE", "SUB_00000621")
        assert json.loads(result)["receipt"]["authority_entity"] == "CID:187064"
    return {"old_fixture_sha256": metrics["fixture_database_sha256"], "quarantined_target_preserved": True,
            "compacted_audit_events_verified": metadata["compaction"]["events"]}


def seal(root=ROOT):
    freeze = read(root / "freeze.json")
    inputs(root)
    files = ["freeze.json", "fresh.json", "gsrs_capture.json", "pubchem_capture.json", "chebi_capture.json",
             "provider_queue.json", "identifier_queue.json", "identifier_reference.json", "reference_plan.json"]
    files += ["gsrs_queue.json", "reference_capture.json", "historical_protection.json"]
    files += [str(Path(name).with_suffix(".json")) for name in sorted(freeze["sql"])]
    path = root / "acquisition_freeze.json"
    if path.exists():
        raise FileExistsError(path)
    write(path, {"sha256": {name: file_digest(root / name) for name in files}})


def verify_inputs(root, cache, *, checkpoint_only, controls_only=False):
    for name, expected in read(root / "acquisition_freeze.json")["sha256"].items():
        if file_digest(root / name) != expected:
            raise ValueError(f"Frozen v4 input changed: {name}")
    cache_pin = root / "derived_index_seal.json"
    if checkpoint_only or (cache_pin.exists() and not controls_only):
        pin = read(cache_pin)
        if (str(cache) != pin["path"] or file_digest(cache) != pin["sha256"]
                or pin["acquisition_seal"] != file_digest(root / "acquisition_freeze.json")):
            raise ValueError("Sealed v4 derived index changed")
        if not checkpoint_only:
            raise ValueError("Sealed v4 execution is available for checkpoint replay")


def verify_history(root=ROOT):
    protected = read(root / "historical_protection.json")
    for name, expected in protected.items():
        if file_digest(Path(name)) != expected:
            raise ValueError(f"Historical evidence changed: {name}")
    return len(protected)


def records(directory):
    permit, concepts, _ = open_fixture(directory)
    with closing(reader(permit.path)) as db:
        decisions = [json.loads(raw) for raw, in db.execute("SELECT result_json FROM stage_c_request ORDER BY rowid")]
        aliases = dict(db.execute("SELECT source_key,alias FROM stage_c_exact_alias"))
        snapshot = registry_digest(db)
    return permit.path, concepts.path, decisions, aliases, snapshot


def replay(directory):
    from ..run import run

    before = records(directory)
    original = (directory / "run.json").read_bytes()
    hashes = [file_digest(path) for path in before[:2]]
    if hashes[0] != read(ROOT / "derived_index_seal.json")["registry_fixture_sha256"]:
        raise ValueError("Registry fixture differs from the sealed index inputs")
    try:
        replay_stats = run(directory, v4=True, checkpoint_only=True)
    finally:
        if (directory / "run.json").read_bytes() != original:
            (directory / "run.json").write_bytes(original)
    after = records(directory)
    assert before == after and hashes == [file_digest(path) for path in after[:2]]
    assert replay_stats["checkpoint_replays"] == len(before[2])
    write(directory / "restart_results.json", {
        "checkpoints": replay_stats["checkpoint_replays"], "elapsed_seconds": replay_stats["elapsed_seconds"],
        "fixture_sha256": hashes, "canonical_digest": before[4], "decisions_and_aliases_unchanged": True,
        "derived_index_sha256": read(ROOT / "derived_index_seal.json")["sha256"],
        "protected_historical_paths": verify_history(),
    })


def gate(directory):
    _, _, rows, aliases, _ = records(directory)
    cosing = {r["designation"]: r for r in rows if r["referent"].startswith("CIC_")}
    for name in UNRESOLVED:
        row = cosing[name]
        if row["status"] != "UNRESOLVED" or row["source"] in aliases:
            raise ValueError(f"Unsafe historical association: {name}")
    missing = {name: cosing[name]["eligibility"]["reasons"] for name in POSITIVE
               if cosing[name]["status"] != "RESOLVED_SUBSTANCE"}
    if missing:
        raise ValueError(f"Expected positive controls did not resolve: {missing}")
    pyridoxine = cosing["PYRIDOXINE SALICYLATE"]
    assert "EXACT_FORM_UNSUPPORTED_BY_SOURCE" in pyridoxine["eligibility"]["reasons"]
    assert cosing["WATER"]["target"] == cosing["AQUA"]["target"]
    for name in ("ETHYLCYCLOHEXENE-1-CARBOXYLATE", "2-TERT-BUTYLHYDROQUINONE METHYL ETHER"):
        assert cosing[name]["eligibility"]["source_identity_safety"]["chemical_form"]["assessment"] == "IDENTITY_CONFLICT"
    ipa = cosing["ISOPROPYL ALCOHOL"]
    assert ipa["match"]["status"] == "NO_MATCH_IN_SEARCHED_REGISTRY"
    assert not ipa["match"]["unresolved_possible_candidate_ids"]
    assert any(r.get("full_graph_distinction") for r in ipa["match"]["candidate_results"])
    suite = parse(ROOT / "tests.xml").find("testsuite").attrib
    assert int(suite["tests"]) > 0 and not any(int(suite[k]) for k in ("failures", "errors"))
    manifest = read(directory / "manifest.json")
    assert manifest["v4_controls_only"] and not read(directory / "metrics.json")["integrity_issues"]
    write(ROOT / "phase_1_gate.json", {
        "passed": True, "acquisition_seal": manifest["evidence"]["v4_inputs"], "policies": manifest["policies"],
        "tests_sha256": file_digest(ROOT / "tests.xml"), "protected_historical_paths": verify_history(),
        "control_logic": {name: file_digest(DATA.parent / name)
                          for name in ("source_identity_safety.py", "workflow.py", "v3_authority.py")},
        "cases": {n: {k: row.get(k) for k in ("status", "outcome", "target", "eligibility")} for n, row in cosing.items()},
        "isopropyl_match_proof": ipa["match"], "control_integrity_sha256": file_digest(directory / "metrics.json"),
    })


def cache_seal(directory):
    from ..run import LOCAL_CACHE
    from derived_index import engine_version

    path = LOCAL_CACHE.with_name("stage_c_v4.sqlite")
    manifest = read(directory / "manifest.json")
    run = read(directory / "run.json")
    assert not manifest["v4_controls_only"] and run["checkpoints"] == run["expected_checkpoints"]
    if (ROOT / "derived_index_seal.json").exists():
        raise FileExistsError("The v4 cache is already sealed")
    write(ROOT / "derived_index_seal.json", {
        "path": str(path), "sha256": file_digest(path), "bytes": path.stat().st_size,
        "engine_version": engine_version(), "acquisition_seal": manifest["evidence"]["v4_inputs"],
        "registry_inputs": manifest["pins"], "registry_fixture_sha256": read(directory / "metrics.json")["fixture_database_sha256"],
        "matcher_policy": manifest["policies"]["matcher"], "history_paths_verified": verify_history(),
    })


def review_packets(directory):
    _, _, rows, aliases, _ = records(directory)
    fresh = {r["concept_id"]: r for r in read(ROOT / "fresh.json")}
    plan = {r["referent"]: r for r in read(ROOT / "reference_plan.json")}
    observations = read(ROOT / "reference_capture.json")
    operational = read(ROOT / "identifier_reference.json")
    screened = {r["referent"]: r for r in read(ROOT / "provisional_reference_screen.json")}
    result = []
    for row in rows:
        key = row["referent"]
        if key not in fresh or (key not in plan and row["status"] != "RESOLVED_SUBSTANCE"):
            continue
        original = fresh[key]
        codes = original["queries"]["CAS"]
        cas = codes[0] if len(codes) == 1 else None
        ref = observations.get(cas) or operational.get(cas)
        graph = row["eligibility"]["specificity"]
        structure = None
        if graph and ref and ref.get("inchi"):
            structure = compare(describe(graph["smiles"]), describe(ref["inchi"], "inchi"))["assessment"]
        result.append({
            "referent": key, "designation": row["designation"], "revision": row["revision"],
            "definition": original["parent"]["description"], "identifiers": original["queries"],
            "stratum": original["stratum"], "status": row["status"], "outcome": row["outcome"],
            "target": row.get("target"), "alias": aliases.get(row["source"]), "form": row["eligibility"]["source_identity_safety"],
            "receipt": row["receipt"], "reference": ref, "reference_used_operationally": cas in operational,
            "reference_structure_comparison": structure,
            "provisional_source_review": screened.get(key, {}).get("reference_judgment"),
        })
    disagreements = [r["referent"] for r in result if r["status"] == "RESOLVED_SUBSTANCE" and (
        r["reference_structure_comparison"] == "DISTINCT" or
        r["provisional_source_review"] == "WITHHOLD_SUPPORTED_BY_SOURCE_SCOPE")]
    write(directory / "review_flags.json", {"review_flags": disagreements,
                                          "basis": "Structural discordance or provisional source-scope disagreement"})
    excluded = set(disagreements)
    write(directory / "reviewed_exports.json", {
        "status": "PROVISIONAL_FIXTURE_OUTPUT",
        "excluded_referents": sorted(excluded),
        "mappings": [{"referent": r["referent"], "revision": r["revision"], "target": r["target"],
                      "alias": r["alias"]} for r in result
                     if r["status"] == "RESOLVED_SUBSTANCE" and r["referent"] not in excluded],
    })
    write(directory / "reference_packets.json", result)
    write(directory / "v4_metrics.json", {
        "fresh_status": dict(Counter(r["status"] for r in rows if r["referent"] in fresh)),
        "fresh_outcomes": dict(Counter(r["outcome"] for r in rows if r["referent"] in fresh)),
        "fresh_qualification": dict(Counter(r["eligibility"]["eligibility"] for r in rows if r["referent"] in fresh)),
        "fresh_status_by_stratum": {s: dict(Counter(r["status"] for r in rows if r["referent"] in fresh
                                                   and fresh[r["referent"]]["stratum"] == s))
                                    for s in sorted({r["stratum"] for r in fresh.values()})},
        "fresh_form_assessments": dict(Counter(r["eligibility"]["source_identity_safety"]["chemical_form"]["assessment"]
                                              for r in rows if r["referent"] in fresh)),
        "reference_packets": len(result),
        "reference_structure_results": dict(Counter(str(r["reference_structure_comparison"]) for r in result)),
        "phase_source_scope_reviews": dict(Counter(r["provisional_source_review"] for r in result if r["provisional_source_review"])),
        "acquisition": capture_diagnostics(),
        "performance": {k: stats(r["timings"][k] for r in rows if k in r["timings"])
                        for k in ("elapsed_seconds", "qualification_seconds", "source_identity_safety_seconds",
                                  "canonical_transaction_seconds")},
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seal", "gate", "cache-seal", "review", "replay"))
    parser.add_argument("--run", default="pilot-v4")
    args = parser.parse_args()
    if not args.run.isascii() or not args.run.replace("-", "").isalnum():
        parser.error("Use a simple fixture name")
    if args.action == "seal":
        seal()
    else:
        {"gate": gate, "cache-seal": cache_seal, "review": review_packets, "replay": replay}[args.action](DATA / args.run)
