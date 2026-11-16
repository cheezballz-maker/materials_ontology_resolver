"""One read-only inspection API for separate Substance and Concept registries."""

from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re

from canonical_registry.chemistry import normalize_name
from canonical_registry.substance_explorer.frozen_sqlite import FrozenSQLite
from canonical_registry.substance_explorer.registry_search import DEFAULT_DB, ROOT, Registry
from canonical_registry.substance_explorer.structure_display import molecular_formula


@dataclass(frozen=True)
class Dataset:
    label: str
    path: Path
    provenance: str
    live: bool = False


def development_datasets():
    # Use the same authenticated manifest as Resolve Chemicals. Never initialize
    # or copy a registry as a side effect of browsing.
    from canonical_registry.enrichment.development import open_development
    try:
        permit, concepts = open_development()
    except FileNotFoundError:
        return None
    return (
        Dataset("Development Substances", permit.path, "Persistent resolver commits.", live=True),
        Dataset("Development Chemical Concepts", concepts.path, "Persistent resolver commits.", live=True),
    )


def substance_datasets():
    datasets = {
        "pilot": Dataset("Frozen warehouse pilot", DEFAULT_DB, "Accepted Substance snapshot with seed identities and pilot additions."),
        "seed": Dataset("Canonical seed", ROOT / "output/registry.sqlite", "Frozen canonical seed snapshot."),
    }
    if development := development_datasets():
        datasets = {"development": development[0], **datasets}
    override = os.environ.get("SUBSTANCE_EXPLORER_DB")
    if override:
        datasets = {"configured": Dataset("Configured Substance snapshot", Path(override), "Local file selected by SUBSTANCE_EXPLORER_DB."), **datasets}
    return datasets


def concept_datasets():
    root = ROOT / "chemical_concept_registry"
    development = development_datasets()
    datasets = {"development": development[1]} if development else {}
    for key, label, manifest, provenance in (
        ("demo", "v1 relationship demonstration", "evaluation.json", "Curated POC demonstration with synthetic source mappings and stored relationship examples."),
        ("v11", "v1.1 warehouse evaluation", "evaluation_v11.json", "Warehouse-derived POC concepts from the original v1.1 evaluation."),
        ("validation", "Unified v1.1 validation", "unified_validation_v11.json", "Warehouse-derived POC concepts from the corrected 65-record replay."),
        ("reuse", "Concept reuse controls", "concept_reuse_validation_v11.json", "POC fixture mixing warehouse-derived concepts and synthetic controls."),
    ):
        path = root / manifest
        try:
            filename = Path(json.loads(path.read_text(encoding="utf8"))["fixture_database"].replace("\\", "/")).name
        except (OSError, ValueError, TypeError, KeyError):
            continue
        if re.fullmatch(r"[A-Za-z0-9_-]+\.sqlite", filename):
            fixture = root / "fixtures" / filename
            if fixture.is_file() and fixture.resolve().parent == (root / "fixtures").resolve():
                datasets[key] = Dataset(label, fixture, provenance + f" Manifest: {manifest}.")
    return datasets


def snapshot_digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class ConceptSnapshot(FrozenSQLite):
    def __init__(self, path, *, live=False):
        super().__init__(path, live=live)
        with closing(self.connect()) as db:
            markers = [row[0] for row in db.execute("SELECT marker FROM fixture_marker")]
            if markers != ["CHEMICAL_CONCEPT_POC_V1"]:
                raise ValueError("Expected a ChemicalConcept POC snapshot.")
            rows = db.execute("SELECT concept_id,definition_json FROM concept").fetchall()
            from canonical_registry.chemical_concept_registry.identity_contract import supported_definition
            self.active_ids = {row[0] for row in rows if supported_definition(json.loads(row[1]))}
            self.count = len(self.active_ids)

    def search(self, text="", *, definition_kind=None):
        text = normalize_name(text)
        prefix, separator, value = text.partition(":")
        kind = prefix.casefold() if separator and prefix.casefold() in {"formula", "source"} else "label"
        value = value.strip() if kind != "label" else text.casefold()
        with closing(self.connect()) as db:
            db.create_function("molecular_formula", 1, molecular_formula, deterministic=True)
            rows = db.execute("""
                SELECT c.concept_id, c.preferred_label, json_extract(c.definition_json,'$.kind') AS kind,
                       json_extract(c.definition_json,'$.smiles') AS smiles
                FROM concept c
                WHERE (:definition_kind IS NULL OR json_extract(c.definition_json,'$.kind')=:definition_kind)
                  AND ((:kind='label' AND (:text='' OR lower(c.concept_id)=:text OR instr(fold(c.preferred_label),:text)>0
                   OR EXISTS (SELECT 1 FROM label l WHERE l.concept_id=c.concept_id
                             AND instr(l.normalized_label,:text)>0)))
                   OR (:kind='formula' AND molecular_formula(json_extract(c.definition_json,'$.smiles'))=:text)
                   OR (:kind='source' AND EXISTS (SELECT 1 FROM source_mapping m
                       WHERE m.concept_id=c.concept_id AND m.record_id=:text)))
                ORDER BY c.concept_id
            """, {"text": value, "kind": kind, "definition_kind": definition_kind})
            from canonical_registry.chemical_concept_registry.identity_contract import preferred_label
            results = [dict(row) for row in rows if row["concept_id"] in self.active_ids]
            for result in results:
                result["preferred_label"] = preferred_label({"smiles": result["smiles"]})
            return results

    def detail(self, concept_id):
        if concept_id not in self.active_ids:
            return None
        with closing(self.connect()) as db:
            row = db.execute("SELECT * FROM concept WHERE concept_id=?", (concept_id,)).fetchone()
            if row is None:
                return None
            record = dict(row)
            record["definition"] = json.loads(record.pop("definition_json"))
            from canonical_registry.chemical_concept_registry.identity_contract import preferred_label, identity_record
            record["preferred_label"] = preferred_label(record["definition"])
            for field, query in (
                ("labels", "SELECT label FROM label WHERE concept_id=? ORDER BY label"),
                ("broader", "SELECT broader_id AS concept_id FROM narrower WHERE narrower_id=? ORDER BY broader_id"),
                ("narrower", "SELECT narrower_id AS concept_id FROM narrower WHERE broader_id=? ORDER BY narrower_id"),
                ("members", "SELECT substance_id,registry_sha256,evidence_json FROM membership WHERE concept_id=? ORDER BY substance_id"),
                ("mappings", "SELECT source_system,record_type,record_id,referent_key,evidence_json FROM source_mapping WHERE concept_id=? ORDER BY source_system,record_id"),
                ("events", "SELECT event_type,recorded_at,evidence_json FROM event WHERE concept_id=? ORDER BY event_id"),
            ):
                record[field] = [dict(item) for item in db.execute(query, (concept_id,))]
            record["labels"] = [{"label": record["preferred_label"]}]
            record["identity"] = identity_record(concept_id, "ChemicalConcept", record["preferred_label"],
                graph=record["definition"]["smiles"], definition=record["definition"],
                validation="VALIDATED_PARTIAL_MOLECULAR_IDENTITY")
            for relation in ("broader", "narrower"):
                record[relation] = [row for row in record[relation] if row["concept_id"] in self.active_ids]
            return record


class RegistryAccess:
    def __init__(self, substances=None, concepts=None):
        self.substances = Registry(substances.path, live=substances.live) if substances else None
        self.concepts = ConceptSnapshot(concepts.path, live=concepts.live) if concepts else None

    def substance_identity(self, sid):
        """Project accepted stored facts. This method performs no new admission."""
        from canonical_registry.chemical_concept_registry.identity_contract import identity_record
        record = self.substances.detail(sid)
        if record is None:
            return None
        graphs = [row["structure_value"] for row in record["structures"] if row["structure_type"] == "SMILES"]
        return identity_record(sid, "Substance", record["preferred_name"],
                               graph=graphs[0] if len(graphs) == 1 else None,
                               aliases=record["aliases"], identifiers=record["identifiers"],
                               sources=record["sources"], validation=record["identity_status"])

    @staticmethod
    def member_target(member, datasets, fingerprints):
        """Resolve a membership only in the snapshot recorded on the edge."""
        for key, digest in fingerprints.items():
            if digest == member["registry_sha256"]:
                registry = Registry(datasets[key].path, live=datasets[key].live)
                if registry.detail(member["substance_id"]):
                    return key
        return None
