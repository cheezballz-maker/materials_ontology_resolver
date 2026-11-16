"""Evaluate and publish monitored Stage B batches against verified source packets."""

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
from time import perf_counter
from uuid import uuid4

from .full_capture import read, write
from .registry import fingerprint
from .stage_b_v3 import _write_batch
from .stage_b_v3_gate import check, decision

DEFAULT_BUDGET = 6.0
OUTPUT = Path(__file__).with_name("data")/"stage_b_v3_closure"
RISK_POLICY = "bounded-stage-b-publication-1"


def restrict(prediction, parent):
    """Preserve the interpreter evidence and restrict which attributes become descriptors."""
    result = deepcopy(prediction)
    withheld = []
    held_keys = {}
    selected = []
    compound = "/" in parent["inci"]
    definition = parent["description"] or ""
    preparation = re.search(r"\b(?:filtrate|extract|dispersion|suspension|preparation|coated|containing)\b",
                            parent["inci"],re.I) or re.search(r"\bsurface[- ]treated\b",definition,re.I)
    for attribute in result["attributes"]:
        predicate = attribute["predicate"]
        reason = None
        if compound and predicate=="source_anatomical_structure":
            reason = "COMPOUND_BOTANICAL_ATTACHMENT_REVIEW"
        if compound and predicate in {"reported_preparation_source_phrase","reported_botanical_preparation"}:
            reason = "COMPOUND_PREPARATION_SCOPE_REVIEW"
        if preparation and predicate in {"reported_mineral_name","reported_oxide_name",
                                          "reported_inorganic_multimetal_oxide","reported_inorganic_mixed_designation"}:
            reason = "MINERAL_CONSTITUENT_SCOPE_REVIEW"
        if reason:
            withheld.append({"reason":reason,"attribute":attribute})
            key = predicate,fingerprint(attribute["value"]),attribute["source_reference"],attribute["method"]
            held_keys[key] = reason
        else:
            selected.append(attribute)
    result["attributes"] = selected
    for entry in result["trace"]["assertion_audit"]:
        key = (entry["predicate"],fingerprint(entry["value"]),entry["evidence"]["source_reference"],entry["method"])
        if entry["decision"]=="PERSISTED_DESCRIPTOR" and key in held_keys:
            entry.update(decision="HELD_PUBLICATION_REVIEW",publication_reason=held_keys[key])
    result["trace"]["publication_review"] = {"policy":RISK_POLICY,"withheld":withheld}
    return result


def _review_tags(prediction, base, publication):
    trace = prediction["trace"]
    reasons = Counter(a["reason"] for a in trace["companion_evidence"]["held_aliases"])
    review = set(base)-{"SOURCE_ALIAS_HOLDS","WITHHELD_OR_CONFLICTING_EVIDENCE"}
    if "MISSING_ALIAS_TYPE" in reasons:
        review.add("MISSING_ALIAS_QUALIFICATION")
    if set(reasons)-{"MISSING_ALIAS_TYPE","ARCHIVE_ONLY_ALIAS_TYPE","ALIAS_STATUS_NOT_ACTIVE"}:
        review.add("SOURCE_ALIAS_INCONSISTENCY")
    issues = trace["interpretation"]["issues"]
    if any(i["conflict"] and any(s in i["code"] for s in ("GRAPH","STRUCTURE","STEREO","INCHI")) for i in issues):
        review.add("STRUCTURAL_CONFLICT")
    if any(i["conflict"] and not any(s in i["code"] for s in ("GRAPH","STRUCTURE","STEREO","INCHI")) for i in issues):
        review.add("NONSTRUCTURAL_CONFLICT")
    review.update(a["reason"] for a in publication["trace"]["publication_review"]["withheld"])
    return sorted(review),dict(reasons)


def _queue(event, checked):
    result = []
    for item in checked:
        for reason in sorted(set(item["failures"])|set(item["review"])):
            if reason=="GENERIC_FALLBACK":
                continue
            severity = "CRITICAL" if reason in item["failures"] else "HIGH" if item.get("retry") or (
                reason.endswith("_REVIEW") or reason in {"SOURCE_ALIAS_INCONSISTENCY","STRUCTURAL_CONFLICT"}
            ) else "MEDIUM"
            result.append({"event":event,"reason":reason,"severity":severity,
                "status":"QUARANTINED" if item["failures"] else "RETRY" if item.get("retry") else "REVIEW",
                "concept_id":item["id"],"source_record":item["source_key"],
                "interpreter":item["interpreter_families"] or ["unassigned"]})
    return result


class MonitoredBatch:
    """Single-writer Stage B session. Audit intents survive interrupted transactions."""

    def __init__(self, registry, journal, packets, version, manifest, verify_source):
        self.registry = registry
        self.journal = journal
        self.packets = packets
        self.version = version
        self.manifest = manifest
        self.verify_source = verify_source

    def _record(self, event):
        history = read(self.journal) if self.journal.exists() else []
        write(self.journal,[*history,event])

    def _parent(self, prior):
        events = read(self.journal)
        history = [e for e in events if e["id"]==prior]
        event = history[-1]
        if event["version"]!=self.version or event["manifest"]!=self.manifest:
            raise ValueError("The prior event is from another source or semantic policy")
        return event

    def rebatch(self, prior, compute, budget):
        event = self._parent(prior)
        ids = event.get("eligible_for_rebatch",[])
        if event["decision"] not in {"HOLD","REJECT"} or not ids:
            raise ValueError("No safe records were released by this event")
        return self._execute(ids,compute,budget,prior,"REBATCH")

    def retry(self, prior, compute, budget, *, ids=None):
        event = self._parent(prior)
        eligible = event.get("retry_ids",[])
        selected = eligible if ids is None else ids
        if not selected or not set(selected)<=set(eligible):
            raise ValueError("The prior event did not release those records for retry")
        return self._execute(selected,compute,budget,prior,"RETRY")

    def submit(self, ids, compute, budget, *, interrupt=None):
        return self._execute(ids,compute,budget,None,"BATCH",interrupt)

    def resume(self, prior, compute, budget):
        event = self._parent(prior)
        if event["decision"] not in {"STARTED","VALIDATED_PENDING_COMMIT"}:
            raise ValueError("Only an unfinished batch can be resumed")
        return self._execute(event["ids"],compute,budget,prior,"RESUME")

    def _execute(self, ids, compute, budget, prior, operation, interrupt=None):
        from .staged_assessment import _current

        start = perf_counter()
        if not ids or len(set(ids))!=len(ids):
            raise ValueError("A batch must contain unique source-bound concepts")
        event = {"id":str(uuid4()),"operation":operation,"parent_event":prior,"ids":list(ids),
                 "timestamp":datetime.now(timezone.utc).isoformat(),"version":self.version,"manifest":self.manifest,
                 "budget_seconds":budget}
        selected = [self.packets[cid] for cid in ids]
        event["packet_digests"] = {p[0]["concept_id"]:fingerprint(p) for p in selected}
        if prior and any(self._parent(prior)["packet_digests"].get(k)!=v for k,v in event["packet_digests"].items()):
            raise ValueError("Retry or rebatch evidence changed")
        self._record({**event,"decision":"STARTED"})
        checked,raw,published,observations = [],{}, {},{}
        source_valid = self.verify_source()
        with self.registry.reader() as db:
            current = {p[0]["concept_id"]:_current(db,p[0],False) for p in selected}
        for packet in selected:
            row,_,parent,aliases,_,_ = packet
            cid = row["concept_id"]
            item = {"id":cid,"source_key":parent["inci_id"],"failures":[],"review":[],"interpreter_families":[]}
            checked.append(item)
            if not source_valid or not current[cid]:
                item["failures"] = ["EVIDENCE" if not source_valid else "REVISION"]
                continue
            execution = compute(packet,budget)
            if not isinstance(execution,dict):
                item["failures"] = ["MALFORMED_INTERPRETATION_PACKET"]
                continue
            prediction = execution.get("prediction")
            observations[cid] = {k:v for k,v in execution.items() if k!="prediction"}
            if prediction is None and execution.get("reason"):
                item.update(review=[execution["reason"]],retry=True)
                continue
            try:
                # The actual interpreter is the only prediction producer. The checks
                # still fail closed when a damaged response reaches the write boundary.
                item["interpreter_families"] = list(prediction["summary"]["modules"])
                if prediction["inci_id"]!=parent["inci_id"]:
                    item["failures"] = ["BINDING"]
                    continue
                faults,review = check(row,parent,aliases,prediction,self.manifest,self.version)
                if faults:
                    item["failures"] = faults
                    continue
                approved = restrict(prediction,parent)
                item["review"],item["excluded_aliases"] = _review_tags(prediction,review,approved)
            except (KeyError,TypeError,AttributeError,ValueError):
                item["failures"] = ["MALFORMED_INTERPRETATION_PACKET"]
                continue
            raw[cid],published[cid] = prediction,approved
        gate = decision(checked)
        event.update(gate, checks=checked, execution=observations, inserted=0,
                     retry_ids=[i["id"] for i in gate["retry_records"]])
        if gate["decision"]=="ACCEPT":
            self._record({**event,"decision":"VALIDATED_PENDING_COMMIT"})
            try:
                event["inserted"] = _write_batch(self.registry,[p[0] for p in selected],published,self.version,
                                                  Counter(),interrupt)
            except (sqlite3.Error,ValueError,KeyboardInterrupt) as exc:
                event.update(decision="REJECT",critical_checks={"TRANSACTION":1},retry_ids=list(ids),
                             transaction_error=type(exc).__name__)
                if isinstance(exc,KeyboardInterrupt):
                    event["interrupted"] = True
        event["elapsed_seconds"] = perf_counter()-start
        event["queue"] = _queue(event["id"],checked)
        if "transaction_error" in event:
            event["queue"].append({"event":event["id"],"reason":"TRANSACTION","severity":"CRITICAL",
                                   "status":"RETRY","concept_id":None,"source_record":None,"interpreter":["unassigned"]})
        self._record(event)
        return event,raw,published


def queue_items(journal, *, reason=None, severity=None, status=None, interpreter=None, source_record=None):
    """Return the latest actionable item for each source/reason, with historical events intact."""
    items = {}
    for event in read(journal):
        if "queue" not in event:
            continue
        if event["decision"]=="ACCEPT":
            items = {key:item for key,item in items.items() if item["concept_id"] not in event["ids"]}
        elif event["operation"]=="RETRY" and event["decision"] in {"REJECT","HOLD"}:
            items = {key:item for key,item in items.items() if item["concept_id"] not in event["ids"] or
                     item["status"] not in {"RETRY","QUARANTINED"}}
        for item in event["queue"]:
            items[(item["concept_id"],item["reason"])] = item
        if event["decision"]=="ACCEPT" and event["parent_event"]:
            items = {key:item for key,item in items.items() if item["event"]!=event["parent_event"] or
                     item["reason"]!="TRANSACTION"}
    return sorted((item for item in items.values()
                   if (reason is None or reason==item["reason"])
                   and (severity is None or severity==item["severity"])
                   and (status is None or status==item["status"])
                   and (interpreter is None or interpreter in item["interpreter"])
                   and (source_record is None or source_record==item["source_record"])),
                  key=lambda item:({"CRITICAL":0,"HIGH":1,"MEDIUM":2}[item["severity"]],
                                   item["source_record"] or "",item["reason"]))
