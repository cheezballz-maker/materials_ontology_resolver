"""Run or resume Stage C from pinned evidence in isolated SQLite fixtures."""

import argparse
from collections import Counter
from contextlib import ExitStack, closing
from pathlib import Path
from time import perf_counter

from rdkit import rdBase
from canonical_registry.authoritative_lookup.sources import cosing_input, gsrs_input, gsrs_controls, file_digest, read, write
from canonical_registry.cosing_pilot.staged_assessment import _bridge
from canonical_registry.identity_sufficiency.contract import Evaluator, digest
from canonical_registry.identity_sufficiency.evaluate import _guards
from .captures import inputs, references
from .cohort import DATA, LOOKUP
from .fixture import initialize, open_fixture, reader
from .workflow import StageC
import derived_index
from creation_transaction import implementation_version
from transactional_association import version as matcher_version
from fixture_registry import registry_digest

LOCAL_CACHE = Path(derived_index.CACHE).with_name("stage_c_derived.sqlite")


def _manifest(freeze, queries):
    core = Path(__file__).resolve().parents[1]
    evidence = [DATA / name for name in ("freeze.json", "fresh.json", "authority_queue.json", "nist_species.json",
                                         "authority_acquisition.json", "gsrs_native.json")]
    evidence += [LOOKUP / "authority_cache.json", LOOKUP / "cohort.json"]
    return {
        "pins": freeze["pins"], "protected": freeze["protected"], "query_receipts": queries,
        "evidence": {str(p.relative_to(core)): file_digest(p) for p in evidence if p.exists()},
        "policies": {"matcher": matcher_version(), "creation": implementation_version(),
                     "admission": file_digest(core / "policy.py"),
                     "qualification": file_digest(core / "identity_sufficiency" / "contract.py"),
                     "authority_lookup": file_digest(core / "authoritative_lookup" / "lookup.py"),
                     "orchestration": digest({p.name: file_digest(p) for p in Path(__file__).parent.glob("*.py")})},
    }


def _source_guards_match(freeze, *, v4):
    observed = _guards()
    expected = freeze["protected"]
    if v4:
        from canonical_registry.authoritative_lookup.protection import DERIVED_CACHE
        # The shared development cache is outside the v4 derivation path.
        # The v4 cache has its own byte seal and evidence/registry provenance.
        shared = str(DERIVED_CACHE)
        observed = {p: d for p, d in observed.items() if p != shared}
        expected = {p: d for p, d in expected.items() if p != shared}
    return observed == expected


def run(directory, *, create=False, limit=None, replay_count=0, v2=False, v3=False, safety_closure=False,
        safety_baseline=False, expansion=False, checkpoint_only=False, expansion_phase=1, v4=False, controls_only=False,
        v5=False):
    begin = perf_counter()
    if v5:
        from .evaluation.v5 import prepare
        v4 = True
        phase = prepare(directory, expansion_phase, create=create, checkpoint_only=checkpoint_only)
    if v4 and (expansion or safety_baseline or (create and checkpoint_only)):
        raise ValueError("Stage C v4 requires its own isolated fixture and safety policy")
    if controls_only and (not v4 or checkpoint_only):
        raise ValueError("Controls-only mode requires a separate v4 execution")
    derived_index.CACHE = (LOCAL_CACHE.with_name("stage_c_v4_controls.sqlite" if controls_only else "stage_c_v4.sqlite") if v4 else
                           LOCAL_CACHE.with_name("stage_c_expansion.sqlite") if expansion else LOCAL_CACHE)
    if v5:
        derived_index.CACHE = phase["cache"]
    safety_closure = safety_closure or expansion or v4
    v3 = v3 or safety_closure
    cohort_directory = (DATA / "v5" if v5 else DATA / "v4" if v4 else DATA / "restricted_expansion" if expansion else DATA / "safety_closure" if safety_closure else
                        DATA / "v3" if v3 else DATA / "v2" if v2 else DATA)
    freeze = read(cohort_directory / "freeze.json")
    if not _source_guards_match(freeze, v4=v4):
        raise ValueError("Protected source state differs from the frozen cohort")
    if expansion:
        evidence_path = cohort_directory / ("acquisition_freeze.json" if expansion_phase == 1 else f"phase_{expansion_phase}_freeze.json")
        evidence = read(evidence_path)
        for name, sha in evidence["sha256"].items():
            if file_digest(cohort_directory / name) != sha:
                raise ValueError("Frozen expansion acquisition changed: " + name)
        fresh_limit = evidence["fresh_limit"]
        fresh_begin = evidence.get("fresh_begin", 0)
        authority_directory = cohort_directory / evidence.get("authority_directory", "")
    else:
        authority_directory = phase["authority"] if v5 else cohort_directory
    if v4 and not v5:
        from .evaluation.v4 import verify_inputs
        verify_inputs(cohort_directory, derived_index.CACHE, checkpoint_only=checkpoint_only, controls_only=controls_only)
    rows, warehouse, queries = inputs(cohort_directory, fresh_limit=phase["end"] if v5 else fresh_limit if expansion else None)
    controls, companions = gsrs_controls()
    authority, extra, rejected = references()
    manifest = _manifest(freeze, queries)
    if v2 or v3:
        from .evaluation.live_records import live_records, verify_controls
        from .evaluation.authority_access import DATA as AUTHORITY_DATA
        capture = AUTHORITY_DATA / "authority_approved.json"
        packet = read(capture)
        fresh_authority, supplemental, failures, diagnostics = live_records(packet)
        verify_controls(packet, fresh_authority, supplemental, diagnostics)
        for accession, records in fresh_authority.items():
            authority[accession] = records + [r for r in authority.get(accession, [])
                                             if r.authority != "NCATS GSRS native"]
        extra += supplemental
        rejected += [{"UNII": r["UNII"], "reason": r["reason"]} for r in failures]
        manifest["evidence"].update(authority_live=file_digest(capture),
                                    v2_freeze=file_digest(cohort_directory / "freeze.json"))
        prior = set(freeze["prior_qualified"])
        controls = [r for r in controls if r["source_id"] in {"059QF0KO0R", "3K9958V90M", "PDC6A3C0OX"}
                    or r["cohort"] == "component"]
        # Preserve earlier held controls and their names before the fresh cohort.
        named = {"SODIUM CHLORIDE", "HYDROGEN PEROXIDE", "CITRIC ACID", "MAGNESIUM SULFATE",
                 "GLUTAMIC ACID", "SODIUM ACETATE", "ALCOHOL DENAT.", "TITANIUM DIOXIDE"}
        rows = [r for r in rows[:380] if r["concept_id"] in prior or r["parent"]["inci"] in named] + rows[380:]
    if v3:
        from .v3_authority import MultiAuthority, retained_source_input
        review_holds = {} if safety_closure else read(cohort_directory / "review_holds.json")
        packet_path = authority_directory / "gsrs_capture.json"
        additional, supplemental, failures, _ = live_records(read(packet_path))
        for accession, records in additional.items():
            authority[accession] = records + [r for r in authority.get(accession, [])
                                              if r.authority != "NCATS GSRS native"]
        extra += supplemental
        rejected += [{"UNII": r["UNII"], "reason": r["reason"]} for r in failures]
        manifest["evidence"].pop("v2_freeze")
        freeze_key = "safety_closure_freeze" if safety_closure else "v3_freeze"
        manifest["evidence"][freeze_key] = file_digest(cohort_directory / "freeze.json")
        names = ["gsrs_capture.json", "pubchem_capture.json", "chebi_capture.json", "provider_queue.json"]
        if safety_closure:
            from .source_identity_safety import SourceIdentitySafety
            operational_refs = read(authority_directory / "identifier_reference.json")
            historical = read(DATA / "v3" / "fresh.json")
            controls_by_id = read(DATA / "v3" / "review_holds.json")
            rows = [r for r in historical if r["concept_id"] in controls_by_id] + rows
            _, historical_warehouse, historical_queries = inputs(DATA / "v3")
            warehouse.update({k: v for k, v in historical_warehouse.items() if k in controls_by_id})
            manifest["evidence"]["historical_controls"] = digest(rows[:len(controls_by_id)])
            manifest["evidence"]["historical_warehouse"] = digest(historical_queries)
            for provider in ("pubchem", "chebi"):
                manifest["evidence"][provider + "_historical"] = file_digest(DATA / "v3" / (provider + "_capture.json"))
            manifest["safety_enabled"] = not safety_baseline
            names.extend(("identifier_reference.json", "identifier_queue.json"))
            if expansion:
                manifest["evidence"]["expansion_freeze"] = file_digest(evidence_path)
                diagnostic = {r["concept_id"]: r for r in read(DATA / "safety_closure" / "fresh.json")
                              if r["parent"]["inci"] in {"ISOPROPYL ALCOHOL", "RETINYL PALMITATE"}}
                _, prior_warehouse, _ = inputs(DATA / "safety_closure")
                warehouse.update({k: v for k, v in prior_warehouse.items() if k in diagnostic})
                fresh_ids = {r["concept_id"] for r in read(cohort_directory / "fresh.json")}
                historical_rows = [r for r in rows if r["concept_id"] not in fresh_ids]
                fresh_rows = [r for r in rows if r["concept_id"] in fresh_ids]
                rows = historical_rows + list(diagnostic.values()) + fresh_rows[:fresh_limit]
                if fresh_begin:
                    rows = fresh_rows[fresh_begin:fresh_limit]
                manifest["evidence"]["diagnostics"] = digest([(r, warehouse.get(k)) for k, r in diagnostic.items()])
            elif v4:
                from .evaluation.v4 import historical_controls
                rows, warehouse = historical_controls(rows, warehouse, cohort_directory)
                manifest["evidence"]["v4_inputs"] = phase["seal"] if v5 else file_digest(cohort_directory / "acquisition_freeze.json")
                manifest["evidence"]["v4_control_rows"] = digest([(r, warehouse.get(r["concept_id"])) for r in rows
                                                                  if r["group"] != "fresh"])
                if controls_only:
                    rows = [r for r in rows if r["group"] != "fresh"]
                manifest["v4_controls_only"] = controls_only
                if v5:
                    development, development_warehouse, _ = inputs(DATA / "v4")
                    stereo = next(r for r in development if r["concept_id"] == "CIC_00006353")
                    warehouse[stereo["concept_id"]] = development_warehouse[stereo["concept_id"]]
                    manifest["evidence"]["v5_stereo_development"] = digest([stereo, warehouse[stereo["concept_id"]]])
                    manifest["v5_phase"] = expansion_phase
                    manifest["v5_seal_path"] = phase["seal_path"]
                    manifest["v5_fresh_end"] = phase["end"]
                    manifest["policies"]["stereo_binding"] = file_digest(Path(__file__).parent / "evaluation/stereo_binding.py")
                    rows = [r for r in rows if r["group"] != "fresh"] + [{**stereo, "group": "historical_control"}] + [
                        r for r in rows if r["group"] == "fresh"
                    ][phase["start"]:phase["end"]]
            else:
                manifest["evidence"]["blind_reference_plan"] = file_digest(cohort_directory / "reference_judgments.json")
        else:
            names.append("review_holds.json")
        for name in names:
            manifest["evidence"][name] = file_digest(authority_directory / name)
    if v4 and not v5 and not controls_only and not checkpoint_only:
        gate = read(cohort_directory / "phase_1_gate.json")
        checked_policies = {k: v for k, v in manifest["policies"].items() if k != "orchestration"}
        gate_policies = {k: v for k, v in gate["policies"].items() if k != "orchestration"}
        if (not gate["passed"] or gate["acquisition_seal"] != manifest["evidence"]["v4_inputs"]
                or gate_policies != checked_policies or gate["control_logic"] != {
                    name: file_digest(Path(__file__).with_name(name)) for name in ("source_identity_safety.py", "workflow.py", "v3_authority.py")}):
            raise ValueError("Stage C v4 safety gate has not passed for this execution")
    if create:
        permit, concepts, fixture = initialize(directory, freeze["pins"], compact=v3)
        write(directory / "manifest.json", manifest)
    else:
        permit, concepts, fixture = open_fixture(directory)
        manifest_path = directory / "manifest.json"
        previous_manifest = read(manifest_path)
        if previous_manifest != manifest:
            if not (expansion and fresh_begin and not checkpoint_only and evidence.get("previous_manifest") == file_digest(manifest_path)
                    and read(directory / "metrics.json")["fixture_database_sha256"] == file_digest(permit.path)):
                raise ValueError("Frozen execution manifest changed")
            write(directory / f"phase_{expansion_phase-1}_manifest.json", previous_manifest)
            write(manifest_path, manifest)
    if expansion and fresh_begin:
        with closing(reader(permit.path)) as db:
            saved_sources = {key for key, in db.execute("SELECT source_key FROM stage_c_request")}
        prior_fresh = [r for r in fresh_rows[:fresh_begin] if r["source_reference"] not in saved_sources]
        rows = prior_fresh + rows
        expected_phase_checkpoints = fresh_limit + len(historical_rows) + len(diagnostic) + len(controls)
    if expansion:
        from canonical_registry.cosing_pilot.benchmark_readiness import peak_rss
        setup_seconds = perf_counter() - begin
        setup_peak = peak_rss()
        initial_fixture_bytes = permit.path.stat().st_size
    work = []
    for row in rows:
        total, found = warehouse.get(row["concept_id"], (0, []))
        group = "A_prior_qualified" if row["concept_id"] in freeze["prior_qualified"] else (
            "B_fresh" if row["group"] == "fresh" and row["stratum"] not in {"forms", "conflict", "broad"} else
            "C_forms" if row["stratum"] == "forms" else
            "D_negative" if row["stratum"] in {"conflict", "broad"} else "prior_replay")
        source = cosing_input(row)
        work.append((group, retained_source_input(row, source, review_holds.get(row["concept_id"])) if v3 else source,
                     found, total, False))
    for row in controls if not (expansion and fresh_begin) else ():
        work.append(("E_GSRS", gsrs_input(row, companions.get(row["chemical_id"], {})),
                     [{**row, "routes": ["ORIGINAL_RECORD:UNII:" + row["source_id"]]}], 1, True))
    group_counts = Counter()
    checkpoint_replays = 0
    if checkpoint_only:
        with closing(reader(permit.path)) as db:
            saved = {key for key, in db.execute("SELECT source_key FROM stage_c_request")}
        if {source.evidence.source_reference for _, source, *_ in work[:limit]} - saved:
            raise ValueError("Missing replay checkpoint")
    with ExitStack() as stack, rdBase.BlockLogs():
        bridge = _bridge(stack)
        evaluator = Evaluator(bridge.official)

        def authority_lookup(existing):
            lookup = MultiAuthority(existing, bridge.opsin, evidence_root=authority_directory)
            if safety_closure:
                # Reuse pinned public records for the historical controls.
                historical_lookup = MultiAuthority(existing, bridge.opsin)
                for current, old in ((lookup.index, historical_lookup.index), (lookup.names, historical_lookup.names)):
                    for key, entries in old.items():
                        current.setdefault(key, []).extend(entries)
                if not safety_baseline:
                    if v5:
                        from .evaluation.stereo_binding import StereoSpeciesBinding
                        lookup = StereoSpeciesBinding(lookup, evaluator, operational_refs, bridge.opsin)
                    return SourceIdentitySafety(lookup, evaluator, operational_refs, form_gate=v4,
                                                name_parser=bridge.opsin if v4 else None)
            return lookup

        engine = StageC(permit, concepts, evaluator, authority,
                        lookup_adapter=authority_lookup if v3 else None,
                        authority_digest=digest(manifest) if v3 else None)
        for index, (group, source, found, total, native) in enumerate(work[:limit], start=1):
            result = engine.process(source, found, total, authority_source=native)
            if checkpoint_only and not result.get("checkpoint_replay"):
                raise ValueError("Missing replay checkpoint")
            checkpoint_replays += bool(result.get("checkpoint_replay"))
            group_counts[(group, result["status"])] += 1
            if result["status"].startswith("RESOLVED") and not result.get("checkpoint_replay"):
                print(source.evidence.designation, result["outcome"], result["target"], flush=True)
            if index % 100 == 0:
                print(f"{index} checkpoints verified", flush=True)
        if replay_count:
            with closing(reader(permit.path)) as db:
                before = registry_digest(db)
            candidates = [v for v in work if v[0] == "A_prior_qualified"][:replay_count]
            for group, source, found, total, native in candidates:
                result = engine.process(source, found, total, authority_source=native, replay=True)
                if not result.get("checkpoint_replay") or result["status"] != "RESOLVED_SUBSTANCE":
                    raise ValueError("Replay did not recover the committed resolution")
            with closing(reader(permit.path)) as db:
                if before != registry_digest(db):
                    raise ValueError("Canonical state changed during revalidation")
    if not _source_guards_match(freeze, v4=v4):
        raise ValueError("Protected state changed during isolated run")
    if v4 and not v5 and checkpoint_only:
        verify_inputs(cohort_directory, derived_index.CACHE, checkpoint_only=True)
    with closing(reader(permit.path)) as db:
        journal_count = db.execute("SELECT count(*) FROM stage_c_request").fetchone()[0]
        if db.execute("PRAGMA integrity_check").fetchone() != ("ok",) or db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Fixture database failed integrity checks")
    stats = {
        "run_id": fixture["run_id"], "elapsed_seconds": perf_counter() - begin,
        "expected_checkpoints": (expected_phase_checkpoints if fresh_begin else len(work[:limit])) if expansion else len(work),
        "checkpoints": journal_count, "checkpoint_replays": checkpoint_replays,
        "canonical_replays": min(replay_count, len(freeze["prior_qualified"])),
        "by_group": {f"{g}:{s}": n for (g, s), n in sorted(group_counts.items())},
        "queries": queries, "archived_supplemental_records": len(extra), "native_rejections": rejected,
        "baseline": fixture["baseline_counts"], "protected_checks": len(freeze["protected"]) - int(v4),
        "compaction": fixture.get("compaction"),
        "adapter_rejections": (getattr(engine.lookup, "lookup", engine.lookup).rejected if v3 else []),
    }
    if safety_closure:
        from canonical_registry.cosing_pilot.benchmark_readiness import peak_rss
        stats["peak_working_set_bytes"] = peak_rss()
    if expansion or v4:
        cache = Path(derived_index.CACHE)
        stats["derived_cache_bytes"] = cache.stat().st_size if cache.exists() else 0
    if expansion:
        stats.update(setup_seconds=setup_seconds, setup_peak_working_set_bytes=setup_peak,
                     initial_fixture_bytes=initial_fixture_bytes, expansion_phase=expansion_phase)
    write(directory / "run.json", stats)
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--replay-count", type=int, default=0)
    parser.add_argument("--v2", action="store_true")
    parser.add_argument("--v3", action="store_true")
    parser.add_argument("--v4", action="store_true")
    parser.add_argument("--v5", action="store_true")
    parser.add_argument("--controls-only", action="store_true")
    parser.add_argument("--safety-closure", action="store_true")
    parser.add_argument("--safety-baseline", action="store_true")
    parser.add_argument("--expansion", action="store_true")
    parser.add_argument("--checkpoint-only", action="store_true")
    parser.add_argument("--expansion-phase", type=int, choices=(1, 2, 3), default=1)
    args = parser.parse_args()
    if not args.run.isascii() or not args.run.replace("-", "").isalnum():
        raise ValueError("Use a simple name for the isolated run")
    if sum((args.v2, args.v3, args.safety_closure, args.expansion, args.v4, args.v5)) > 1 or (args.safety_baseline and not args.safety_closure):
        parser.error("Choose one evidence version")
    result = run(DATA / args.run, create=args.create, limit=args.limit, replay_count=args.replay_count,
                 v2=args.v2, v3=args.v3, safety_closure=args.safety_closure, safety_baseline=args.safety_baseline,
                 expansion=args.expansion, checkpoint_only=args.checkpoint_only, expansion_phase=args.expansion_phase,
                 v4=args.v4, controls_only=args.controls_only, v5=args.v5)
    print({k: v for k, v in result.items() if k not in {"queries", "native_rejections", "adapter_rejections"}})


if __name__ == "__main__":
    main()
