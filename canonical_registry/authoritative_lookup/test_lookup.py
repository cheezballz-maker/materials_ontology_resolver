from dataclasses import replace
from hashlib import sha256

import pytest

from canonical_registry.chemistry import describe
from canonical_registry.identity_sufficiency.contract import Evidence, Evaluator, structure_signature
from .lookup import AuthorityRecord, IdentityLookup, SourceReferent
from .matching import ABSENT, AMBIGUOUS, PARTIAL, CanonicalMatching
from .sources import DATA, read
from canonical_registry.chemical_concept_registry.constraints import molecular

FORM_CONTROLS = read(DATA / "form_controls.json")


def proof(graph):
    return {"status": "SUCCESS", "agrees": True, "inchi": graph["inchi"], "inchikey": graph["inchikey"]}


def case(source_smiles="OCC", authority_smiles="CCO", validator=proof, composition=False):
    graph = describe(authority_smiles)
    source = SourceReferent(Evidence("referent", "test:record", "rev", "designated", ()), "synthetic",
                            ("designated",), "", {"CAS": ("64-17-5",)},
                            (structure_signature(describe(source_smiles)),))
    authority = AuthorityRecord("UNII:fixture", "synthetic", "SMILES", authority_smiles, graph["inchikey"],
                                ("Designated",), {"UNII": ("fixture",), "CAS": ("64-17-5",)},
                                "synthetic fixture", "structure", {"sha256": sha256(b"fixture").hexdigest()},
                                complete_composition=composition)
    candidate = {"source_id": "fixture", "substance_type": "chemical", "ingredient_type": "INGREDIENT SUBSTANCE",
                 "chemical_id": "1", "chemical_name": "DESIGNATED", "smiles": authority_smiles,
                 "inchikey": graph["inchikey"], "routes": ["REPORTED_IDENTIFIER:CAS:64-17-5"]}
    return source, authority, candidate, IdentityLookup(Evaluator(validator), {"fixture": [authority]})


@pytest.mark.parametrize("control", FORM_CONTROLS, ids=[c["case"] for c in FORM_CONTROLS])
def test_forms_are_not_collapsed(control):
    source, _, candidate, service = case(control["source"], control["reference"])
    result, receipt, _ = service.evaluate(source, [candidate], 1)
    assert result["eligibility"] == control["expected"]
    if receipt:
        assert receipt["source_revision"] == "rev"
        assert receipt["validation"]["official_inchi"]["agrees"]
    else:
        assert result["reasons"] == ["SOURCE_AND_AUTHORITY_CLAIMS_DISAGREE"]


@pytest.mark.parametrize("rejection", ["truncated", "missing_roles", "misleading_alias", "wrong_namespace",
                                      "fragment", "variable", "original_hold", "wrong_official"])
def test_insufficient_or_bad_evidence_never_qualifies(rejection):
    validator = (lambda graph: {**proof(graph), "inchikey": "different"}) if rejection == "wrong_official" else proof
    source, _, candidate, service = case(validator=validator)
    count = 1
    if rejection == "truncated":
        count = 11
    elif rejection == "missing_roles":
        service.authorities.clear()
    elif rejection == "misleading_alias":
        source = replace(source, evidence=replace(source.evidence, designation="broad label"))
        candidate["routes"].append("REPORTED_ALIAS:NAME:broad label")
    elif rejection == "wrong_namespace":
        candidate["routes"] = ["REPORTED_IDENTIFIER:EC:64-17-5"]
    elif rejection == "fragment":
        candidate["ingredient_type"] = "MOLECULAR FRAGMENT"
    elif rejection == "variable":
        source = replace(source, evidence=replace(source.evidence, material_scope="PREPARATION",
                                                  scope_evidence=("original definition",)))
    elif rejection == "original_hold":
        source = replace(source, evidence=replace(source.evidence, holds=("SOURCE_CONFLICT",)))
    result, _, _ = service.evaluate(source, [candidate], count)
    assert result["eligibility"] != "CANDIDATE_READY"


def test_alias_collision_with_another_structural_form_abstains():
    source, _, candidate, service = case()
    alternate = {**candidate, "chemical_id": "2", "source_id": "other",
                 "smiles": "[13CH3]CO", "inchikey": describe("[13CH3]CO")["inchikey"],
                 "routes": ["REPORTED_ALIAS:NAME:DESIGNATED"]}
    result, receipt, _ = service.evaluate(source, [alternate, candidate], 2)
    assert result["reasons"] == ["ALTERNATE_FORM_NAME_CANDIDATE_UNRESOLVED"]
    assert receipt is None


def test_authoritative_scope_can_bind_without_parser_or_local_graph():
    source, authority, candidate, service = case()
    authority = replace(authority, identifiers={**authority.identifiers, "EC": ("200-578-6",)})
    service.authorities["fixture"] = [authority]
    source = replace(source, evidence=replace(source.evidence, designation="another designation"),
                     definition="Designated", graph_signatures=(),
                     identifiers={**source.identifiers, "EC": ("200-578-6",)})
    result, receipt, _ = service.evaluate(source, [candidate], 1)
    assert result["eligibility"] == "CANDIDATE_READY"
    assert receipt["assertion_type"] == "SOURCE_DEFINITION_AND_TYPED_IDENTIFIER"


def test_complete_composition_still_requires_source_form():
    source, authority, candidate, service = case("CC(=O)[O-].[Na+]", "[Na+].CC(=O)[O-]", composition=True)
    no_graph = replace(source, graph_signatures=(), identifiers={**source.identifiers, "EC": ("200-578-6",)})
    service.authorities["fixture"] = [replace(authority, identifiers={**authority.identifiers, "EC": ("200-578-6",)})]
    result, receipt, _ = service.evaluate(no_graph, [candidate], 1)
    assert result["eligibility"] != "CANDIDATE_READY"
    assert receipt is None


@pytest.mark.parametrize(("route", "ready"), [("preferred", True), ("typed_unii", True), ("alias_only", False),
                                              ("component", False), ("conflicting_graph", False)])
def test_role_bearing_native_authority_requires_binding_and_full_form(route, ready):
    source, authority, candidate, service = case()
    service.authorities["fixture"] = [replace(authority, provenance={
        **authority.provenance, "stage_c_live_native": True})]
    source = replace(source, identifiers={"UNII": ("fixture",)} if route == "typed_unii" else {})
    candidate["routes"] = ["PREFERRED_NAME:NAME:DESIGNATED"]
    if route in {"typed_unii", "alias_only"}:
        source = replace(source, evidence=replace(source.evidence, designation="alternative"))
    if route == "alias_only":
        candidate["routes"] = ["REPORTED_ALIAS:NAME:ALTERNATIVE"]
    if route == "component":
        candidate["ingredient_type"] = "IONIC MOIETY"
    if route == "conflicting_graph":
        source = replace(source, graph_signatures=(structure_signature(describe("COC")),))
    decision, receipt, _ = service.evaluate(source, [candidate], 1)
    assert (decision["eligibility"] == "CANDIDATE_READY") is ready
    if route == "typed_unii":
        assert receipt["qualified_claims"][1]["namespace"] == "UNII"
        assert decision["evidence_pathway"] == "C_IDENTIFIER"
        assert receipt["supporting_source_evidence"]["bound_identifier"] == "fixture"
        assert receipt["supporting_source_evidence"]["binding_value"] is None


@pytest.mark.parametrize(("matches", "expected"), [(0, ABSENT), (1, PARTIAL), (2, AMBIGUOUS)])
def test_partial_route_compares_every_active_definition(matches, expected):
    definition = molecular("CC(O)C(=O)O", "EXPLICITLY_UNSPECIFIED")
    decision = {"eligibility": "CANDIDATE_READY", "resolution_pathway": "CHEMICAL_CONCEPT",
                "specificity": {"partial_definition": definition}}
    service = CanonicalMatching.__new__(CanonicalMatching)
    service.pins = {"ChemicalConcept": {"registry_type": "ChemicalConcept", "snapshot_sha256": "fixture"}}
    service.concepts = [(f"CC_{i:08}", definition) for i in range(matches)]
    result = service.match(decision, None)
    assert result["outcome"] == expected
    assert len(result["proof"]["comparisons"]) == matches
