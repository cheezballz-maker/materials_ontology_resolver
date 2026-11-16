"""Create fresh, capability-limited clones of the selected registries."""

from contextlib import closing
from dataclasses import asdict
import hashlib
import os
from pathlib import Path
import secrets
import sqlite3
import uuid
from itertools import zip_longest

from canonical_registry.authoritative_lookup.sources import file_digest, read, write
from canonical_registry.chemical_concept_registry.registry import FIXTURES, Registry, fixture_path
from canonical_registry.cosing_pilot.mapping_preview import development_targets
from creation_authorization import CreationPermit, connect_creation
from fixture_registry import ROOT, FixturePermit, registry_digest, validate_path

SCHEMA = """
CREATE TABLE stage_c_fixture(run_id TEXT PRIMARY KEY, pins_json TEXT NOT NULL);
CREATE TABLE stage_c_request(
 source_key TEXT PRIMARY KEY, source_revision TEXT NOT NULL, request_digest TEXT NOT NULL,
 designation TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN
 ('UNRESOLVED','RESOLVED_SUBSTANCE','RESOLVED_CHEMICAL_CONCEPT')),
 substance_id TEXT REFERENCES substance_identity, chemical_concept_id TEXT,
 event_id TEXT REFERENCES concept_resolution_event, mapping_predicate TEXT,
 result_json TEXT NOT NULL CHECK(json_valid(result_json)),
 CHECK((status='RESOLVED_SUBSTANCE' AND substance_id IS NOT NULL AND chemical_concept_id IS NULL
          AND event_id IS NOT NULL AND mapping_predicate='mapsToSubstance')
    OR (status='RESOLVED_CHEMICAL_CONCEPT' AND chemical_concept_id IS NOT NULL AND substance_id IS NULL
          AND mapping_predicate='mapsToChemicalConcept')
    OR (status='UNRESOLVED' AND substance_id IS NULL AND chemical_concept_id IS NULL
          AND mapping_predicate IS NULL)));
CREATE TABLE stage_c_exact_alias(
 source_key TEXT NOT NULL REFERENCES stage_c_request, substance_id TEXT NOT NULL,
 alias TEXT NOT NULL, evidence_digest TEXT NOT NULL,
 PRIMARY KEY(source_key,alias), FOREIGN KEY(substance_id,alias) REFERENCES substance_alias);
CREATE TRIGGER stage_c_request_append_only_update BEFORE UPDATE ON stage_c_request
 BEGIN SELECT RAISE(ABORT,'STAGE_C_REQUEST_APPEND_ONLY'); END;
CREATE TRIGGER stage_c_request_append_only_delete BEFORE DELETE ON stage_c_request
 BEGIN SELECT RAISE(ABORT,'STAGE_C_REQUEST_APPEND_ONLY'); END;
"""


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def reader(path):
    return sqlite3.connect(Path(path).as_uri() + "?mode=ro", uri=True)


def _clone(source, destination, sha):
    if file_digest(source) != sha:
        raise ValueError("SOURCE_SNAPSHOT_CHANGED")
    os.close(os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
    with closing(reader(source)) as origin, closing(sqlite3.connect(destination)) as clone:
        origin.backup(clone)
        if clone.execute("PRAGMA integrity_check").fetchone() != ("ok",) or clone.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("CLONE_INTEGRITY_FAILURE")
        for table, in origin.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            quoted = '"' + table.replace('"', '""') + '"'
            query = "SELECT * FROM " + quoted + " ORDER BY rowid"
            if any(left != right for left, right in zip_longest(origin.execute(query), clone.execute(query))):
                raise ValueError("CLONE_CONTENT_DIFFERS: " + table)
    if file_digest(source) != sha:
        raise ValueError("SOURCE_CHANGED_DURING_CLONE")


def initialize(directory, pins, *, compact=False):
    directory.mkdir(exist_ok=False)
    run_id = uuid.uuid4().hex
    filename = f"stage_c_{run_id}.sqlite"
    substance, concept = validate_path(ROOT / filename), fixture_path(FIXTURES / filename)
    sources = development_targets()
    for kind, target in (("Substance", substance), ("ChemicalConcept", concept)):
        if Path(pins[kind]["path"]) != sources[kind]:
            raise ValueError("SOURCE_SNAPSHOT_PATH_CHANGED")
        _clone(sources[kind], target, pins[kind]["sha256"])
    association_token, creation_token = secrets.token_hex(32), secrets.token_hex(32)
    import json
    compaction = None
    with closing(sqlite3.connect(substance)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        baseline_digest = registry_digest(db)
        counts = {"Substance": db.execute("SELECT count(*) FROM substance_identity").fetchone()[0]}
        fixture_id, = db.execute("SELECT fixture_id FROM fixture_authorization").fetchone()
        if compact:
            from .compact_history import compact_history
            compaction = compact_history(db)
            if registry_digest(db) != baseline_digest:
                raise ValueError("CANONICAL_CONTENT_CHANGED_DURING_COMPACTION")
        db.executescript(SCHEMA)
        db.execute("UPDATE fixture_authorization SET token_hash=?", (_hash(association_token),))
        db.execute("UPDATE creation_authorization SET token_hash=?", (_hash(creation_token),))
        db.execute("INSERT INTO stage_c_fixture VALUES(?,?)", (run_id, json.dumps(pins, sort_keys=True)))
        db.commit()
    with closing(reader(concept)) as db:
        counts["ChemicalConcept"] = db.execute("SELECT count(*) FROM concept_alignment WHERE status='ACTIVE'").fetchone()[0]
    permit = CreationPermit(FixturePermit(substance, fixture_id, association_token), creation_token)
    doc = {"run_id": run_id, "pins": pins, "baseline_digest": baseline_digest, "baseline_counts": counts,
           "compaction": compaction,
           "capability": asdict(permit.association) | {"path": str(substance)}, "creation_token": creation_token,
           "concept": str(concept), "initial_clone_digests": {"Substance": file_digest(substance),
                                                           "ChemicalConcept": file_digest(concept)}}
    pending = directory / "fixture.pending"
    write(pending, doc)
    pending.replace(directory / "fixture.json")
    return open_fixture(directory)


def open_fixture(directory):
    doc = read(directory / "fixture.json")
    name = f"stage_c_{uuid.UUID(hex=doc['run_id']).hex}.sqlite"
    cap = doc["capability"]
    if Path(cap["path"]) != ROOT / name or Path(doc["concept"]) != FIXTURES / name:
        raise PermissionError("STAGE_C_FIXTURE_PATH_MISMATCH")
    permit = CreationPermit(FixturePermit(Path(cap["path"]), cap["fixture_id"], cap["token"]), doc["creation_token"])
    with closing(connect_creation(permit)) as db:
        marker = db.execute("SELECT run_id FROM stage_c_fixture").fetchall()
        if marker != [(doc["run_id"],)]:
            raise PermissionError("STAGE_C_FIXTURE_MARKER_MISMATCH")
    return permit, Registry(doc["concept"]), doc
