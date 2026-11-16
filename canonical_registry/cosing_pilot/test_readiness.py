from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
import json
import sqlite3
import subprocess
import sys
from uuid import UUID

import pytest

from .cosing_source import PARENT, observation
from .readiness import register
from .registry import COSMETICS, DomainRegistry, Registration, canonical
from .staged_registry import StagedRegistry


def source(i, **fields):
    return {"inci_id":str(UUID(int=i)), "inci":f"Source {i}", **fields}


def fixture(tmp_path):
    db = StagedRegistry(tmp_path / "readiness.sqlite")
    db.initialize()
    return db


def database_state(db):
    with db.reader() as connection:
        return {
            table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid")]
            for table in ("domain_type","domain_concept","source_revision","source_head","source_review","assessment")
        }


def test_registration_is_chemistry_free(tmp_path):
    database = tmp_path / "independent.sqlite"
    subprocess.run([sys.executable,"-B","-c",f"""
import sys
from uuid import UUID
from canonical_registry.cosing_pilot.readiness import register
from canonical_registry.cosing_pilot.cosing_source import observation
from canonical_registry.cosing_pilot.staged_registry import StagedRegistry
r = StagedRegistry({str(database)!r})
r.initialize()
result = register(r,[observation({{'inci_id':str(UUID(int=1)),'inci':'Original'}})],'one')
assert result['created'] == 1
assert not any(name.split('.')[0] in ('rdkit','providers','resolver') for name in sys.modules)
"""], check=True)


def test_order_insensitive_evidence_and_companion_omission(tmp_path):
    db = fixture(tmp_path)
    base = source(1,cas_nos='["22","11"]', functions=["HUMECTANT","SOLVENT"])
    aliases = [{"inci_alias_id":"a","alias_type":"IUPAC","alias":" exact  text ","source":"test"},
               {"inci_alias_id":"b","alias_type":"SMILES","alias":"O","source":"test"}]
    complete = observation({**base,"alias_count":2,"alias_claims":aliases})
    reordered = observation({**base,"cas_nos":["11","22"],"functions":["SOLVENT","HUMECTANT"],
                             "alias_count":2,"alias_claims":json.dumps(aliases[::-1])})
    assert complete.content_key == reordered.content_key
    assert register(db,[complete],"first")["created"] == 1
    before = database_state(db)
    assert register(db,[reordered],"repeat")["new_revisions"] == 0
    assert register(db,[observation(base)],"partial-companion")["new_revisions"] == 0
    assert database_state(db) == before
    assert register(db,[observation({**base,"alias_count":0})],"explicit-empty")["held"] == 1
    assert db.source_queue()[0]["preferred_label"] == base["inci"]


def test_invalid_or_duplicate_source_records_do_not_allocate(tmp_path):
    db = fixture(tmp_path)
    good = observation(source(1))
    for invalid in ({},source(2,inci_id="malformed"),source(2,inci_id=None),source(2,inci_id=" "+str(UUID(int=2))),
                    source(2,cas_nos={"untyped":2}),source(2,alias_count=1),source(2,alias_count=0,alias_claims={}),
                    source(2,alias_count=1,alias_claims=[{"alias_type":"SMILES"}])):
        with pytest.raises((ValueError,TypeError)):
            observation(invalid)
    with pytest.raises(ValueError,match="same CosIng UUID"):
        observation(source(1),source(2))
    with pytest.raises(ValueError,match="source keys"):
        register(db,[good,good],"duplicate")
    with pytest.raises(ValueError,match="fingerprint"):
        register(db,[replace(good,content_key="a"*64)],"bad-digest")
    with pytest.raises(ValueError,match="snapshot count"):
        register(db,[good],"bad-count",complete_count=2)
    assert db.search() == []
    assert register(db,[good],"valid")["created"] == 1
    assert db.search()[0]["ingredient_concept_id"] == "CIC_00000001"


def test_snapshot_holds_approved_mapping_and_retains_separate_keys(tmp_path):
    db = fixture(tmp_path)
    old = observation(source(1,inci="Original name"))
    missing = observation(source(2,inci="Possibly changed key"))
    register(db,[old,missing],"original",complete_count=2)
    target = {"id":"SUB_00000001","registry_type":"Substance","registry_key":"synthetic-only",
              "snapshot_sha256":"a"*64,"approval_reference":"fixture setup"}
    with db.writer() as connection:
        connection.execute("""UPDATE domain_concept SET canonical_status='RESOLVED_SUBSTANCE',
                           canonical_target_json=? WHERE concept_id='CIC_00000001'""",(canonical(target),))
    revised = observation(source(1,inci="Updated name",cas_nos=["changed"]))
    new_key = observation(source(3,inci=missing.label))
    assert register(db,[revised,new_key],"changed",complete_count=2)["missing"] == 1
    assert len(db.source_queue()) == 3
    old_entry = db.detail("CIC_00000001")
    assert old_entry["preferred_label"] == old.label
    assert old_entry["canonical_target"] == target
    assert old_entry["canonical_status"] == "RESOLVED_SUBSTANCE"
    assert old_entry["current_mapping_applicability"] == "PENDING_SOURCE_REVIEW"
    with pytest.raises(ValueError,match="approved mapping hold"):
        db.review_source("CIC_00000001",revised.content_key,action="adopt",actor="Reviewer",note="Reviewed")
    with pytest.raises(ValueError,match="current observed"):
        db.review_source("CIC_00000001",old.content_key,action="defer",actor="Reviewer",note="Stale")
    db.review_source("CIC_00000001",revised.content_key,action="defer",actor="Reviewer",note="Compare revised claim")
    db.review_source("CIC_00000003",new_key.content_key,action="confirm-separate",actor="Reviewer",note="Separate evidence")
    assert len(db.source_queue()) == 2
    assert register(db,[missing],"reappeared")["new_revisions"] == 0
    queued = {row["concept_id"]:row for row in db.source_queue()}
    assert queued["CIC_00000002"]["continuity_hold"] == queued["CIC_00000002"]["present"] == 1
    with db.writer() as connection, pytest.raises(sqlite3.IntegrityError,match="APPEND_ONLY"):
        connection.execute("DELETE FROM source_review")


def test_checkpoint_manifest_rollback_and_concurrency(tmp_path):
    db = fixture(tmp_path)
    rows = [observation(source(i)) for i in range(1,7)]
    first = register(db,rows,"run",batch_size=2,max_batches=1,complete_count=6)
    assert first["offset"] == 2
    before = database_state(db)

    def interrupted(offset):
        assert offset == 2
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        register(db,rows,"run",batch_size=2,complete_count=6,batch_hook=interrupted)
    assert database_state(db) == before
    with pytest.raises(ValueError,match="different snapshot"):
        register(db,rows[1:],"run",complete_count=5)
    with pytest.raises(sqlite3.IntegrityError):
        register(db,rows,"competitor",complete_count=6)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: register(db,reversed(rows),"run",batch_size=2,complete_count=6),range(2)))
    assert sum(result["created"] for result in results) == 4
    assert all(result["completed"] and result["offset"] == 6 for result in results)
    with db.reader() as connection:
        assert connection.execute("SELECT count(DISTINCT source_reference),count(DISTINCT concept_id) FROM domain_concept").fetchone()[:] == (6,6)
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_additive_pilot_copy_requires_exact_revision_binding(tmp_path):
    row = observation(source(1))
    v1 = DomainRegistry(tmp_path / "original.sqlite")
    v1.ingest([Registration(COSMETICS,row.source_reference,row.label,"a"*64)],pipeline_version="pilot")
    before = sha256(v1.path.read_bytes()).hexdigest()
    v2 = StagedRegistry(tmp_path / "copy.sqlite")
    with pytest.raises(ValueError,match="complete concept/revision"):
        v2.initialize(v1.path,legacy_observations=[row])
    assert not v2.path.exists()
    v2.initialize(v1.path,legacy_observations=[replace(row,legacy_key="a"*64)])
    assert v2.detail("CIC_00000001")["assessment"]["pipeline_version"] == "pilot"
    assert register(v2,[row],"unchanged")["new_revisions"] == 0
    with pytest.raises(ValueError,match="explicit migration"):
        register(StagedRegistry(v1.path),[row],"attempt-v1-write")
    assert sha256(v1.path.read_bytes()).hexdigest() == before


def test_selective_interpretation_caches_per_revision_and_does_not_assign(tmp_path):
    from .staged_assessment import assess

    db = fixture(tmp_path)
    botanical = observation(source(1,inci="QUERCUS SALICINA LEAF EXTRACT",functions=["PERFUMING","FRAGRANCE"]))
    polymer = observation(source(2,inci="POLYQUATERNIUM-62"))
    register(db,[botanical,polymer],"test")
    result = assess(db,"interpret",batch="test",capability="botanical",typed_only=True)
    assert result["counts"] == {"assessed":1,"capability_excluded":1,"screened_and_cached":1}
    assert assess(db,"interpret",source_ids=[polymer.source_reference],typed_only=True)["counts"] == {"cached":1}
    detail = db.detail("CIC_00000001")
    assert detail["canonical_status"] == "NOT_EVALUATED"
    assert {f["reported_function"]:f["qualification"] for f in detail["assessment"]["trace"]["interpretation"]["functions"]} == {
        "PERFUMING":"VOCABULARY_VALIDATED","FRAGRANCE":"LABEL_UNMAPPED"}
    changed = observation(source(1,inci=botanical.label,description="New source definition"))
    register(db,[changed],"delta")
    assert assess(db,"resolve",concept_ids=["CIC_00000001"],typed_only=True)["counts"] == {"source_held_or_payload_unavailable":1}
    assert assess(db,"interpret",batch="delta",typed_only=True,pending=True)["counts"] == {"assessed":1}
    assert db.detail("CIC_00000001")["canonical_status"] == "NOT_EVALUATED"
    db.review_source("CIC_00000001",changed.content_key,action="adopt",actor="Reviewer",note="Source confirmed")
    assert assess(db,"interpret",batch="delta",typed_only=True)["counts"] == {"cached":1}


def test_malformed_semantic_packet_stays_registered_and_is_held(tmp_path):
    from .staged_assessment import assess

    db = fixture(tmp_path)
    malformed = observation(source(1,alias_count=1,alias_claims=[
        {"inci_alias_id":"one","alias_type":"SMILES","alias":" ","source":"test"},
    ]))
    register(db,[malformed,observation(source(2))],"inputs")
    assert assess(db,"interpret",batch="inputs",typed_only=True)["counts"] == {"invalid_source_packet":1,"assessed":1}
    assert assess(db,"interpret",concept_ids=["CIC_00000001"],typed_only=True)["counts"] == {"cached_invalid_source_packet":1}
    assert assess(db,"resolve",concept_ids=["CIC_00000001"],typed_only=True)["counts"] == {"invalid_interpretation_input":1}
    detail = db.detail("CIC_00000001")
    assert detail["assessment"]["summary"]["input_error"] == "INVALID_SOURCE_PACKET"
    assert detail["canonical_status"] == "NOT_EVALUATED"
