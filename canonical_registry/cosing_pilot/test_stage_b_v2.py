"""Stage B v2 controls for dependency isolation, nomenclature and evidence order."""

from dataclasses import replace

import pytest

from canonical_registry.nomenclature_interpretation import InterpretationFramework
from canonical_registry.nomenclature_interpretation.contracts import (
    Assertion, Category, Evidence, EvidenceRole, InterpretationInput, Issue, ModuleResult, State, StructureKind, TypedStructure,
)

from .organization import assertion_audit, supported_attributes
from .staged_assessment import _hold_incomplete_structure


def sample(name, definition=None, graphs=()):
    return InterpretationInput(Evidence(name,"label","fixture:1"),
          tuple(TypedStructure(StructureKind.SMILES,Evidence(s,"typed_alias",f"alias:{i}"))
                for i,s in enumerate(graphs)),
          source_definition=Evidence(definition,"definition","fixture:1") if definition else None)


def facets(rows):
    return {(a.predicate,str(a.value).casefold()) for a in rows}


def test_graph_conflict_preserves_independent_oxide_and_provenance():
    result = InterpretationFramework().interpret(sample("CALCIUM OXIDE",graphs=("CC","CCO")))
    assert result.state==State.CONFLICT
    persisted = supported_attributes(result)
    assert {(a["predicate"],a["value"]) for a in persisted}=={("reported_oxide_name","CALCIUM OXIDE")}
    assert persisted[0]["subject"]=="fixture:1" and persisted[0]["evidence_qualification"]=="SOURCE_REPORTED"
    assert sum(a.category==Category.STRUCTURAL for a in result.withheld_assertions)==2
    assert any(row["decision"]=="WITHHELD" and any(d["dimension"]=="STRUCTURAL_GRAPH" for d in row["diagnostics"])
               for row in assertion_audit(result))


def test_botanical_anatomy_dispute_withholds_part_and_po_but_keeps_preparation():
    result = InterpretationFramework().interpret(sample("ROSA CANINA LEAF EXTRACT",
        "Rosa Canina Leaf Extract is an extract of the roots of Rosa canina."))
    assert result.state==State.CONFLICT
    assert not {"reported_plant_part","source_anatomical_structure"}.intersection(a.predicate for a in result.assertions)
    assert {"reported_plant_part","source_anatomical_structure"}<={a.predicate for a in result.withheld_assertions}
    assert ("reported_botanical_preparation","extract") in facets(result.assertions)


def test_preparation_dispute_withholds_both_claims_but_keeps_anatomy():
    result = InterpretationFramework().interpret(sample("ROSA CANINA FRUIT JUICE",
        "Rosa Canina Fruit Extract is an extract of the fruit of Rosa canina."))
    assert result.state==State.CONFLICT
    assert {"reported_botanical_preparation","reported_source_preparation","reported_preparation_qualifier"}<={
        a.predicate for a in result.withheld_assertions}
    assert ("reported_plant_part","fruit") in facets(result.assertions)


@pytest.mark.parametrize(("part","inflected"),[("KERNEL","kernels"),("SPROUT","sprouts"),("LEAF","leaves")])
def test_same_source_part_inflection_does_not_trigger_conflict(part,inflected):
    result = InterpretationFramework().interpret(sample(f"ROSA CANINA {part} EXTRACT",
        f"The ingredient is an extract obtained from the {inflected} of Rosa canina."))
    assert result.state!=State.CONFLICT
    assert ("reported_plant_part",part.casefold()) in facets(result.assertions)
    assert any(a["predicate"]=="reported_plant_part" for a in supported_attributes(result))


class ConflictingTaxon:
    def interpret(self,item):
        claims = (Assertion(Category.NOMENCLATURE,"reported_taxon_text","rosa rubiginosa",
            EvidenceRole.CANDIDATE_ONLY,Evidence("Rosa rubiginosa","source_alias","fixture:1"),
            "FIXTURE_SOURCE_TAXON","botanical.taxon"),)
        return ModuleResult("fixture_taxon",State.PARTIAL,assertions=claims)


def test_taxon_conflict_preserves_anatomy_and_preparation_with_order_invariance():
    item = sample("ROSA CANINA LEAF EXTRACT",graphs=("CC","CCO"))
    modules = (*InterpretationFramework().interpreters,ConflictingTaxon())
    normal = InterpretationFramework(interpreters=modules).interpret(item)
    reordered = InterpretationFramework(interpreters=modules[::-1]).interpret(
        replace(item,structures=item.structures[::-1]+item.structures[:1]))
    assert normal==reordered and normal.state==State.CONFLICT
    assert {("reported_plant_part","leaf"),("reported_botanical_preparation","extract")}<=facets(normal.assertions)
    assert not any(a.predicate=="reported_taxon_text" or a.category==Category.STRUCTURAL for a in normal.assertions)


class FilteredAnatomyClaim:
    def interpret(self,item):
        a = Assertion(Category.MATERIAL,"reported_plant_part","leaf",EvidenceRole.SUPPORTING,item.designation,
                      "FIXTURE_PART","botanical.anatomy")
        b = Assertion(Category.MATERIAL,"reported_plant_part","root",EvidenceRole.CANDIDATE_ONLY,
                      Evidence("root","typed_source","fixture:1"),"FIXTURE_PART","botanical.anatomy")
        return ModuleResult("fixture",State.PARTIAL,assertions=(a,b))


def test_unpersistable_companion_still_blocks_disputed_descriptor():
    result = InterpretationFramework(interpreters=(FilteredAnatomyClaim(),)).interpret(sample("Leaf"))
    assert len(result.withheld_assertions)==2 and not supported_attributes(result)


def test_unavailable_typed_companion_does_not_release_other_graphs():
    result = InterpretationFramework().interpret(sample("UNRESOLVED SOURCE",graphs=("CCO",)))
    assert any(a.category==Category.STRUCTURAL for a in result.assertions)
    held = _hold_incomplete_structure(result,{"held_aliases":[{"id":"absent","type":"INCHI"}]})
    assert not any(a.category==Category.STRUCTURAL for a in held.assertions)
    assert any(i.code=="INCOMPLETE_TYPED_STRUCTURE_EVIDENCE" for i in held.issues)


@pytest.mark.parametrize(("name","expected"),[
    ("COBALT(II) HYDROXIDE",{("reported_hydroxide_name","cobalt(ii) hydroxide"),("reported_oxidation_state","ii")}),
    ("MAGNESIUM ZINC OXIDE",{("reported_inorganic_multimetal_oxide","magnesium zinc oxide")}),
    ("ZINC SULFATE HEPTAHYDRATE",{("reported_hydration_qualifier","heptahydrate")}),
    ("POLYURETHANE-301",{("reported_polymer_category","polyurethane"),("reported_polymer_designation_number","polyurethane-301")}),
    ("CORYLUS AVELLANA KERNEL OIL",{("reported_plant_part","kernel")}),
    ("SALIX ALBA STEM BARK EXTRACT",{("reported_taxon_text","salix alba"),("reported_plant_part","stem bark")}),
])
def test_generalized_nomenclature_without_composition_inference(name,expected):
    result = InterpretationFramework().interpret(sample(name))
    assert expected<=facets(result.assertions)
    assert not any(a.category==Category.STRUCTURAL for a in result.assertions)


def test_source_process_and_preparation_can_coexist():
    result = InterpretationFramework().interpret(sample("PLANT EXTRACT FERMENT FILTRATE",
         "The product is a filtrate of a preparation obtained by the fermentation of plant extract."))
    assert {("reported_preparation_process","filtration"),("reported_preparation_process","fermentation"),
            ("reported_preparation_qualifier","filtrate")}<=facets(result.assertions)


def test_policy_version_cache_miss_preserves_the_prior_assessment(tmp_path):
    from .cosing_source import observation
    from .readiness import register
    from .staged_assessment import _interpret, _select
    from .staged_registry import StagedRegistry

    registry = StagedRegistry(tmp_path/"version_fixture.sqlite")
    registry.initialize()
    key = "00000000-0000-0000-0000-000000000001"
    register(registry,[observation({"inci_id":key,"inci":"ROSA CANINA LEAF EXTRACT"})],"fixture")
    rows = _select(registry,(),[key],None)
    options = dict(typed_only=True,pending=False,capability=None)
    assert _interpret(registry,rows,"old-rules",**options)=={"assessed":1}
    assert _interpret(registry,rows,"old-rules",**options)=={"cached":1}
    assert _interpret(registry,rows,"changed-rules",**options)=={"assessed":1}
    with registry.reader() as db:
        assert db.execute("SELECT count(DISTINCT pipeline_version) FROM assessment").fetchone()[0]==2
        assert db.execute("SELECT canonical_status FROM domain_concept").fetchone()[0]=="NOT_EVALUATED"
