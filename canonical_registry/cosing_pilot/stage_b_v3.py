"""Run, gate and persist bounded Stage B batches without invoking Stage C."""

from time import perf_counter
MODULE_STARTED = perf_counter()

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack, closing
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from .benchmark_readiness import peak_rss
from .full_capture import digest, read, write
from .full_registration import protected_paths
from .registry import canonical, fingerprint
from .stage_b_v1 import _overlay
from .stage_b_v2 import _audit, _baseline_state
from .stage_b_v3_cohort import OUTPUT, V2_DB
from .stage_b_v2_evidence import assemble, verified
from .staged_registry import StagedRegistry

DB = V2_DB.with_name("cosing_stage_b_quality_gate_v3.sqlite")
POLICY = OUTPUT/"gate_policy.json"
REFERENCE = OUTPUT/"reference.json"
COHORT = OUTPUT/"cohort.json"
MANIFEST = OUTPUT/"companion_manifest.json"


def _copy(path):
    if path.exists():
        raise FileExistsError(path)
    if digest(V2_DB)!=read(COHORT)["source_database_sha256"]:
        raise ValueError("The Stage B v2 lineage database changed")
    dest = StagedRegistry(path)
    with StagedRegistry(V2_DB).reader() as source,closing(sqlite3.connect(dest.path)) as target:
        source.backup(target)
    return dest


def _guards():
    return {**protected_paths(),str(V2_DB):digest(V2_DB)}


def _input(registry,timing):
    from .staged_assessment import _eligible, _select

    start = perf_counter()
    _,evidence,held,counts = verified(OUTPUT)
    if read(REFERENCE)["manifest_sha256"]!=digest(MANIFEST) or read(REFERENCE)["policy_sha256"]!=digest(POLICY):
        raise ValueError("Frozen reference no longer matches the source and gate policy")
    records = {x["parent"]["inci_id"]:x for x in read(COHORT)["records"]}
    overlay = _overlay([x["parent"] for x in records.values()],evidence,held,digest(MANIFEST))
    timing["source_evidence_preparation"] += perf_counter()-start
    start = perf_counter()
    rows = _select(registry,(),list(records),None)
    timing["sqlite_selection_reads"] += perf_counter()-start
    if len(rows)!=len(records) or any(not _eligible(row,False) for row in rows):
        raise ValueError("Selected registry source revisions are missing or held")
    start = perf_counter()
    for row in rows:
        overlay(row,json.loads(row["payload_json"]))
    timing["source_binding_preflight"] += perf_counter()-start
    return records,evidence,overlay,rows,counts


def _version():
    from .staged_assessment import interpretation_version

    return "cosing-stage-b-v3:"+fingerprint([
        interpretation_version(False),digest(REFERENCE),digest(POLICY),digest(MANIFEST),
        digest(Path(__file__)),digest(Path(__file__).with_name("stage_b_v3_gate.py"))])


def _batch_rows(rows,records):
    groups = defaultdict(list)
    for row in rows:
        item = records[row["source_reference"].split(":",1)[1]]
        group = item["cohort"] if item["cohort"] in {"representative","high_risk"} else "controls"
        groups[group].append(row)
    size = read(POLICY)["batch_size"]
    for group in ("controls","representative","high_risk"):
        block = size if group=="representative" else 200
        for index in range(0,len(groups[group]),block):
            yield f"{group}-{index//block+1:02}",groups[group][index:index+block]


def _build(framework,bridge,row,record,overlay,version,timing):
    from canonical_registry.nomenclature_interpretation.cosing_preview_adapter import adapt_cosing_preview
    from .organization import assertion_audit, supported_attributes
    from .staged_assessment import _hold_incomplete_structure

    start = perf_counter()
    parent,aliases,provenance = overlay(row,json.loads(row["payload_json"]))
    item = adapt_cosing_preview(parent,aliases,include_registry_claims=True)
    timing["record_evidence_preparation"] += perf_counter()-start
    failures = bridge.failures
    start = perf_counter()
    result = _hold_incomplete_structure(framework.interpret(item),provenance)
    timing["interpreter_and_reconciliation_wall"] += perf_counter()-start
    if bridge.failures!=failures:
        return None
    start = perf_counter()
    attributes = list(supported_attributes(result))
    audit = assertion_audit(result)
    roles = [asdict(r) for r in result.functions if r.qualification.startswith("VOCABULARY_")
             and r.qualified_vocabulary_labels]
    timing["assertion_qualification_audit"] += perf_counter()-start
    start = perf_counter()
    modules = [m.module for m in result.modules]
    prediction = {"inci_id":parent["inci_id"],"concept_id":row["concept_id"],"name":parent["inci"],
        "cohort":record["cohort"],"stratum":record["stratum"],"revision":row["observed_revision"],"version":version,
        "attributes":attributes,"roles":roles,"summary":{"stage":"INTERPRETATION","state":result.state,"modules":modules,
            "aliases_observed":True,"chemical_candidate":("molecular_chemical" in modules or any(
                a.category=="STRUCTURAL" for a in (*result.assertions,*result.withheld_assertions)))},
        "trace":{"interpretation":asdict(result),"companion_evidence":provenance,"assertion_audit":audit}}
    timing["assessment_object_creation"] += perf_counter()-start
    return prediction


def _cached(registry,rows,version,timing):
    start = perf_counter()
    ids = [r["concept_id"] for r in rows]
    with registry.reader() as db:
        cached = {r["concept_id"]:r["revision"] for r in db.execute(
            f"SELECT concept_id,revision FROM assessment WHERE pipeline_version=? AND concept_id IN ({','.join('?' for _ in ids)})",
            (version,*ids))}
    timing["cache_sqlite_reads"] += perf_counter()-start
    return {r["concept_id"] for r in rows if cached.get(r["concept_id"])==r["observed_revision"]}


def _write_batch(registry,rows,predictions,version,timing,interrupt=None):
    from .staged_assessment import _current

    start = perf_counter()
    values = [(r["concept_id"],r["observed_revision"],version,0,
               *(canonical(predictions[r["concept_id"]][k]) for k in ("attributes","roles","summary","trace"))) for r in rows]
    timing["assessment_serialization"] += perf_counter()-start
    start = perf_counter()
    with registry.writer() as db:
        if not all(_current(db,r,False) for r in rows):
            raise ValueError("Source revision changed inside the write transaction")
        before = db.total_changes
        db.executemany("INSERT INTO assessment VALUES(?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",values)
        inserted = db.total_changes-before
        for value in values:
            old = db.execute("SELECT * FROM assessment WHERE concept_id=? AND revision=? AND pipeline_version=?",value[:3]).fetchone()
            if tuple(old)!=value:
                raise ValueError("Existing cache entry differs from validated assessment")
        if interrupt is not None:
            interrupt()
    timing["sqlite_write_and_revision_checks"] += perf_counter()-start
    return inserted


def _evaluate(rows,predictions,records,evidence,version,manifest_hash,reference):
    from .stage_b_v3_gate import check, decision

    checks, states, families, coverage = [],Counter(),Counter(),Counter()
    for row in rows:
        cid = row["concept_id"]
        if cid not in predictions:
            checks.append({"id":cid,"failures":[],"review":["RETRYABLE_PROVIDER_FAILURE"],"retry":True})
            continue
        prediction = predictions[cid]
        key = prediction["inci_id"]
        faults,review = check(row,records[key]["parent"],evidence[key],prediction,manifest_hash,version)
        ref = reference[key]
        missing = sorted(m for m in ref.get("required_routes",[]) if m not in prediction["summary"]["modules"])
        if missing:
            review.append("REFERENCE_SPECIALIST_MISSING")
        states[prediction["summary"]["state"]]+=1
        families.update(prediction["summary"]["modules"])
        coverage.update({"records":1,"qualified_descriptors":len(prediction["attributes"]),
            "qualified_roles":len(prediction["roles"]),
            "withheld_assertions":len(prediction["trace"]["interpretation"]["withheld_assertions"]),
            "fallback":int("generic_ingredient" in prediction["summary"]["modules"])})
        checks.append({"id":cid,"source_key":key,"failures":faults,"review":review,"missing_routes":missing,
                       "interpreter_families":prediction["summary"]["modules"]})
    result = decision(checks)
    return {**result,"records":len(rows),"coverage":dict(coverage),"states":dict(states),"families":dict(families)}


def dry_run(phase):
    start = perf_counter()
    from rdkit import rdBase
    from canonical_registry.nomenclature_interpretation import InterpretationFramework
    from canonical_registry.nomenclature_interpretation.cosing_preview_adapter import COSMETICS_FUNCTIONS
    from .staged_assessment import _bridge, _interpret

    timings = Counter({"module_import_and_startup":perf_counter()-MODULE_STARTED})
    guards = _guards()
    refs = {r["reference"]["id"]:r for r in read(REFERENCE)["records"]}
    manifest_hash = digest(MANIFEST)
    version = _version()
    with TemporaryDirectory(dir=OUTPUT.parents[1]) as temp:
        clock = perf_counter()
        registry = _copy(Path(temp)/"dry.sqlite")
        timings["sqlite_lineage_copy"] += perf_counter()-clock
        records,evidence,overlay,rows,alias_gate = _input(registry,timings)
        old = _baseline_state(registry,version)
        old_bytes = registry.path.stat().st_size
        print(f"Starting {phase}: {len(rows)} registered concepts",flush=True)
        reports,predictions = [],{}
        recovery = {}
        with ExitStack() as stack,rdBase.BlockLogs():
            begin = perf_counter()
            bridge = _bridge(stack)
            framework = InterpretationFramework(name_parser=bridge,
                 function_vocabularies={"cosmetics":COSMETICS_FUNCTIONS},timings=timings)
            timings["engine_and_java_bridge_startup"] += perf_counter()-begin
            clock = perf_counter()
            for batch, selected in _batch_rows(rows,records):
                batch_start = perf_counter()
                for row in selected:
                    item = records[row["source_reference"].split(":",1)[1]]
                    p = _build(framework,bridge,row,item,overlay,version,timings)
                    if p:
                        p["batch"] = batch
                        predictions[row["concept_id"]] = p
                begin = perf_counter()
                report = _evaluate(selected,predictions,records,evidence,version,manifest_hash,refs)
                timings["semantic_gate"] += perf_counter()-begin
                if report["decision"]=="ACCEPT":
                    if phase=="corrected" and not recovery and reports:
                        def interrupt():
                            raise KeyboardInterrupt
                        begin = perf_counter()
                        with registry.reader() as connection:
                            prior_count = connection.execute("SELECT count(*) FROM assessment WHERE pipeline_version=?",(version,)).fetchone()[0]
                        try:
                            _write_batch(registry,selected,predictions,version,Counter(),interrupt)
                        except KeyboardInterrupt:
                            if _cached(registry,selected,version,Counter()):
                                raise ValueError("Interrupted Stage B transaction left partial assessments")
                            with registry.reader() as connection:
                                after_count = connection.execute("SELECT count(*) FROM assessment WHERE pipeline_version=?",(version,)).fetchone()[0]
                            if after_count!=prior_count:
                                raise ValueError("Rollback modified a previously accepted batch")
                            recovery = {"interrupted_batch":batch,"rolled_back":True,"previous_records_preserved":prior_count,
                                        "recovery_seconds":perf_counter()-begin}
                    report["inserted"] = _write_batch(registry,selected,predictions,version,timings)
                else:
                    report["inserted"] = 0
                report.update(batch=batch,elapsed_seconds=perf_counter()-batch_start)
                reports.append(report)
                if phase=="corrected" and report["decision"]!="ACCEPT":
                    write(OUTPUT/"stopped_batch.json",report)
                    raise ValueError(f"Stage B gate stopped at {batch}: {report['decision']}, {report['critical_checks']}")
            cold = perf_counter()-clock
            timings["opsin_transport_seconds"] = bridge.elapsed
            timings["opsin_transport_calls"] = bridge.calls
        begin = perf_counter()
        hits = sum(len(_cached(registry,batch,version,timings)) for _,batch in _batch_rows(rows,records))
        warm = perf_counter()-begin
        begin = perf_counter()
        audit = _audit(registry,version,old,hits)
        timings["batch_integrity_checks"] += perf_counter()-begin
        comparison = None
        if phase=="baseline":
            # Same 60 sources, policy and evidence on the v2 per-record path.
            sample = [r for r in rows if records[r["source_reference"].split(":",1)[1]]["cohort"]=="representative"][:60]
            begin = perf_counter()
            legacy = _interpret(registry,sample,version+":legacy-benchmark",typed_only=False,pending=False,
                                capability=None,overlay=overlay)
            legacy_seconds = perf_counter()-begin
            measured = Counter()
            begin = perf_counter()
            with ExitStack() as stack,rdBase.BlockLogs():
                bridge = _bridge(stack)
                framework = InterpretationFramework(name_parser=bridge,
                    function_vocabularies={"cosmetics":COSMETICS_FUNCTIONS},timings=measured)
                fresh = {}
                for row in sample:
                    fresh[row["concept_id"]] = _build(framework,bridge,row,records[row["source_reference"].split(":",1)[1]],
                                             overlay,version+":batch-benchmark",measured)
                _write_batch(registry,sample,fresh,version+":batch-benchmark",measured)
            batch_seconds = perf_counter()-begin
            with registry.reader() as db:
                for cid,prediction in fresh.items():
                    stored = db.execute("SELECT * FROM assessment WHERE concept_id=? AND pipeline_version=?",
                                        (cid,version+":legacy-benchmark")).fetchone()
                    if any(stored[k+"_json"]!=canonical(prediction[k]) for k in ("attributes","roles","summary","trace")):
                        raise ValueError("Matched-input benchmark changed semantic output")
            comparison = {"records":len(sample),"legacy_seconds":legacy_seconds,"batched_seconds":batch_seconds,
                          "legacy_result":legacy,"batched_timing":dict(measured),"semantic_outputs_identical":True}
        if _guards()!=guards:
            raise ValueError("A protected input path changed during dry run")
        write(OUTPUT/f"{phase}_predictions.json",{"predictions":list(predictions.values()),"batches":reports,
            "statistics":{"version":version,"manifest_sha256":manifest_hash,"reference_sha256":digest(REFERENCE),
              "cold_seconds":cold,"warm_seconds":warm,"cache_hits":hits,"elapsed_seconds":perf_counter()-start,
              "timings":dict(timings),"alias_gate":alias_gate,"storage_growth_bytes":registry.path.stat().st_size-old_bytes,
              "peak_working_set_bytes":peak_rss(),"recovery":recovery,"comparison":comparison,"integrity":audit}})


def publish():
    start = perf_counter()
    version = _version()
    result = read(OUTPUT/"corrected_predictions.json")
    validation = read(OUTPUT/"validation.json")
    if (result["statistics"]["version"]!=version or validation["predictions_sha256"]!=digest(OUTPUT/"corrected_predictions.json")
            or validation["critical_errors"]):
        raise ValueError("Corrected dry-run results or identity safety validation failed")
    guards = _guards()
    registry = StagedRegistry(DB) if DB.exists() else _copy(DB)
    timings = Counter()
    records,evidence,_,rows,_ = _input(registry,timings)
    baseline = _baseline_state(StagedRegistry(V2_DB),version)
    if _baseline_state(registry,version)!=baseline:
        raise ValueError("Designated registry differs from the v2 lineage")
    predictions = {r["concept_id"]:r for r in result["predictions"]}
    refs = {r["reference"]["id"]:r for r in read(REFERENCE)["records"]}
    reports = []
    for batch,selected in _batch_rows(rows,records):
        report = _evaluate(selected,predictions,records,evidence,version,digest(MANIFEST),refs)
        if report["decision"]!="ACCEPT":
            write(OUTPUT/"stopped_batch.json",{**report,"batch":batch})
            raise ValueError("Quality gate refused publication")
        report.update(batch=batch,inserted=_write_batch(registry,selected,predictions,version,timings))
        reports.append(report)
    audit = _audit(registry,version,baseline,len(rows))
    replay = sum(len(_cached(registry,b,version,timings)) for _,b in _batch_rows(rows,records))
    after = _guards()
    if guards!=after or replay!=len(rows):
        raise ValueError("Publication failed cache or protected-path checks")
    write(OUTPUT/"persistence_audit.json",{"version":version,"database":DB.name,"batches":reports,"integrity":audit,
        "cache_hits":replay,"timings":dict(timings),"elapsed_seconds":perf_counter()-start,
        "protected_before":guards,"protected_after":after})


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("archive","baseline","corrected","publish"))
    phase = parser.parse_args().phase
    if phase=="archive":
        assemble(OUTPUT,16)
        manifest = read(MANIFEST)
        prior = OUTPUT.with_name("stage_b_v1")
        chemistry = read(prior/"companion_manifest.json")["archives"]["chem"]
        archive = prior/chemistry["file"]
        if digest(archive)!=chemistry["sha256"]:
            raise ValueError("Historical chemistry archive changed")
        keys = {x["parent"]["inci_id"] for x in read(COHORT)["records"]}
        manifest["chemistry"]={"archive_sha256":chemistry["sha256"],"historical_rows":chemistry["records"],
            "selected_key_annotations":sum(r["inci_id"] in keys for r in read(archive)),
            "role":"archived source reports only; excluded from all interpretation inputs"}
        write(MANIFEST,manifest)
    elif phase=="publish":
        publish()
    else:
        dry_run(phase)
