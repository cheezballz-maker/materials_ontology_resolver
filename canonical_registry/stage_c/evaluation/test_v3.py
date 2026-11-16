from dataclasses import replace
import sqlite3

import pytest

from canonical_registry.authoritative_lookup.lookup import SourceReferent
from canonical_registry.identity_sufficiency.contract import Evidence, structure_signature
from ..compact_history import compact_history, verify_history
from ..v3_authority import ROOT, adapt, binding, retained_source_input
from canonical_registry.authoritative_lookup.sources import cosing_input, read


def compound():
    row = {"CID": 702, "IUPACName": "ethanol", "SMILES": "CCO",
           "InChI": "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",
           "InChIKey": "LFQSCWFLJHTTHZ-UHFFFAOYSA-N"}
    return row, {"sha256": "test", "retrieved_at": "test", "url": "https://example.test"}


def test_compound_needs_independent_source_binding():
    row, packet = compound()
    authority, graph = adapt("pubchem", packet, row)
    evidence = Evidence("test", "source:test", "rev", "ethanol", ())
    source = SourceReferent(evidence, "test", ("ethanol",), "", {}, (structure_signature(graph),), True)
    assert binding(source, authority, graph) == "QUALIFIED_PREFERRED_NAME_AND_GRAPH"
    assert binding(replace(source, preferred_name_graph_retained=False), authority, graph).startswith("NO_")
    assert binding(replace(source, evidence=replace(evidence, designation="alcohol")), authority, graph).startswith("AUTHORITY_")
    assert binding(replace(source, identifiers={"CAS": ("a", "b")}), authority, graph).startswith("SOURCE_SCOPE_")
    assert binding(replace(source, evidence=replace(evidence, material_scope="MIXTURE")), authority, graph).startswith("SOURCE_SCOPE_")
    with pytest.raises(ValueError, match="DESCRIPTOR"):
        adapt("pubchem", packet, {**row, "InChIKey": "invalid"})


def test_chebi_class_cannot_qualify():
    _, packet = compound()
    with pytest.raises(ValueError, match="DISCRETE"):
        adapt("chebi", packet, {"chebi_accession": "CHEBI:30879", "is_released": True,
                               "stars": 3, "definition": "Alcohol class", "default_structure": {"is_r_group": True}})


def test_reviewed_source_contradictions_block_admission_and_pin_revision():
    reviews = read(ROOT / "review_holds.json")
    for row in read(ROOT / "fresh.json"):
        if row["concept_id"] not in reviews:
            continue
        review = reviews[row["concept_id"]]
        source = cosing_input(row)
        checked = retained_source_input(row, source, review)
        assert review["reason"] in checked.evidence.holds
        assert checked.evidence.claims[-1].document == review["url"]
        stale = retained_source_input(row, source, {**review, "revision": "older"})
        assert "REVIEW_SCOPE_RECEIPT_STALE" in stale.evidence.holds


def audit_db():
    db = sqlite3.connect(":memory:")
    db.executescript("""CREATE TABLE concept_resolution_event(event_id TEXT PRIMARY KEY,decision_json TEXT);
      CREATE TRIGGER immutable_event_update BEFORE UPDATE ON concept_resolution_event
      BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END;""")
    db.executemany("INSERT INTO concept_resolution_event VALUES(?,?)",
                   [("one", '{"test": "β"}'), ("two", '{"test": "β"}')])
    db.commit()
    return db


def test_compacted_history_roundtrips_and_fails_closed_on_corruption():
    with audit_db() as db:
        proof = compact_history(db)
        assert proof["events"] == 2
        verify_history(db, proof)
        assert db.execute("SELECT count(*) FROM resolution_audit_payload").fetchone() == (1,)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE concept_resolution_event SET decision_json='{}'")
        db.execute("DROP TRIGGER audit_payload_no_update")
        db.execute("UPDATE resolution_audit_payload SET json_bytes=json_bytes+1")
        with pytest.raises(ValueError, match="INVALID_AUDIT_PAYLOAD"):
            verify_history(db, proof)


def test_interrupted_compaction_preserves_original_content(monkeypatch):
    def stop(*args):
        raise KeyboardInterrupt
    with audit_db() as db:
        monkeypatch.setitem(compact_history.__globals__, "decode", stop)
        with pytest.raises(KeyboardInterrupt):
            compact_history(db)
        assert db.execute("SELECT decision_json FROM concept_resolution_event ORDER BY rowid").fetchall() == [
            ('{"test": "β"}',), ('{"test": "β"}',)]
        assert not db.execute("SELECT 1 FROM sqlite_schema WHERE name='resolution_audit_payload'").fetchone()
