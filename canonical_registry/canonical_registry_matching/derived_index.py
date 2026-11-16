"""Reproducible SQLite cache of derived chemistry. Never stores identity decisions."""
from contextlib import closing
from pathlib import Path
import hashlib
import json
import sqlite3
from time import perf_counter
from rdkit import rdBase

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "enrichment/local/chemical_index.sqlite"
VERSION = "connectivity-proof-v1"


def engine_version():
    directories = ("", "canonical_registry_matching", "source_candidate_correspondence",
                   "identity_reconciliation", "chemical_correspondence_hardening",
                   "charge_dimension_evidence", "real_world_validation")
    h = hashlib.sha256((VERSION + rdBase.rdkitVersion).encode())
    for directory in directories:
        for path in sorted((ROOT / directory).glob("*.py")):
            h.update(str(path.relative_to(ROOT)).encode())
            h.update(path.read_bytes())
    return h.hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class DerivedIndex:
    def __init__(self, path=None):
        self.path = Path(path or CACHE).absolute()
        for part in (self.path, *self.path.parents):
            if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
                raise PermissionError("INDEX_LINK_PATH_REJECTED")
        self.path = self.path.resolve()
        allowed = (ROOT / "enrichment/local", ROOT / "canonical_registry_matching/evaluation")
        if not any(directory.resolve() in self.path.parents for directory in allowed):
            raise PermissionError("INDEX_OUTSIDE_MANAGED_CACHE_LOCATION")
        if self.path.exists():
            if self.path.stat().st_nlink != 1:
                raise PermissionError("INDEX_SHARED_FILE_REJECTED")
            with closing(sqlite3.connect(self.path.as_uri()+"?mode=ro", uri=True)) as existing:
                tables = {row[0] for row in existing.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if tables & {"substance_identity", "concept", "fixture_authorization"}:
                raise PermissionError("CANONICAL_DATABASE_CANNOT_BE_AN_INDEX")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.version = engine_version()
        self.db = sqlite3.connect(self.path, timeout=60)
        try:
            self.db.execute("""CREATE TABLE IF NOT EXISTS derived (
                engine TEXT NOT NULL, kind TEXT NOT NULL, input_key TEXT NOT NULL,
                payload TEXT NOT NULL, checksum TEXT NOT NULL,
                PRIMARY KEY(engine,kind,input_key))""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS chemical_candidate_key (
                engine TEXT NOT NULL, snapshot TEXT NOT NULL, substance_id TEXT NOT NULL,
                signature TEXT, PRIMARY KEY(engine,snapshot,substance_id))""")
            self.db.execute("""CREATE INDEX IF NOT EXISTS chemical_signature_lookup
                ON chemical_candidate_key(engine,snapshot,signature)""")
        except BaseException:
            self.db.close()
            raise
        self.hits = self.misses = 0
        self.started = perf_counter()

    def get(self, kind, key, compute):
        # Every row is bound to its exact derivation inputs and engine version.
        key = hashlib.sha256(encode(key).encode()).hexdigest()
        def checksum(raw):
            return hashlib.sha256(encode([self.version, kind, key, raw]).encode()).hexdigest()
        row = self.db.execute("SELECT payload,checksum FROM derived WHERE engine=? AND kind=? AND input_key=?",
                              (self.version, kind, key)).fetchone()
        if row and checksum(row[0]) == row[1]:
            try:
                value = json.loads(row[0])
                self.hits += 1
                return value
            except ValueError:
                pass
        value = compute()
        raw = encode(value)
        self.db.execute("INSERT OR REPLACE INTO derived VALUES(?,?,?,?,?)",
                        (self.version, kind, key, raw, checksum(raw)))
        self.misses += 1
        return value

    def close(self):
        self.db.commit()
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if exc[0]:
            self.db.rollback()
        self.close()
