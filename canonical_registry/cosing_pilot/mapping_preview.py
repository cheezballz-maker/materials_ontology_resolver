"""Read-only existing-target checks behind the interpreter's chemical eligibility gate."""

from contextlib import closing
import json
from pathlib import Path
import re

from canonical_registry.chemical_concept_registry.constraints import EQUIVALENT, UNRESOLVED, compare, validate
from canonical_registry.chemical_concept_registry.identity_contract import supported_definition
from canonical_registry.enrichment.workflow import ChemicalInput
from canonical_registry.nomenclature_interpretation.preview import ChemicalEligibilityPreview
from canonical_registry.substance_explorer.frozen_sqlite import FrozenSQLite
from canonical_registry.substance_explorer.registry_access import ConceptSnapshot, snapshot_digest
from canonical_registry.substance_explorer.registry_search import ROOT
from registry_identity_adapter import RegistrySnapshot
from registry_matcher import RegistryMatcher
from registry_matching_models import RetrievalPolicy


def development_targets():
    manifest = json.loads((ROOT / "enrichment" / "local" / "registries.json").read_text(encoding="utf-8"))
    paths = {}
    for kind, folder, value in (
        ("Substance", "controlled_identity_reuse", manifest["association"]["path"]),
        ("ChemicalConcept", "chemical_concept_registry", manifest["concept_database"]),
    ):
        path = Path(value).resolve(strict=True)
        if (not re.fullmatch(r"enrichment_[a-f0-9]{32}\.sqlite", path.name)
                or path.parent != (ROOT / folder / "fixtures").resolve()):
            raise ValueError("Expected an existing managed development target database")
        FrozenSQLite(path)
        paths[kind] = path
    return paths


class MappingPreview:
    def __init__(self, bridge):
        self.bridge = bridge
        self.eligibility = ChemicalEligibilityPreview(bridge)
        self.paths = development_targets()
        self.identities = {
            kind: {"registry_type": kind, "registry_key": path.relative_to(ROOT).as_posix(),
                   "snapshot_sha256": snapshot_digest(path)}
            for kind, path in self.paths.items()
        }
        self.substances = None
        self.concepts = None

    def verify_snapshots(self):
        for kind, path in self.paths.items():
            if snapshot_digest(path) != self.identities[kind]["snapshot_sha256"]:
                raise ValueError(f"Target registry changed during preview: {kind}")

    def verify_target(self, proposal):
        kind, identifier = proposal.get("registry_type"), proposal.get("id")
        patterns = {"Substance": r"SUB_[0-9]{8}", "ChemicalConcept": r"CC_[0-9]{8}"}
        if (kind not in self.identities or not isinstance(identifier, str)
                or not re.fullmatch(patterns[kind], identifier)
                or any(proposal.get(k) != v for k, v in self.identities[kind].items())):
            return False
        if snapshot_digest(self.paths[kind]) != self.identities[kind]["snapshot_sha256"]:
            return False
        query = {
            "Substance": "SELECT 1 FROM substance_identity WHERE substance_id=? AND identity_status='ACCEPTED'",
            "ChemicalConcept": "SELECT definition_json FROM concept JOIN concept_alignment USING(concept_id) "
                               "WHERE concept_id=? AND status='ACTIVE'",
        }[kind]
        with closing(FrozenSQLite(self.paths[kind]).connect()) as db:
            row = db.execute(query, (identifier,)).fetchone()
        return bool(row and (kind == "Substance" or supported_definition(json.loads(row[0]))))

    def assess(self, interpretation):
        eligibility = self.eligibility.evaluate(interpretation)
        if not eligibility.route:
            return {"eligibility": None, "disposition": "HELD", "reasons": list(eligibility.reasons)}
        namespace, _, key = interpretation.designation.source_reference.partition(":")
        item = ChemicalInput(interpretation.designation.original_value, source_system=namespace, source_record_id=key)
        graph, source = self.eligibility.adapter.interpret(item, self.eligibility.local, self.bridge)
        if eligibility.route == "SUBSTANCE":
            ids, proof = self._substance(source.incoming)
            kind = "Substance"
        else:
            ids, proof = self._concept(graph)
            kind = "ChemicalConcept"
        result = {"eligibility": eligibility.route, "disposition": "HELD", "reasons": [], "proof": proof}
        if len(ids) == 1:
            proposal = {**self.identities[kind], "id": ids[0]}
            if self.verify_target(proposal):
                result.update(disposition="PROPOSED_EXISTING_TARGET", proposal=proposal)
            else:
                result["reasons"].append("PINNED_EXISTING_TARGET_NOT_VERIFIED")
        return result

    def _substance(self, incoming):
        if self.substances is None:
            snapshot = RegistrySnapshot(self.paths["Substance"], use_derived_cache=False)
            if snapshot.sqlite_integrity != [("ok",)] or snapshot.foreign_key_errors:
                raise ValueError("Pinned Substance snapshot failed integrity checks")
            self.substances = RegistryMatcher(snapshot, official_validator=self.bridge.official)
        match = self.substances.match(incoming, RetrievalPolicy(max_candidates=750))
        eligible = (match["retrieval"]["search_complete"] and match["status"] == "UNIQUE_CANONICAL_MATCH"
                    and match["admission"]["admission_eligible"] and match["matching_proposal"])
        return ([match["unique_matched_substance_id"]] if eligible else []), {
            "match_status": match["status"], "search_complete": match["retrieval"]["search_complete"],
            "admission_eligible": match["admission"]["admission_eligible"],
            "compared": match["uniqueness"]["compared"],
        }

    def _concept(self, graph):
        official = self.bridge.official(graph)
        if official["status"] not in {"SUCCESS", "WARNING"} or not official["agrees"]:
            return [], {"reason": "OFFICIAL_INCHI_NOT_CONFIRMED"}
        if self.concepts is None:
            snapshot = ConceptSnapshot(self.paths["ChemicalConcept"])
            with closing(snapshot.connect()) as db:
                if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchone():
                    raise ValueError("Pinned ChemicalConcept snapshot failed integrity checks")
                rows = db.execute("""SELECT concept_id,definition_json FROM concept JOIN concept_alignment USING(concept_id)
                    WHERE status='ACTIVE' ORDER BY concept_id""")
                self.concepts = [(cid, json.loads(definition)) for cid, definition in rows]
            if any(not supported_definition(d) for _, d in self.concepts):
                raise ValueError("Pinned ChemicalConcept snapshot contains an unsupported active definition")
        definition = validate({"kind": "molecular", "smiles": graph["smiles"]})
        comparisons = [(cid, compare(definition, other)) for cid, other in self.concepts]
        exact = [cid for cid, relation in comparisons if relation == EQUIVALENT]
        unknown = sum(relation == UNRESOLVED for _, relation in comparisons)
        return (exact if len(exact) == 1 and not unknown else []), {
            "comparison_count": len(comparisons), "equivalent_count": len(exact), "unresolved_count": unknown,
            "official_inchi_agrees": True,
        }
