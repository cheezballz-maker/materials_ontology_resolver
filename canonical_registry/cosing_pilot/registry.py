"""Versioned local SQLite storage shared by source-backed domain concepts."""

from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3

SCHEMA = Path(__file__).with_name("schema_v1.sql")
APPLICATION_ID = 1129272143
VERSION = 1


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=sorted)


def fingerprint(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DomainType:
    name: str
    prefix: str

    def __post_init__(self):
        if not self.name.strip() or not re.fullmatch(r"[A-Z]{2,8}", self.prefix):
            raise ValueError("Invalid domain configuration")


COSMETICS = DomainType("CosmeticsIngredientConcept", "CIC")


@dataclass(frozen=True)
class Registration:
    domain: DomainType
    source_reference: str
    label: str
    revision: str
    source_version: str | None = None
    attempted: bool = False
    attributes: tuple = ()
    roles: tuple = ()
    summary: dict = field(default_factory=dict)
    trace: dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("A source designation is required")
        namespace, sep, key = self.source_reference.partition(":")
        if not (sep and namespace and key.strip() and re.fullmatch("[a-f0-9]{64}", self.revision)):
            raise ValueError("A namespaced source key and a content fingerprint are required")


@dataclass(frozen=True)
class Comparison:
    left: str
    right: str
    verdict: str
    evidence: dict
    external_revision: str | None = None


class DomainRegistry:
    def __init__(self, path):
        self.path = Path(os.path.abspath(path))
        if self.path.suffix != ".sqlite":
            raise ValueError("Choose a dedicated .sqlite pilot database")
        for part in (self.path, *self.path.parents):
            if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
                raise PermissionError("Linked pilot database paths are unsupported")
        if self.path.exists() and self.path.stat().st_nlink != 1:
            raise PermissionError("Shared database file rejected")

    @staticmethod
    def _verify(db, versions=(VERSION,)):
        application = db.execute("PRAGMA application_id").fetchone()[0]
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if application != APPLICATION_ID:
            raise PermissionError("Expected a domain pilot database")
        if version not in versions:
            raise ValueError(f"Pilot schema {version} needs an explicit migration or compatible workflow")

    @staticmethod
    def _schema(db):
        db.executescript("BEGIN IMMEDIATE;\n" + SCHEMA.read_text(encoding="utf-8") + "\nCOMMIT;")

    def _create(self):
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return
        os.close(fd)
        try:
            with closing(sqlite3.connect(self.path)) as db:
                self._schema(db)
        except BaseException:
            self.path.unlink()
            raise

    @contextmanager
    def reader(self):
        with closing(sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=30)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            self._verify(db, (1, 2))
            yield db

    def ingest(self, records, *, pipeline_version, comparisons=(), dry_run=False):
        records = sorted(records, key=lambda r: r.source_reference)
        if len({r.source_reference for r in records}) != len(records) or not pipeline_version.strip():
            raise ValueError("Unique source bindings and a pipeline version are required")
        if dry_run:
            with closing(sqlite3.connect(":memory:", isolation_level=None)) as db:
                if self.path.exists():
                    with self.reader() as source:
                        source.backup(db)
                else:
                    self._schema(db)
                return self._transaction(db, records, comparisons, pipeline_version)
        if not self.path.exists():
            self._create()
        # Check the marker through a read-only connection before requesting a write lock.
        with self.reader():
            pass
        with closing(sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=30, isolation_level=None)) as db:
            return self._transaction(db, records, comparisons, pipeline_version)

    def _transaction(self, db, records, comparisons, version):
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        try:
            self._verify(db)
            result = [self._ingest_record(db, record, version) for record in records]
            accepted = {r["source_reference"]: r for r in result if not r["held"]}
            comparison_inserts = 0
            for comparison in comparisons:
                left, right = accepted.get(comparison.left), accepted.get(comparison.right)
                if left is None or (right is None and comparison.external_revision is None):
                    continue
                right_reference = comparison.right
                if right is not None and comparison.right < comparison.left:
                    left, right = right, left
                    right_reference = comparison.left
                cursor = db.execute("""
                    INSERT INTO review_comparison VALUES(?,?,?,?,?,?,?,?)
                    ON CONFLICT DO NOTHING
                    """, (left["id"], left["revision"], right_reference, right["id"] if right else None,
                          right["revision"] if right else comparison.external_revision, version,
                          comparison.verdict, canonical(comparison.evidence)))
                comparison_inserts += cursor.rowcount
            db.commit()
        except BaseException:
            db.rollback()
            raise
        return {"records": result, "comparison_inserts": comparison_inserts}

    @staticmethod
    def _ingest_record(db, record, version):
        row = db.execute("SELECT * FROM domain_concept WHERE source_reference=?", (record.source_reference,)).fetchone()
        created = row is None
        label_key = record.label.casefold().strip()
        possible_shared_label = False
        if created:
            possible_shared_label = db.execute(
                "SELECT 1 FROM domain_concept WHERE domain_type=? AND label_key=? LIMIT 1",
                (record.domain.name, label_key),
            ).fetchone() is not None
            db.execute("INSERT INTO domain_type(name,id_prefix) VALUES(?,?) ON CONFLICT(name) DO NOTHING",
                       (record.domain.name, record.domain.prefix))
            config = db.execute("SELECT id_prefix FROM domain_type WHERE name=?", (record.domain.name,)).fetchone()
            if config["id_prefix"] != record.domain.prefix:
                raise ValueError("Domain prefix changed")
            sequence = db.execute("UPDATE domain_type SET last_id=last_id+1 WHERE name=? RETURNING last_id",
                                  (record.domain.name,)).fetchone()[0]
            concept_id = f"{record.domain.prefix}_{sequence:08d}"
            db.execute("""INSERT INTO domain_concept(concept_id,domain_type,preferred_label,label_key,
                          source_reference,registered_revision) VALUES(?,?,?,?,?,?)""",
                       (concept_id, record.domain.name, record.label, label_key, record.source_reference, record.revision))
            status, held = "NOT_EVALUATED", False
        else:
            if (row["domain_type"] != record.domain.name or row["concept_id"].split("_")[0] != record.domain.prefix):
                raise ValueError("Source key is already bound to another domain configuration")
            concept_id, status = row["concept_id"], row["canonical_status"]
            held = row["registered_revision"] != record.revision
            observed = db.execute("SELECT observed_label FROM source_revision WHERE concept_id=? AND fingerprint=?",
                                  (concept_id, record.revision)).fetchone()
            if observed and observed["observed_label"] != record.label:
                raise ValueError("Source label conflicts with the stored fingerprint")
        revision_inserted = db.execute("""INSERT INTO source_revision(concept_id,fingerprint,observed_label,
             source_version,review_required) VALUES(?,?,?,?,?) ON CONFLICT DO NOTHING""",
                                      (concept_id, record.revision, record.label, record.source_version,
                                       int(held or possible_shared_label))).rowcount
        assessment_inserted = False
        if version is not None:
            assessment_inserted = db.execute("""INSERT INTO assessment VALUES(?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING""",
                (concept_id, record.revision, version, int(record.attempted), canonical(record.attributes),
                 canonical(record.roles), canonical(record.summary), canonical(record.trace))).rowcount
        if version is not None and not held and record.attempted and status == "NOT_EVALUATED":
            db.execute("UPDATE domain_concept SET canonical_status='UNRESOLVED' WHERE concept_id=?", (concept_id,))
            status = "UNRESOLVED"
        return dict(id=concept_id, source_reference=record.source_reference, revision=record.revision,
                    status=status, created=created, held=held, revision_inserted=bool(revision_inserted),
                    assessment_inserted=bool(assessment_inserted), possible_shared_label=possible_shared_label)

    def search(self, query="", *, limit=25):
        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")
        with self.reader() as db:
            query = query.strip()
            fields = "concept_id AS ingredient_concept_id, preferred_label, source_reference, canonical_status"
            if re.fullmatch(r"[A-Za-z]{2,8}_[0-9]{8}", query) or ":" in query:
                exact = db.execute(f"""SELECT {fields} FROM domain_concept
                    WHERE concept_id=? OR source_reference=?""", (query.upper(), query)).fetchall()
                return [dict(row) for row in exact]
            rows = db.execute("""
                SELECT concept_id AS ingredient_concept_id, preferred_label, source_reference, canonical_status
                FROM domain_concept WHERE instr(label_key,?)>0
                ORDER BY label_key,concept_id LIMIT ?
                """, (query.casefold(), limit))
            return [dict(row) for row in rows]

    def detail(self, concept_id):
        with self.reader() as db:
            row = db.execute("""SELECT concept_id AS ingredient_concept_id, domain_type, preferred_label,
                source_reference, canonical_status,canonical_target_json,registered_revision
                FROM domain_concept WHERE concept_id=?""", (concept_id.upper(),)).fetchone()
            if row is None:
                return None
            result = dict(row)
            target = result.pop("canonical_target_json")
            if target:
                result["canonical_target"] = json.loads(target)
            result["source_revisions"] = [dict(r) for r in db.execute(
                "SELECT * FROM source_revision WHERE concept_id=? ORDER BY observed_at,rowid", (row[0],))]
            result["assessment"] = None
            last = db.execute("""SELECT * FROM assessment WHERE concept_id=? AND revision=?
                ORDER BY rowid DESC LIMIT 1""", (row[0], row["registered_revision"])).fetchone()
            if last:
                result["assessment"] = {k[:-5] if k.endswith("_json") else k:
                    json.loads(last[k]) if k.endswith("_json") else last[k] for k in last.keys()}
            result["pending_assessments"] = [
                {"revision": r["revision"], "pipeline_version": r["pipeline_version"],
                 "summary": json.loads(r["summary_json"])}
                for r in db.execute("""SELECT revision,pipeline_version,summary_json FROM assessment
                    WHERE concept_id=? AND revision<>? ORDER BY rowid""",
                    (row[0], row["registered_revision"]))
            ]
            result["comparisons"] = [dict(r) for r in db.execute("""
                SELECT left_id, right_id, right_reference, verdict, comparison_json
                FROM review_comparison WHERE left_id=? OR right_id=? ORDER BY left_id,right_reference
                """, (row[0], row[0]))]
            for item in result["comparisons"]:
                item["evidence"] = json.loads(item.pop("comparison_json"))
            return result
