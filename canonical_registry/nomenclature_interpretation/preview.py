"""Preview chemical eligibility using the existing resolver's qualification gates."""

from dataclasses import dataclass

from canonical_registry.enrichment.chemical_qualification import MolecularInputAdapter, QualificationError
from canonical_registry.enrichment.workflow import ChemicalInput
from canonical_registry.chemical_concept_registry.constraints import molecular
from canonical_registry.substance_explorer.resolution_bridge import OfflineEvidence
from comparison_session import qualify_source
from diagnostic_match_policy import assess_admission
from resolver import Resolver

from .contracts import Category, InterpretationResult, State
from .molecular import reconcile_graphs


@dataclass(frozen=True)
class ChemicalPreview:
    route: str | None
    reasons: tuple[str, ...]


class ChemicalEligibilityPreview:
    """Assess eligibility before registry search. Never turns aliases into direct claims."""

    def __init__(self, bridge):
        self.bridge = bridge
        offline = OfflineEvidence()
        self.local = Resolver(bridge, offline, offline)
        self.adapter = MolecularInputAdapter()

    def evaluate(self, interpretation: InterpretationResult) -> ChemicalPreview:
        if interpretation.state == State.CONFLICT:
            return ChemicalPreview(None, ("INTERPRETATION_CONFLICT",))
        if any(module.whole_referent_graph_unestablished for module in interpretation.modules):
            return ChemicalPreview(None, ("WHOLE_REFERENT_GRAPH_UNESTABLISHED",))
        if any(a.category == Category.STRUCTURAL for a in interpretation.withheld_assertions):
            return ChemicalPreview(None, ("GRAPH_RECONCILIATION_INCOMPLETE",))
        if any(issue.code == "TYPED_STRUCTURE_NOT_VALIDATED" for issue in interpretation.issues):
            return ChemicalPreview(None, ("UNVALIDATED_REPORTED_STRUCTURE",))
        incomplete = {"MOLECULAR_FORMULA_COMPARISON_INCOMPLETE", "SOURCE_DEFINITION_GRAPH_COMPARISON_INCOMPLETE"}
        if reasons := sorted({issue.code for issue in interpretation.issues} & incomplete):
            return ChemicalPreview(None, tuple(reasons))
        name_graphs = [a.value for a in interpretation.assertions if a.method == "OPSIN_THEN_STRICT_RDKIT"]
        if not name_graphs:
            return ChemicalPreview(None, ("PREFERRED_NAME_GRAPH_NOT_ESTABLISHED",))

        # Pass only the original designation. An attached graph is evidence for
        # comparison, without proof that it defines the whole source ingredient.
        reference = interpretation.designation.source_reference or ""
        namespace, sep, record_id = reference.partition(":")
        item = ChemicalInput(interpretation.designation.original_value,
                             source_system=namespace if sep else "", source_record_id=record_id)
        try:
            graph, record = self.adapter.interpret(item, self.local, self.bridge)
            if any(reconcile_graphs(candidate, graph)[1] != "COMPATIBLE" for candidate in name_graphs):
                return ChemicalPreview(None, ("QUALIFIED_GRAPH_DISAGREES_WITH_INTERPRETATION",))
            if any(feature["specified"] != "Specified" for feature in graph["stereo"]):
                molecular(graph["smiles"])
                return ChemicalPreview("CHEMICAL_CONCEPT", ())
        except QualificationError as error:
            return ChemicalPreview(None, tuple(error.reasons))
        except ValueError as error:
            return ChemicalPreview(None, (getattr(error, "code", str(error)),))

        incoming = record.incoming
        source = qualify_source(incoming.concept)
        admission = assess_admission(incoming, source, self.bridge.official)
        if admission["admission_eligible"]:
            return ChemicalPreview("SUBSTANCE", ())
        return ChemicalPreview(None, tuple(admission["existing_policy_result"]["reason_codes"]))
