"""Isolated Stage B controls. These tests never run eligibility or matching."""

from dataclasses import replace

import pytest

from canonical_registry.nomenclature_interpretation import InterpretationFramework
from canonical_registry.nomenclature_interpretation.contracts import Evidence, InterpretationInput, StructureKind, TypedStructure
from canonical_registry.nomenclature_interpretation.cosing_preview_adapter import adapt_cosing_preview

from .cosing_source import observation
from .stage_b_evidence import _eligible_alias
from .stage_b_v1 import _overlay


@pytest.mark.parametrize(("name","definition","module","predicate","expected"), [
    ("TILIA CORDATA/PLATYPHYLLOS FLOWER EXTRACT","Extract from flowers of the hybrid.",
     "botanical","source_anatomical_structure","http://purl.obolibrary.org/obo/PO_0009046"),
    ("PYRUS MALUS FRUIT JUICE VESICLES","The vesicles isolated from the juice of the fruit.",
     "botanical","reported_botanical_preparation","vesicles"),
    ("BOSWELLIA SACRA GUM WATER","Aqueous solution of the steam distillates of the gum.",
     "botanical","reported_botanical_preparation","steam distillate"),
    ("RUMEX ACETOSA EXTRACT","The extract of the whole plant, Rumex acetosa, Polygonaceae.",
     "botanical","reported_plant_part","whole plant"),
    ("SD ALCOHOL 40-B","Ethyl alcohol denatured with a specified denaturant.",
     "preparation_mixture","reported_source_preparation","denatured alcohol"),
    ("BACTERIAL CELL CULTURE CONDITIONED MEDIUM","The growth media removed from cultures.",
     "biological_biotechnological","reported_biological_category","conditioned media"),
    ("CALCIUM OXIDE",None,"inorganic_mineral","reported_oxide_name","CALCIUM OXIDE"),
    ("SMECTITE","A clay mineral of variable composition.","inorganic_mineral","reported_mineral_name","SMECTITE"),
])
def test_source_qualified_rules(name,definition,module,predicate,expected):
    item = InterpretationInput(Evidence(name,"designation"),source_definition=Evidence(definition,"definition") if definition else None)
    result = InterpretationFramework().interpret(item)
    assert any(m.module==module and m.whole_referent_graph_unestablished and
               any(a.predicate==predicate and a.value==expected for a in m.assertions) for m in result.modules)


def test_ambiguous_new_forms_need_source_definition():
    for label in ("TILIA CORDATA/PLATYPHYLLOS FLOWER EXTRACT","PYRUS MALUS FRUIT JUICE VESICLES","SD ALCOHOL 40-B"):
        result = InterpretationFramework().interpret(InterpretationInput(Evidence(label,"designation")))
        assert not {"botanical","reported_source_preparation"}.intersection(
            {m.module for m in result.modules}|{a.predicate for a in result.assertions})


def test_order_invariance_and_exact_duplicate_evidence_preserve_conflict():
    structures = tuple(TypedStructure(StructureKind.SMILES,Evidence(v,"structure",f"source:{n}"))
                       for n,v in enumerate(("CCO","CC")))
    item = InterpretationInput(Evidence("PLANT SEED OIL GLYCERIDES","designation"),structures)
    framework = InterpretationFramework()
    baseline = framework.interpret(item)
    reordered = InterpretationFramework(interpreters=tuple(reversed(framework.interpreters)))
    assert reordered.interpret(replace(item,structures=structures[::-1]+structures[:1]))==baseline
    assert baseline.state=="CONFLICT"
    assert all(a.category!="STRUCTURAL" for a in baseline.assertions)


def test_original_typed_values_and_parent_revision_binding():
    key = "00000000-0000-0000-0000-000000000001"
    parent = {"inci_id":key,"inci":"TEST"}
    alias = {"inci_alias_id":key,"alias_type":"SMILES","alias":"O","source":"example",
             "normalized_alias":"C","created_ts":"10","updated_ts":"12","data_status":"1"}
    assert _eligible_alias(alias,12) is None
    assert _eligible_alias(alias,11)=="ALIAS_REVISION_UNESTABLISHED_FOR_PARENT_CAPTURE"
    assert _eligible_alias({**alias,"alias_type":None},12)=="MISSING_ALIAS_TYPE"
    assert _eligible_alias({**alias,"alias":" "},12)=="INVALID_OR_EMPTY_ORIGINAL_VALUE"
    row = {"source_reference":"mse_dwd.dwd_mse_cosmetics_incis:"+key,"observed_revision":"original"}
    apply = _overlay([parent],{key:[alias]},{key:[]},"manifest")
    original,claims,provenance = apply(row,observation(parent).payload)
    item = adapt_cosing_preview(original,claims,include_registry_claims=True)
    assert item.structures[0].evidence.original_value=="O"
    assert provenance["parent_revision"]=="original"
    with pytest.raises(ValueError,match="does not match"):
        apply(row,observation({**parent,"description":"revised"}).payload)
