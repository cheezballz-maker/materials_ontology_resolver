"""Focused controls for source adaptation, broader grammar and preview boundaries."""

from dataclasses import replace

import pytest

from .contracts import Category, Evidence, InterpretationInput, ReportedFunction
from .cosing_preview_adapter import COSMETICS_FUNCTIONS, adapt_cosing_preview
from .framework import InterpretationFramework
from .preview import ChemicalEligibilityPreview
from providers import Bridge


def interpret(name, definition=None):
    item = InterpretationInput(
        Evidence(name, "designation"),
        source_definition=Evidence(definition, "definition") if definition else None,
    )
    return InterpretationFramework().interpret(item)


def test_source_adapter_uses_original_alias_and_keeps_role_occurrences():
    row = {"inci_id": "example", "inci": "CI 77891", "description": "Original\nsource",
           "functions": '["COLORANT","COLORANT","SURFACTANT - CLEANSING","UNKNOWN ROLE"]',
           "alias_claims": [{"inci_alias_id": "alias", "alias_type": "SMILES", "alias": "O=[Ti]=O",
                             "normalized_alias": "O=[TI]=O", "source": "example"}]}
    item = adapt_cosing_preview(row)
    assert item.source_definition.original_value == "Original\nsource"
    assert item.structures[0].evidence.original_value == "O=[Ti]=O"
    framework = InterpretationFramework(function_vocabularies={"cosmetics": COSMETICS_FUNCTIONS})
    result = framework.interpret(item)
    assert result.designation.source_reference == "mse_dwd.dwd_mse_cosmetics_incis:example"
    assert [role.qualification for role in result.functions] == [
        "VOCABULARY_VALIDATED", "VOCABULARY_VALIDATED", "VOCABULARY_COMPONENTS_VALIDATED", "LABEL_UNMAPPED",
    ]
    assert result.functions[0].qualified_vocabulary_labels == ("COSMETIC COLORANT",)
    assert result.functions[0].evidence.field != result.functions[1].evidence.field
    assert result.functions[2].qualified_vocabulary_labels == ("SURFACTANT", "CLEANSING")
    assert all(a.category != Category.STRUCTURAL for a in result.assertions)
    food = replace(item, functions=(ReportedFunction(Evidence("COLORANT", "reported"), "food"),))
    assert framework.interpret(food).functions[0].qualification == "REPORTED"
    assert framework.interpret(food).modules == result.modules


def test_botanical_preparation_and_taxon_scope():
    result = interpret("Rosa canina (rose) fruit/seed extract")
    iris = {a.value for a in result.assertions if a.predicate == "source_anatomical_structure"}
    assert iris == {"http://purl.obolibrary.org/obo/PO_0009001", "http://purl.obolibrary.org/obo/PO_0009010"}
    assert any(a.predicate == "reported_botanical_preparation" and a.value == "extract" for a in result.assertions)
    coral = interpret("Leather coral extract", "An extract of the animal Sinularia sandensis.")
    assert {m.module for m in coral.modules} == {"preparation_mixture"}
    plant = interpret("Helianthus tuberosus extract", "Extract of the whole plant Helianthus tuberosus.")
    assert any(a.predicate == "reported_taxon_text" for a in plant.assertions)
    assert all(a.predicate != "source_anatomical_structure" for a in plant.assertions)


def test_complex_inorganic_labels_preserve_whole_wording():
    oxide = interpret("ALUMINIUM/MAGNESIUM/ZINC OXIDE")
    assert {(a.predicate, a.value) for a in oxide.assertions} == {
        ("reported_inorganic_multimetal_oxide", "ALUMINIUM/MAGNESIUM/ZINC OXIDE"),
    }
    salt = interpret("ZINC CHLORIDE HYDROXIDE")
    assert any(a.value == "ZINC CHLORIDE HYDROXIDE" for a in salt.assertions)
    assert all(m.whole_referent_graph_unestablished for m in oxide.modules + salt.modules)
    organic = interpret("DIHYDROXYETHYL TALLOWAMINE OXIDE")
    assert "inorganic_mineral" not in {m.module for m in organic.modules}


def test_colorant_and_polymer_notation_do_not_infer_composition():
    color = interpret("C.I.123456:1")
    assert [(a.predicate, a.value, a.evidence_role) for a in color.assertions] == [
        ("ColourIndex", "123456:1", "CANDIDATE_ONLY"),
    ]
    lake = interpret("ACID BLUE 9 ALUMINUM LAKE")
    assert {a.predicate for a in lake.assertions} == {"ColourIndexGenericName", "reported_colorant_qualifier"}
    polymer = interpret("PEG/PPG-23/23 NYLON-6 CROSSPOLYMER")
    assert ("reported_polyether_grade", "PEG/PPG-23/23") in {(a.predicate, a.value) for a in polymer.assertions}
    assert ("reported_polymer_designation_number", "NYLON-6") in {(a.predicate, a.value) for a in polymer.assertions}
    assert all(a.category != Category.STRUCTURAL for a in polymer.assertions)


@pytest.fixture(scope="module")
def engine():
    bridge = Bridge()
    try:
        yield InterpretationFramework(name_parser=bridge), ChemicalEligibilityPreview(bridge)
    finally:
        bridge.close()


@pytest.mark.parametrize(("name", "route", "reason"), [
    ("water", "SUBSTANCE", None),
    ("butan-2-ol", "CHEMICAL_CONCEPT", None),
    ("lauryl isostearate", None, "WHOLE_REFERENT_GRAPH_UNESTABLISHED"),
    ("zinc carbonate hydroxide", None, "WHOLE_REFERENT_GRAPH_UNESTABLISHED"),
    ("alcohol denat.", None, "WHOLE_REFERENT_GRAPH_UNESTABLISHED"),
])
def test_existing_resolver_retains_eligibility_authority(engine, name, route, reason):
    framework, preview = engine
    result = preview.evaluate(framework.interpret(InterpretationInput(Evidence(name, "name"))))
    assert result.route == route
    assert result.reasons == ((reason,) if reason else ())
