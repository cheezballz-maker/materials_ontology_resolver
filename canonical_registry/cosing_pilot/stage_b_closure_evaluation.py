"""Run bounded Stage B confirmation, failure injection, and registry audit."""

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack, closing
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import re
import sqlite3
from time import perf_counter

from .benchmark_readiness import peak_rss
from .full_capture import digest, read, write
from .registry import canonical, fingerprint
from .stage_b_closure import DEFAULT_BUDGET, OUTPUT, MonitoredBatch, queue_items
from .stage_b_evidence import _eligible_alias
from .stage_b_v1 import _overlay
from .stage_b_v2 import _audit, _baseline_state
from .stage_b_v2_evidence import verified
from .stage_b_v3 import DB as V3_DB, _build, _cached, _guards
from .stage_b_v3_cohort import OUTPUT as V3, PARENT_ARCHIVE
from .stage_b_worker import StageBWorker
from .staged_assessment import _bridge, _select, interpretation_version
from .staged_registry import StagedRegistry

HEALTHY = ("UREA","CUPRIC OXIDE","ACETANILID","GLUTAMINE","AMMONIUM ACETATE","CARNITINE HCL",
           "QUERCETIN CAPRYLATE","CITRUS SUNKI SEED OIL","SODIUM GLUCONATE","THORIUM DIOXIDE",
           "HC BLUE NO. 16","SORBETH-7","RHAMNOLIPIDS","STRONTIUM HYDROXIDE","ILLITE","POLYURETHANE-46",
           "ACACIA FARNESIANA STEM BARK EXTRACT","ZINC DNA","SODIUM RNA","GLYCOL ROSINATE")
PATHOLOGICAL = ("DIRECT RED 23","PERFLUORODECALIN")
DEVELOPMENT = ("SILICON/TITANIUM/CERIUM/ZINC OXIDES","TOCOPHERETH-18","NONOXYNOL-35",
               "CETOLETH-18","SODIUM C12-15 ALKETH-3 SULFONATE","COCETH-7 CARBOXYLIC ACID")
REGISTRY = V3_DB.with_name("cosing_stage_b_v3_gate_closure.sqlite")
FRESH = OUTPUT/"frozen_confirmation.json"
ALIASES = OUTPUT/"fresh_alias_capture.json"


def _policy():
    inputs = (FRESH,ALIASES,OUTPUT/"frozen_known_controls.json",V3/"companion_manifest.json",V3/"aliases.json")
    hashes = {str(p):digest(p) for p in inputs}
    manifest = fingerprint(hashes)
    policy_paths = (Path(__file__).with_name("stage_b_closure.py"),Path(__file__).with_name("stage_b_worker.py"))
    version = "cosing-stage-b-v3-closure:"+fingerprint([manifest,interpretation_version(False),[digest(p) for p in policy_paths]])
    return hashes,manifest,version


def _verified(hashes):
    try:
        return all(digest(Path(k))==v for k,v in hashes.items())
    except OSError:
        return False


def freeze():
    path = OUTPUT/"frozen_known_controls.json"
    if path.exists():
        raise FileExistsError(path)
    known = {x["parent"]["inci"]:x["parent"]["inci_id"] for x in read(V3/"cohort.json")["records"]}
    groups = {"healthy_controls":HEALTHY,"pathological":PATHOLOGICAL,"development":DEVELOPMENT}
    fallback = {name:"generic" for name in ("ZINC DNA","SODIUM RNA","GLYCOL ROSINATE",
               "SODIUM C12-15 ALKETH-3 SULFONATE","COCETH-7 CARBOXYLIC ACID")}
    fallback.update({name:"specialist" for name in ("TOCOPHERETH-18","NONOXYNOL-35","CETOLETH-18","RHAMNOLIPIDS")})
    write(path,{"groups":{g:[{"name":n,"key":known[n]} for n in names] for g,names in groups.items()},
                "expected_fallback":fallback,"expect_protected_graphs":True,
                "fresh_reference_sha256":digest(FRESH),
                "v3_predictions_sha256":digest(V3/"corrected_predictions.json")})


def _source_packets(registry, version, manifest):
    fresh = read(FRESH)
    known = read(OUTPUT/"frozen_known_controls.json")
    assert fresh["parent_sha256"]==digest(PARENT_ARCHIVE)
    assert known["fresh_reference_sha256"]==digest(FRESH)
    archive, evidence, held, _ = verified(V3)
    evidence,held = dict(evidence),dict(held)
    selected = {x["key"]:g for g,rows in known["groups"].items() for x in rows}
    records = {x["parent"]["inci_id"]:{**x,"cohort":selected[x["parent"]["inci_id"]]}
               for x in read(V3/"cohort.json")["records"] if x["parent"]["inci_id"] in selected}
    fresh_records = {x["parent"]["inci_id"]:x for x in fresh["rows"]}
    records.update(fresh_records)
    for key in records:
        evidence.setdefault(key,[])
        held.setdefault(key,[])
    capture = read(ALIASES)
    raw = [{k:r.get(k) for k in capture["columns"]} for r in capture["rows"]]
    assert raw and len(raw)<400 and {int(r["capture_rows"]) for r in raw}=={len(raw)}
    assert {r["inci_id"] for r in raw}==set(fresh_records)
    assert len({r["inci_alias_id"] for r in raw if r["inci_alias_id"]})==sum(bool(r["inci_alias_id"]) for r in raw)
    for key in fresh_records:
        evidence[key],held[key] = [],[]
    for row in raw:
        if not row["inci_alias_id"]:
            continue
        working = {**row}
        for field in ("created_ts","updated_ts"):
            if row[field] is not None:
                working[field] = int(datetime.fromisoformat(row[field].removesuffix(" UTC")+"+00:00").timestamp()*1000)
        reason = _eligible_alias(working,archive["parent_cutoff_epoch_ms"])
        key = row["inci_id"]
        if reason:
            held[key].append({"id":row["inci_alias_id"],"type":row["alias_type"],"reason":reason})
        else:
            evidence[key].append({k:row[k] for k in ("inci_alias_id","alias_type","alias","source","lang")})
    overlay = _overlay([x["parent"] for x in records.values()],evidence,held,manifest)
    packets, groups = {},defaultdict(list)
    for source in _select(registry,(),list(records),None):
        row = dict(source)
        parent,aliases,provenance = overlay(row,json.loads(row["payload_json"]))
        item = records[parent["inci_id"]]
        cid = row["concept_id"]
        packets[cid] = row,item,parent,aliases,provenance,version
        groups[item["cohort"]].append(cid)
    assert len(packets)==len(records)
    return packets,groups,known


def _outcomes(event):
    return {k:event.get(k) for k in ("id","parent_event","operation","decision","inserted","elapsed_seconds",
                                    "critical_checks","retry_ids","eligible_for_rebatch","held_families")}


def _faults(session, by_name, worker, budget, count):
    safe = by_name["ACETANILID"]
    bad = by_name["ACACIA FARNESIANA STEM BARK EXTRACT"]
    other = by_name["CITRUS SUNKI SEED OIL"]
    original = session.verify_source
    events = {}

    def compute_with(fault):
        def compute(packet, seconds):
            result = worker.run(packet,seconds)
            assert result["prediction"] is not None
            if packet[0]["concept_id"]!=safe:
                fault(result)
            return result
        return compute

    def execute(name, ids, compute):
        event,_,_ = session.submit(ids,compute,budget)
        assert count()==starting
        events[name] = _outcomes(event)
        return event

    starting = count()
    digest_mismatch = lambda: digest(ALIASES)==digest(FRESH)
    session.verify_source = digest_mismatch
    event = execute("source_digest_mismatch",[bad,safe],worker.run)
    assert event["decision"]=="REJECT" and not event["eligible_for_rebatch"]
    session.verify_source = original

    stale = session.packets[bad][0]
    stale["observed_revision"] = "injected stale revision"
    try:
        event = execute("stale_revision",[bad,safe],worker.run)
        assert event["critical_checks"]=={"REVISION":1} and event["eligible_for_rebatch"]==[safe]
    finally:
        stale["observed_revision"] = stale["registered_revision"]

    def malformed(result):
        result["prediction"].pop("trace")

    event = execute("malformed_packet",[bad,safe],compute_with(malformed))
    assert event["critical_checks"]=={"MALFORMED_INTERPRETATION_PACKET":1}
    rebatch,_,_ = session.rebatch(event["id"],worker.run,budget)
    assert rebatch["decision"]=="ACCEPT" and rebatch["inserted"]==1
    events["safe_rebatch"] = _outcomes(rebatch)
    starting += 1

    def unsupported(result):
        result["prediction"]["attributes"][0]["predicate"] = "canonical_identity"

    event = execute("shared_identity_scope_defect",[bad,other,safe],compute_with(unsupported))
    assert event["critical_checks"]["MATERIAL_SCOPE"]==2 and "botanical" in event["held_families"]
    assert event["eligible_for_rebatch"]==[safe]

    def disputed(result):
        interpretation = result["prediction"]["trace"]["interpretation"]
        a = interpretation["assertions"][0]
        a["depends_on"] = ["injected.scope"]
        interpretation["issues"] = [*interpretation["issues"],{"code":"INJECTED_SCOPE_CONFLICT","conflict":True,
                                                                   "affected_slots":["injected.scope"]}]

    event = execute("conflicting_dependency",[bad,safe],compute_with(disputed))
    assert "CONFLICT_ISOLATION" in event["critical_checks"]

    # A real SQLite abort rolls back the earlier row in the same write batch.
    with session.registry.writer() as db:
        db.execute(f"""CREATE TRIGGER closure_injected_abort BEFORE INSERT ON assessment
                       WHEN NEW.concept_id='{other}' BEGIN SELECT RAISE(ABORT,'injected write failure'); END""")
    try:
        event = execute("sqlite_abort",[bad,other],worker.run)
        assert event["critical_checks"]=={"TRANSACTION":1}
    finally:
        with session.registry.writer() as db:
            db.execute("DROP TRIGGER closure_injected_abort")

    def interrupted():
        raise SystemExit("injected coordinator interruption")

    try:
        session.submit([bad,other],worker.run,budget,interrupt=interrupted)
    except SystemExit:
        pending = read(session.journal)[-1]
        assert pending["decision"]=="VALIDATED_PENDING_COMMIT" and count()==starting
    else:
        raise AssertionError("The coordinator interruption was not exercised")
    reopened = MonitoredBatch(StagedRegistry(session.registry.path),session.journal,session.packets,
                             session.version,session.manifest,session.verify_source)
    recovered,_,_ = reopened.resume(pending["id"],worker.run,budget)
    assert recovered["decision"]=="ACCEPT" and recovered["inserted"]==2
    again,_,_ = reopened.retry(event["id"],worker.run,budget)
    assert again["decision"]=="ACCEPT" and again["inserted"]==0
    events.update(interruption=_outcomes(pending),restart=_outcomes(recovered),transaction_retry=_outcomes(again))
    return events


def evaluate(retry_seconds, run_name=None):
    from rdkit import rdBase
    from canonical_registry.nomenclature_interpretation import InterpretationFramework
    from canonical_registry.nomenclature_interpretation.cosing_preview_adapter import COSMETICS_FUNCTIONS

    start = perf_counter()
    protected = {**_guards(),str(V3_DB):digest(V3_DB)}
    assert protected[str(V3_DB)]==(OUTPUT/"v3_database.sha256").read_text(encoding="utf-8").strip()
    hashes,manifest,version = _policy()
    source = StagedRegistry(V3_DB)
    output = OUTPUT
    destination = REGISTRY
    if run_name is not None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,60}",run_name):
            raise ValueError("Use a simple name for the isolated reproduction directory")
        output = REGISTRY.parent/run_name
        output.mkdir()
        destination = output/"registry.sqlite"
    registry = StagedRegistry(destination)
    if destination.exists() or (output/"decision_log.json").exists():
        raise FileExistsError("The closure run requires a new dedicated registry and journal")
    packets,groups,known = _source_packets(source,version,manifest)
    with source.reader() as db,closing(sqlite3.connect(destination)) as dest:
        db.backup(dest)
    prior = _baseline_state(source,version)
    assert _baseline_state(registry,version)==prior
    before_bytes = destination.stat().st_size
    by_name = {p[2]["inci"]:cid for cid,p in packets.items()}
    session = MonitoredBatch(registry,output/"decision_log.json",packets,version,manifest,lambda:_verified(hashes))

    def count():
        with registry.reader() as db:
            return db.execute("SELECT count(*) FROM assessment WHERE pipeline_version=?",(version,)).fetchone()[0]

    audit, raw, approved = {}, {}, {}
    with ExitStack() as stack,rdBase.BlockLogs():
        bridge = _bridge(stack)
        direct = InterpretationFramework(name_parser=bridge,function_vocabularies={"cosmetics":COSMETICS_FUNCTIONS})
        healthy = groups["healthy_controls"]
        timer = perf_counter()
        inline = {}
        for cid in healthy:
            row,item,parent,aliases,provenance,_ = packets[cid]
            inline[cid] = _build(direct,bridge,row,item,lambda *_:(parent,aliases,provenance),version,Counter())
        direct_seconds = perf_counter()-timer
        worker = stack.enter_context(StageBWorker(bridge))
        timer = perf_counter()
        isolated = {cid:worker.run(packets[cid],DEFAULT_BUDGET) for cid in healthy}
        isolated_seconds = perf_counter()-timer
        assert all(canonical(inline[cid])==canonical(out["prediction"]) for cid,out in isolated.items())
        audit["healthy"] = {"records":len(healthy),"direct_seconds":direct_seconds,"isolated_seconds":isolated_seconds,
                            "record_seconds":{cid:out["elapsed_seconds"] for cid,out in isolated.items()},
                            "outputs_identical":True}
        audit["faults"] = _faults(session,by_name,worker,DEFAULT_BUDGET,count)
        red,perfluoro = (by_name[n] for n in PATHOLOGICAL)
        timer = perf_counter()
        event,r,p = session.submit([red,perfluoro,*healthy],worker.run,DEFAULT_BUDGET)
        audit["initial"] = _outcomes(event)
        assert event["decision"]=="HOLD" and red in event["retry_ids"] and len(event["eligible_for_rebatch"])>=len(healthy)
        rebatch,r,p = session.rebatch(event["id"],worker.run,DEFAULT_BUDGET)
        assert rebatch["decision"]=="ACCEPT"
        raw.update(r)
        approved.update(p)
        audit["rebatch"] = _outcomes(rebatch)
        again,_,_ = session.retry(event["id"],worker.run,DEFAULT_BUDGET,ids=[red])
        audit["repeated_timeout"] = _outcomes(again)
        assert again["decision"]=="HOLD" and again["retry_ids"]==[red]
        audit["timeout_phase_seconds"] = perf_counter()-timer

        event,r,p = session.submit([*groups["development"],*groups["fresh"]],worker.run,DEFAULT_BUDGET)
        assert event["decision"]=="ACCEPT"
        raw.update(r)
        approved.update(p)
        audit["targeted_confirmation"] = _outcomes(event)
        if retry_seconds:
            event,r,p = session.retry(again["id"],worker.run,retry_seconds)
            audit["explicit_native_retry"] = _outcomes(event)
            if event["decision"]=="ACCEPT":
                raw.update(r)
                approved.update(p)
                replay,_,_ = session.retry(again["id"],worker.run,retry_seconds)
                assert replay["decision"]=="ACCEPT" and replay["inserted"]==0
                audit["explicit_retry_replay"] = _outcomes(replay)
        timer = perf_counter()
        replay,_,_ = session.submit(list(approved),lambda packet,_:{"prediction":raw[packet[0]["concept_id"]]},DEFAULT_BUDGET)
        assert replay["decision"]=="ACCEPT" and replay["inserted"]==0
        audit["validated_replay_seconds"] = perf_counter()-timer
        audit["validated_replay_records"] = len(approved)
        audit["worker_peak_bytes"] = max(x["worker_peak_bytes"] for x in isolated.values())
        worker.close()
        audit["worker_lifecycle"] = worker.lifecycle

    assert len(_cached(registry,[packets[k][0] for k in approved],version,Counter()))==len(approved)
    guards = {**_guards(),str(V3_DB):digest(V3_DB)}
    assert protected==guards
    audit.update(registry=_audit(registry,version,prior,len(approved)), protected_before=protected, protected_after=guards,
                 version=version, manifest=manifest, source_digests=hashes, elapsed_seconds=perf_counter()-start,
                 parent_peak_bytes=peak_rss(), database_growth_bytes=destination.stat().st_size-before_bytes)
    old = read(V3/"corrected_predictions.json")["predictions"]
    prior_predictions = {x["inci_id"]:x for x in old}
    fresh = []
    for cid in groups["fresh"]:
        item = packets[cid][1]
        p = approved[cid]
        predicates = {a["predicate"] for a in p["attributes"]}
        before = {a["predicate"] for a in raw[cid]["attributes"]}
        must = item["must_have"]
        forbidden = item["must_withhold"]
        semantic_pass = (not must or must in predicates) and (not forbidden or forbidden not in predicates)
        identity_safe = not predicates.intersection({"molecular_graph","reported_taxon_text","reported_taxon_rank","canonical_identity"})
        fresh.append({"id":cid,"name":p["name"],"must_have":must,"must_withhold":forbidden,
                      "raw_predicates":sorted(before),"published_predicates":sorted(predicates),
                      "semantic_pass":semantic_pass,"identity_safe":identity_safe})
    fallback = [{"name":name,"expected":expected,
                 "actual":"generic" if "generic_ingredient" in raw[by_name[name]]["summary"]["modules"] else "specialist"}
                for name,expected in known["expected_fallback"].items()]
    write(output/"confirmation_results.json",{"fresh":fresh,"fallback":fallback,"audit":audit,
        "queue_counts":dict(Counter(x["reason"] for x in queue_items(session.journal)))})
    write(output/"semantic_outputs.json",{"archived_v3":[prior_predictions[x["inci_id"]] for x in raw.values()
          if x["inci_id"] in prior_predictions],"corrected":list(raw.values()),"approved":list(approved.values())})
    print("Completed closure confirmation",len(approved),audit["registry"],flush=True)


def _operator(options):
    from os.path import samefile

    published = read(OUTPUT/"confirmation_results.json")["audit"]
    hashes,manifest,version = _policy()
    if (version,manifest,hashes)!=(published["version"],published["manifest"],published["source_digests"]):
        raise ValueError("The current inputs no longer match the verified closure copy")
    registry = StagedRegistry(REGISTRY)
    guards = {**_guards(),str(V3_DB):digest(V3_DB)}
    if guards!=published["protected_after"] or any(
            value is not None and samefile(registry.path,path) for path,value in guards.items()):
        raise ValueError("Protected files or the working database path changed")
    source = StagedRegistry(V3_DB)
    prior = _baseline_state(source,version)
    if _baseline_state(registry,version)!=prior:
        raise ValueError("The working copy no longer matches its verified lineage")
    packets,_,_ = _source_packets(source,version,manifest)
    session = MonitoredBatch(registry,OUTPUT/"decision_log.json",packets,version,manifest,lambda:_verified(hashes))
    with ExitStack() as stack:
        worker = stack.enter_context(StageBWorker(_bridge(stack)))
        if options.action=="batch":
            event,_,_ = session.submit(options.concept,worker.run,options.budget_seconds)
        elif options.action=="retry":
            event,_,_ = session.retry(options.event,worker.run,options.budget_seconds,ids=options.concept or None)
        else:
            event,_,_ = getattr(session,options.action)(options.event,worker.run,options.budget_seconds)
    with registry.reader() as db:
        count = db.execute("SELECT count(*) FROM assessment WHERE pipeline_version=?",(version,)).fetchone()[0]
    _audit(registry,version,prior,count)
    if guards!={**_guards(),str(V3_DB):digest(V3_DB)}:
        raise ValueError("A protected path changed during processing")
    print(canonical(_outcomes(event)))


def _matched_warm_benchmark():
    from rdkit import rdBase
    from canonical_registry.nomenclature_interpretation import InterpretationFramework
    from canonical_registry.nomenclature_interpretation.cosing_preview_adapter import COSMETICS_FUNCTIONS

    _,manifest,version = _policy()
    packets,groups,_ = _source_packets(StagedRegistry(V3_DB),version,manifest)
    selected = [packets[cid] for cid in groups["healthy_controls"]]
    trials = []
    with ExitStack() as stack, rdBase.BlockLogs():
        bridge = _bridge(stack)
        framework = InterpretationFramework(name_parser=bridge,function_vocabularies={"cosmetics":COSMETICS_FUNCTIONS})
        worker = stack.enter_context(StageBWorker(bridge))

        def direct():
            return [_build(framework,bridge,p[0],p[1],lambda *_:p[2:5],version,Counter()) for p in selected]

        def isolated():
            return [worker.run(p,DEFAULT_BUDGET)["prediction"] for p in selected]

        def measure(run):
            start = perf_counter()
            return run(),perf_counter()-start

        assert canonical(direct())==canonical(isolated())
        for index in range(6):
            runners = (direct,isolated) if index%2==0 else (isolated,direct)
            samples = {fn.__name__:measure(fn) for fn in runners}
            assert canonical(samples["direct"][0])==canonical(samples["isolated"][0])
            trials.append({"direct_seconds":samples["direct"][1],"isolated_seconds":samples["isolated"][1],
                           "isolated_first":index%2==1})
    write(OUTPUT/"warm_benchmark.json",{"records_per_trial":len(selected),"trials":trials,
          "outputs_identical":True,"worker_lifecycle":worker.lifecycle})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("freeze","run","queue","benchmark","batch","retry","rebatch","resume"))
    parser.add_argument("--retry-seconds",type=float,default=0)
    parser.add_argument("--run-name")
    parser.add_argument("--budget-seconds",type=float,default=DEFAULT_BUDGET)
    parser.add_argument("--event")
    parser.add_argument("--concept",action="append",default=[])
    for key in ("reason","severity","status","interpreter","source-record"):
        parser.add_argument("--"+key)
    options = parser.parse_args()
    if options.action=="freeze":
        freeze()
    elif options.action=="run":
        evaluate(options.retry_seconds,options.run_name)
    elif options.action=="queue":
        print(canonical(queue_items(OUTPUT/"decision_log.json",**{k:getattr(options,k) for k in
                                  ("reason","severity","status","interpreter","source_record")})))
    elif options.action=="benchmark":
        _matched_warm_benchmark()
    else:
        if options.action=="batch" and not options.concept:
            parser.error("batch requires at least one --concept")
        if options.action!="batch" and not options.event:
            parser.error(f"{options.action} requires --event")
        _operator(options)


if __name__=="__main__":
    main()
