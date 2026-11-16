"""Compact the verified private clone using the existing audit payload format."""

from hashlib import sha256
from time import perf_counter
import zlib

from audit_payload import SCHEMA, decode
from source_concept_models import canonical


def compact_history(db):
    started = perf_counter()
    table = "concept_resolution_event"
    trigger = db.execute("SELECT sql FROM sqlite_schema WHERE name='immutable_event_update'").fetchone()
    if not trigger or db.execute("SELECT 1 FROM sqlite_schema WHERE name='resolution_audit_payload'").fetchone():
        raise ValueError("EXPECTED_UNCOMPACTED_VERIFIED_FIXTURE")
    db.executescript("BEGIN IMMEDIATE;\n" + SCHEMA)
    events = 0
    before = 0
    content = sha256()
    try:
        db.execute("DROP TRIGGER immutable_event_update")
        for rowid, event, raw in db.execute(f"SELECT rowid,event_id,decision_json FROM {table} ORDER BY rowid"):
            data = raw.encode("utf-8")
            key = sha256(data).hexdigest()
            db.execute("INSERT OR IGNORE INTO resolution_audit_payload VALUES(?,?,?)",
                       (key, len(data), zlib.compress(data, 1)))
            ref = canonical({"format": "zlib-json-v1", "audit_sha256": key})
            if decode(db, ref) != raw:
                raise ValueError("AUDIT_ROUND_TRIP_FAILED")
            db.execute(f"UPDATE {table} SET decision_json=? WHERE rowid=?", (ref, rowid))
            content.update(canonical([event, key]).encode())
            events += 1
            before += len(data)
        db.execute(trigger[0])
        db.commit()
    except BaseException:
        db.rollback()
        raise
    db.execute("VACUUM")
    if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)] or db.execute("PRAGMA foreign_key_check").fetchone():
        raise ValueError("COMPACTED_FIXTURE_INTEGRITY_FAILURE")
    after = sha256()
    for event, stored in db.execute(f"SELECT event_id,decision_json FROM {table} ORDER BY rowid"):
        key = sha256(decode(db, stored).encode("utf-8")).hexdigest()
        after.update(canonical([event, key]).encode())
    if after.digest() != content.digest():
        raise ValueError("AUDIT_ORDER_OR_CONTENT_CHANGED")
    return {"events": events, "original_payload_bytes": before,
            "compressed_payload_bytes": db.execute("SELECT sum(length(compressed)) FROM resolution_audit_payload").fetchone()[0],
            "ordered_event_content_sha256": after.hexdigest(), "seconds": perf_counter() - started}


def verify_history(db, expected):
    """Detect missing, corrupt, or reordered historical events after execution."""
    observed = sha256()
    rows = db.execute("SELECT event_id,decision_json FROM concept_resolution_event ORDER BY rowid LIMIT ?",
                      (expected["events"],)).fetchall()
    for event, stored in rows:
        observed.update(canonical([event, sha256(decode(db, stored).encode("utf-8")).hexdigest()]).encode())
    if len(rows) != expected["events"] or observed.hexdigest() != expected["ordered_event_content_sha256"]:
        raise ValueError("HISTORICAL_AUDIT_DIGEST_MISMATCH")
