"""Run post-cleanup regression checks without starting a new Stage C expansion."""

import subprocess
import sys

from .hygiene import FIXTURE_DIRS, OUTPUT, REGISTRY, ROOT, SYNTHETIC, save, sha


def main():
    def stage_test_files():
        fixtures = {p for directory in FIXTURE_DIRS for p in directory.glob("stage_c_*.sqlite")}
        return fixtures.union(REGISTRY.glob("enrichment/local/stage_c_test_index_*.sqlite"))

    before = stage_test_files()
    assert not any(p.name in SYNTHETIC for p in before)
    groups = {
        "stage_c": ["stage_c/evaluation"],
        "stage_b_and_authority": [
            "cosing_pilot", "identity_sufficiency/test_contract.py", "authoritative_lookup/test_lookup.py",
        ],
        "matching_and_concepts": [
            "canonical_registry_matching/matching_tests.py", "canonical_registry_matching/test_indexing.py",
            "chemical_concept_registry", "enrichment/test_qualification.py",
        ],
        "creation": ["canonical_substance_creation/safety_tests.py"],
    }
    results = {}
    for name, tests in groups.items():
        if sys.argv[1:] and name not in sys.argv[1:]:
            continue
        args = ["-B", "-m", "canonical_registry.maintenance.verify_hygiene", "pytest", "-p", "no:cacheprovider", "-q",
                "--junitxml", str(OUTPUT / f"{name}.xml"), *(str(REGISTRY / p) for p in tests)]
        results[name] = execute(name, args)
        if name == "stage_c":
            remaining = sorted(str(p) for p in stage_test_files() - before)
            save("test_fixture_teardown.json", {"passed": not remaining, "leftovers": remaining})
            if remaining:
                results["stage_c_fixture_teardown"] = 1
        save(f"regression_{name}_status.json", {name: results[name]})
    if any(results.values()):
        raise SystemExit(1)


def execute(name, args):
    with (OUTPUT / f"{name}.log").open("wb") as log:
        p = subprocess.run([sys.executable, *args], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    print(f"{name}: exit {p.returncode}", flush=True)
    return p.returncode


def pytest_isolated(args):
    # Load the same import bootstrap used by the application before patching its index module.
    from canonical_registry.enrichment import workflow  # noqa: F401
    import derived_index
    import pytest
    from uuid import uuid4

    from canonical_registry.authoritative_lookup.protection import DERIVED_CACHE

    cache = REGISTRY / "enrichment/local" / f"hygiene_test_index_{uuid4().hex}.sqlite"
    shared_before = sha(DERIVED_CACHE)
    original = derived_index.CACHE
    derived_index.CACHE = cache
    import creation_authorization

    created = set()
    create = creation_authorization.create_creation_fixture

    def tracked_create(*positional, **named):
        permit = create(*positional, **named)
        created.add(permit.path)
        return permit

    creation_authorization.create_creation_fixture = tracked_create
    try:
        return pytest.main(args)
    finally:
        creation_authorization.create_creation_fixture = create
        derived_index.CACHE = original
        for path in created:
            path.unlink(missing_ok=True)
        for suffix in ("", "-wal", "-shm", "-journal"):
            cache.with_name(cache.name + suffix).unlink(missing_ok=True)
        if sha(DERIVED_CACHE) != shared_before:
            raise ValueError("Regression suite changed the shared derived index")


def cache_compatible_replay():
    """Run the original checkpoint-only path with a local cache-only exception."""
    from canonical_registry.authoritative_lookup.protection import DERIVED_CACHE
    from canonical_registry.stage_c import run
    import json

    baseline = json.loads((run.DATA / "restricted_expansion/freeze.json").read_bytes())["protected"]
    comparison_path = OUTPUT / "protected_comparison.json"
    comparison = json.loads(comparison_path.read_bytes()) if comparison_path.exists() else None
    guard = run._guards
    cache_key = str(DERIVED_CACHE)
    actual_cache = sha(DERIVED_CACHE)
    if comparison and (not comparison["passed"] or actual_cache != comparison["after"][cache_key]):
        raise ValueError("Derived cache changed since the maintenance comparison")

    def guarded():
        current = guard()
        differences = {key for key in current.keys() | baseline.keys() if current.get(key) != baseline.get(key)}
        if differences != {cache_key} or current[cache_key] != actual_cache:
            raise ValueError("Replay exception applies only to the one stable derived cache")
        return current | {cache_key: baseline[cache_key]}

    run._guards = guarded
    try:
        run.run(run.DATA / "pilot-expansion", expansion=True, checkpoint_only=True, expansion_phase=3)
    finally:
        run._guards = guard


def replay(compatible=False):
    from canonical_registry.stage_c.cohort import DATA
    from canonical_registry.stage_c.evaluation.replay_compare import stable_results
    from canonical_registry.stage_c.fixture import open_fixture, reader
    from contextlib import closing
    import json

    run = DATA / "pilot-expansion"
    permit, concepts, _ = open_fixture(run)
    original = (run / "run.json").read_bytes()
    before = stable_results(run)
    hashes = [sha(p) for p in (permit.path, concepts.path)]
    try:
        if compatible:
            result = execute("cache_compatible_checkpoint_replay",
                             ["-B", "-m", "canonical_registry.maintenance.verify_hygiene", "cache-compatible-child"])
        else:
            result = execute("restricted_checkpoint_replay", ["-B", "-m", "canonical_registry.stage_c.run",
                             "--expansion", "--expansion-phase", "3", "--run", "pilot-expansion", "--checkpoint-only"])
        if result:
            raise ValueError("Checkpoint replay failed")
        stats = json.loads((run / "run.json").read_bytes())
    finally:
        if (run / "run.json").read_bytes() != original:
            (run / "run.json").write_bytes(original)
    assert stats["checkpoint_replays"] == 1200 and stats["checkpoints"] == 2033
    assert before == stable_results(run)
    assert hashes == [sha(p) for p in (permit.path, concepts.path)]
    findings = {r["referent"]: r for r in json.loads((run / "quarantined_findings.json").read_bytes())}
    expected = findings["CIC_00019582"]
    with closing(reader(permit.path)) as db:
        actual, = db.execute("SELECT substance_id FROM stage_c_request WHERE source_key=?",
                             (expected["source_evidence"]["source_reference"],)).fetchone()
    assert actual == expected["target"]
    assert expected["judgment"] == "UNSUPPORTED_EXACT_MAPPING_AND_ALIAS"
    assert findings["CIC_00019455"]["judgment"] == "REVIEW_HISTORICAL_SCOPE_CONFLICT"
    save("restricted_replay_status.json", {
        "passed": True, "checkpoints_recovered": 1200, "total_preserved": 2033,
        "both_fixture_digests_unchanged": True, "substance_sha256": hashes[0],
        "chemical_concept_sha256": hashes[1], "elapsed_seconds": stats["elapsed_seconds"],
        "pyridoxine_quarantine_preserved": True, "tridecyl_review_preserved": True,
        "frozen_derived_cache_digest_waived_in_this_test": compatible,
    })


if __name__ == "__main__":
    if sys.argv[1:] == ["replay"]:
        replay()
    elif sys.argv[1:] == ["cache-compatible-replay"]:
        replay(compatible=True)
    elif sys.argv[1:] == ["cache-compatible-child"]:
        cache_compatible_replay()
    elif sys.argv[1:2] == ["pytest"]:
        raise SystemExit(pytest_isolated(sys.argv[2:]))
    else:
        main()
