"""Lossless audit storage for new disposable fixtures."""

import hashlib
import json
import zlib

SCHEMA = """
CREATE TABLE resolution_audit_payload(
 sha256 TEXT PRIMARY KEY, json_bytes INTEGER NOT NULL, compressed BLOB NOT NULL
);
CREATE TRIGGER audit_payload_no_update BEFORE UPDATE ON resolution_audit_payload
 BEGIN SELECT RAISE(ABORT,'IMMUTABLE_AUDIT_PAYLOAD'); END;
CREATE TRIGGER audit_payload_no_delete BEFORE DELETE ON resolution_audit_payload
 BEGIN SELECT RAISE(ABORT,'IMMUTABLE_AUDIT_PAYLOAD'); END;
CREATE TRIGGER audit_payload_reference BEFORE INSERT ON concept_resolution_event
 WHEN json_extract(NEW.decision_json,'$.format')='zlib-json-v1'
 AND NOT EXISTS (SELECT 1 FROM resolution_audit_payload
                 WHERE sha256=json_extract(NEW.decision_json,'$.audit_sha256'))
 BEGIN SELECT RAISE(ABORT,'MISSING_AUDIT_PAYLOAD'); END;
"""


def encode(db, decision):
    from source_concept_models import canonical

    encoded = canonical(decision)
    if not db.execute("SELECT 1 FROM sqlite_schema WHERE name='resolution_audit_payload' AND type='table'").fetchone():
        return encoded
    raw = encoded.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    if not db.execute("SELECT 1 FROM resolution_audit_payload WHERE sha256=?", (digest,)).fetchone():
        db.execute("INSERT INTO resolution_audit_payload VALUES(?,?,?)", (digest, len(raw), zlib.compress(raw, 1)))
    return canonical({"format": "zlib-json-v1", "audit_sha256": digest})


def decode(db, stored):
    """Return the original JSON text and verify referenced content."""
    decision = json.loads(stored)
    if decision.get("format") != "zlib-json-v1":
        return stored
    digest = decision["audit_sha256"]
    row = db.execute("SELECT json_bytes,compressed FROM resolution_audit_payload WHERE sha256=?", (digest,)).fetchone()
    if row is None:
        raise ValueError("MISSING_AUDIT_PAYLOAD")
    raw = zlib.decompress(row[1])
    if len(raw) != row[0] or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("INVALID_AUDIT_PAYLOAD")
    return raw.decode("utf-8")
