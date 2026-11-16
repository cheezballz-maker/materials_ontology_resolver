"""Identity model v2 contract. Chemistry is delegated to the retained validators."""
import json
from .constraints import molecular, EQUIVALENT, ProposalError
from canonical_registry.chemistry import describe

SCHEMA_VERSION = 2
POLICY_VERSION = "molecular-concept-2"


def supported_definition(definition):
    if definition.get("kind") != "molecular":
        return False
    try:
        expected = molecular(definition["smiles"], definition["stereo_state"])
        if definition["stereo_state"] == "EXPLICITLY_UNSPECIFIED":
            expected["stereo_state"] = "EXPLICITLY_UNSPECIFIED"
        return expected == definition
    except (ValueError, KeyError, RuntimeError):
        return False


def preferred_label(definition):
    return definition["smiles"] + " (unassigned stereochemistry)"


def classify(definition=None, *, validation=None, conflicts=False):
    """Consume validated meaning. Retrieval or parse success cannot establish exactness."""
    if conflicts or validation == "INVALID":
        return "INVALID_OR_CONFLICTING_INPUT"
    if definition and definition.get("kind") == "family":
        return "NONCANONICAL_BROAD_TERM"
    if definition and supported_definition(definition):
        return "PARTIALLY_SPECIFIED_MOLECULAR_IDENTITY"
    if validation == "EXACT_IDENTITY_VALIDATED":
        return "EXACT_MOLECULAR_IDENTITY"
    return "UNSUPPORTED_MOLECULAR_INTERPRETATION"


def identity_record(identifier, registry_type, label, *, graph=None, definition=None,
                    aliases=(), identifiers=(), sources=(), evidence=None, validation="UNRESOLVED"):
    """Common projection, with exact aliases kept distinct from Concept alternative labels."""
    dimensions = describe(graph) if graph else {}
    return {
        "canonical_id": identifier, "registry_type": registry_type, "preferred_label": label,
        "alternative_labels": list(aliases), "label_semantics": "SubstanceAlias" if registry_type == "Substance" else "skos:altLabel",
        "molecular_formula": dimensions.get("formula"), "structure": graph, "structure_format": "SMILES" if graph else None,
        "charge": dimensions.get("charge"), "identity_dimensions": dimensions,
        "constraints": definition, "validation_status": validation,
        "source_references": list(sources), "external_identifiers": list(identifiers),
        "evidence": evidence, "schema_version": SCHEMA_VERSION,
    }


def validate_label(label, definition):
    """An incoming label may be a graph or a deterministic equivalent chemical name."""
    from providers import Bridge
    from .constraints import compare_proposals
    proposal = {"kind": "molecular", "smiles": definition["smiles"]}
    try:
        if compare_proposals({"kind": "molecular", "smiles": label}, proposal) == EQUIVALENT:
            return
    except (ValueError, RuntimeError):
        pass
    bridge = Bridge()
    try:
        response = bridge.opsin(label)
        if response["status"] == "SUCCESS" and compare_proposals(
                {"kind": "molecular", "smiles": response["smiles"]}, proposal) == EQUIVALENT:
            return
    finally:
        bridge.close()
    raise ProposalError("LABEL_MEANING_NOT_EQUIVALENT")


def migrate(db):
    """Append compatibility state without rewriting old definitions, labels or IDs."""
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute("CREATE TABLE IF NOT EXISTS identity_model_version (singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL)")
        version = db.execute("SELECT version FROM identity_model_version").fetchone()
        if version and version[0] != SCHEMA_VERSION:
            raise ValueError("UNSUPPORTED_IDENTITY_SCHEMA_VERSION")
        db.execute("""CREATE TABLE IF NOT EXISTS concept_alignment (
            concept_id TEXT PRIMARY KEY REFERENCES concept(concept_id),
            status TEXT NOT NULL CHECK(status IN ('ACTIVE','HISTORICAL_EXCLUDED','REVIEW_REQUIRED')),
            display_label TEXT, reason TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS validated_concept_label (
            concept_id TEXT NOT NULL REFERENCES concept(concept_id), label TEXT NOT NULL,
            PRIMARY KEY(concept_id,label))""")
        rows = db.execute("SELECT concept_id,definition_json FROM concept ORDER BY concept_id").fetchall()
        for sid, raw in rows:
            definition = json.loads(raw)
            active = supported_definition(definition)
            status = "ACTIVE" if active else "HISTORICAL_EXCLUDED" if definition.get("kind") == "family" else "REVIEW_REQUIRED"
            db.execute("INSERT OR IGNORE INTO concept_alignment VALUES(?,?,?,?)",
                       (sid, status, preferred_label(definition) if active else None,
                        "VALIDATED_MOLECULAR_DEFINITION" if active else "OUTSIDE_MOLECULAR_CONCEPT_CONTRACT"))
        db.execute("INSERT OR IGNORE INTO identity_model_version VALUES(1,?)", (SCHEMA_VERSION,))
        db.execute("""CREATE TRIGGER IF NOT EXISTS molecular_concepts_only BEFORE INSERT ON concept
            WHEN json_extract(NEW.definition_json,'$.kind') IS NOT 'molecular'
            BEGIN SELECT RAISE(ABORT,'NONCANONICAL_BROAD_TERM'); END""")
        if not version:
            db.execute("INSERT INTO event(event_type,evidence_json) VALUES('IDENTITY_MODEL_MIGRATION',?)",
                       (json.dumps({"schema_version": SCHEMA_VERSION, "policy": POLICY_VERSION}),))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
