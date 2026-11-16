"""Registration, revision, approval, and rollback controls."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import sqlite3

import pytest

from .mapping_preview import MappingPreview
from .registry import COSMETICS, Comparison, DomainRegistry, DomainType, Registration, fingerprint


def source(key, label="Same name", **changes):
    return Registration(COSMETICS, f"fixture.source:{key}", label, fingerprint([key, label]), **changes)


def test_dry_run_then_persistence_are_idempotent(tmp_path):
    path = tmp_path / "pilot.sqlite"
    db = DomainRegistry(path)
    records = [source("b"), source("a", attempted=True)]
    dry = db.ingest(records, pipeline_version="fixture", dry_run=True)
    assert not path.exists()
    actual = db.ingest(records, pipeline_version="fixture")
    assert actual == dry
    assert [r["id"] for r in actual["records"]] == ["CIC_00000001", "CIC_00000002"]
    assert actual["records"][1]["possible_shared_label"]
    assert db.detail("CIC_00000002")["source_revisions"][0]["review_required"] == 1
    before = path.read_bytes()
    replay = db.ingest(list(reversed(records)), pipeline_version="fixture")
    assert not any(r["created"] or r["revision_inserted"] or r["assessment_inserted"] for r in replay["records"])
    assert db.ingest(records, pipeline_version="fixture", dry_run=True) == replay
    assert path.read_bytes() == before
    assert db.search("fixture.source:a")[0]["canonical_status"] == "UNRESOLVED"
    assert db.search("CIC_00000002")[0]["canonical_status"] == "NOT_EVALUATED"


def test_source_rename_stays_held_and_stored_for_review(tmp_path):
    db = DomainRegistry(tmp_path / "pilot.sqlite")
    first = source("a", "old")
    renamed = source("a", "renamed", attempted=True, summary={"condition": "new input examined"})
    db.ingest([first], pipeline_version="fixture")
    row = db.ingest([renamed], pipeline_version="fixture")["records"][0]
    assert row["held"] and not row["created"] and row["revision_inserted"]
    details = db.detail(row["id"])
    assert details["preferred_label"] == "old"
    assert details["canonical_status"] == "NOT_EVALUATED"
    assert details["source_revisions"][-1]["observed_label"] == "renamed"
    assert details["pending_assessments"][0]["summary"] == renamed.summary
    assert not db.ingest([renamed], pipeline_version="fixture")["records"][0]["revision_inserted"]


def test_batch_failure_rolls_back_rows_and_counter(tmp_path):
    db = DomainRegistry(tmp_path / "pilot.sqlite")
    a, b = source("a"), source("b")
    with pytest.raises(sqlite3.IntegrityError):
        db.ingest([a,b], pipeline_version="fixture",
                  comparisons=[Comparison(a.source_reference, b.source_reference, "INVALID", {})])
    assert db.search() == []
    assert db.ingest([b], pipeline_version="fixture")["records"][0]["id"] == "CIC_00000001"


def test_review_is_symmetric_idempotent_and_preserves_both_ids(tmp_path):
    db = DomainRegistry(tmp_path / "pilot.sqlite")
    a, b = source("a"), source("b")
    cmp = Comparison(a.source_reference, b.source_reference, "EQUIVALENT", {"review": "fixture"})
    assert db.ingest([a,b], pipeline_version="fixture", comparisons=[cmp])["comparison_inserts"] == 1
    reverse = replace(cmp, left=cmp.right, right=cmp.left)
    assert db.ingest([b,a], pipeline_version="fixture", comparisons=[reverse])["comparison_inserts"] == 0
    assert len(db.search()) == 2
    assert db.detail("CIC_00000001")["comparisons"][0]["verdict"] == "EQUIVALENT"


def test_concurrent_ingest_and_domain_configuration(tmp_path):
    db = DomainRegistry(tmp_path / "pilot.sqlite")
    db.ingest([], pipeline_version="fixture")
    with ThreadPoolExecutor(max_workers=4) as pool:
        writes = list(pool.map(lambda i: db.ingest([source("same"), source(str(i))],
                                                  pipeline_version="fixture"), range(8)))
    assert len({next(r["id"] for r in w["records"] if r["source_reference"].endswith(":same"))
                for w in writes}) == 1
    assert len(db.search()) == 9
    food = Registration(DomainType("food-ingredient-demo", "FID"), "fixture.food:x", "Example", fingerprint("x"))
    assert db.ingest([food], pipeline_version="fixture")["records"][0]["id"] == "FID_00000001"
    with pytest.raises(ValueError, match="Unique source"):
        db.ingest([food, food], pipeline_version="fixture")
    with db.reader() as conn:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_database_marker_version_and_status_constraints(tmp_path):
    raw = tmp_path / "unrelated.sqlite"
    with sqlite3.connect(raw) as conn:
        conn.execute("CREATE TABLE unrelated(id TEXT)")
    baseline = raw.read_bytes()
    with pytest.raises(PermissionError, match="Expected a domain"):
        DomainRegistry(raw).ingest([source("a")], pipeline_version="fixture")
    assert raw.read_bytes() == baseline
    path = tmp_path / "pilot.sqlite"
    db = DomainRegistry(path)
    db.ingest([source("a")], pipeline_version="fixture")
    with sqlite3.connect(path) as conn:
        for status in ("RESOLVED_SUBSTANCE", "RESOLVED_CHEMICAL_CONCEPT", "UNKNOWN"):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("UPDATE domain_concept SET canonical_status=?", (status,))
        conn.execute("PRAGMA user_version=99")
    with pytest.raises(ValueError, match="explicit migration"):
        db.search()


def test_pinned_targets_verify_existence_type_and_context():
    mapping = MappingPreview(None)
    from canonical_registry.substance_explorer.frozen_sqlite import FrozenSQLite
    from contextlib import closing
    cases = {
        "Substance": "SELECT substance_id FROM substance_identity WHERE identity_status='ACCEPTED' LIMIT 1",
        "ChemicalConcept": "SELECT concept_id FROM concept_alignment WHERE status='ACTIVE' LIMIT 1",
    }
    for kind, query in cases.items():
        with closing(FrozenSQLite(mapping.paths[kind]).connect()) as conn:
            identifier = conn.execute(query).fetchone()[0]
        pinned = {**mapping.identities[kind], "id": identifier}
        assert mapping.verify_target(pinned)
        assert not mapping.verify_target({**pinned, "snapshot_sha256": "0"*64})
        assert not mapping.verify_target({**pinned, "registry_key": "wrong environment"})
        assert not mapping.verify_target({**pinned, "id": "CC_99999999"})
    mapping.verify_snapshots()
