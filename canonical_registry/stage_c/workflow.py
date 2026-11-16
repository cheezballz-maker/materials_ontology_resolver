"""Resolve qualified source referents in the managed Stage C fixtures."""

from contextlib import closing
from dataclasses import asdict
import json
from time import perf_counter

from canonical_registry.identity_sufficiency.contract import digest
from canonical_registry.chemical_concept_registry.identity_contract import supported_definition
from canonical_registry.authoritative_lookup.lookup import IdentityLookup, normalize
from adapter_registry import AdaptedRecord
from chemical_input_policy import authorize
from correspondence_models import IncomingConcept
from creation_authorization import connect_creation
from creation_transaction import CreationService
from evidence_adapter_contract import EvidencePackage, structural_field
from registry_matching_models import MatchingInput, RetrievalPolicy
from source_concept_models import SourceConcept, SourceRevision, canonical

VERSION = "stage-c-chemical-resolution-v1"


def _adapt(source, decision, receipt):
    evidence = source.evidence
    graph = decision["specificity"]
    key = SourceConcept(evidence.source_reference.partition(":")[0], source.record_type,
                        evidence.source_reference.partition(":")[2] or evidence.referent, "primary-record-referent")
    key.validate()
    support = {"source": evidence.source_reference, "revision": evidence.source_revision,
               "eligibility_digest": decision["evidence_version"]}
    package = EvidencePackage(key.source_system, key.source_record_type, key.source_record_id, support)
    native = decision["evidence_pathway"] == "A_DIRECT_STRUCTURE"
    kind = {"A_DIRECT_STRUCTURE": "EXPLICIT_STRUCTURAL_FIELD_REFERENT",
            "B_NOMENCLATURE": "QUALIFIED_NAME_IDENTITY",
            "C_IDENTIFIER": "INDEPENDENTLY_VALIDATED_IDENTIFIER_MAPPING"}[decision["evidence_pathway"]]
    claim = structural_field(package, "stage-c-validated-graph", graph["smiles"], "$.qualified_identity.smiles",
                             representation="VALIDATED_MOLECULAR_INTERPRETATION")
    # A cross-reference is a rule-established source identity, with its own
    # evidence lineage. It must not be marked as an original supplied field.
    claim.source_provenance.update(origin="SOURCE_PROVIDED" if native else "DERIVED_SOURCE",
                                   interpretation_basis="SOURCE_TYPED_STRUCTURE" if native else "RULE_ESTABLISHED")
    claim.source_provenance["lineage_roots"] = [c.document for c in evidence.claims
                                              if c.claim_id in decision["supporting_claim_ids"]]
    if receipt:
        claim.source_provenance["lineage_roots"].append(receipt["record_reference"])
    package.source_attributes = {"policy": VERSION, "qualification": decision, "authority_receipt": receipt}
    authorize(package)
    binding = {"status": "ESTABLISHED", "kind": kind, "evidence_ids": [claim.evidence_id],
               "document": receipt["record_reference"] if receipt else evidence.source_reference}
    incoming = IncomingConcept(key.concept_id, package, binding,
                               "DEFINED_MULTICOMPONENT_COMPOSITION" if graph["components"] > 1 else "DISCRETE_MOLECULAR",
                               {"referent_key": key.referent_key, "source_revision": evidence.source_revision,
                                "stage_c": VERSION})
    revision = SourceRevision(evidence.source_revision, {"source_evidence": asdict(evidence),
        "record_type": source.record_type, "names": source.names, "definition": source.definition,
        "identifiers": source.identifiers, "graph_signatures": source.graph_signatures})
    return AdaptedRecord(key, revision, MatchingInput(incoming, evidence.designation, evidence_origin=VERSION))


class StageC:
    def __init__(self, permit, concepts, evaluator, authorities, *, lookup_adapter=None, authority_digest=None):
        self.permit = permit
        self.concepts = concepts
        self.lookup = IdentityLookup(evaluator, authorities)
        if lookup_adapter:
            self.lookup = lookup_adapter(self.lookup)
        self.authority_digest = authority_digest
        self.creation = CreationService(permit, evaluator.official_validator)

    def process(self, source, candidates, total, *, authority_source=False, failure_injector=None, replay=False):
        started = perf_counter()
        evidence = source.evidence
        source_key = evidence.source_reference
        source_packet = asdict(source)
        if self.authority_digest is None:
            source_packet.pop("preferred_name_graph_retained")
        authority_packet = self.authority_digest or [asdict(a) for key in sorted(self.lookup.authorities)
                                                     for a in self.lookup.authorities[key]]
        request = digest([VERSION, source_packet, candidates, total, authority_source, authority_packet])
        with closing(connect_creation(self.permit)) as db:
            prior = db.execute("SELECT request_digest,result_json FROM stage_c_request WHERE source_key=?",
                               (source_key,)).fetchone()
        if prior:
            if prior[0] != request:
                raise ValueError("SOURCE_REVISION_OR_EVIDENCE_CHANGED_START_NEW_PINNED_RUN")
            if not replay:
                return {**json.loads(prior[1]), "checkpoint_replay": True}

        tick = perf_counter()
        decision, receipt, evaluated = self.lookup.evaluate(source, candidates, total, authority_source=authority_source)
        scope_seconds = decision.pop("source_identity_safety_seconds", None)
        result = {"source": source_key, "referent": evidence.referent, "revision": evidence.source_revision,
                  "designation": evidence.designation, "source_evidence": asdict(evidence),
                  "candidate_total": total, "candidates": evaluated, "eligibility": decision, "receipt": receipt,
                  "status": "UNRESOLVED", "outcome": "EVIDENCE_NOT_SUFFICIENT", "timings": {
                      "qualification_seconds": perf_counter() - tick}}
        if scope_seconds is not None:
            result["timings"]["source_identity_safety_seconds"] = scope_seconds

        def save(db, creation=None):
            previous = db.execute("SELECT request_digest,result_json FROM stage_c_request WHERE source_key=?",
                                  (source_key,)).fetchone()
            if previous:
                if previous[0] != request:
                    raise ValueError("SOURCE_REVISION_OR_EVIDENCE_CHANGED_START_NEW_PINNED_RUN")
                existing = json.loads(previous[1])
                if creation and existing.get("target") != creation.get("substance_id"):
                    raise ValueError("REPLAY_TARGET_MISMATCH")
                result.clear()
                result.update(existing, checkpoint_replay=True)
                return
            target, event_id, predicate = None, None, None
            if creation:
                result["outcome"] = creation["outcome"]
                result["admission"] = creation["eligibility"]
                result["match"] = creation["matching"]
                result["association"] = creation["association"]
                result["creation_event_id"] = event_id = creation["event_id"]
                result["timings"]["canonical_transaction_seconds"] = creation["transaction_seconds"]
                if creation["association"]["exact_current"]:
                    target = creation["substance_id"]
                    result.update(status="RESOLVED_SUBSTANCE", target=target)
                    predicate = "mapsToSubstance"
            if result["status"] == "RESOLVED_CHEMICAL_CONCEPT":
                predicate = "mapsToChemicalConcept"
            result["timings"]["elapsed_seconds"] = perf_counter() - started
            db.execute("INSERT INTO stage_c_request VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (source_key, evidence.source_revision, request, evidence.designation, result["status"],
                        target, result.get("target") if predicate == "mapsToChemicalConcept" else None,
                        event_id, predicate, canonical(result)))
            if target and receipt and receipt["supporting_source_evidence"].get("binding_value"):
                alias = evidence.designation.strip()
                if alias and not any(ord(c) < 32 for c in alias):
                    db.execute("INSERT OR IGNORE INTO substance_alias VALUES(?,?)", (target, alias))
                    db.execute("INSERT INTO stage_c_exact_alias VALUES(?,?,?,?)",
                               (source_key, target, alias, receipt["receipt_sha256"]))

        if decision["eligibility"] == "CANDIDATE_READY":
            if decision["resolution_pathway"] == "SUBSTANCE":
                normalized = _adapt(source, decision, receipt)
                self.creation._execute(normalized, "stage-c:" + request,
                                       retrieval_policy=RetrievalPolicy(max_candidates=750), finalize=save,
                                       failure_injector=failure_injector)
                return result
            if decision["resolution_pathway"] == "CHEMICAL_CONCEPT":
                self._concept(source, decision, receipt, request, result)
        with closing(connect_creation(self.permit)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            save(db)
        return result

    def _concept(self, source, decision, receipt, request, result):
        definition = decision["specificity"]["partial_definition"]
        if not supported_definition(definition):
            result["outcome"] = "PARTIAL_DEFINITION_UNSUPPORTED"
            return
        e = source.evidence
        namespace, _, record = e.source_reference.partition(":")
        raw = self.concepts.create_or_reuse(
            {"kind": "molecular", "smiles": definition["smiles"], "stereo_state": definition["stereo_state"]},
            e.designation, "stage-c:" + request,
            evidence={"source_revision": e.source_revision, "qualification": decision, "receipt": receipt},
            source_key=(namespace, source.record_type, record or e.referent, "primary-record-referent"),
        )
        result["concept_receipt"] = raw
        result["outcome"] = "CONCEPT_" + raw["outcome"]
        if raw.get("concept_id"):
            result.update(status="RESOLVED_CHEMICAL_CONCEPT", target=raw["concept_id"])
