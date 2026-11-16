"""Bounded interpretation adapters and sealed, source-independent molecular evidence."""
from copy import deepcopy
from dataclasses import asdict
from canonical_registry.enrichment.development import open_development  # initializes existing module paths
from adapter_registry import AdaptedRecord, InputValidationError
from correspondence_models import IncomingConcept
from evidence_adapter_contract import EvidencePackage, structural_field, record_identifier
from registry_matching_models import MatchingInput
from source_concept_models import SourceConcept, SourceRevision, digest
from chemistry import describe
from canonical_registry.chemical_concept_registry.constraints import molecular, FAMILIES
from canonical_registry.chemical_concept_registry.unified_chemical import reconcile_graphs

from chemical_input_policy import VERSION, authorize, qualified


class QualificationError(InputValidationError):
    def __init__(self, status, reasons):
        super().__init__(";".join(reasons))
        self.status, self.reasons = status, reasons


class MolecularInputAdapter:
    """Names are chemical claims, structures define graphs, IDs retrieve candidates.

    Supports the existing discrete-molecular contract. Names are interpreted by
    Resolver.evaluate, all supplied graphs are strictly parsed by describe, and
    reconcile_graphs compares claims without synthesizing a new identity.
    """
    def interpret(self, item, local, bridge):
        original = asdict(item)
        if not all(isinstance(value, str) for value in original.values()):
            raise QualificationError("INVALID", ["INPUT_FIELDS_MUST_BE_STRINGS"])
        if any(ord(char) < 32 for value in original.values() for char in value):
            raise QualificationError("INVALID", ["CONTROL_CHARACTERS_IN_INPUT"])
        if bool(item.source_system.strip()) != bool(item.source_record_id.strip()) or not item.referent_key.strip():
            raise QualificationError("INVALID", ["SOURCE_REFERENT_FIELDS_INVALID"])
        names = [name for name in (item.name, item.inci_name) if name.strip()]
        claims, attempts = [], []
        for value, kind in ((item.smiles, "smiles"), (item.inchi, "inchi")):
            if value:
                if len(value) > 1200:
                    raise QualificationError("UNSUPPORTED", ["STRUCTURE_LENGTH_LIMIT"])
                try:
                    claims.append(describe(value, kind))
                except (ValueError, RuntimeError) as error:
                    raise QualificationError("INVALID", ["INVALID_STRUCTURE", str(error)]) from error
        supplied = bool(claims)
        allowed_open = {"SOURCE_INTERPRETATION_INCOMPLETE", "MULTICOMPONENT_SOURCE_INCOMPLETE",
                        "INCHI_WARNING_REQUIRES_REVIEW", "STEREO_UNSPECIFIED"}
        for name in dict.fromkeys(names):
            if name.strip().casefold().replace(" ", "_") in FAMILIES:
                raise QualificationError("NONCANONICAL_BROAD_TERM", ["FAMILY_DEFINITION_EXCLUDED"])
            if len(name) > 1200:
                raise QualificationError("UNSUPPORTED", ["NAME_LENGTH_LIMIT"])
            attempt = local.evaluate(name)
            attempts.append(attempt)
            graph = attempt.get("structure")
            reasons = set(attempt["reason_codes"])
            if attempt["status"] in {"INVALID", "CONFLICT", "OUT_OF_SCOPE"}:
                raise QualificationError(attempt["status"], attempt["reason_codes"])
            if graph is None:
                raise QualificationError("UNRESOLVED", attempt["reason_codes"])
            open_stereo = any(s["specified"] != "Specified" for s in graph["stereo"])
            if open_stereo:
                if (reasons != allowed_open or graph["components"] != 1 or
                        attempt["evidence"]["name_interpretation"].get("diagnostic") != "NAME_UNDERSPECIFIED"):
                    raise QualificationError("UNRESOLVED", attempt["reason_codes"])
                molecular(graph["smiles"])
            else:
                # A deterministic established name and a fully specified form
                # define its graph. The historical source-author tautomer intent
                # obligation adds no missing dimension to that interpretation.
                established = (attempt["evidence"]["name_interpretation"]["status"] == "ESTABLISHED"
                               and attempt.get("form", {}).get("specification") == "SPECIFIED"
                               and not attempt.get("form", {}).get("reason_codes"))
                allowed = {"NO_QUALIFYING_CORROBORATION"}
                if established:
                    allowed.add("SOURCE_TAUTOMER_SPECIFICITY_UNKNOWN")
                if reasons - allowed:
                    raise QualificationError("UNRESOLVED", attempt["reason_codes"])
            claims.append(graph)
        if not claims:
            raise QualificationError("UNRESOLVED", ["NO_INTERPRETABLE_MOLECULAR_ASSERTION"])
        graph = claims[0]
        for other in claims[1:]:
            graph, relation = reconcile_graphs(graph, other)
            if graph is None:
                raise QualificationError("CONFLICT" if relation.startswith("CONFLICT") else "UNRESOLVED", [relation])
        if graph["atoms"] > 100:
            raise QualificationError("UNSUPPORTED", ["INPUT_ATOM_LIMIT"])
        if item.inchikey and item.inchikey != graph["inchikey"]:
            raise QualificationError("CONFLICT", ["SUPPLIED_INCHIKEY_STRUCTURE_MISMATCH"])
        if item.cas or item.ec:
            raise QualificationError("UNRESOLVED", ["IDENTIFIER_REFERENT_REQUIRES_VALIDATION"])
        official = bridge.official(graph)
        if (official.get("status") not in {"SUCCESS", "WARNING"} or not official.get("agrees")
                or official.get("inchi") != graph["inchi"] or official.get("inchikey") != graph["inchikey"]):
            raise QualificationError("UNRESOLVED", ["OFFICIAL_INCHI_NOT_CONFIRMED"])
        label = names[0] if names else graph["smiles"]
        namespace = item.source_system or "ChemicalInputAudit"
        record_id = item.source_record_id or digest(original)
        concept = SourceConcept(namespace, "CHEMICAL_INPUT" if item.source_record_id else "INPUT_AUDIT",
                                record_id, item.referent_key)
        concept.validate()
        package = EvidencePackage(namespace, concept.source_record_type, record_id,
                                  {"input": original, "adapter_version": VERSION})
        field = structural_field(package, "interpreted_graph", graph["smiles"], "$.interpretation",
                                 representation="VALIDATED_MOLECULAR_INTERPRETATION")
        field.source_provenance.update(
            origin="SOURCE_PROVIDED" if supplied else "DERIVED_SOURCE",
            interpretation_basis="SOURCE_TYPED_STRUCTURE" if supplied else "RULE_ESTABLISHED")
        package.source_attributes = {
            "adapter_version": VERSION, "original_input": original, "interpretations": attempts,
            "structure_origin": "SUPPLIED" if supplied else "NAME_DERIVED",
            "official_validation": official,
            "referent_scope": "SOURCE_REFERENT" if item.source_record_id else "INPUT_LEVEL_AUDIT_ONLY",
        }
        authorize(package)
        binding = {"status": "ESTABLISHED", "kind": "EXPLICIT_STRUCTURAL_FIELD_REFERENT" if supplied else "QUALIFIED_NAME_IDENTITY",
                   "evidence_ids": [field.evidence_id], "document": "Typed molecular interpretation " + VERSION}
        incoming = IncomingConcept(concept.concept_id, package, binding,
                                   "DEFINED_MULTICOMPONENT_COMPOSITION" if graph["components"] > 1 else "DISCRETE_MOLECULAR",
                                   {"referent_key": item.referent_key, "input_audit": not bool(item.source_record_id)})
        matching = MatchingInput(incoming, label, official_validation=None, evidence_origin=VERSION)
        return graph, AdaptedRecord(concept, SourceRevision("input:" + digest(original), original), matching)


class InputAdapters:
    def __init__(self):
        self.adapters = {"molecular": MolecularInputAdapter()}

    def register(self, name, adapter):
        if name in self.adapters or not callable(getattr(adapter, "interpret", None)):
            raise ValueError("INVALID_OR_DUPLICATE_INPUT_ADAPTER")
        self.adapters[name] = adapter

    def get(self, name):
        if name not in self.adapters:
            raise ValueError("UNSUPPORTED_INPUT_ADAPTER")
        return self.adapters[name]


class ChemicalInputSourceAdapter:
    """Bridge typed chemical inputs to SubstanceResolver's existing adapter interface."""
    def __init__(self, local, bridge, adapter=None):
        self.local = local
        self.bridge = bridge
        self.adapter = adapter or MolecularInputAdapter()

    def adapt(self, record):
        from .workflow import ChemicalInput
        item = record if isinstance(record, ChemicalInput) else ChemicalInput(**record)
        return self.adapter.interpret(item, self.local, self.bridge)[1]
