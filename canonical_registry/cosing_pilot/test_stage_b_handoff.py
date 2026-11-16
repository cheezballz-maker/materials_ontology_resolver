from copy import deepcopy

import pytest

from .stage_b_handoff import Trace, alias_triage, eligibility
from .stage_b_handoff_recovery import processing_label, rebind_prediction


def test_reversible_layout_edits_preserve_source_claim():
    source = "ROSA LEAF\r\n/\tEXTRACT"
    label, edits = processing_label(source)
    assert label == "ROSA LEAF / EXTRACT"
    recovered = label
    for edit in edits:
        offset = edit["offset"]
        recovered = recovered[:offset]+edit["original"]+recovered[offset+1:]
    assert recovered==source
    p = {"trace":{"interpretation":{"designation":{"source_reference":"r","original_value":label,
                                                 "field":"preferred_label"}}}}
    rebind_prediction(p,"r",source,label,edits)
    assert p["trace"]["interpretation"]["designation"]["original_value"]==source
    with pytest.raises(ValueError):
        processing_label("ROSA\x00 LEAF")


@pytest.mark.parametrize(("raw","expected"),[
    ("CCO","P1"),("InChI=1S/CH4/h1H4","P1"),("64-17-5","P1"),("C2H6O","P1"),
    ("Reported old cosmetic label","P3"),
])
def test_missing_type_chemical_shapes_trigger_review(raw,expected):
    alias = {"alias":raw,"source":"COSING","data_status":"1","created_ts":"1","updated_ts":"2"}
    assert alias_triage(alias,{"inci":"Other label","description":None},[],10)[0]==expected


def test_same_source_typed_duplicate_can_be_qualified_without_identity():
    alias = {"alias":"CCO","source":"COSING","data_status":"1","created_ts":"1","updated_ts":"2"}
    t = {"inci":"ETHANOL","description":None}
    assert alias_triage(alias,t,[{**alias,"alias_type":"SMILES"}],10)[:2]==(
        "P3","SUPPORTED_DUPLICATE_QUALIFICATION")


def _case():
    graph = {"smiles":"CCO","inchi":"InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",
             "inchikey":"LFQSCWFLJHTTHZ-UHFFFAOYSA-N","fixed_h_inchi":"fixed",
             "components":1,"charge":0,"radicals":0,"isotopes":[],"atoms":3,"stereo":[],"inchi_warning":""}
    ref = "mse_dwd.dwd_mse_cosmetics_inci_aliases:alias-key"
    assertions = [
        {"category":"STRUCTURAL","evidence_role":"CANDIDATE_ONLY","method":"OPSIN_THEN_STRICT_RDKIT",
         "predicate":"molecular_graph","value":graph,"evidence":{"source_reference":"source","original_value":"ETHANOL"}},
        {"category":"STRUCTURAL","evidence_role":"CANDIDATE_ONLY","method":"STRICT_RDKIT_STRUCTURE",
         "predicate":"molecular_graph","value":deepcopy(graph),"evidence":{"source_reference":ref,"original_value":"CCO"}},
        {"category":"NOMENCLATURE","predicate":"molecular_name_reading","value":"ESTABLISHED"},
    ]
    return {"inci":"ETHANOL","description":None},Trace([],{"state":"VALIDATED"},{"interpretation":{
        "assertions":assertions,"withheld_assertions":[],"issues":[],"modules":[],
        "graph_comparisons":[{"relation":"COMPATIBLE"}]}}),[
        {"inci_alias_id":"alias-key","alias":"CCO","alias_type":"SMILES","source":"COSING",
         "referent_scope":"VERIFIED_WHOLE_INGREDIENT"}]


def _official(g):
    return {"status":"SUCCESS","agrees":True,"inchi":g["inchi"],"inchikey":g["inchikey"]}


def test_preflight_requires_graph_binding_and_reference_confirmation():
    p,t,a = _case()
    assert eligibility(p,t,a,set(),_official)[0:3]==("CANDIDATE_READY","CONSISTENT_NAMED_WHOLE_REFERENT","SUBSTANCE")
    assert eligibility(p,t,a,set(),lambda g:{})[0]=="NEEDS_MORE_EVIDENCE"
    assert eligibility(p,t,[],set(),_official)[0]=="NEEDS_MORE_EVIDENCE"
    assert eligibility(p,t,a,{"P1"},_official)[0]=="REVIEW_HOLD"


def test_constituent_scope_and_unqualified_stereo_cannot_route():
    p,t,a = _case()
    for g in t.graphs:
        g["value"]["stereo"] = [{"specified":"Unspecified","type":"Atom_Tetrahedral"}]
    assert eligibility(p,t,a,set(),_official)[0]=="NEEDS_MORE_EVIDENCE"
    t.interpretation["modules"].append({"whole_referent_graph_unestablished":True})
    t.interpretation["withheld_assertions"]=t.graphs
    t.interpretation["assertions"]=[]
    p["description"] = "This is a mixture of reported components."
    assert eligibility(p,t,a,set(),_official)[0]=="NOT_APPLICABLE_TO_EXACT_MOLECULAR_RESOLUTION"
