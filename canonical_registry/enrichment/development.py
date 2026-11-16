"""Private, persistent development registries backed by the existing write capabilities."""
from contextlib import closing
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import os
import secrets
import sqlite3
import uuid
import sys

from canonical_registry.canonical_substance_creation import bootstrap  # noqa: F401
from creation_authorization import CreationPermit
from fixture_registry import ROOT, FixturePermit, validate_path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "chemical_concept_registry"))
from canonical_registry.chemical_concept_registry.registry import FIXTURES, Registry, initialize
from canonical_registry.substance_explorer.registry_search import DEFAULT_DB

DATA = Path(__file__).resolve().parent / "local"
BASELINE_SHA = "6f99fba4c0874aa5db6f3bde0ac780bc706aa05f59466868b92959c3406d57d4"
VERSION = 1


def file_digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _clone(key):
    if file_digest(DEFAULT_DB) != BASELINE_SHA:
        raise ValueError("FROZEN_PILOT_DIGEST_MISMATCH")
    ROOT.mkdir(exist_ok=True)
    path = validate_path(ROOT / f"enrichment_{key}.sqlite")
    os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
    with closing(sqlite3.connect(DEFAULT_DB.resolve().as_uri() + "?mode=ro", uri=True)) as source:
        with closing(sqlite3.connect(path)) as target, target:
            source.backup(target)
            target.execute("PRAGMA foreign_keys=ON")
            if target.execute("SELECT count(*) FROM substance_identity").fetchone() != (560,):
                raise ValueError("UNEXPECTED_PILOT_COUNT")
            [(fixture_id,)] = target.execute("SELECT fixture_id FROM fixture_authorization")
            association_token, creation_token = secrets.token_hex(32), secrets.token_hex(32)
            target.execute("UPDATE fixture_authorization SET token_hash=?", (_hash(association_token),))
            target.execute("UPDATE creation_authorization SET token_hash=?", (_hash(creation_token),))
            if target.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("COPIED_PILOT_FOREIGN_KEY_FAILURE")
    if file_digest(DEFAULT_DB) != BASELINE_SHA:
        raise ValueError("PILOT_CHANGED_DURING_COPY")
    return CreationPermit(FixturePermit(path, fixture_id, association_token), creation_token)


def open_development(directory=DATA, *, create=False):
    """Explicit initialization publishes both registries together via a local manifest."""
    directory = Path(directory)
    manifest = directory / "registries.json"
    if create:
        directory.mkdir(parents=True, exist_ok=False)
        key = uuid.uuid4().hex
        permit = _clone(key)
        concepts = initialize(FIXTURES / f"enrichment_{key}.sqlite")
        doc = {"version": VERSION, "baseline_sha256": BASELINE_SHA, "key": key,
               "association": {**asdict(permit.association), "path": str(permit.path)},
               "creation_token": permit.creation_token, "concept_database": str(concepts.path)}
        pending = directory / "registries.pending"
        with os.fdopen(os.open(pending, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as stream:
            json.dump(doc, stream)
        pending.replace(manifest)
    doc = json.loads(manifest.read_text(encoding="utf8"))
    if doc["version"] != VERSION or doc["baseline_sha256"] != BASELINE_SHA:
        raise ValueError("UNSUPPORTED_DEVELOPMENT_MANIFEST")
    key = uuid.UUID(hex=doc["key"]).hex
    stem = f"enrichment_{key}.sqlite"
    association = doc["association"]
    if (Path(association["path"]) != ROOT / stem or
            Path(doc["concept_database"]) != FIXTURES / stem):
        raise PermissionError("DEVELOPMENT_PATH_MISMATCH")
    permit = CreationPermit(FixturePermit(Path(association["path"]), association["fixture_id"],
                                          association["token"]), doc["creation_token"])
    # Authenticate using a read-only open. Writer services authenticate again.
    path = validate_path(permit.path)
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        markers = db.execute("SELECT f.fixture_id,f.token_hash,c.token_hash FROM fixture_authorization f "
                             "JOIN creation_authorization c USING(fixture_id)").fetchall()
    if markers != [(permit.association.fixture_id, _hash(permit.association.token),
                    _hash(permit.creation_token))]:
        raise PermissionError("DEVELOPMENT_CAPABILITY_MISMATCH")
    return permit, Registry(doc["concept_database"])
