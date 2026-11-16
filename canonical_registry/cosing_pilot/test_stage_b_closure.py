"""Exercise actual worker boundaries and the Stage B publication transaction."""

from contextlib import closing
import json
import os
import time

import pytest

from .cosing_source import observation
from .full_capture import read
from .readiness import register
from .stage_b_closure import MonitoredBatch, queue_items, restrict
from .stage_b_v1 import _overlay
from .stage_b_worker import StageBWorker
from .staged_assessment import _select
from .staged_registry import StagedRegistry


class FixtureBridge:
    timeout = 4
    unavailable = False

    def opsin(self, query):
        return {"status":"ERROR" if self.unavailable else "FAILURE","diagnostic":"injected" if self.unavailable else None}


def _timed_child(link):
    with closing(link):
        link.send(("ready",))
        while True:
            delay = link.recv()
            if delay is None:
                return
            if delay < 0:
                os._exit(31)
            time.sleep(delay)
            link.send(("complete",{"done":True},{},0))


def test_native_process_boundary_reaps_restarts_and_retries():
    with StageBWorker(FixtureBridge(),target=_timed_child) as worker:
        assert worker.run(0,1)["prediction"]=={"done":True}
        for _ in range(2):
            result = worker.run(3,0.15)
            assert result["reason"]=="RECONCILIATION_TIMEOUT"
            assert 0.12<=result["elapsed_seconds"]<2
            assert worker.process is None
            assert worker.lifecycle[-1]["pid"]==result["pid"]
        result = worker.run(-1,2)
        assert result["reason"]=="WORKER_EXIT"
        assert worker.lifecycle[-1]["exit_code"]==31
        assert worker.run(0.2,1)["prediction"]=={"done":True}


def _session(tmp_path):
    parent = {"inci_id":"00000000-0000-0000-0000-000000000001","inci":"ROSA CANINA LEAF EXTRACT",
              "description":"The extract of the leaves of Rosa canina.","cas_nos":None,"ec_nos":None,"functions":[]}
    registry = StagedRegistry(tmp_path/"fixture.sqlite")
    registry.initialize()
    register(registry,[observation(parent)],"closure-fixture")
    row, = _select(registry,(),[parent["inci_id"]],None)
    row = dict(row)
    raw = _overlay([parent],{parent["inci_id"]:[]},{parent["inci_id"]:[
        {"id":"archive","type":"SYNONYM","reason":"ARCHIVE_ONLY_ALIAS_TYPE"}]},"fixture")
    packet = row,{"cohort":"fixture","stratum":"botanical"},*raw(row,json.loads(row["payload_json"])),"policy"
    cid = row["concept_id"]
    return MonitoredBatch(registry,tmp_path/"journal.json",{cid:packet},"policy","fixture",lambda:True),cid


def test_provider_failure_withholds_incomplete_record_and_retry_reopens(tmp_path):
    session,cid = _session(tmp_path)
    bridge = FixtureBridge()
    bridge.unavailable = True
    with StageBWorker(bridge) as worker:
        failed,_,_ = session.submit([cid],worker.run,3)
        assert failed["decision"]=="HOLD" and failed["retry_ids"]==[cid]
        assert failed["execution"][cid]["provider_activity"][0]["status"]=="ERROR"
        with session.registry.reader() as db:
            assert db.execute("SELECT count(*) FROM assessment").fetchone()[0]==0
        assert len(queue_items(session.journal,reason="RETRYABLE_PROVIDER_FAILURE",status="RETRY"))==1
        bridge.unavailable = False
        first,_,_ = session.retry(failed["id"],worker.run,3)
        again,_,_ = session.retry(failed["id"],worker.run,3)
        assert first["inserted"]==1 and again["inserted"]==0
        assert first["packet_digests"]==failed["packet_digests"]==again["packet_digests"]
        assert not queue_items(session.journal)
        assert first["checks"][0]["excluded_aliases"]=={"ARCHIVE_ONLY_ALIAS_TYPE":1}
        assert [e["decision"] for e in read(session.journal) if e["id"]==failed["id"]]==["STARTED","HOLD"]


def test_interpreter_exception_worker_cannot_return_an_assessment(tmp_path):
    session,cid = _session(tmp_path)
    packet = session.packets[cid]
    bad = ({**packet[0],"payload_json":"broken"},*packet[1:])
    with StageBWorker(FixtureBridge()) as worker:
        result = worker.run(bad,3)
        assert result["reason"]=="WORKER_EXCEPTION" and result["error"]=="JSONDecodeError"
        assert worker.process is None
        assert worker.run(packet,3)["prediction"]["attributes"]


def test_retry_rejects_changed_source_packet(tmp_path):
    session,cid = _session(tmp_path)
    failed,_,_ = session.submit([cid],lambda *_:{"prediction":None,"reason":"RETRYABLE_PROVIDER_FAILURE"},3)
    session.packets[cid][2]["description"] = "altered"
    with pytest.raises(ValueError,match="evidence changed"):
        session.retry(failed["id"],lambda *_:None,3)


def test_compound_scope_hold_updates_the_persisted_assertion_audit():
    attribute = {"predicate":"source_anatomical_structure","value":"PO:0025034",
                 "source_reference":"source","method":"ANATOMY"}
    audit = {**attribute,"evidence":{"source_reference":"source"},"decision":"PERSISTED_DESCRIPTOR"}
    prediction = {"attributes":[attribute],"trace":{"assertion_audit":[audit]}}
    parent = {"inci":"VITIS VINIFERA/LABRUSCA LEAF EXTRACT","description":None}
    published = restrict(prediction,parent)
    assert not published["attributes"]
    assert published["trace"]["assertion_audit"][0]["decision"]=="HELD_PUBLICATION_REVIEW"
    assert prediction["trace"]["assertion_audit"][0]["decision"]=="PERSISTED_DESCRIPTOR"
