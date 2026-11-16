"""Disposable, transactionally serialized ChemicalConcept registry."""
import hashlib
import json
import os
import re
import sqlite3
import unicodedata
from contextlib import closing
from pathlib import Path

from constraints import (BROADER, EQUIVALENT, NARROWER, UNRESOLVED, ProposalError,
                         compare, contains_substance, validate)

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
BASE = ROOT.parent
SOURCES = {
    (BASE / "output/registry.sqlite").resolve(): "57d0d8143c22c89e0a8dcbdb66f06b7c9e61b4081ec0432d739cf9d26cccb15e",
    (BASE / "warehouse_admission_consolidation/output/normalized_pilot.sqlite").resolve():
        "6f99fba4c0874aa5db6f3bde0ac780bc706aa05f59466868b92959c3406d57d4",
}
REVIEWED_MAPPINGS = {
    ("SYNTHETIC_COSMETICS", "ingredient", "iron-oxides"): "iron_oxides",
    ("SYNTHETIC_A", "chemical", "iron-oxide"): "iron_oxides",
    ("SYNTHETIC_B", "chemical", "metal-oxide"): "metal_oxides",
    ("SYNTHETIC_C", "chemical", "iron-oxides"): "iron_oxides",
}
SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE fixture_marker (marker TEXT PRIMARY KEY CHECK(marker='CHEMICAL_CONCEPT_POC_V1'));
INSERT INTO fixture_marker VALUES ('CHEMICAL_CONCEPT_POC_V1');
CREATE TABLE concept (concept_id TEXT PRIMARY KEY, preferred_label TEXT NOT NULL,
  definition_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE label (concept_id TEXT NOT NULL REFERENCES concept(concept_id),
  label TEXT NOT NULL, normalized_label TEXT NOT NULL, UNIQUE(concept_id,label));
CREATE INDEX label_lookup ON label(normalized_label);
CREATE TABLE revision (concept_id TEXT NOT NULL REFERENCES concept(concept_id),
  revision INTEGER NOT NULL, snapshot_json TEXT NOT NULL,
  recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(concept_id,revision));
CREATE TABLE event (event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL, concept_id TEXT REFERENCES concept(concept_id),
  evidence_json TEXT NOT NULL, recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE request (request_key TEXT PRIMARY KEY, payload_sha256 TEXT NOT NULL, result_json TEXT NOT NULL);
CREATE TABLE narrower (broader_id TEXT NOT NULL REFERENCES concept(concept_id),
  narrower_id TEXT NOT NULL REFERENCES concept(concept_id),
  CHECK(broader_id<>narrower_id), PRIMARY KEY(broader_id,narrower_id));
CREATE TABLE membership (concept_id TEXT NOT NULL REFERENCES concept(concept_id),
  substance_id TEXT NOT NULL, registry_sha256 TEXT NOT NULL, evidence_json TEXT NOT NULL,
  PRIMARY KEY(concept_id,substance_id));
CREATE TABLE source_mapping (source_system TEXT NOT NULL, record_type TEXT NOT NULL,
  record_id TEXT NOT NULL, referent_key TEXT NOT NULL, concept_id TEXT NOT NULL REFERENCES concept(concept_id),
  evidence_json TEXT NOT NULL, PRIMARY KEY(source_system,record_type,record_id,referent_key));
CREATE TRIGGER concept_no_update BEFORE UPDATE ON concept BEGIN SELECT RAISE(ABORT,'CONCEPT_IMMUTABLE'); END;
CREATE TRIGGER concept_no_delete BEFORE DELETE ON concept BEGIN SELECT RAISE(ABORT,'CONCEPT_IMMUTABLE'); END;
CREATE TRIGGER revision_no_update BEFORE UPDATE ON revision BEGIN SELECT RAISE(ABORT,'REVISION_APPEND_ONLY'); END;
CREATE TRIGGER revision_no_delete BEFORE DELETE ON revision BEGIN SELECT RAISE(ABORT,'REVISION_APPEND_ONLY'); END;
CREATE TRIGGER event_no_update BEFORE UPDATE ON event BEGIN SELECT RAISE(ABORT,'EVENT_APPEND_ONLY'); END;
CREATE TRIGGER event_no_delete BEFORE DELETE ON event BEGIN SELECT RAISE(ABORT,'EVENT_APPEND_ONLY'); END;
"""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def normalize_label(value):
    if not isinstance(value, str) or not value.strip():
        raise ProposalError("LABEL_REQUIRED")
    return " ".join(unicodedata.normalize("NFC", value).split()).casefold()


def fixture_path(path):
    FIXTURES.mkdir(exist_ok=True)
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
            raise PermissionError("LINK_PATH_REJECTED")
    path = path.resolve()
    if path.parent != FIXTURES.resolve() or not re.fullmatch(r"[a-zA-Z0-9_-]+\.sqlite", path.name):
        raise PermissionError("ONLY_POC_FIXTURE_PATHS_ALLOWED")
    if path.exists() and (path.stat().st_nlink != 1 or any(os.path.samefile(path, p) for p in SOURCES)):
        raise PermissionError("SHARED_FILE_REJECTED")
    return path


def initialize(path):
    path = fixture_path(path)
    if path.exists():
        raise FileExistsError(path)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    with closing(sqlite3.connect(path)) as db:
        db.executescript(SCHEMA)
    from canonical_registry.chemical_concept_registry.identity_contract import migrate
    with closing(sqlite3.connect(path, isolation_level=None)) as db:
        migrate(db)
    return Registry(path)


class Registry:
    def __init__(self, path):
        self.path = fixture_path(path)
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        with closing(self.connect()) as db:
            if db.execute("SELECT marker FROM fixture_marker").fetchall() != [("CHEMICAL_CONCEPT_POC_V1",)]:
                raise PermissionError("FIXTURE_MARKER_REQUIRED")

    def connect(self):
        path = fixture_path(self.path)
        db = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=30, isolation_level=None)
        try:
            db.execute("PRAGMA foreign_keys=ON")
            if db.execute("SELECT marker FROM fixture_marker").fetchall() != [("CHEMICAL_CONCEPT_POC_V1",)]:
                raise PermissionError("FIXTURE_MARKER_REQUIRED")
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='identity_model_version'").fetchone():
                raise ValueError("IDENTITY_MODEL_MIGRATION_REQUIRED")
            row = db.execute("SELECT version FROM identity_model_version").fetchone()
            if row != (2,):
                raise ValueError("IDENTITY_MODEL_MIGRATION_REQUIRED")
            return db
        except Exception:
            db.close()
            raise

    def propose(self, proposal):
        definition = validate(proposal)
        with closing(self.connect()) as db:
            rows = db.execute("SELECT c.concept_id,c.definition_json FROM concept c JOIN concept_alignment a USING(concept_id) WHERE a.status='ACTIVE' ORDER BY c.concept_id").fetchall()
        compared = [(sid, compare(definition, json.loads(raw))) for sid, raw in rows]
        exact = [sid for sid, outcome in compared if outcome == EQUIVALENT]
        unknown = [sid for sid, outcome in compared if outcome == UNRESOLVED]
        return {"definition": definition, "comparisons": compared, "matches": exact, "unresolved": unknown}

    def create_or_reuse(self, proposal, label, request_key, *, fail_after_insert=False,
                        evidence=None, source_key=None):
        normalized = normalize_label(label)
        if not isinstance(request_key, str) or not request_key:
            raise ValueError("IDEMPOTENCY_KEY_REQUIRED")
        definition = validate(proposal)
        from canonical_registry.chemical_concept_registry.identity_contract import validate_label, preferred_label
        validate_label(label, definition)
        payload_data = {"proposal": proposal, "label": label}
        if evidence is not None:
            payload_data["evidence"] = evidence
        if source_key is not None:
            if (len(source_key) != 4 or
                    not all(isinstance(value, str) and value.strip() for value in source_key)):
                raise ValueError("INVALID_SOURCE_REFERENT")
            payload_data["source_key"] = source_key
        payload = hashlib.sha256(canonical(payload_data).encode()).hexdigest()
        event_evidence = {"proposal": proposal, "request_key": request_key, "source_evidence": evidence}
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT payload_sha256,result_json FROM request WHERE request_key=?",
                                  (request_key,)).fetchone()
            if previous:
                if previous[0] != payload:
                    raise ValueError("IDEMPOTENCY_CONFLICT")
                result = json.loads(previous[1])
                return {**result, "outcome": "IDEMPOTENT_REPLAY"}
            rows = db.execute("SELECT c.concept_id,c.definition_json FROM concept c JOIN concept_alignment a USING(concept_id) WHERE a.status='ACTIVE' ORDER BY c.concept_id").fetchall()
            compared = [(sid, compare(definition, json.loads(raw))) for sid, raw in rows]
            matches = [sid for sid, result in compared if result == EQUIVALENT]
            unknown = [sid for sid, result in compared if result == UNRESOLVED]
            if source_key is not None:
                mapped = db.execute(
                    "SELECT concept_id FROM source_mapping WHERE source_system=? AND record_type=? "
                    "AND record_id=? AND referent_key=?", source_key,
                ).fetchone()
                if mapped and (matches != [mapped[0]] or unknown):
                    raise ValueError("SOURCE_CONCEPT_REASSIGNMENT_REQUIRES_REVIEW")
            if len(matches) > 1 or unknown:
                result = {"outcome": "WITHHELD", "matches": matches, "unresolved": unknown,
                          "comparisons": len(compared)}
                db.execute("INSERT INTO event(event_type,evidence_json) VALUES('WITHHELD',?)",
                           (canonical({**event_evidence, "comparisons": compared}),))
            else:
                if matches:
                    sid, outcome = matches[0], "REUSED"
                else:
                    # BEGIN IMMEDIATE serializes allocation and the complete comparison.
                    index = db.execute("SELECT COALESCE(MAX(CAST(SUBSTR(concept_id,4) AS INTEGER)),0)+1 FROM concept").fetchone()[0]
                    sid, outcome = f"CC_{index:08d}", "CREATED"
                    db.execute("INSERT INTO concept(concept_id,preferred_label,definition_json) VALUES(?,?,?)",
                               (sid, preferred_label(definition), canonical(definition)))
                    db.execute("INSERT INTO concept_alignment VALUES(?, 'ACTIVE', ?, 'VALIDATED_MOLECULAR_DEFINITION')",
                               (sid, preferred_label(definition)))
                    db.execute("INSERT INTO revision VALUES(?,?,?,CURRENT_TIMESTAMP)",
                               (sid, 1, canonical({"definition": definition, "preferred_label": label})))
                db.execute("INSERT OR IGNORE INTO validated_concept_label VALUES(?,?)", (sid, label))
                inserted = db.execute("INSERT OR IGNORE INTO label VALUES(?,?,?)", (sid, label, normalized)).rowcount
                if inserted and outcome == "REUSED":
                    revision = db.execute("SELECT MAX(revision)+1 FROM revision WHERE concept_id=?", (sid,)).fetchone()[0]
                    labels = [x[0] for x in db.execute("SELECT label FROM validated_concept_label WHERE concept_id=? ORDER BY label", (sid,))]
                    db.execute("INSERT INTO revision VALUES(?,?,?,CURRENT_TIMESTAMP)",
                               (sid, revision, canonical({"definition": definition, "labels": labels})))
                db.execute("INSERT INTO event(event_type,concept_id,evidence_json) VALUES(?,?,?)",
                           (outcome, sid, canonical({**event_evidence, "comparisons": compared})))
                if source_key is not None and not mapped:
                    db.execute("INSERT INTO source_mapping VALUES(?,?,?,?,?,?)",
                               (*source_key, sid, canonical(event_evidence)))
                result = {"outcome": outcome, "concept_id": sid, "comparisons": len(compared)}
            if fail_after_insert:
                raise RuntimeError("INJECTED_TRANSACTION_FAILURE")
            db.execute("INSERT INTO request VALUES(?,?,?)", (request_key, payload, canonical(result)))
            db.execute("COMMIT")
            return result

    def get(self, concept_id):
        with closing(self.connect()) as db:
            row = db.execute("SELECT a.display_label,c.definition_json FROM concept c JOIN concept_alignment a USING(concept_id) WHERE c.concept_id=? AND a.status='ACTIVE'",
                             (concept_id,)).fetchone()
            if not row:
                raise KeyError(concept_id)
            labels = [x[0] for x in db.execute("SELECT label FROM validated_concept_label WHERE concept_id=? ORDER BY label", (concept_id,))]
            definition = json.loads(row[1])
            from canonical_registry.chemical_concept_registry.identity_contract import identity_record
            return {"concept_id": concept_id, "preferred_label": row[0],
                    "definition": definition, "labels": labels,
                    "identity": identity_record(concept_id, "ChemicalConcept", row[0],
                        graph=definition["smiles"], definition=definition, aliases=labels,
                        validation="VALIDATED_PARTIAL_MOLECULAR_IDENTITY")}

    def search(self, label):
        with closing(self.connect()) as db:
            return [sid for sid, in db.execute("SELECT l.concept_id FROM label l JOIN concept_alignment a USING(concept_id) WHERE normalized_label=? AND a.status='ACTIVE' ORDER BY l.concept_id",
                                               (normalize_label(label),))]

    def compare_concepts(self, left_id, right_id):
        return compare(self.get(left_id)["definition"], self.get(right_id)["definition"])

    def relate(self, broader, narrower):
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            a, b = self.get(broader)["definition"], self.get(narrower)["definition"]
            if compare(a, b) != BROADER:
                raise ValueError("CONTAINMENT_NOT_ESTABLISHED")
            cycle = db.execute("""WITH RECURSIVE descendants(id) AS (
                SELECT narrower_id FROM narrower WHERE broader_id=?
                UNION SELECT n.narrower_id FROM narrower n JOIN descendants d ON n.broader_id=d.id
                ) SELECT 1 FROM descendants WHERE id=?""", (narrower, broader)).fetchone()
            if cycle or broader == narrower:
                raise ValueError("HIERARCHY_CYCLE")
            db.execute("INSERT OR IGNORE INTO narrower VALUES(?,?)", (broader, narrower))
            db.execute("INSERT INTO event(event_type,concept_id,evidence_json) VALUES('HIERARCHY',?,?)",
                       (broader, canonical({"narrower": narrower, "comparison": BROADER})))
            db.execute("COMMIT")

    def relationships(self, concept_id):
        self.get(concept_id)
        with closing(self.connect()) as db:
            return {"narrower": [x[0] for x in db.execute("SELECT narrower_id FROM narrower JOIN concept_alignment a ON a.concept_id=narrower_id WHERE broader_id=? AND a.status='ACTIVE' ORDER BY 1", (concept_id,))],
                    "broader": [x[0] for x in db.execute("SELECT broader_id FROM narrower JOIN concept_alignment a ON a.concept_id=broader_id WHERE narrower_id=? AND a.status='ACTIVE' ORDER BY 1", (concept_id,))],
                    "members": [x[0] for x in db.execute("SELECT substance_id FROM membership WHERE concept_id=? ORDER BY 1", (concept_id,))]}

    def map_source(self, source_system, record_type, record_id, referent_key, concept_id):
        raise ValueError("LEGACY_FAMILY_SOURCE_MAPPING_DISABLED")

    def include_substance(self, concept_id, substance_id, source_registry):
        source = Path(source_registry).resolve()
        if source not in SOURCES or sha(source) != SOURCES[source]:
            raise PermissionError("UNAPPROVED_OR_CHANGED_SUBSTANCE_SNAPSHOT")
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            definition = self.get(concept_id)["definition"]
            with closing(sqlite3.connect(source.as_uri() + "?mode=ro&immutable=1", uri=True)) as canonical_db:
                row = canonical_db.execute("SELECT identity_status FROM substance_identity WHERE substance_id=?", (substance_id,)).fetchone()
                graphs = canonical_db.execute("SELECT structure_value FROM substance_structure WHERE substance_id=? AND structure_type='SMILES'", (substance_id,)).fetchall()
                keys = canonical_db.execute("SELECT identifier_value FROM substance_identifier WHERE substance_id=? AND identifier_type='InChIKey'", (substance_id,)).fetchall()
            if not row or row[0] != "ACCEPTED" or len(graphs) != 1:
                raise ValueError("SUBSTANCE_IDENTITY_NOT_VALIDATED")
            from chemistry import describe
            graph = describe(graphs[0][0])
            if len(keys) != 1 or keys[0][0] != graph["inchikey"]:
                raise ValueError("SUBSTANCE_IDENTIFIER_INCONSISTENT")
            result = contains_substance(definition, graphs[0][0])
            if result != "SUPPORTED":
                raise ValueError("MEMBERSHIP_" + result)
            if sha(source) != SOURCES[source]:
                raise PermissionError("SUBSTANCE_SNAPSHOT_CHANGED")
            evidence = {"smiles": graph["smiles"], "inchikey": graph["inchikey"], "comparison": result}
            db.execute("INSERT OR IGNORE INTO membership VALUES(?,?,?,?)", (concept_id, substance_id, SOURCES[source], canonical(evidence)))
            db.execute("INSERT INTO event(event_type,concept_id,evidence_json) VALUES('MEMBERSHIP',?,?)",
                       (concept_id, canonical({"substance_id": substance_id, **evidence})))
            db.execute("COMMIT")
