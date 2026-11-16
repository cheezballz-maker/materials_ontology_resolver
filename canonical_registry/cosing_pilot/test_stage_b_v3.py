"""Monitored Stage B source checks, isolation, and transactional recovery."""

from collections import Counter
from copy import deepcopy
from types import SimpleNamespace

import pytest

from canonical_registry.nomenclature_interpretation import InterpretationFramework
from canonical_registry.nomenclature_interpretation.contracts import Evidence, InterpretationInput

from .cosing_source import observation
from .readiness import register
from .stage_b_v1 import _overlay
from .stage_b_v3 import _build, _cached, _write_batch
from .stage_b_v3_gate import check, decision
from .staged_assessment import _select
from .staged_registry import StagedRegistry


@pytest.mark.parametrize(("label","definition","module","predicate"),[
    ("SORBETH-12","It is the polyethylene glycol ether of sorbitol.","lipid_surfactant","reported_lipid_surfactant_qualifier"),
    ("REPORTED GLYCOLIPID MATERIAL","The ingredient is a glycolipid.","lipid_surfactant","reported_lipid_surfactant_qualifier"),
    ("HC RED NO. 19",None,"colorant","HCColorantDesignation"),
    ("PHASEOLUS VULGARIS HULL","Outer covering of the common bean, Phaseolus vulgaris.","botanical","reported_plant_part"),
    ("MAGNESIUM/POTASSIUM/SILICON/FLUORIDE/HYDROXIDE/OXIDE",None,"inorganic_mineral","reported_inorganic_mixed_designation"),
    ("TREATED MONTMORILLONITE","Montmorillonite surface treated with a polymer.","preparation_mixture","reported_preparation_process"),
])
def test_source_bound_rules_stay_lexical(label,definition,module,predicate):
    item = InterpretationInput(Evidence(label,"name"),source_definition=Evidence(definition,"definition") if definition else None)
    result = InterpretationFramework().interpret(item)
    assert any(m.module==module and m.whole_referent_graph_unestablished for m in result.modules)
    assert any(a.predicate==predicate for a in result.assertions)
    assert not any(a.category=="STRUCTURAL" for a in result.assertions)


def test_unsubstantiated_ethoxylate_does_not_activate():
    result = InterpretationFramework().interpret(InterpretationInput(Evidence("SORBETH-12","name")))
    assert not any(m.module=="lipid_surfactant" for m in result.modules)


def _fixture(tmp_path):
    registry = StagedRegistry(tmp_path/"stage_b_gate.sqlite")
    registry.initialize()
    parent = {"inci_id":"00000000-0000-0000-0000-000000000001","inci":"ROSA CANINA LEAF EXTRACT",
              "description":"The extract of the leaves of Rosa canina.","cas_nos":None,"ec_nos":None,"functions":[]}
    register(registry,[observation(parent)],"fixture")
    row, = _select(registry,(),[parent["inci_id"]],None)
    overlay = _overlay([parent],{parent["inci_id"]:[]},{parent["inci_id"]:[]},"fixture-manifest")
    pred = _build(InterpretationFramework(),SimpleNamespace(failures=0),row,
                  {"cohort":"fixture","stratum":"botanical"},overlay,"fixture-policy",Counter())
    return registry,row,parent,pred


def test_gate_rejects_tampered_descriptor_and_stale_revision(tmp_path):
    _,row,parent,pred = _fixture(tmp_path)
    assert check(row,parent,[],pred,"fixture-manifest","fixture-policy")[0]==[]
    corrupt = deepcopy(pred)
    corrupt["revision"] = "stale"
    corrupt["attributes"][0]["reported_text"] = "unbound"
    corrupt["attributes"][0]["predicate"] = "canonical_identity"
    errors,_ = check(row,parent,[],corrupt,"fixture-manifest","fixture-policy")
    assert {"EVIDENCE","REVISION","MATERIAL_SCOPE","CONFLICT_ISOLATION"}<=set(errors)


def test_batch_quarantine_and_family_isolation_are_explicit():
    safe = {"id":"A","failures":[],"review":[],"interpreter_families":["polymer_silicone"]}
    unsafe = [{"id":f"B{i}","failures":["WHOLE_REFERENT"],"review":[],"interpreter_families":["botanical"]} for i in (1,2)]
    report = decision([safe,*unsafe])
    assert report["decision"]=="REJECT" and report["eligible_for_rebatch"]==["A"]
    assert report["held_families"]==["botanical"] and len(report["quarantine"])==2
    assert decision([{**safe,"retry":True}])["decision"]=="HOLD"
    assert decision([safe])["decision"]=="ACCEPT"


def test_interrupted_sqlite_batch_reopens_and_replays(tmp_path):
    registry,row,_,pred = _fixture(tmp_path)
    payload = {row["concept_id"]:pred}
    def interrupt():
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        _write_batch(registry,[row],payload,"fixture-policy",Counter(),interrupt)
    reopened = StagedRegistry(registry.path)
    assert not _cached(reopened,[row],"fixture-policy",Counter())
    assert _write_batch(reopened,[row],payload,"fixture-policy",Counter())==1
    assert _write_batch(reopened,[row],payload,"fixture-policy",Counter())==0
    assert not _cached(reopened,[row],"changed-policy",Counter())
