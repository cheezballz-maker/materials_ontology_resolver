"""Resumable source registration and review using the shared domain registry."""

from contextlib import closing, contextmanager
from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import sqlite3

from .registry import DomainRegistry, DomainType, Registration, canonical, fingerprint

MIGRATION = Path(__file__).with_name("schema_v2.sql")


@dataclass(frozen=True)
class Observation:
    source_reference: str
    label: str
    content_key: str
    payload: dict
    source_version: str | None = None
    legacy_key: str | None = None


class StagedRegistry(DomainRegistry):
    @staticmethod
    def _migrate(db):
        db.executescript("BEGIN IMMEDIATE;\n" + MIGRATION.read_text(encoding="utf-8") + """
            INSERT INTO source_head
            SELECT concept_id,
                (SELECT r.fingerprint FROM source_revision r WHERE r.concept_id=d.concept_id
                 ORDER BY r.rowid DESC LIMIT 1),
                1,
                (SELECT r.review_required FROM source_revision r WHERE r.concept_id=d.concept_id
                 AND r.fingerprint=d.registered_revision)
            FROM domain_concept d;
            COMMIT;
        """)

    def initialize(self, pilot=None, *, legacy_observations=None):
        if pilot is None and legacy_observations is not None:
            raise ValueError("Legacy payloads require a pilot database")
        if self.path.exists():
            raise FileExistsError(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            with closing(sqlite3.connect(self.path)) as db:
                if pilot is None:
                    self._schema(db)
                else:
                    with DomainRegistry(pilot).reader() as source:
                        self._verify(source)
                        source.backup(db)
                self._verify(db)
                db.execute("PRAGMA foreign_keys=ON")
                self._migrate(db)
                if db.execute("PRAGMA foreign_key_check").fetchone():
                    raise ValueError("Foreign-key failure on migrated copy")
            if legacy_observations is not None:
                self._restore_payloads(legacy_observations)
        except BaseException:
            self.path.unlink()
            raise

    def _restore_payloads(self, observations):
        with self.writer() as db:
            expected = dict(db.execute("SELECT source_reference,registered_revision FROM domain_concept"))
            supplied = {row.source_reference: row.legacy_key for row in observations}
            if len(supplied) != len(observations) or supplied != expected:
                raise ValueError("Archived source packets do not match this pilot's complete concept/revision binding")
            db.executemany("""INSERT INTO source_payload
                SELECT concept_id,registered_revision,?,? FROM domain_concept WHERE source_reference=?""",
                           ((row.content_key,canonical(row.payload),row.source_reference) for row in observations))

    @contextmanager
    def writer(self):
        with self.reader() as read:
            self._verify(read, (2,))
        with closing(sqlite3.connect(self.path.as_uri()+"?mode=rw", uri=True, timeout=30,
                                     isolation_level=None)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            try:
                self._verify(db, (2,))
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def register(self, observations, *, domain: DomainType, namespace, run_id, batch_size=500,
                 complete_count=None, max_batches=None, batch_hook=None):
        records = sorted(observations, key=lambda row: row.source_reference)
        keys = {row.source_reference for row in records}
        if (len(keys) != len(records) or not run_id.strip() or not namespace.strip()
                or any(not key.startswith(namespace+":") for key in keys)):
            raise ValueError("Unique source keys in the declared namespace are required")
        if complete_count is not None and complete_count != len(records):
            raise ValueError("Complete snapshot count does not match its records")
        if batch_size < 1 or (max_batches is not None and max_batches < 1):
            raise ValueError("Positive batch limits are required")
        for row in records:
            Registration(domain,row.source_reference,row.label,row.content_key)
            if row.content_key != fingerprint(row.payload):
                raise ValueError("Source content fingerprint does not match the packet")
        stamp = fingerprint([domain.name, domain.prefix, namespace, complete_count,
                             [(r.source_reference,r.content_key,r.source_version,r.legacy_key) for r in records]])
        counts = {"created":0,"new_revisions":0,"held":0,"missing":0,"batches":0}
        while True:
            with self.writer() as db:
                previous = db.execute("SELECT * FROM registration_run WHERE run_id=?", (run_id,)).fetchone()
                if previous is None:
                    db.execute("""INSERT INTO registration_run(run_id,source_namespace,domain_type,manifest_sha256,
                                   expected_count,full_snapshot) VALUES(?,?,?,?,?,?)""",
                               (run_id,namespace,domain.name,stamp,len(records),int(complete_count is not None)))
                    offset = 0
                else:
                    if previous["manifest_sha256"] != stamp:
                        raise ValueError("Run identifier is bound to a different snapshot")
                    offset = previous["next_offset"]
                    if previous["completed"]:
                        return {**counts,"completed":True,"offset":offset}
                part = records[offset:offset+batch_size]
                for row in part:
                    result = self._register_record(db, row, domain)
                    db.execute("INSERT INTO registration_member VALUES(?,?,?,?)",
                               (run_id,result["id"],result["revision"],row.source_version))
                    counts["created"] += int(result["created"])
                    counts["new_revisions"] += int(result["revision_inserted"])
                    counts["held"] += int(result["held"])
                next_offset = offset + len(part)
                finished = next_offset == len(records)
                if finished and complete_count is not None:
                    counts["missing"] += self._mark_missing(db,domain.name,namespace,run_id)
                    members, valid_heads = db.execute("""SELECT count(*),coalesce(sum(
                        h.present=1 AND h.observed_revision=m.revision),0)
                        FROM registration_member m JOIN source_head h USING(concept_id)
                        WHERE m.run_id=?""",(run_id,)).fetchone()
                    if members != complete_count or valid_heads != complete_count:
                        raise ValueError("Complete snapshot does not reconcile with current source heads")
                if batch_hook:
                    batch_hook(offset)  # Interruption at this point must roll back the batch and its checkpoint.
                db.execute("UPDATE registration_run SET next_offset=?,completed=? WHERE run_id=?",
                           (next_offset,int(finished),run_id))
            counts["batches"] += 1
            if finished or (max_batches is not None and counts["batches"] >= max_batches):
                return {**counts,"completed":finished,"offset":next_offset}

    @staticmethod
    def _event(db, concept, revision, event, detail="", actor="source-registration"):
        db.execute("""INSERT INTO source_review(concept_id,revision,event,actor,detail) VALUES(?,?,?,?,?)""",
                   (concept,revision,event,actor,detail))

    def _register_record(self, db, row, domain):
        old = db.execute("""SELECT d.concept_id,d.registered_revision,h.observed_revision,h.present,h.continuity_hold
                            FROM domain_concept d JOIN source_head h USING(concept_id)
                            WHERE source_reference=?""", (row.source_reference,)).fetchone()
        revision = row.content_key
        if old:
            if "aliases" in row.payload and row.payload["aliases"] is None:
                previous = db.execute("SELECT payload_json FROM source_payload WHERE concept_id=? AND revision=?",
                                      (old["concept_id"],old["observed_revision"])).fetchone()
                if previous:
                    previous_packet = json.loads(previous[0])
                    if previous_packet.get("source") == row.payload.get("source") and previous_packet.get("aliases") is not None:
                        payload = {**row.payload, "aliases": previous_packet["aliases"]}
                        row = replace(row, payload=payload, content_key=fingerprint(payload))
                        revision = row.content_key
            existing = db.execute("SELECT revision FROM source_payload WHERE concept_id=? AND content_key=?",
                                  (old["concept_id"],row.content_key)).fetchone()
            if existing:
                revision = existing[0]
        record = Registration(domain,row.source_reference,row.label,revision,row.source_version)
        result = self._ingest_record(db,record,None)
        concept = result["id"]
        db.execute("INSERT INTO source_payload VALUES(?,?,?,?) ON CONFLICT DO NOTHING",
                   (concept,revision,row.content_key,canonical(row.payload)))
        if old:
            if old["observed_revision"] != revision:
                self._event(db,concept,revision,"REVISION_OBSERVED",old["observed_revision"])
            if not old["present"]:
                self._event(db,concept,revision,"REAPPEARED")
            reverted = old["observed_revision"] != old["registered_revision"] and revision == old["registered_revision"]
            if reverted:
                self._event(db,concept,revision,"RETURNED_TO_REGISTERED_REVISION",old["observed_revision"])
            if old["observed_revision"] != revision or not old["present"]:
                db.execute("""UPDATE source_head SET observed_revision=?,present=1,
                              continuity_hold=max(continuity_hold,?) WHERE concept_id=?""",
                           (revision,int(not old["present"] or reverted),concept))
        else:
            db.execute("INSERT INTO source_head VALUES(?,?,1,?)",
                       (concept,revision,int(result["possible_shared_label"])))
            if result["possible_shared_label"]:
                self._event(db,concept,revision,"POSSIBLE_KEY_CHANGE_OR_SHARED_LABEL")
        return result

    def _mark_missing(self, db, domain, namespace, run_id):
        prefix = namespace + ":"
        rows = db.execute("""SELECT h.concept_id,h.observed_revision FROM source_head h
            JOIN domain_concept d USING(concept_id)
            WHERE h.present=1 AND d.domain_type=? AND substr(d.source_reference,1,?)=?
              AND NOT EXISTS(SELECT 1 FROM registration_member m WHERE m.run_id=? AND m.concept_id=h.concept_id)""",
                          (domain,len(prefix),prefix,run_id)).fetchall()
        for concept, revision in rows:
            db.execute("UPDATE source_head SET present=0 WHERE concept_id=?", (concept,))
            self._event(db,concept,revision,"MISSING_FROM_COMPLETE_SNAPSHOT",run_id)
        return len(rows)

    def review_source(self, concept, revision, *, action, actor, note):
        if not actor.strip() or not note.strip() or action not in {
            "defer","adopt","confirm-separate","confirm-continuity",
        }:
            raise ValueError("A supported review decision, reviewer and note are required")
        with self.writer() as db:
            row = db.execute("""SELECT d.canonical_status,h.observed_revision,h.present,h.continuity_hold
                               FROM domain_concept d JOIN source_head h USING(concept_id) WHERE d.concept_id=?""",
                             (concept,)).fetchone()
            if row is None or row["observed_revision"] != revision:
                raise ValueError("Review must name the current observed revision")
            if action != "defer" and not row["present"]:
                raise ValueError("The source record is missing")
            if action == "adopt":
                if row["canonical_status"].startswith("RESOLVED_") or row["continuity_hold"]:
                    raise ValueError("Resolve the continuity or approved mapping hold separately")
                db.execute("UPDATE domain_concept SET registered_revision=? WHERE concept_id=?", (revision,concept))
            if action in {"confirm-separate","confirm-continuity"}:
                db.execute("UPDATE source_head SET continuity_hold=0 WHERE concept_id=?", (concept,))
            self._event(db,concept,revision,action,note,actor)

    def source_queue(self):
        with self.reader() as db:
            self._verify(db,(2,))
            return [dict(r) for r in db.execute("""SELECT d.concept_id,d.source_reference,d.preferred_label,
                d.registered_revision,h.observed_revision,h.present,h.continuity_hold,d.canonical_status,
                r.observed_label
                FROM domain_concept d JOIN source_head h USING(concept_id)
                JOIN source_revision r ON r.concept_id=d.concept_id AND r.fingerprint=h.observed_revision
                WHERE h.present=0 OR h.continuity_hold=1 OR h.observed_revision<>d.registered_revision
                ORDER BY d.concept_id""")]

    def detail(self, concept_id):
        result = super().detail(concept_id)
        if result is None:
            return None
        with self.reader() as db:
            head = db.execute("SELECT * FROM source_head WHERE concept_id=?", (concept_id.upper(),)).fetchone()
            events = db.execute("SELECT * FROM source_review WHERE concept_id=? ORDER BY event_id",
                                (concept_id.upper(),)).fetchall()
        held = (not head["present"] or head["continuity_hold"]
                or head["observed_revision"] != result["registered_revision"])
        result["source_head"] = dict(head)
        result["source_review"] = [dict(event) for event in events]
        result["current_assessment_applicability"] = (
            "PENDING_SOURCE_REVIEW" if held else "SOURCE_REVISION_CURRENT"
        ) if result.get("assessment") else "NO_APPROVED_REVISION_ASSESSMENT"
        result["current_mapping_applicability"] = (
            "PENDING_SOURCE_REVIEW" if held else "SOURCE_REVISION_CURRENT"
        ) if result.get("canonical_target") else "NO_APPROVED_MAPPING"
        return result
