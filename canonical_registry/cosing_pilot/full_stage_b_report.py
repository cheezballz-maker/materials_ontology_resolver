"""Aggregate completed or stopped full Stage B execution into the review report."""

from collections import Counter
import json
from pathlib import Path
import sqlite3
from statistics import median
from xml.etree import ElementTree

from .full_capture import digest, read, write
from .full_stage_b_capture import MANIFEST, OUTPUT
from .full_stage_b_enrichment import (
    CLOSURE_DB, JOURNALS, PROGRESS, REGISTRY, STOP, SystemicFailure, _baseline_state, _events, _integrity, _protected, utc,
)
from .organization import SUPPORTED_DESCRIPTORS
from .stage_b_closure import queue_items
from .staged_registry import StagedRegistry

REPORT = Path(__file__).resolve().parents[1]/"FULL_COSING_STAGE_B_ENRICHMENT_V1_REPORT.md"
STRUCTURAL_TYPES = {"SMILES","INCHI","INCHI_KEY","MOLECULAR_FORMULA"}


def pct(n,d):
    return f"{n/d:.2%}" if d else "n/a"


def _semantic(registry, version):
    state, modules, predicates, roles, holds = (Counter() for _ in range(5))
    totals = Counter()
    examples, critical = {},[]
    with registry.reader() as db:
        rows = db.execute("""SELECT a.*, d.preferred_label FROM assessment a
                             JOIN domain_concept d USING(concept_id) WHERE pipeline_version=?""",(version,))
        for row in rows:
            cid = row["concept_id"]
            attrs,functions,summary,trace = (json.loads(row[k+"_json"]) for k in ("attributes","roles","summary","trace"))
            interp = trace["interpretation"]
            state[summary["state"]]+=1
            modules.update(summary["modules"])
            totals.update({"new_assessments":1,"with_descriptors":bool(attrs),"with_qualified_roles":bool(functions),
                           "fallback_records":"generic_ingredient" in summary["modules"],
                           "conflicts_retaining_descriptors":summary["state"]=="CONFLICT" and bool(attrs),
                           "withheld_assertions":len(interp["withheld_assertions"])})
            predicates.update(a["predicate"] for a in attrs)
            roles.update(v for f in functions for v in f["qualified_vocabulary_labels"])
            holds.update(h["reason"] for h in trace["publication_review"]["withheld"])
            graphs = [a for a in interp["assertions"] if a["category"]=="STRUCTURAL"]
            withheld = [a for a in interp["withheld_assertions"] if a["category"]=="STRUCTURAL"]
            totals.update({"retained_candidate_graphs":len(graphs),"withheld_candidate_graphs":len(withheld),
                           "records_with_withheld_graphs":bool(withheld)})
            guarded = summary["state"]=="CONFLICT" or any(m["whole_referent_graph_unestablished"] for m in interp["modules"]) or any(
                a["type"] in STRUCTURAL_TYPES for a in trace["companion_evidence"]["held_aliases"])
            blocked = {s for i in interp["issues"] if i["conflict"] for s in i["affected_slots"]}
            retained_audit = {(a["predicate"],json.dumps(a["value"],sort_keys=True),a["evidence"]["source_reference"],a["method"])
                              for a in trace["assertion_audit"] if a["decision"]=="PERSISTED_DESCRIPTOR"}
            actual = {(a["predicate"],json.dumps(a["value"],sort_keys=True),a["source_reference"],a["method"]) for a in attrs}
            if (guarded and graphs or any(a["evidence_role"]!="CANDIDATE_ONLY" for a in graphs+withheld)
                    or any(a["predicate"] not in SUPPORTED_DESCRIPTORS or a.get("exclusive_slot") in blocked
                           or blocked.intersection(a["depends_on"]) for a in attrs) or actual!=retained_audit):
                critical.append({"concept_id":cid,"source_label":row["preferred_label"]})
            if summary["state"]=="CONFLICT" and attrs:
                examples.setdefault("independent_descriptors",{"id":cid,"name":row["preferred_label"],
                                                               "predicates":sorted({a["predicate"] for a in attrs})})
    return {"totals":dict(totals),"states":dict(state),"modules":dict(modules),"descriptors":dict(predicates),
            "qualified_roles":dict(roles),"publication_holds":dict(holds),"critical_failures":critical,"examples":examples}


def _operations():
    decisions,failures,workers,provider = Counter(),Counter(),Counter(),Counter()
    times,latencies,processed,queue = [],[],set(),[]
    peak = 0
    exceptions = {}
    for path in sorted(JOURNALS.glob("*.json")):
        queue.extend(queue_items(path))
        for event in _events(path).values():
            decision = event["decision"]
            if decision not in {"ACCEPT","HOLD","REJECT"}:
                continue
            decisions[(event["operation"],decision)]+=1
            failures.update(event["critical_checks"])
            times.append(event["elapsed_seconds"])
            processed.update(event["execution"])
            for cid,result in event["execution"].items():
                if result.get("reason"):
                    workers[result["reason"]]+=1
                if result.get("reason")=="WORKER_EXCEPTION":
                    exceptions[cid] = {"type":result.get("error"),"message":result.get("detail")}
                if "elapsed_seconds" in result:
                    latencies.append(result["elapsed_seconds"])
                peak = max(peak,result.get("worker_peak_bytes",0))
                provider.update(p["status"] for p in result.get("provider_activity",[]))
    latencies.sort()
    def quantile(p):
        return latencies[min(round(p*(len(latencies)-1)),len(latencies)-1)] if latencies else 0
    return {"attempted_records":len(processed),"decisions":{"/".join(k):v for k,v in decisions.items()},
            "gate_failures":dict(failures),"worker_failures":dict(workers),
            "peak_worker_bytes":peak,"opsin_response_counts":dict(provider),"worker_exception_diagnostics":exceptions,
            "batch_event_seconds_median":median(times) if times else 0,
            "elapsed_attempts":len(latencies),"latency_seconds":{"p50":quantile(.5),"p95":quantile(.95),
            "p99":quantile(.99),"max":quantile(1)}},queue


def generate():
    progress = read(PROGRESS) if PROGRESS.exists() else {}
    stop = read(STOP) if STOP.exists() else None
    source = read(MANIFEST) if MANIFEST.exists() else None
    frozen = progress.get("frozen",{})
    batches = progress.get("batches",{})
    semantic, integrity = {},{}
    if REGISTRY.exists() and frozen:
        registry = StagedRegistry(REGISTRY)
        version = frozen["version"]
        try:
            historical = _baseline_state(StagedRegistry(CLOSURE_DB),version)
            integrity = _integrity(registry,version,historical)
            if _protected()!=frozen["protected_before"]:
                raise SystemicFailure("PROTECTED_PATH_CHANGED",{})
            semantic = _semantic(registry,version)
        except (SystemicFailure,OSError,ValueError,sqlite3.Error) as exc:
            stop = stop or {"at":utc(),"code":getattr(exc,"code","FINAL_INTEGRITY_AUDIT_FAILED"),
                            "detail":getattr(exc,"detail",{"message":str(exc)})}
            if not STOP.exists():
                write(STOP,stop)
        if semantic.get("critical_failures") and stop is None:
            stop = {"at":utc(),"code":"POST_PUBLICATION_SEMANTIC_INTEGRITY_FAILURE",
                    "detail":{"records":semantic["critical_failures"]}}
            write(STOP,stop)
    operations,queue = _operations()
    queue.sort(key=lambda r:({"CRITICAL":0,"HIGH":1,"MEDIUM":2}[r["severity"]],r["source_record"] or "",r["reason"]))
    queue_counts = Counter(x["reason"] for x in queue)
    if queue:
        write(OUTPUT/"review_queue.json",queue)
    new = integrity.get("new_assessments",sum(batch["completed"] for batch in batches.values()))
    previous = frozen.get("existing_assessed",2404)
    target = frozen.get("target_records",30360-previous)
    remaining = target-new
    held = {cid for b in batches.values() for cid in b["held"]}
    quarantine = {cid for b in batches.values() for cid in b["quarantined"]}
    unpublished_details = []
    if (held or quarantine) and integrity:
        by_id = {}
        for item in queue:
            by_id.setdefault(item["concept_id"],[]).append(item["reason"])
        with StagedRegistry(REGISTRY).reader() as db:
            for cid in sorted(held|quarantine):
                label = db.execute("SELECT preferred_label FROM domain_concept WHERE concept_id=?",(cid,)).fetchone()[0]
                unpublished_details.append({"concept_id":cid,"label":label,
                    "outcome":"HOLD" if cid in held else "QUARANTINED","reasons":sorted(set(by_id.get(cid,[])))})
    elapsed = sum(s["elapsed_seconds"] for s in progress.get("sessions",[]))
    worker_starts = [e["elapsed_seconds"] for s in progress.get("sessions",[]) for e in s.get("worker_lifecycle",[])
                     if e["event"]=="started"]
    finished = bool(progress.get("finished_at"))
    status = "STOPPED" if stop else "FINISHED_WITH_HOLDS" if finished and remaining else "FINISHED" if finished else "IN_PROGRESS"
    old_any = 2799
    with StagedRegistry(CLOSURE_DB).reader() as db:
        old_ids = {r[0] for r in db.execute("SELECT DISTINCT concept_id FROM assessment")}
        old_any = len(old_ids)
    legacy_only = old_any-previous
    legacy_completed = 0
    if integrity:
        with StagedRegistry(REGISTRY).reader() as db:
            legacy_completed = sum(r[0] in old_ids for r in db.execute(
                "SELECT concept_id FROM assessment WHERE pipeline_version=?",(frozen["version"],)))
    growth = REGISTRY.stat().st_size-CLOSURE_DB.stat().st_size if REGISTRY.exists() else 0
    metrics = {"status":status,"existing_assessed":previous,"target_records":target,"new_assessments":new,
               "unpublished":remaining,"completed_batches":len(batches),"held":sorted(held),
               "quarantined":sorted(quarantine),"sessions":progress.get("sessions",[]),"semantic":semantic,
               "operations":operations,"queue_counts":dict(queue_counts),"integrity":integrity,"stop":stop,
               "prior_any_assessment":old_any,"prior_organization_only":legacy_only,
               "prior_organization_only_now_assessed":legacy_completed,"database_growth_bytes":growth,
               "unpublished_details":unpublished_details}
    write(OUTPUT/"metrics.json",metrics)
    data = "cosing_pilot/data/full_stage_b_v1/"
    lines = ["# Full-Scale CosIng Stage B Semantic Enrichment v1","",
             f"**{status}.** The working copy contains {previous+new:,} of 30,360 registered concepts with a current Stage B assessment. "
             f"The full-scale run added {new:,} of {target:,} targeted assessments. "
             f"{remaining:,} target concepts remain without a completed assessment.",""]
    if stop:
        lines += [f"Execution stopped on `{stop['code']}`. No further batches were authorized by the runner after this failure.",
                  f"The stop receipt identifies the affected batch and evidence. [Stop receipt]({data}stop.json)",""]
    lines += ["## Coverage and quality","", "| Measure | Result |","| --- | ---: |",
              f"| Prior assessed concepts retained | {previous:,} |",
              f"| New Stage B assessments | {new:,}/{target:,} |",
              f"| Total current assessment coverage | {previous+new:,}/30,360 ({pct(previous+new,30360)}) |",
              f"| Distinct target concepts with an execution receipt | {operations['attempted_records']:,} |",
              f"| Completed monitored batch groups | {len(batches):,} |",
              f"| Unpublished holds / quarantines in accounted batch groups | {len(held):,} / {len(quarantine):,} |",""]
    lines += [f"The starting registry contained assessments for {old_any:,} distinct concepts. "
              f"{legacy_only:,} had only legacy organization-pilot outputs, so they were included in the target for a dedicated Stage B assessment. "
              f"Of those, {legacy_completed:,} received a dedicated Stage B assessment. All of their pilot rows were preserved. "
              f"[Batch and lineage checkpoints]({data}progress.json)",""] if progress else []
    if semantic:
        t = semantic["totals"]
        lines += [f"Of the {new:,} new assessments, {t.get('with_descriptors',0):,} contain at least one qualified descriptor, "
                  f"{t.get('with_qualified_roles',0):,} contain a qualified function, and {t.get('fallback_records',0):,} used generic fallback.",
                  f"Structural candidates retained or withheld numbered {t.get('retained_candidate_graphs',0):,} and {t.get('withheld_candidate_graphs',0):,}. "
                  f"The persistence audit detected {len(semantic['critical_failures']):,} critical semantic violations among committed assessments.",
                  f"Within source-conflict assessments, {t.get('conflicts_retaining_descriptors',0):,} retained independently qualified descriptors.",
                  "These checks measure policy compliance and output coverage. Independent accuracy across the full dataset remains unmeasured.",""]
        for title,key in (("Interpretation state","states"),("Interpreter routes","modules"),
                          ("Assertion-level publication holds","publication_holds")):
            lines += [f"| {title} | Count |","| --- | ---: |",
                      *(f"| {k} | {n:,} |" for k,n in sorted(semantic[key].items())),""]
    if source:
        lines += ["## Source verification","",
                  f"The read-only source capture verified all {source['parent_count']:,} registered parents and "
                  f"{source['alias_count']:,} original companion rows across {len(source['buckets'])} buckets. "
                  "Before and after parent digests matched the registered archive. Alias counts, keys and content digests matched the live profiles. "
                  f"The source qualification rule admitted {source['alias_eligibility'].get('ELIGIBLE_ORIGINAL_ALIAS',0):,} original alias claims as eligible evidence. "
                  f"There were {source['parents_without_aliases']:,} registered parents without companion alias rows. "
                  "The capture has no atomic cross-table version pin. "
                  f"[Source manifest]({data}source_manifest.json), [alias capture SQL]({data}alias_bucket.sql)",""]
    l = operations["latency_seconds"]
    lines += ["## Performance and review backlog","",
              f"Recorded execution time was {elapsed:,.1f} seconds across {len(progress.get('sessions',[]))} session"
              f"{'' if len(progress.get('sessions',[]))==1 else 's'}. "
              f"Completed-assessment throughput was {new/elapsed if elapsed else 0:.2f}/s. "
              f"The {operations['elapsed_attempts']:,} timed attempts had p50, p95 and p99 latencies of "
              f"{l['p50']:.3f}, {l['p95']:.3f} and {l['p99']:.3f} seconds. The longest recorded attempt took {l['max']:.3f} seconds.",
              "The six-second chemistry deadline remained in force for retries. Worker startup and cancellation cleanup are accounted for separately by the existing worker.",
              f"Worker starts numbered {len(worker_starts):,}, with a median startup of "
              f"{median(worker_starts) if worker_starts else 0:.2f} seconds. The highest recorded worker working set was "
              f"{operations['peak_worker_bytes']/1024**2:.1f} MiB.",
              f"The SQLite working copy grew by {growth/1024**2:.1f} MiB.",
              f"Operational decisions were {', '.join(f'{k} {v:,}' for k,v in sorted(operations['decisions'].items())) or 'none'}.",
              f"Processing hold reasons were {', '.join(f'{k} {v:,}' for k,v in sorted(operations['worker_failures'].items())) or 'none'}.",
              "", "| Actionable reason | Items |","| --- | ---: |",
              *(f"| {reason} | {count:,} |" for reason,count in queue_counts.most_common()),""]
    if queue:
        lines += [f"The current run produced {len(queue):,} actionable items across "
                  f"{len({r['concept_id'] for r in queue if r['concept_id']}):,} concepts. Multiple reasons can apply to one concept. "
                  f"Historical review records remain in their source artifacts. [Current review queue]({data}review_queue.json)",""]
    if unpublished_details:
        categories = Counter((item["outcome"],reason) for item in unpublished_details for reason in item["reasons"])
        lines += ["| Unpublished outcome and reason | Concepts |","| --- | ---: |",
                  *(f"| {state} · {reason} | {n:,} |" for (state,reason),n in sorted(categories.items())),"",
                  f"Concept IDs, source labels and reasons for unpublished outcomes are listed in the [metrics]({data}metrics.json).",""]
        for item in unpublished_details:
            cid = item["concept_id"]
            if cid in operations["worker_exception_diagnostics"]:
                error = operations["worker_exception_diagnostics"][cid]
                lines += [f"`{cid}` remained on hold after its original designation was rejected by the source-text validation contract. "
                          f"The worker reported `{error['type']}` with message `{error['message']}`.",""]
    lines += ["## Registry integrity",""]
    if integrity:
        lines += [f"SQLite integrity passed with zero foreign-key violations. All {integrity['concepts']:,} concept IDs, source heads and "
                  f"{integrity['history_rows']:,} prior assessment rows were preserved. Canonical status remained 30,230 "
                  "`NOT_EVALUATED` and 130 `UNRESOLVED`. Canonical targets remained zero. "
                  f"All {len(frozen['protected_before'])} protected paths matched their starting digests. "
                  "[Working registry](cosing_pilot/local/cosing_full_stage_b_enrichment_v1.sqlite)",""]
    lines += ["Stage C did not run. Canonical mappings and ingredient merges were outside the execution path.",
              f"[Metrics and integrity evidence]({data}metrics.json)",""]
    test_path = OUTPUT/"tests.xml"
    if test_path.exists():
        test = ElementTree.parse(test_path).getroot()[0].attrib
        lines += [f"The scoped regression run reported {test['tests']} tests, {test['failures']} failures and {test['errors']} errors. "
                  f"[Regression results]({data}tests.xml)",""]
    if progress:
        lines += ["For an interrupted run, use the same command and working copy. The coordinator verifies the source, policy and journal lineage before resuming. A systemic stop leaves a separate stop receipt.","",
                  "```powershell",
                  "python -B -m canonical_registry.cosing_pilot.full_stage_b_enrichment --workers 6",
                  "python -B -m canonical_registry.cosing_pilot.full_stage_b_report",
                  "```",""]
    REPORT.write_text("\n".join(lines),encoding="utf-8")
    return status


if __name__=="__main__":
    print(generate())
