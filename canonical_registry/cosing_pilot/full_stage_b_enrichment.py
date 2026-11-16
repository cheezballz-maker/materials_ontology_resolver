"""Run the validated Stage B gate over the remaining registered CosIng concepts."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, closing, contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from threading import Lock, local
from time import perf_counter

from .full_capture import digest, read, write
from .full_stage_b_capture import BUCKETS, CAPTURE, MANIFEST, OUTPUT, PARENT_ARCHIVE, load_bucket, source_bucket
from .registry import canonical, fingerprint
from .stage_b_closure import DEFAULT_BUDGET, MonitoredBatch, queue_items
from .stage_b_closure_evaluation import REGISTRY as CLOSURE_DB, OUTPUT as CLOSURE_OUTPUT, _policy
from .stage_b_v1 import _overlay
from .stage_b_v2 import _baseline_state
from .stage_b_v3 import DB as V3_DB, _guards
from .stage_b_worker import StageBWorker
from .staged_assessment import _bridge, _eligible, _select
from .staged_registry import StagedRegistry

REGISTRY = CLOSURE_DB.with_name("cosing_full_stage_b_enrichment_v1.sqlite")
PROGRESS = OUTPUT/"progress.json"
JOURNALS = OUTPUT/"batches"
STOP = OUTPUT/"stop.json"
BATCH_SIZE = 200
STATUSES = {"NOT_EVALUATED":30230,"UNRESOLVED":130}
HARD = {"BINDING","REVISION","EVIDENCE","VERSION","REGISTRY","TRANSACTION"}
SEMANTIC = {"QUALIFICATION","WHOLE_REFERENT","MATERIAL_SCOPE","CONFLICT_ISOLATION",
            "MALFORMED_INTERPRETATION_PACKET"}
SYSTEM_WORKER_ERRORS = {"WORKER_STARTUP_FAILURE","WORKER_EXIT","WORKER_EXCEPTION","INVALID_WORKER_RESPONSE"}


def utc():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def coordinator():
    """One journal writer. The OS releases this lock if the coordinator exits."""
    import msvcrt

    with (OUTPUT/"coordinator.lock").open("a+b") as handle:
        handle.seek(0)
        msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)


class Workers:
    """Reuse the existing worker independently in each lane and write through one gate."""

    def __init__(self, stack, count):
        self.local = local()
        self.lock = Lock()
        self.stacks = stack.enter_context(ExitStack())
        self.executor = stack.enter_context(ThreadPoolExecutor(max_workers=count))
        self.workers = []
        self.reused = {}

    def _run(self, packet):
        if not hasattr(self.local,"worker"):
            lane = ExitStack()
            try:
                self.local.worker = lane.enter_context(StageBWorker(_bridge(lane)))
            except BaseException:
                lane.close()
                raise
            with self.lock:
                self.stacks.callback(lane.close)
                self.workers.append(self.local.worker)
        return self.local.worker.run(packet,DEFAULT_BUDGET)

    def compute(self, packets, ids):
        future = {}
        dispatched = False

        def compute(packet, budget):
            nonlocal dispatched
            if budget!=DEFAULT_BUDGET:
                raise ValueError("Stage B full enrichment uses the validated six-second deadline")
            if not dispatched:
                future.update((cid,self.executor.submit(self._run,packets[cid])) for cid in ids if cid not in self.reused)
                dispatched = True
            cid = packet[0]["concept_id"]
            if cid in self.reused:
                prior = self.reused[cid]
                return {"prediction":prior["prediction"],"reason":None,"reused_validated_computation":True}
            result = future[cid].result()
            if result.get("prediction") is not None:
                self.reused[cid] = result
            return result
        return compute


class SystemicFailure(RuntimeError):
    def __init__(self, code, detail):
        super().__init__(code)
        self.code,self.detail = code,detail


class Monitor:
    """Stop on any integrity error or repeatable semantic defect."""

    def __init__(self):
        self.checked = set()
        self.failures = defaultdict(set)
        self.workers = defaultdict(set)

    def check(self, event, name):
        if event["id"] in self.checked:
            return
        self.checked.add(event["id"])
        issues = event["critical_checks"]
        evidence = {"batch":name,"event":event["id"],"critical_checks":issues,
                    "held_families":event["held_families"],"quarantine":event["quarantine"]}
        if HARD.intersection(issues):
            raise SystemicFailure("MANDATORY_INTEGRITY_GATE",evidence)
        if event["held_families"]:
            raise SystemicFailure("REPEATED_INTERPRETER_SAFETY_FAILURE",evidence)
        for item in event["quarantine"]:
            for issue in SEMANTIC.intersection(item["failures"]):
                for family in item["interpreter_families"] or ["unassigned"]:
                    self.failures[(issue,family)].add(item["id"])
                    if len(self.failures[(issue,family)])>=2:
                        raise SystemicFailure("REPEATED_INTERPRETER_SAFETY_FAILURE",{
                            **evidence,"reason":issue,"interpreter":family,
                            "affected_concepts":sorted(self.failures[(issue,family)])})
        for cid,result in event["execution"].items():
            reason = result.get("reason")
            if reason in SYSTEM_WORKER_ERRORS:
                key = reason,result.get("error"),result.get("detail")
                self.workers[key].add(cid)
                if len(self.workers[key])>=3:
                    raise SystemicFailure("REPEATED_EXECUTION_FAILURE",{
                        **evidence,"reason":key,"affected_concepts":sorted(self.workers[key])})


def _events(journal):
    return {event["id"]:event for event in read(journal)} if journal.exists() else {}


def _batch(name, session, ids, workers, monitor):
    def children(parent, operation):
        matching = [e for e in _events(session.journal).values() if
                    e["operation"]==operation and e["parent_event"]==parent]
        if len(matching)>1:
            raise SystemicFailure("DUPLICATE_BATCH_ACTION",{"batch":name,"operation":operation,"parent":parent})
        return matching[0] if matching else None

    def apply(operation, parent, selected):
        prior = parent["id"] if parent else None
        current = children(prior,operation)
        if current is not None:
            if current["ids"]!=list(selected) or current["version"]!=session.version or current["manifest"]!=session.manifest:
                raise SystemicFailure("CHECKPOINT_LINEAGE_MISMATCH",{"batch":name,"event":current["id"]})
            return current
        compute = workers.compute(session.packets,selected)
        if operation=="BATCH":
            return session.submit(selected,compute,DEFAULT_BUDGET)[0]
        if operation=="RETRY":
            return session.retry(prior,compute,DEFAULT_BUDGET,ids=selected)[0]
        return getattr(session,operation.lower())(prior,compute,DEFAULT_BUDGET)[0]

    def finish(event, may_retry):
        while event["decision"] in {"STARTED","VALIDATED_PENDING_COMMIT"}:
            event = apply("RESUME",event,event["ids"])
        monitor.check(event,name)
        if event["eligible_for_rebatch"]:
            finish(apply("REBATCH",event,event["eligible_for_rebatch"]),may_retry)
        if event["retry_ids"] and may_retry:
            finish(apply("RETRY",event,event["retry_ids"]),False)

    workers.reused.clear()
    finish(apply("BATCH",None,ids),True)
    return _summarize_batch(session.journal,ids)


def _summarize_batch(journal, ids):
    completed,held,quarantined = set(),set(),set()
    decisions = Counter()
    for e in _events(journal).values():
        if e["decision"] not in {"ACCEPT","HOLD","REJECT"}:
            continue
        decisions[e["decision"]]+=1
        if e["decision"]=="ACCEPT":
            completed.update(e["ids"])
        else:
            held.update(e["retry_ids"])
            quarantined.update(q["id"] for q in e["quarantine"])
    held -= completed
    quarantined -= completed|held
    if set(ids)!=completed|held|quarantined:
        raise SystemicFailure("INCOMPLETE_BATCH_ACCOUNTING",{"journal":str(journal)})
    return {"completed":len(completed),"held":sorted(held),"quarantined":sorted(quarantined),
            "decisions":dict(decisions),"journal_sha256":digest(journal)}


def _protected():
    paths = {**_guards(),str(V3_DB):digest(V3_DB),str(CLOSURE_DB):digest(CLOSURE_DB)}
    for suffix in ("-journal","-wal","-shm"):
        path = Path(str(CLOSURE_DB)+suffix)
        paths[str(path)] = digest(path) if path.exists() else None
    return paths


def _integrity(registry,version,historical, expected=None):
    if _baseline_state(registry,version)!=historical:
        raise SystemicFailure("CORE_OR_HISTORY_CHANGED",{})
    with registry.reader() as db:
        quick = db.execute("PRAGMA integrity_check").fetchone()[0]
        fk = db.execute("PRAGMA foreign_key_check").fetchone()
        statuses = dict(db.execute("SELECT canonical_status,count(*) FROM domain_concept GROUP BY canonical_status"))
        targets = db.execute("SELECT count(*) FROM domain_concept WHERE canonical_target_json IS NOT NULL").fetchone()[0]
        assessed,attempted = db.execute("SELECT count(*),coalesce(sum(attempted),0) FROM assessment WHERE pipeline_version=?",
                                       (version,)).fetchone()
    if quick!="ok" or fk or targets or attempted or statuses!=STATUSES or (expected is not None and assessed!=expected):
        raise SystemicFailure("REGISTRY_INTEGRITY_CHECK_FAILED",{
            "sqlite":quick,"foreign_key_failure":bool(fk),"targets":targets,"attempted":attempted,
            "statuses":statuses,"expected":expected,"assessed":assessed})
    return {"concepts":sum(statuses.values()),"canonical_statuses":statuses,"canonical_targets":targets,
            "history_rows":len(historical[1]),"new_assessments":assessed,"foreign_key_violations":0,
            "sqlite_integrity":quick,"core_table_sha256":historical[0]}


def _inputs():
    manifest = read(MANIFEST)
    files = {CAPTURE/name:sha for name,sha in manifest["profile_files"].items()}
    files.update({OUTPUT/name:sha for name,sha in manifest["sql_files"].items()})
    files[PARENT_ARCHIVE] = manifest["parent_sha256"]
    files.update({CAPTURE/b["file"]:b["file_sha256"] for b in manifest["buckets"].values()})
    if any(digest(path)!=sha for path,sha in files.items()):
        raise SystemicFailure("FROZEN_SOURCE_DIGEST_MISMATCH",{})
    parents = {r["inci_id"]:r for r in read(PARENT_ARCHIVE)}
    if len(parents)!=30360:
        raise SystemicFailure("WRONG_PARENT_COVERAGE",{"parents":len(parents)})
    return manifest,parents


def _prepare():
    manifest,parents = _inputs()
    protected = _protected()
    closure = read(CLOSURE_OUTPUT/"confirmation_results.json")["audit"]
    if any(protected.get(k)!=v for k,v in closure["protected_after"].items()) or _policy()[2]!=closure["version"]:
        raise SystemicFailure("CLOSURE_POLICY_OR_PROTECTED_SOURCE_CHANGED",{})
    source = StagedRegistry(CLOSURE_DB)
    manifest_hash = digest(MANIFEST)
    version = "cosing-full-stage-b-v1:"+fingerprint([closure["version"],manifest_hash])
    historical = _baseline_state(source,version)
    if historical[0]!=closure["registry"]["core_hashes"] or len(historical[1])!=2903:
        raise SystemicFailure("CLOSURE_REGISTRY_LINEAGE_MISMATCH",{})
    prior_version = closure["version"]
    if _baseline_state(source,prior_version)!=_baseline_state(StagedRegistry(V3_DB),prior_version):
        raise SystemicFailure("CLOSURE_HISTORY_DIFFERS_FROM_V3",{})
    prior_predictions = {p["concept_id"]:p for p in read(CLOSURE_OUTPUT/"semantic_outputs.json")["approved"]}
    rows = [dict(r) for r in _select(source,(),(),None)]
    by_id = {r["concept_id"]:r for r in rows}
    if (len(by_id)!=len(parents) or len({r["source_reference"] for r in rows})!=len(parents)
            or any(not _eligible(r,False) for r in rows)):
        raise SystemicFailure("UNBOUND_OR_CHANGED_SOURCE_HEAD",{})
    with source.reader() as db:
        saved = list(db.execute("SELECT * FROM assessment WHERE pipeline_version=?",(prior_version,)))
        if len(saved)!=42 or len(prior_predictions)!=42 or any(r["concept_id"] not in prior_predictions or
                r["attempted"] or any(r[k+"_json"]!=canonical(prior_predictions[r["concept_id"]][k])
                for k in ("attributes","roles","summary","trace")) for r in saved):
            raise SystemicFailure("CLOSURE_ASSESSMENTS_DIFFER_FROM_AUDIT",{})
        existing = {r[0] for r in db.execute("""SELECT DISTINCT a.concept_id FROM assessment a
                   JOIN source_head h ON h.concept_id=a.concept_id AND h.observed_revision=a.revision
                   WHERE a.attempted=0 AND json_extract(a.summary_json,'$.stage')='INTERPRETATION'""")}
    groups = defaultdict(list)
    for r in rows:
        key = r["source_reference"].rsplit(":",1)[1]
        if key not in parents:
            raise SystemicFailure("UNBOUND_REGISTERED_SOURCE_KEY",{"id":r["concept_id"],"source_key":key})
        if r["concept_id"] not in existing:
            groups[source_bucket(key)].append(r["concept_id"])
    plan = {}
    for n,ids in sorted(groups.items()):
        blocks = (len(ids)+BATCH_SIZE-1)//BATCH_SIZE
        for i in range(blocks):
            start,end = i*len(ids)//blocks,(i+1)*len(ids)//blocks
            plan[f"{n:02}-{i+1:02}"] = ids[start:end]
    frozen = {"version":version,"manifest":manifest_hash,"protected_before":protected,
              "existing_assessed":len(existing),"target_records":len(rows)-len(existing),"plan_sha256":fingerprint(plan)}
    return frozen,manifest,parents,by_id,plan,historical


def _working_copy(protected):
    registry = StagedRegistry(REGISTRY)
    if not REGISTRY.exists():
        temporary = REGISTRY.with_suffix(".copying")
        if temporary.exists():
            temporary.unlink()  # A previous backup never reached publication.
        with StagedRegistry(CLOSURE_DB).reader() as src,closing(sqlite3.connect(temporary)) as dest:
            src.backup(dest)
        temporary.replace(REGISTRY)
    if REGISTRY.is_symlink() or any(Path(p).is_file() and REGISTRY.samefile(p) for p in protected):
        raise SystemicFailure("UNSAFE_WORKING_DATABASE_PATH",{})
    return registry


def run(count):
    if STOP.exists():
        raise SystemicFailure("SYSTEMIC_STOP_REQUIRES_REVIEW",read(STOP))
    started = perf_counter()
    frozen,manifest,parents,rows,plan,historical = _prepare()
    if PROGRESS.exists():
        progress = read(PROGRESS)
        if progress["frozen"]!=frozen:
            raise SystemicFailure("RESUME_LINEAGE_MISMATCH",{})
    else:
        progress = {"started_at":utc(),"frozen":frozen,"batches":{},"sessions":[]}
        write(PROGRESS,progress)
    registry = _working_copy(frozen["protected_before"])
    version = frozen["version"]
    _integrity(registry,version,historical)
    JOURNALS.mkdir(exist_ok=True)
    monitor = Monitor()
    completed = 0
    for name,batch in progress["batches"].items():
        path = JOURNALS/f"{name}.json"
        if name not in plan or digest(path)!=batch["journal_sha256"]:
            raise SystemicFailure("COMPLETED_BATCH_JOURNAL_CHANGED",{"batch":name})
        completed += batch["completed"]
        for event in _events(path).values():
            if event["decision"] in {"ACCEPT","HOLD","REJECT"}:
                monitor.check(event,name)
    previous_bucket = None
    protected = frozen["protected_before"]
    launch = {"at":utc(),"lanes":count,"initial_completed":completed}
    workers = None
    try:
        with ExitStack() as stack:
            workers = Workers(stack,count)
            for name,ids in plan.items():
                if name in progress["batches"]:
                    continue
                bucket = int(name.split("-")[0])
                if previous_bucket!=bucket:
                    aliases,held,source_path = load_bucket(manifest,bucket,parents)
                    previous_bucket = bucket
                source_sha = manifest["buckets"][str(bucket)]["file_sha256"]
                selected = [parents[rows[cid]["source_reference"].rsplit(":",1)[1]] for cid in ids]
                for p in selected:
                    aliases.setdefault(p["inci_id"],[])
                    held.setdefault(p["inci_id"],[])
                overlay = _overlay(selected,aliases,held,frozen["manifest"])
                packets = {}
                for cid in ids:
                    row = rows[cid]
                    parent,evidence,provenance = overlay(row,json.loads(row["payload_json"]))
                    item = {"cohort":"full_stage_b_v1","stratum":"registered_remaining"}
                    packets[cid] = row,item,parent,evidence,provenance,version
                verify = lambda: digest(MANIFEST)==frozen["manifest"] and digest(source_path)==source_sha
                session = MonitoredBatch(registry,JOURNALS/f"{name}.json",packets,version,frozen["manifest"],verify)
                batch = _batch(name,session,ids,workers,monitor)
                completed += batch["completed"]
                progress["batches"][name] = batch
                write(PROGRESS,progress)
                print(f"{utc()} batch={name} records={len(ids)} committed={batch['completed']} "
                      f"hold={len(batch['held'])} quarantine={len(batch['quarantined'])} "
                      f"total={completed}/{frozen['target_records']}",flush=True)
                if len(progress["batches"])%16==0:
                    _integrity(registry,version,historical,completed)
                    if _protected()!=protected:
                        raise SystemicFailure("PROTECTED_PATH_CHANGED",{"batch":name})
            progress["integrity"] = _integrity(registry,version,historical,completed)
            after = _protected()
            if after!=protected:
                raise SystemicFailure("PROTECTED_PATH_CHANGED",{})
            progress.update(finished_at=utc(),protected_after=after)
    finally:
        launch.update(elapsed_seconds=perf_counter()-started,final_completed=completed)
        if workers:
            launch["worker_lifecycle"] = [entry for worker in workers.workers for entry in worker.lifecycle]
        progress["sessions"].append(launch)
        write(PROGRESS,progress)
    return progress


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers",type=int,default=6,choices=range(1,9))
    options = parser.parse_args()
    with coordinator():
        try:
            p = run(options.workers)
        except SystemicFailure as exc:
            if not STOP.exists():
                write(STOP,{"at":utc(),"code":exc.code,"detail":exc.detail})
            raise SystemExit(f"Stage B stopped: {exc.code}") from exc
        except (OSError,ValueError,sqlite3.Error,RuntimeError) as exc:
            if not STOP.exists():
                write(STOP,{"at":utc(),"code":"EXECUTION_OR_SOURCE_VERIFICATION_FAILURE",
                            "detail":{"error":type(exc).__name__,"message":str(exc)}})
            raise SystemExit(f"Stage B stopped: {type(exc).__name__}: {exc}") from exc
        print(f"Finished Stage B with {p['integrity']['new_assessments']:,} new assessments.",flush=True)


if __name__=="__main__":
    main()
