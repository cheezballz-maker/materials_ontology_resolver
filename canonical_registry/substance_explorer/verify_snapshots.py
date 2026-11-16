"""Record snapshot digests, identity inventories and read-only integrity checks."""

from contextlib import closing
import hashlib
import json

from canonical_registry.substance_explorer.registry_access import (
    ConceptSnapshot, concept_datasets, snapshot_digest, substance_datasets,
)
from canonical_registry.substance_explorer.registry_search import ROOT, Registry


def inventory():
    snapshots = {}
    substances = {}
    for key, item in substance_datasets().items():
        if key == "configured":
            continue
        registry = Registry(item.path)
        with closing(registry.connect()) as db:
            ids = [row[0] for row in db.execute("SELECT substance_id FROM substance_identity ORDER BY 1")]
            counts = {"identities": len(ids)}
            if "current_exact_association" in registry.objects:
                counts["current_exact_associations"] = db.execute("SELECT count(*) FROM current_exact_association").fetchone()[0]
            digest = snapshot_digest(registry.path)
            substances[digest] = set(ids)
            snapshots[key] = evidence(db, registry.path, digest, ids, counts)
    for key, item in concept_datasets().items():
        registry = ConceptSnapshot(item.path)
        with closing(registry.connect()) as db:
            ids = [row[0] for row in db.execute("SELECT concept_id FROM concept ORDER BY 1")]
            counts = {"identities": len(ids)}
            for table in ("membership", "narrower", "source_mapping"):
                counts[table] = db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            missing = [dict(row) for row in db.execute("SELECT substance_id,registry_sha256 FROM membership")
                       if row["substance_id"] not in substances.get(row["registry_sha256"], set())]
            assert not missing, (key, missing)
            snapshots[key] = evidence(db, registry.path, snapshot_digest(registry.path), ids, counts)
    ontology = ROOT.parents[2] / "13. Materials Ontology/Ontology/substance_ontology.ttl"
    return {"snapshots": snapshots, "ontology": {"path": str(ontology), "sha256": snapshot_digest(ontology)}}


def evidence(db, path, digest, ids, counts):
    integrity = [row[0] for row in db.execute("PRAGMA integrity_check")]
    foreign_keys = list(db.execute("PRAGMA foreign_key_check"))
    assert integrity == ["ok"] and not foreign_keys, path
    assert db.execute("PRAGMA query_only").fetchone()[0] == 1
    return {"path": str(path), "sha256": digest, "counts": counts, "integrity": integrity,
            "id_sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest(), "foreign_key_errors": len(foreign_keys)}


if __name__ == "__main__":
    print(json.dumps(inventory(), indent=2, ensure_ascii=False))
