"""Bounded retrieval from a standalone, frozen SQLite snapshot."""

from contextlib import closing
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from uuid import UUID

from rdkit import Chem
from rdkit import rdBase

from canonical_registry.chemistry import normalize_name, parse
from canonical_registry.controlled_identity_reuse.audit_payload import decode as decode_audit
from canonical_registry.substance_explorer.frozen_sqlite import FrozenSQLite


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "warehouse_admission_consolidation/output/normalized_pilot.sqlite"
MAX_QUERY = 1200
MAX_ATOMS = 100
PAGE_SIZE = 20
KEY = re.compile(r"[A-Z]{14}-[A-Z]{10}-[A-Z]", re.I)
IDENTIFIERS = {
    "inchikey": "InChIKey", "inchi": "InChI", "pubchemcid": "PubChemCID",
    "cid": "PubChemCID", "chebiid": "ChEBIID", "chebi": "ChEBIID",
    "cas": "CASRegistryNumber", "casregistrynumber": "CASRegistryNumber",
    "ec": "ECNumber", "ecnumber": "ECNumber",
}
LABEL_FIELDS = (
    "substance_master_name_en", "compound_name", "iupac_name", "scientificname",
    "jchem_name", "cheman_name_en", "cas_scientificname", "inci_name",
)


@dataclass(frozen=True)
class Query:
    raw: str
    kind: str
    value: str
    identifier_type: str = ""


class StructureQueryLimit(ValueError):
    """The interactive input exceeds its resource envelope."""


def interpret(raw):
    value = raw.strip()
    if not value or len(value) > MAX_QUERY or any(ord(ch) < 32 for ch in value):
        raise ValueError(f"Enter one line of text, up to {MAX_QUERY:,} characters.")
    prefix, sep, payload = value.partition(":")
    prefix = prefix.casefold()
    if sep and prefix in {"name", "smiles", "patsnap", "formula", *IDENTIFIERS}:
        value = payload.strip()
        if not value:
            raise ValueError("Enter a value after the prefix.")
        if prefix in IDENTIFIERS:
            kind = IDENTIFIERS[prefix]
            if kind == "InChIKey":
                value = value.upper()
                if not KEY.fullmatch(value):
                    raise ValueError("Enter a full InChIKey.")
            if kind == "ChEBIID":
                value = "CHEBI:" + value.upper().removeprefix("CHEBI:")
            return Query(raw, "identifier", value, kind)
        return Query(raw, prefix, normalize_name(value) if prefix == "name" else value)
    if re.fullmatch(r"SUB_\d{8}", value, re.I | re.ASCII):
        return Query(raw, "canonical ID", value.upper())
    if KEY.fullmatch(value):
        return Query(raw, "identifier", value.upper(), "InChIKey")
    if value.startswith(("InChI=1S/", "InChI=1/")):
        return Query(raw, "identifier", value, "InChI")
    try:
        if str(UUID(value)) == value.lower():
            return Query(raw, "patsnap", value.lower())
    except ValueError:
        pass
    # Bare tokens can be chemical names as well as valid SMILES (e.g. CO).
    return Query(raw, "name", normalize_name(value))


def proposed_smiles(value):
    with rdBase.BlockLogs():
        mol = parse(value)
    if mol.GetNumAtoms() > MAX_ATOMS:
        raise StructureQueryLimit(f"The interactive comparison limit is {MAX_ATOMS} atoms.")
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)


class Registry(FrozenSQLite):
    def __init__(self, path=None, *, live=False):
        super().__init__(path or os.environ.get("SUBSTANCE_EXPLORER_DB") or DEFAULT_DB, live=live)
        with closing(self.connect()) as db:
            self.objects = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_schema WHERE type IN ('table','view')"
            )}
            for table, columns in (
                ("substance_identity", "substance_id, preferred_name, identity_status"),
                ("substance_alias", "substance_id, alias"),
                ("substance_identifier", "substance_id, identifier_type, identifier_value"),
                ("substance_structure", "substance_id, structure_type, structure_value"),
            ):
                db.execute(f"SELECT {columns} FROM {table} LIMIT 0")
            self.count = db.execute("SELECT count(*) FROM substance_identity").fetchone()[0]

    def search(self, query, page=0, size=PAGE_SIZE, *, connectivity_key=None, source_linked=None):
        """Return a stable candidate page and whether another page exists."""
        if page < 0 or not 1 <= size <= 50:
            raise ValueError("Invalid candidate page.")
        value = query.value
        if query.kind == "browse":
            routes = "SELECT substance_id, 'Registry entry' basis, 0 rank FROM substance_identity"
            params = {}
        elif query.kind == "formula":
            routes = """SELECT substance_id, 'Formula of stored SMILES' basis, 0 rank FROM substance_structure
                        WHERE structure_type='SMILES' AND molecular_formula(structure_value)=:value"""
            params = {"value": value}
        elif query.kind == "name":
            routes = """
                SELECT substance_id, 'Preferred name (exact)' basis, 0 rank FROM substance_identity WHERE fold(preferred_name)=:name
                UNION ALL SELECT substance_id, 'Validated alias (exact)', 1 FROM substance_alias WHERE fold(alias)=:name
                UNION ALL SELECT substance_id, 'Preferred name (contains)', 2 FROM substance_identity
                  WHERE instr(fold(preferred_name),:name)>0 AND fold(preferred_name)<>:name
                UNION ALL SELECT substance_id, 'Validated alias (contains)', 3 FROM substance_alias
                  WHERE instr(fold(alias),:name)>0 AND fold(alias)<>:name
            """
            params = {"name": value.casefold()}
        elif query.kind == "canonical ID":
            routes = "SELECT substance_id, 'Canonical ID' basis, 0 rank FROM substance_identity WHERE substance_id=:value"
            params = {"value": value}
        elif query.kind == "identifier":
            routes = """SELECT substance_id, identifier_type || ' identifier' basis, 0 rank FROM substance_identifier
                        WHERE identifier_type=:type AND identifier_value=:value"""
            params = {"type": query.identifier_type, "value": value}
        elif query.kind == "smiles":
            routes = """
                SELECT substance_id, 'Stored isomeric SMILES' basis, 0 rank FROM substance_structure
                  WHERE structure_type='SMILES' AND structure_value=:value
                UNION ALL SELECT substance_id, 'InChIKey connectivity block', 1 FROM substance_identifier
                  WHERE identifier_type='InChIKey' AND substr(identifier_value,1,14)=:key
            """
            params = {"value": proposed_smiles(value), "key": connectivity_key}
        elif query.kind == "patsnap":
            if not {"source_concept", "current_exact_association"} <= self.objects:
                return [], False
            routes = """
                SELECT a.substance_id, 'PatSnap source reference' basis, 0 rank FROM source_concept c
                JOIN current_exact_association a USING(concept_id)
                WHERE c.source_system='PatSnapWarehouse' AND c.source_record_id=:value
            """
            params = {"value": value}
        else:
            raise ValueError("Unsupported query type.")
        source_filter = ""
        if source_linked is not None:
            if "current_exact_association" in self.objects:
                source_filter = """WHERE EXISTS (SELECT 1 FROM current_exact_association a
                                    WHERE a.substance_id=i.substance_id) = :source_linked"""
                params["source_linked"] = source_linked
            elif source_linked:
                return [], False
        with closing(self.connect()) as db:
            if query.kind == "formula":
                from canonical_registry.substance_explorer.structure_display import molecular_formula
                db.create_function("molecular_formula", 1, molecular_formula, deterministic=True)
            rows = db.execute(f"""
                WITH hits AS ({routes}), grouped AS (
                    SELECT substance_id, min(rank) rank, group_concat(DISTINCT basis) match_basis
                    FROM hits GROUP BY substance_id
                )
                SELECT i.*, g.match_basis,
                  (SELECT structure_value FROM substance_structure s WHERE s.substance_id=i.substance_id
                   AND s.structure_type='SMILES' ORDER BY structure_value LIMIT 1) smiles
                FROM grouped g JOIN substance_identity i USING(substance_id)
                {source_filter}
                ORDER BY g.rank, fold(i.preferred_name), i.substance_id LIMIT :limit OFFSET :offset
            """, {**params, "limit": size + 1, "offset": page * size}).fetchall()
        return [dict(r) for r in rows[:size]], len(rows) > size

    def source_record(self, source_id):
        if "warehouse_pilot" not in self.objects:
            return None
        with closing(self.connect()) as db:
            row = db.execute("""
                SELECT sample_id, original_substance_id, record_json FROM warehouse_pilot
                WHERE original_substance_id=? LIMIT 1
            """, (source_id,)).fetchone()
        if row is None:
            return None
        raw = json.loads(row["record_json"])
        return {
            "sample_id": row["sample_id"], "original_substance_id": row["original_substance_id"],
            "source_labels": {key: raw[key] for key in LABEL_FIELDS if raw.get(key)},
        }

    def detail(self, sid):
        with closing(self.connect()) as db:
            row = db.execute("SELECT * FROM substance_identity WHERE substance_id=?", (sid,)).fetchone()
            if not row:
                return None
            result = dict(row)
            result["cuma_indices"] = []
            if "substance_reconciliation" in self.objects:
                result["cuma_indices"] = [r[0] for r in db.execute(
                    "SELECT cuma_index FROM substance_reconciliation "
                    "WHERE substance_id=? AND resolution_status='EXACT' ORDER BY cuma_index", (sid,))]
            result["aliases"] = [r[0] for r in db.execute(
                "SELECT alias FROM substance_alias WHERE substance_id=? ORDER BY alias", (sid,))]
            for table, key in (("substance_identifier", "identifier"), ("substance_structure", "structure")):
                result[key + "s"] = [dict(r) for r in db.execute(
                    f"SELECT {key}_type, {key}_value FROM {table} WHERE substance_id=? ORDER BY 1,2", (sid,))]
            result["sources"] = []
            if {"source_concept", "current_exact_association", "concept_resolution_event"} <= self.objects:
                result["sources"] = [dict(r) for r in db.execute("""
                    SELECT c.source_system, c.source_record_type, c.source_record_id, c.referent_key,
                      a.association_type, a.association_status, a.resolution_event_id,
                      e.outcome, e.reason_codes
                    FROM current_exact_association a JOIN source_concept c USING(concept_id)
                    JOIN concept_resolution_event e ON e.event_id=a.resolution_event_id
                    WHERE a.substance_id=? ORDER BY c.source_system,c.source_record_id,c.referent_key
                """, (sid,))]
        for source in result["sources"]:
            record = self.source_record(source["source_record_id"]) if source["source_system"] == "PatSnapWarehouse" else None
            source["source_labels"] = record["source_labels"] if record else {}
        return result

    def audit(self, sid, event_id):
        """Read one matching event, only for the selected record's current link."""
        with closing(self.connect()) as db:
            row = db.execute("""
                SELECT e.event_id, e.timestamp, e.operation, e.outcome, e.matching_status,
                  e.admission_status, e.reason_codes, e.decision_json
                FROM concept_resolution_event e JOIN current_exact_association a
                ON a.resolution_event_id=e.event_id WHERE a.substance_id=? AND e.event_id=?
            """, (sid, event_id)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["decision_json"] = decode_audit(db, result["decision_json"])
        return result
