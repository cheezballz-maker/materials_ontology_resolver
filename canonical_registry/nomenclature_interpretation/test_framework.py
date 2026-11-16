"""Exercise warehouse replay, evidence boundaries and competing interpretations."""

from dataclasses import replace

import pytest

from .contracts import (
    Assertion, Category, Evidence, EvidenceRole, InterpretationInput, ModuleResult, ReportedFunction,
    ReportedIdentifier, State, StructureKind, TypedStructure,
)
from .evaluate_sample import sampled_inputs
from .framework import InterpretationFramework


def item(name, *smiles):
    return InterpretationInput(
        Evidence(name, "name", "test:record"),
        tuple(TypedStructure(StructureKind.SMILES, Evidence(s, "structure", f"test:{i}"))
              for i, s in enumerate(smiles)),
    )


def modules(result):
    return {module.module for module in result.modules}


def graphs(assertions):
    return [a for a in assertions if a.category == Category.STRUCTURAL]


@pytest.fixture(scope="module")
def sample_results():
    from providers import Bridge

    bridge = Bridge()
    try:
        framework = InterpretationFramework(name_parser=bridge)
        return {record.designation.original_value: framework.interpret(record) for record in sampled_inputs()}
    finally:
        bridge.close()


@pytest.mark.parametrize(("name", "state", "expected_modules"), [
    ("GLYCERIN", State.VALIDATED, {"molecular_chemical"}),
    ("LACTIC ACID", State.PARTIAL, {"molecular_chemical"}),
    ("DISODIUM EDTA", State.PARTIAL, {"molecular_chemical"}),
    ("CI 77891", State.PARTIAL, {"colorant", "molecular_chemical"}),
    ("TITANIUM DIOXIDE", State.CONFLICT, {"inorganic_mineral", "molecular_chemical"}),
    ("ACRYLATES COPOLYMER", State.PARTIAL, {"polymer_silicone"}),
    ("ALOE BARBADENSIS LEAF JUICE", State.PARTIAL, {"botanical", "preparation_mixture"}),
    ("ALCOHOL DENAT.", State.PARTIAL, {"preparation_mixture"}),
    ("HYDROLYZED WHEAT PROTEIN", State.PARTIAL, {"biological_biotechnological", "preparation_mixture"}),
])
def test_real_sample_routing(sample_results, name, state, expected_modules):
    result = sample_results[name]
    assert result.state == state
    assert modules(result) == expected_modules
    assert result.designation.source_reference.startswith("mse_dwd.dwd_mse_cosmetics_incis:")


def test_real_sample_preserves_evidence_and_scope(sample_results):
    glycerin = sample_results["GLYCERIN"]
    assert {a.value["smiles"] for a in graphs(glycerin.assertions)} == {"OCC(O)CO"}
    assert len(glycerin.graph_comparisons) == 3
    assert all(pair.relation == "COMPATIBLE" for pair in glycerin.graph_comparisons)
    assert all(a.evidence_role == EvidenceRole.CANDIDATE_ONLY for a in graphs(glycerin.assertions))
    assert "OPSIN_THEN_STRICT_RDKIT" in {a.method for a in graphs(glycerin.assertions)}

    lactic = sample_results["LACTIC ACID"]
    assert all(a.value["stereo"][0]["specified"] == "Unspecified" for a in graphs(lactic.assertions))

    edta = sample_results["DISODIUM EDTA"]
    assert len(graphs(edta.assertions)) == 2
    assert all(a.value["components"] == 3 and a.value["charge"] == 0 for a in graphs(edta.assertions))
    assert any(a.evidence.original_value.endswith(".[Na+].[Na+]") for a in graphs(edta.assertions))
    assert any(a.value == {"component": "sodium", "count": 2} for a in edta.assertions)

    ci = sample_results["CI 77891"]
    assert any(a.category == Category.IDENTIFIER and a.value == "77891" for a in ci.assertions)
    assert not graphs(ci.assertions) and len(graphs(ci.withheld_assertions)) == 1
    assert [role.reported_function for role in ci.functions] == ["COLORANT", "COLORANT"]
    assert ci.functions[0].evidence.field != ci.functions[1].evidence.field

    titanium = sample_results["TITANIUM DIOXIDE"]
    assert not graphs(titanium.assertions) and len(graphs(titanium.withheld_assertions)) == 2
    assert {a.method for a in graphs(titanium.withheld_assertions)} == {
        "OPSIN_THEN_STRICT_RDKIT", "STRICT_RDKIT_STRUCTURE",
    }
    assert any(issue.code == "CONFLICTING_STRUCTURE_DIMENSIONS" for issue in titanium.issues)

    aloe = sample_results["ALOE BARBADENSIS LEAF JUICE"]
    assert any(a.value == "http://purl.obolibrary.org/obo/PO_0025034" for a in aloe.assertions)
    assert any(a.predicate == "reported_taxon_text" and a.evidence_role == EvidenceRole.CANDIDATE_ONLY
               for a in aloe.assertions)
    assert not graphs(aloe.assertions)


@pytest.mark.parametrize(("name", "expected"), [
    ("PEG-8 LAURATE", {"polymer_silicone", "lipid_surfactant"}),
    ("IRON OXIDE PIGMENT", {"inorganic_mineral", "colorant"}),
    ("C.I. Acid Blue 52", {"colorant"}),
    ("CALCIUM CHLORIDE DIHYDRATE", {"inorganic_mineral"}),
    ("Rosa canina seed oil", {"botanical", "preparation_mixture"}),
])
def test_specialists_overlap_outside_cosmetics(name, expected):
    result = InterpretationFramework().interpret(item(name))
    assert modules(result) == expected
    assert result.state == State.PARTIAL
    assert not graphs(result.assertions)


def test_fallback_keeps_designation_and_reported_context_separate():
    base = item("  Unclassified Designation QZ  ")
    evidence = Evidence("ANTIOXIDANT", "reported_use", "food:123")
    designation = replace(base, functions=(ReportedFunction(evidence, "food formulation", "urn:test:role"),))
    result = InterpretationFramework().interpret(designation)
    assert result.designation == base.designation
    assert result.state == State.UNINTERPRETED and modules(result) == {"generic_ingredient"}
    assert not result.assertions and not result.withheld_assertions
    role, = result.functions
    assert (role.application_context, role.reported_function, role.vocabulary_reference, role.qualification) == (
        "food formulation", "ANTIOXIDANT", "urn:test:role", "REPORTED",
    )
    assert role.evidence is evidence


def test_structure_is_never_cleaned_or_replaced_by_identifier():
    original = r"F/C=C\F"
    result = InterpretationFramework().interpret(item("difluoroethene", original))
    graph, = graphs(result.assertions)
    assert graph.evidence.original_value == original
    assert graph.value["stereo"][0]["specified"] == "Specified"

    malformed = "O=[TI]=O"
    invalid = InterpretationFramework().interpret(item("Arbitrary Designation", malformed))
    assert invalid.state == State.UNINTERPRETED and not graphs(invalid.assertions)
    assert invalid.issues[0].evidence[0].original_value == malformed

    identifier_only = replace(item("Arbitrary Designation"), identifiers=(
        ReportedIdentifier("CAS", Evidence("56-81-5", "reported_cas")),
    ))
    result = InterpretationFramework().interpret(identifier_only)
    assert result.state == State.UNINTERPRETED and modules(result) == {"generic_ingredient"}
    assert result.assertions[0].evidence_role == EvidenceRole.CANDIDATE_ONLY


def test_compatible_stereo_refinement_keeps_both_without_choosing():
    result = InterpretationFramework().interpret(item("Example", "CC(O)C(=O)O", "C[C@@H](O)C(=O)O"))
    assert result.state == State.PARTIAL
    assert result.graph_comparisons[0].relation == "RIGHT_MORE_SPECIFIC"
    assert not graphs(result.assertions) and len(graphs(result.withheld_assertions)) == 2


def test_graph_and_identifier_conflicts():
    framework = InterpretationFramework()
    opposite = framework.interpret(item("Example", r"F/C=C\F", "F/C=C/F"))
    assert opposite.state == State.CONFLICT and not graphs(opposite.assertions)
    assert any(i.code == "CONFLICTING_STEREOCHEMISTRY" for i in opposite.issues)

    graph_key_disagreement = framework.interpret(replace(item("Example", "O"), identifiers=(
        ReportedIdentifier("InChIKey", Evidence("LFQSCWFLJHTTHZ-UHFFFAOYSA-N", "source_key")),
    )))
    assert graph_key_disagreement.state == State.CONFLICT
    assert any(i.code == "INCHIKEY_DISAGREES_WITH_ALL_GRAPHS" for i in graph_key_disagreement.issues)
    assert not graphs(graph_key_disagreement.assertions)
    assert any(a.category == Category.IDENTIFIER for a in graph_key_disagreement.withheld_assertions)

    composition_disagreement = framework.interpret(item("DISODIUM EDTA", "CCO"))
    assert composition_disagreement.state == State.CONFLICT
    assert any(i.code == "GRAPH_DISAGREES_WITH_NAMED_COMPOSITION" for i in composition_disagreement.issues)
    assert not graphs(composition_disagreement.assertions)


def test_molecular_graph_cannot_replace_a_preparation():
    result = InterpretationFramework().interpret(item("ALCOHOL DENAT.", "CCO"))
    assert result.state == State.PARTIAL
    assert modules(result) == {"molecular_chemical", "preparation_mixture"}
    assert not graphs(result.assertions) and len(graphs(result.withheld_assertions)) == 1
    assert result.issues[0].code == "WHOLE_REFERENT_GRAPH_UNESTABLISHED"


def test_extension_conflicts_are_symmetric_and_nonconflicting_facets_survive():
    class FixtureInterpreter:
        def __init__(self, name, value):
            self.name = name
            self.value = value

        def interpret(self, record):
            return ModuleResult(self.name, State.VALIDATED, assertions=(
                Assertion(Category.MATERIAL, "reported_form", self.value, EvidenceRole.DEFINING,
                          record.designation, self.name, exclusive_slot="single_form_fixture"),
                Assertion(Category.NOMENCLATURE, "recognized_notation", self.name,
                          EvidenceRole.SUPPORTING, record.designation, self.name),
            ))

    pair = FixtureInterpreter("A", "liquid"), FixtureInterpreter("B", "solid")
    for order in (pair, pair[::-1]):
        result = InterpretationFramework(interpreters=order).interpret(item("Fixture Designation"))
        assert result.state == State.CONFLICT
        assert result.issues[0].code == "CONTRADICTORY_EXCLUSIVE_ASSERTIONS"
        assert {a.value for a in result.withheld_assertions} == {"liquid", "solid"}
        assert {a.value for a in result.assertions} == {"A", "B"}
