"""Match qualified chemistry against pinned, existing canonical snapshots."""

from contextlib import closing
import json

from canonical_registry.cosing_pilot.mapping_preview import development_targets
from canonical_registry.chemical_concept_registry.constraints import EQUIVALENT, UNRESOLVED, compare
from canonical_registry.chemical_concept_registry.identity_contract import supported_definition
from canonical_registry.enrichment.chemical_qualification import MolecularInputAdapter, QualificationError
from canonical_registry.enrichment.workflow import ChemicalInput
from canonical_registry.substance_explorer.frozen_sqlite import FrozenSQLite
from canonical_registry.substance_explorer.registry_access import ConceptSnapshot, snapshot_digest
from canonical_registry.substance_explorer.registry_search import ROOT
from registry_identity_adapter import RegistrySnapshot
from registry_matcher import RegistryMatcher
from registry_matching_models import RetrievalPolicy

EXACT = "EXISTING_EXACT_MATCH"
PARTIAL = "EXISTING_CHEMICAL_CONCEPT_MATCH"
ABSENT = "QUALIFIED_NO_EXISTING_MATCH"
AMBIGUOUS = "AMBIGUOUS_MATCH"
INSUFFICIENT = "EVIDENCE_INSUFFICIENT"


class CanonicalMatching:
    def __init__(self, bridge):
        self.bridge = bridge
        self.paths = development_targets()
        self.pins = self._digests()
        self.registry = RegistrySnapshot(self.paths["Substance"], use_derived_cache=False)
        if self.registry.sqlite_integrity != [("ok",)] or self.registry.foreign_key_errors:
            raise ValueError("Pinned Substance snapshot failed integrity checks")
        self.matcher = RegistryMatcher(self.registry, official_validator=bridge.official)
        self.authority_matches = {}
        with closing(ConceptSnapshot(self.paths["ChemicalConcept"]).connect()) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Pinned ChemicalConcept snapshot failed integrity checks")
            self.concepts = [(cid, json.loads(definition)) for cid, definition in db.execute(
                "SELECT concept_id,definition_json FROM concept JOIN concept_alignment USING(concept_id) "
                "WHERE status='ACTIVE' ORDER BY concept_id")]
        if any(not supported_definition(d) for _, d in self.concepts):
            raise ValueError("Pinned ChemicalConcept contains an unsupported active definition")
        self.verify()

    def _digests(self):
        return {kind: {"registry_type": kind, "registry_key": path.relative_to(ROOT).as_posix(),
                       "snapshot_sha256": snapshot_digest(path)} for kind, path in self.paths.items()}

    def verify(self):
        if self._digests() != self.pins:
            raise ValueError("Canonical registry changed during matching")

    def _proposal(self, kind, target, proof):
        return {"outcome": EXACT if kind == "Substance" else PARTIAL,
                "proposal": {**self.pins[kind], "id": target}, "proof": proof}

    def match(self, decision, receipt):
        if decision["eligibility"] != "CANDIDATE_READY":
            return {"outcome": INSUFFICIENT, "reasons": decision["reasons"]}
        if decision["resolution_pathway"] == "CHEMICAL_CONCEPT":
            definition = decision["specificity"]["partial_definition"]
            if not supported_definition(definition):
                return {"outcome": INSUFFICIENT, "reasons": ["PARTIAL_DEFINITION_UNSUPPORTED"]}
            comparisons = {cid: compare(definition, other) for cid, other in self.concepts}
            equal = [cid for cid, relation in comparisons.items() if relation == EQUIVALENT]
            proof = {"comparisons": comparisons, "search_complete": True}
            if len(equal) > 1 or UNRESOLVED in comparisons.values():
                return {"outcome": AMBIGUOUS, "proof": proof}
            if equal:
                return self._proposal("ChemicalConcept", equal[0], proof)
            return {"outcome": ABSENT, "registry": self.pins["ChemicalConcept"], "proof": proof}
        if decision["resolution_pathway"] != "SUBSTANCE" or not receipt:
            return {"outcome": INSUFFICIENT, "reasons": ["NO_AUTHORITATIVE_MOLECULAR_STRUCTURE"]}
        claim = receipt["qualified_claims"][0]
        key = receipt["authority"], receipt["authority_entity"], claim["kind"], claim["value"]
        if key not in self.authority_matches:
            self.authority_matches[key] = self._match_authority(*key)
        else:
            self.verify()
        return self.authority_matches[key]

    def _match_authority(self, authority, entity, kind, value):
        # Match the authority's own original structural field. The upstream
        # receipt separately establishes the correspondence to the source.
        item = ChemicalInput(name="", source_system=authority, source_record_id=entity,
                             referent_key="defining-chemical-entity", **{kind.lower(): value})
        try:
            _, source = MolecularInputAdapter().interpret(item, None, self.bridge)
        except QualificationError as exc:
            return {"outcome": INSUFFICIENT, "reasons": exc.reasons}
        match = self.matcher.match(source.incoming, RetrievalPolicy(max_candidates=750))
        proof = {"status": match["status"], "search_complete": match["retrieval"]["search_complete"],
                 "admission_eligible": match["admission"]["admission_eligible"],
                 "admission_reasons": match["admission"]["existing_policy_result"]["reason_codes"],
                 "compared": match["uniqueness"]["compared"], "uniqueness": match["uniqueness"],
                 "candidates": match["candidate_results"],
                 "excluded_by_necessary_condition": match["retrieval"]["excluded_candidate_ids"]}
        target = match["unique_matched_substance_id"]
        if proof["search_complete"] and proof["admission_eligible"]:
            if match["status"] == "UNIQUE_CANONICAL_MATCH" and match["matching_proposal"]:
                with closing(FrozenSQLite(self.paths["Substance"]).connect()) as db:
                    accepted = db.execute("SELECT 1 FROM substance_identity WHERE substance_id=? "
                                          "AND identity_status='ACCEPTED'", (target,)).fetchone()
                if not accepted:
                    raise ValueError("Proposed target missing from pinned accepted registry")
                return self._proposal("Substance", target, proof)
            if match["status"] == "NO_MATCH_IN_SEARCHED_REGISTRY":
                return {"outcome": ABSENT, "registry": self.pins["Substance"], "proof": proof}
        if match["status"] in {"MULTIPLE_CANONICAL_MATCHES", "MATCH_UNRESOLVED", "SOURCE_CONFLICT"}:
            return {"outcome": AMBIGUOUS, "proof": proof}
        return {"outcome": INSUFFICIENT, "proof": proof}
