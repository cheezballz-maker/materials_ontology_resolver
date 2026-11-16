"""Form specificity and complete-graph nonidentity regressions for Stage C v4."""

from dataclasses import replace

import pytest

from canonical_registry.authoritative_lookup.lookup import IdentityLookup
from canonical_registry.authoritative_lookup.sources import cosing_input, read
from canonical_registry.chemistry import describe
from canonical_registry.identity_sufficiency.contract import Claim, Evaluator, WHOLE
from canonical_registry.cosing_pilot.staged_assessment import _bridge
from canonical_registry.stage_c.cohort import DATA
from canonical_registry.stage_c.source_identity_safety import SourceIdentitySafety
from canonical_registry.stage_c.v3_authority import MultiAuthority, retained_source_input
from contextlib import ExitStack
from comparison_session import qualify_source
from correspondence_models import CanonicalCandidate
from registry_matcher import compare_registry_candidate
from ..workflow import _adapt
from .test_source_identity_safety import QualifiedLookup, official, source


class Lookup(QualifiedLookup):
    def __init__(self, graph, authority="PubChem", reason=None):
        self.graph = graph
        self.authority = authority
        self.reason = reason

    def evaluate(self, incoming, candidates, total, *, authority_source):
        decision, receipt, evaluated = super().evaluate(incoming, candidates, total, authority_source=authority_source)
        if self.reason:
            return Evaluator(official).evaluate(replace(incoming.evidence, holds=(self.reason,))), None, evaluated
        return ({**decision, "specificity": describe(self.graph)},
                {**receipt, "assertion_type": "AUTHORITY_PREFERRED_NAME_AND_SOURCE_GRAPH",
                 "authority": self.authority}, evaluated)


@pytest.mark.parametrize("label,graph,authority,expected", [
    ("Amyl acetate", "CCCCCOC(C)=O", "PubChem", "EXACT_FORM_UNSUPPORTED_BY_SOURCE"),
    ("Nicotinamide lactate", "CC(OC(=O)c1cccnc1)C(N)=O", "NCATS GSRS native", "EXACT_FORM_UNSUPPORTED_BY_SOURCE"),
    ("Methyl ammonium", "C[NH3+]", "ChEBI", "EXACT_FORM_UNSUPPORTED_BY_SOURCE"),
    ("Calcium chloride", "[Cl-].[Cl-].[Ca+2]", "ChEBI", "EXACT_FORM_UNSUPPORTED_BY_SOURCE"),
    ("Coordination adduct", "NCCN", "ChEBI", "EXACT_FORM_UNSUPPORTED_BY_SOURCE"),
    ("Methyl acetate", "COC(C)=O", "ChEBI", "EXACT_FORM_ESTABLISHED"),
])
def test_generic_form_obligation(label, graph, authority, expected):
    result, receipt, _ = SourceIdentitySafety(Lookup(graph, authority), Evaluator(official), {}, form_gate=True
                                              ).evaluate(source(label), [], 0)
    assert result["source_identity_safety"]["chemical_form"]["assessment"] == expected
    assert bool(receipt) == (expected == "EXACT_FORM_ESTABLISHED")


@pytest.mark.parametrize("graph", ["CC(=O)OCCN", "C[NH3+].[Cl-]", "C[NH3+]", "CC(=O)OCC[NH3+].[Cl-]"])
def test_source_bound_complete_form_can_satisfy_obligation(graph):
    row = source("Form-sensitive designation")
    c = Claim("spec", "SMILES", graph, WHOLE, "test", "source", ("STRUCTURE", "REFERENT", "SPECIFICATION"),
              "source-document", "complete form", "rev")
    gate = SourceIdentitySafety(Lookup(graph), Evaluator(official), {}, form_gate=True)
    for revision, expected in (("rev", "EXACT_FORM_ESTABLISHED"), ("stale", "EXACT_FORM_UNSUPPORTED_BY_SOURCE")):
        updated = replace(row, evidence=replace(row.evidence, claims=(replace(c, revision=revision),)))
        decision, _, _ = gate.evaluate(updated, [], 0)
        assert decision["source_identity_safety"]["chemical_form"]["assessment"] == expected


@pytest.mark.parametrize("reason,expected", [
    ("COMPETING_AUTHORITY_STRUCTURAL_FORMS", "MULTIPLE_FORMS_PLAUSIBLE"),
    ("SOURCE_AND_AUTHORITY_CLAIMS_DISAGREE", "IDENTITY_CONFLICT"),
    ("WHOLE_REFERENT_BINDING_UNESTABLISHED", "FORM_SCOPE_UNESTABLISHED"),
])
def test_conflict_and_uncertainty_remain_distinct(reason, expected):
    gate = SourceIdentitySafety(Lookup("CCO", reason=reason), Evaluator(official), {}, form_gate=True)
    decision, receipt, _ = gate.evaluate(source("Candidate"), [], 0)
    assert not receipt
    assert decision["source_identity_safety"]["chemical_form"]["assessment"] == expected


def test_pyridoxine_uses_real_saved_parser_and_pubchem_path():
    root = DATA / "restricted_expansion"
    row = next(r for r in read(root / "fresh.json") if r["concept_id"] == "CIC_00019582")
    incoming = retained_source_input(row, cosing_input(row))
    with ExitStack() as stack:
        bridge = _bridge(stack)
        evaluator = Evaluator(bridge.official)
        lookup = MultiAuthority(IdentityLookup(evaluator, {}), bridge.opsin,
                                evidence_root=root / "phase_3_authority")
        old, receipt, _ = SourceIdentitySafety(lookup, evaluator, {}).evaluate(incoming, [], 0)
        assert old["eligibility"] == "CANDIDATE_READY" and receipt["authority_entity"] == "CID:187064"
        current, receipt, _ = SourceIdentitySafety(lookup, evaluator, {}, form_gate=True, name_parser=bridge.opsin
                                                  ).evaluate(incoming, [], 0)
    assert current["eligibility"] == "REVIEW_HOLD" and receipt is None
    assert current["source_identity_safety"]["chemical_form"]["assessment"] == "EXACT_FORM_UNSUPPORTED_BY_SOURCE"


@pytest.mark.parametrize("left,right,expected", [
    ("CC(C)O", "CC(C)=O", "CHEMICALLY_DIFFERENT"),
    ("CC", "C=C", "CHEMICALLY_DIFFERENT"),
    ("CCO", "COC", "CHEMICALLY_DIFFERENT"),
    ("CC(C)=O", "C=C(C)O", "CHEMICALLY_DIFFERENT"),
    ("C[N+](=O)[O-]", "C[N+]([O-])=O", "CHEMICALLY_EQUIVALENT"),
    ("CN", "C[NH3+]", "CHEMICALLY_DIFFERENT"),
    ("CCO", "[13CH3]CO", "CHEMICALLY_DIFFERENT"),
    ("C[C@H](O)CC", "C[C@@H](O)CC", "CHEMICALLY_DIFFERENT"),
    ("C[C@H](O)CC", "CC(O)CC", "CHEMICALLY_UNRESOLVED"),
    ("CN", "C[NH3+].[Cl-]", "CHEMICALLY_DIFFERENT"),
])
def test_registry_distinction_preserves_identity_dimensions(left, right, expected):
    incoming = source("Synthetic graph")
    graph = describe(left)
    incoming = replace(incoming, evidence=replace(incoming.evidence, source_reference="test:graph"))
    decision = {"specificity": graph, "evidence_pathway": "A_DIRECT_STRUCTURE",
                "evidence_version": "test", "supporting_claim_ids": []}
    normalized = _adapt(incoming, decision, None).incoming
    right_scope = "DEFINED_MULTICOMPONENT_COMPOSITION" if "." in right else "DISCRETE_MOLECULAR"
    candidate = CanonicalCandidate("SUB_TEST", "Control", right,
                                   {"document": "registry", "lineage_roots": ["registry"]}, right_scope)
    result = compare_registry_candidate(qualify_source(normalized.concept), {"candidate": candidate, "issues": []},
                                        retain_full=True)
    assert result["chemical_status"] == expected
    if left == "CC(C)O":
        assert result["full_graph_distinction"]["reason"] == "COMPLETE_MOLECULAR_COMPOSITION_DIFFERS"
