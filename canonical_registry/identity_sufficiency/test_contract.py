from dataclasses import replace

import pytest

from .contract import Claim, Evidence, Evaluator, WHOLE
from .adapters import cosing

UNKNOWN = "SCOPE_UNESTABLISHED"


def claim(key,kind,value,grants=(),scope=WHOLE,entity="entity:1",namespace="",identity_scope=""):
    return Claim(key,kind,value,scope,entity,"Fixture authority",tuple(grants),"fixture:source",
                 "fixture:"+key,"r1",namespace,identity_scope)


def packet(*claims,material="UNESTABLISHED",holds=()):
    return Evidence("referent:1","source:record","r1","UNPARSED DESIGNATION",claims,material,
                    ("source:scope",) if material!="UNESTABLISHED" else (),holds)


def official(graph):
    return {"status":"SUCCESS","agrees":True,"inchi":graph["inchi"],"inchikey":graph["inchikey"]}


def evaluate(*claims,**kw):
    return Evaluator(official).evaluate(packet(*claims,**kw))


def direct(smiles="CCO",key="structure",extra=()):
    return claim(key,"SMILES",smiles,("STRUCTURE","REFERENT",*extra))


@pytest.mark.parametrize(("kind","grant","path","namespace","scope"),[
    ("NOMENCLATURE_LINK","NOMENCLATURE","B_NOMENCLATURE","",""),
    ("IDENTIFIER_LINK","IDENTIFIER","C_IDENTIFIER","UNII","DEFINED_CHEMICAL"),
])
def test_alternative_paths_require_a_qualified_referent_link(kind,grant,path,namespace,scope):
    link = claim("link",kind,"fixture value",(grant,"REFERENT"),namespace=namespace,identity_scope=scope)
    graph = claim("graph","SMILES","CCO",("STRUCTURE",),scope=UNKNOWN)
    a = evaluate(link,graph)
    assert a["eligibility"]=="CANDIDATE_READY" and a["evidence_pathway"]==path
    assert evaluate(replace(link,grants=(grant,)),graph)["eligibility"]=="NEEDS_MORE_EVIDENCE"
    assert evaluate(link,replace(graph,scope="CONSTITUENT"))["eligibility"]=="NEEDS_MORE_EVIDENCE"
    assert evaluate(link,replace(graph,entity="different"))["eligibility"]=="NEEDS_MORE_EVIDENCE"
    assert evaluate(link,graph,material="PREPARATION")["eligibility"]=="REVIEW_HOLD"


def test_direct_structure_does_not_require_a_name_parser():
    a = evaluate(direct(),direct("OCC","other representation"))
    assert a["eligibility"]=="CANDIDATE_READY" and a["evidence_pathway"]=="A_DIRECT_STRUCTURE"
    assert a["supporting_claim_ids"]==["other representation","structure"]
    assert evaluate(replace(direct(),document=""))["eligibility"]=="NEEDS_MORE_EVIDENCE"
    assert evaluate(replace(direct(),binding_revision="stale"))["eligibility"]=="NEEDS_MORE_EVIDENCE"


@pytest.mark.parametrize(("left","right"),[
    ("C[C@H](O)C(=O)O","C[C@@H](O)C(=O)O"),
    ("O","[2H]O[2H]"),
    ("[Na+].[Cl-]","[Na+].[Cl-].O"),
    ("CC(=O)O","CC(=O)[O-]"),
    ("O=c1cccc[nH]1","Oc1ccccn1"),
    ("CCO","COC"),
])
def test_exact_form_disagreement_blocks_without_selection(left,right):
    assert evaluate(direct(left),direct(right,"other"))["eligibility"]=="REVIEW_HOLD"


def test_component_composition_and_authoritative_descriptor():
    assert evaluate(direct("[Na+].[Cl-]"))["reasons"]==["COMPONENT_COMPOSITION_UNQUALIFIED"]
    exact = evaluate(direct("[Na+].[Cl-]",extra=("COMPLETE_COMPOSITION",)))
    assert exact["eligibility"] in {"REVIEW_HOLD","CANDIDATE_READY"}
    if exact["eligibility"]=="CANDIDATE_READY":
        assert exact["specificity"]["components"]==2
    wrong = claim("key","INCHIKEY","INVALID",("STRUCTURE",))
    assert evaluate(direct(),wrong)["reasons"]==["QUALIFIED_STRUCTURE_DESCRIPTOR_DISAGREES"]


def test_whole_multicomponent_definition_keeps_every_component():
    a = evaluate(direct("CCO.O",extra=("COMPLETE_COMPOSITION",)))
    assert a["eligibility"]=="CANDIDATE_READY" and a["specificity"]["components"]==2


def test_partial_chemical_concept_requires_explicit_source_scope():
    stereo = claim("stereo","STEREO_SCOPE","EXPLICITLY_UNSPECIFIED",("SPECIFICATION","REFERENT"))
    open_graph = direct("CC(O)C(=O)O")
    assert evaluate(open_graph)["eligibility"]=="NEEDS_MORE_EVIDENCE"
    a = evaluate(open_graph,stereo)
    assert a["eligibility"]=="CANDIDATE_READY" and a["resolution_pathway"]=="CHEMICAL_CONCEPT"
    assert a["specificity"]["partial_definition"]["stereo_state"]=="EXPLICITLY_UNSPECIFIED"
    assert evaluate(direct("C[C@H](O)C(=O)O"),stereo)["eligibility"]=="REVIEW_HOLD"


def test_scope_and_provenance_guards():
    precursor = replace(direct(),scope="PRECURSOR")
    assert evaluate(precursor)["eligibility"]=="NEEDS_MORE_EVIDENCE"
    assert evaluate(precursor,material="POLYMER")["eligibility"]=="NOT_APPLICABLE_TO_EXACT_MOLECULAR_RESOLUTION"
    assert evaluate(direct(),holds=("SOURCE_CONFLICT",))["eligibility"]=="REVIEW_HOLD"
    assert Evaluator(lambda _:{}).evaluate(packet(direct()))["eligibility"]=="REVIEW_HOLD"
    with pytest.raises(ValueError):
        evaluate(direct(),direct())


def test_equivalent_evidence_has_same_result_with_other_source_labels():
    a = packet(direct())
    b = replace(a,referent="other",source_reference="other database",
                claims=(replace(direct(),authority="Different authority"),))
    engine = Evaluator(official)
    fields = ("eligibility","resolution_pathway","evidence_pathway","specificity","reasons")
    assert all(engine.evaluate(a)[k]==engine.evaluate(b)[k] for k in fields)


def test_adapter_retains_nonempty_original_identifier_claims():
    row = {"source_reference":"r","revision":"r1","concept_id":"cid","attributes":[],"summary":{},
           "trace":{},"stage_b_version":"stage-b","old_evidence":{"risk_priorities":[]}}
    parent = {"inci":"WATER","description":None,"cas_nos":[None,"7732-18-5"],"ec_nos":[]}
    packet = cosing(row,parent,[])
    assert [(c.claim_id,c.value) for c in packet.claims if c.kind=="IDENTIFIER"]==[("cas_nos:1","7732-18-5")]
    assert Evaluator(official).evaluate(packet)["eligibility"]=="NEEDS_MORE_EVIDENCE"
