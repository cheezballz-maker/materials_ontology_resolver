from contextlib import ExitStack
from dataclasses import replace

import pytest

from canonical_registry.authoritative_lookup.lookup import IdentityLookup
from canonical_registry.authoritative_lookup.sources import cosing_input, read
from canonical_registry.cosing_pilot.staged_assessment import _bridge
from canonical_registry.identity_sufficiency.contract import Evaluator
from ..captures import inputs
from ..source_identity_safety import SourceIdentitySafety
from ..v3_authority import retained_source_input
from .stereo_binding import StereoSpeciesBinding, systematic_name
from .v4 import ROOT


@pytest.fixture(scope="module")
def nonadienol():
    rows, warehouse, _ = inputs(ROOT)
    row = next(item for item in rows if item["concept_id"] == "CIC_00006353")
    source = retained_source_input(row, cosing_input(row))
    total, candidates = warehouse[row["concept_id"]]
    references = {"28069-72-9": read(ROOT / "reference_capture.json")["28069-72-9"]}
    with ExitStack() as stack:
        bridge = _bridge(stack)
        yield source, candidates, total, references, bridge


def qualification(case, *, improved=True, source=None, candidates=None, total=None, references=None):
    original, saved_candidates, saved_total, saved_refs, bridge = case
    refs = saved_refs if references is None else references
    evaluator = Evaluator(bridge.official)
    lookup = IdentityLookup(evaluator, {})
    if improved:
        lookup.rejected = []
        lookup = StereoSpeciesBinding(lookup, evaluator, refs, bridge.opsin)
    engine = SourceIdentitySafety(lookup, evaluator, refs, form_gate=True, name_parser=bridge.opsin)
    return engine.evaluate(source or original, saved_candidates if candidates is None else candidates,
                           saved_total if total is None else total)


def test_same_evidence_baseline_and_improved(nonadienol):
    baseline, receipt, _ = qualification(nonadienol, improved=False)
    assert baseline["reasons"] == ["NO_SUFFICIENT_EVIDENCE_PATH"] and receipt is None
    decision, receipt, _ = qualification(nonadienol)
    assert decision["eligibility"] == "CANDIDATE_READY"
    assert decision["specificity"]["inchikey"] == "AMXYRHBJZOVHOL-ODYTWBPASA-N"
    assert decision["source_identity_safety"]["chemical_form"]["assessment"] == "EXACT_FORM_ESTABLISHED"
    assert receipt["supporting_source_evidence"]["binding_value"] == nonadienol[0].evidence.designation
    assert qualification(nonadienol, references={})[1] is None


@pytest.mark.parametrize("name", ["NONADIENOL", "2-trans-nonadienol", "2-trans, 3-cis-nonadienol",
                                  "2-trans, 8-cis-nonadienol", "2-trans, 6-cis-nonadienol mixture",
                                  "2-trans, 6-cis-nonadienol acetate"])
def test_ambiguous_or_outside_grammar(name):
    assert systematic_name(name) is None


def test_generic_normalization():
    assert systematic_name("2-cis, 5-trans-octadienol") == "(2Z,5E)-octa-2,5-dien-1-ol"


def test_wrong_stereoisomer_and_incomplete_candidate_search_are_withheld(nonadienol):
    source, candidates, total, _, _ = nonadienol
    wrong = "2-CIS, 6-CIS-NONADIENOL"
    claims = tuple(replace(claim, value=wrong) if claim.claim_id == "designation" else claim
                   for claim in source.evidence.claims)
    reversed_source = replace(source, evidence=replace(source.evidence, designation=wrong, claims=claims))
    assert qualification(nonadienol, source=reversed_source)[1] is None
    assert qualification(nonadienol, total=total + 1)[1] is None
    opposite = [{**c, "smiles": "C/C=C/CC/C=C/CO"} for c in candidates]
    assert qualification(nonadienol, candidates=opposite)[1] is None
