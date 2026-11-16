"""Freeze, dry-run and commit only the bounded Stage B v2 evaluation."""

import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from time import perf_counter

from .benchmark_readiness import peak_rss
from .full_capture import digest, read, write
from .full_registration import protected_paths
from .registry import fingerprint
from .stage_b_v1 import CORE, REGISTRY, _checksum, _overlay
from .stage_b_v2_cohort import OUTPUT
from .stage_b_v2_evidence import COHORT, MANIFEST, verified
from .staged_registry import StagedRegistry

REFERENCE = OUTPUT/"reference.json"
PROTOCOL = OUTPUT/"review_protocol.json"
DESIGNATED = REGISTRY.with_name("cosing_stage_b_reliability_v2.sqlite")


def freeze_reference():
    from rdkit import rdBase
    from canonical_registry.nomenclature_interpretation.reliability_reference import annotate

    if REFERENCE.exists():
        raise FileExistsError("The v2 reference is frozen")
    _, aliases, _, _ = verified()
    protocol = read(PROTOCOL)
    references = []
    with rdBase.BlockLogs():
        for item in read(COHORT)["records"]:
            parent = item["parent"]
            ref = annotate({**parent,"stratum":item["stratum"].upper(),"alias_claims":aliases[parent["inci_id"]]})
            has_typed_graph = bool(ref["assertions"].get("molecular_chemical"))
            if not has_typed_graph:
                ref["routes"]["molecular_chemical"] = None
            for role in ref["roles"]:
                if role["reported_function"].strip().upper()=="PERFUMING":
                    role.update(qualification="VOCABULARY_VALIDATED",qualified_vocabulary_labels=["PERFUMING"])
            manual = protocol["controls"].get(parent["inci"],{}).copy()
            facts = list(manual.get("facts",[]))
            if parent["inci"].startswith("POLYURETHANE-") and parent["inci"].split("-")[-1].isdigit():
                facts += [["polymer_silicone","reported_polymer_category","polyurethane"],
                          ["polymer_silicone","reported_polymer_designation_number",parent["inci"]]]
                manual["whole_hold"] = True
            if item.get("challenge")=="polymer_control":
                manual["not_polyurethane"] = True
            required = {*manual.get("routes",[]),*(m for m,_,_ in facts)}
            fallback = protocol["fallback"].get(parent["inci"])
            if fallback:
                outcome, routes, reason = fallback
                if outcome=="TYPED_ONLY":
                    outcome = "SPECIALIST" if has_typed_graph else "UNKNOWN"
                    routes = ["molecular_chemical"] if has_typed_graph else []
                if outcome=="FALLBACK" and has_typed_graph:
                    outcome = "UNKNOWN"
                    reason += " A source typed graph also requires adjudication."
                required.update(routes)
                manual["fallback_review"] = {"expected":outcome,"routes":routes,"basis":reason}
                ref["fallback"] = {"FALLBACK":True,"SPECIALIST":False,"UNKNOWN":None}[outcome]
            for module in required:
                ref["routes"][module] = True
            for module,predicate,value in facts:
                values = ref["assertions"].setdefault(module,[])
                if not any(p==predicate and str(v).casefold()==str(value).casefold() for p,v,_ in values):
                    values.append([predicate,value,"SOURCE_REVIEW_CONTROL"])
            for forbidden in manual.get("absent",[]):
                for module,values in ref["assertions"].items():
                    ref["assertions"][module] = [x for x in values if x[0]!=forbidden]
            if "fallback" in manual:
                ref["fallback"] = manual["fallback"]
            elif required:
                ref["fallback"] = False
            manual["routes"],manual["facts"] = sorted(required),facts
            references.append({"cohort":item["cohort"],"stratum":item["stratum"],"challenge":item.get("challenge"),
              "reference":ref,"manual":manual,"missing_parent_identifiers":not any(parent.get(k) for k in ("cas_nos","ec_nos"))})
    write(REFERENCE,{"status":"PROVISIONAL_NO_INDEPENDENT_REVIEWER","manifest_sha256":digest(MANIFEST),
                     "protocol_sha256":digest(PROTOCOL),"records":references})


def _inputs(registry):
    from .staged_assessment import _eligible, _select

    manifest,evidence,held,alias_counts = verified()
    ref = read(REFERENCE)
    if ref["manifest_sha256"]!=digest(MANIFEST) or ref["protocol_sha256"]!=digest(PROTOCOL):
        raise ValueError("Frozen reference and evidence disagree")
    by_key = {r["parent"]["inci_id"]:r for r in read(COHORT)["records"]}
    selected = _select(registry,(),list(by_key),None)
    overlay = _overlay([r["parent"] for r in by_key.values()],evidence,held,digest(MANIFEST))
    if len(selected)!=len(by_key):
        raise ValueError("Some source keys are missing from the current registry")
    for row in selected:
        if not _eligible(row,False):
            raise ValueError("A selected revision is held")
        overlay(row,json.loads(row["payload_json"]))
    return by_key,selected,overlay,alias_counts


def _version():
    from .staged_assessment import interpretation_version

    return "cosing-stage-b-v2:"+fingerprint([
        interpretation_version(False),digest(MANIFEST),digest(REFERENCE),digest(Path(__file__))])


def _baseline_state(registry,version):
    with registry.reader() as db:
        return (_checksum(db,CORE),[tuple(r) for r in db.execute(
            "SELECT * FROM assessment WHERE pipeline_version<>? ORDER BY rowid",(version,))])


def _audit(registry,version,baseline,expected):
    if _baseline_state(registry,version)!=baseline:
        raise ValueError("Protected registry rows or historical assessments changed")
    with registry.reader() as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Stage B database integrity failed")
        count,attempted = db.execute("SELECT count(*),sum(attempted) FROM assessment WHERE pipeline_version=?",(version,)).fetchone()
        if count!=expected or attempted!=0:
            raise ValueError("Stage B version is incomplete or includes chemical resolution attempts")
        return {"canonical_statuses":dict(db.execute("SELECT canonical_status,count(*) FROM domain_concept GROUP BY canonical_status")),
                "concepts":db.execute("SELECT count(*) FROM domain_concept").fetchone()[0],
                "canonical_targets":db.execute("SELECT count(*) FROM domain_concept WHERE canonical_target_json IS NOT NULL").fetchone()[0],
                "historical_assessments":len(baseline[1]),"core_hashes":baseline[0],"version_assessments":count,
                "sqlite_integrity":"ok","foreign_key_violations":0}


def _copy(path):
    copied = StagedRegistry(path)
    if copied.path.exists():
        raise FileExistsError(copied.path)
    with StagedRegistry(REGISTRY).reader() as source,closing(sqlite3.connect(copied.path)) as destination:
        source.backup(destination)
    return copied


def dry_run(mode):
    from .staged_assessment import _interpret

    start = perf_counter()
    protected = {**protected_paths(),str(REGISTRY):digest(REGISTRY)}
    with TemporaryDirectory(dir=OUTPUT.parents[1]) as temp:
        registry = _copy(Path(temp)/"evaluation.sqlite")
        by_key,selected,overlay,alias_counts = _inputs(registry)
        preparation = perf_counter()-start
        version = _version()
        policy_digests = {name:digest(OUTPUT.parents[2]/name) for name in (
            "nomenclature_interpretation/specialists.py","nomenclature_interpretation/framework.py",
            "nomenclature_interpretation/contracts.py","cosing_pilot/organization.py","cosing_pilot/staged_assessment.py")}
        baseline = _baseline_state(registry,version)
        bytes_before = registry.path.stat().st_size
        options = dict(typed_only=False,pending=False,capability=None,overlay=overlay)
        print(f"Starting {mode}: {len(selected)} source-bound records",flush=True)
        timings = Counter()
        interruption = None
        if mode=="baseline":
            def stop(counts):
                if counts["assessed"]==8:
                    raise KeyboardInterrupt
            try:
                _interpret(registry,selected,version,**options,after_commit=stop)
            except KeyboardInterrupt:
                with registry.reader() as db:
                    interruption = db.execute("SELECT count(*) FROM assessment WHERE pipeline_version=?",(version,)).fetchone()[0]
                if interruption!=8:
                    raise ValueError("Unexpected interruption checkpoint")
        start = perf_counter()
        result = _interpret(registry,selected,version,**options,timings=timings)
        elapsed = perf_counter()-start
        start = perf_counter()
        replay = _interpret(registry,selected,version,**options)
        warm = perf_counter()-start
        if replay!={"cached":len(selected)}:
            raise ValueError(f"Stage B dry run did not replay cleanly: {replay}")
        audit = _audit(registry,version,baseline,len(selected))
        predictions = []
        with registry.reader() as db:
            for row in db.execute("""SELECT a.*,d.source_reference,d.preferred_label FROM assessment a
                   JOIN domain_concept d USING(concept_id) WHERE pipeline_version=? ORDER BY a.concept_id""",(version,)):
                key = row["source_reference"].split(":",1)[1]
                item = by_key[key]
                predictions.append({"inci_id":key,"concept_id":row["concept_id"],"name":row["preferred_label"],
                     "revision":row["revision"],"cohort":item["cohort"],"stratum":item["stratum"],
                     **{k:json.loads(row[k+"_json"]) for k in ("attributes","roles","summary","trace")}})
        after = {**protected_paths(),str(REGISTRY):digest(REGISTRY)}
        if protected!=after:
            raise ValueError("Dry run modified a protected registry path")
        write(OUTPUT/f"{mode}_predictions.json",{"predictions":predictions,"statistics":{
            "version":version,"policy_digests":policy_digests,"reference_sha256":digest(REFERENCE),
            "manifest_sha256":digest(MANIFEST),"source_preparation_seconds":preparation,"elapsed_seconds":elapsed,
            "warm_seconds":warm,"results":result,"replay":replay,"interrupted_after":interruption,
            "timings":dict(timings),"storage_growth_bytes":registry.path.stat().st_size-bytes_before,
            "peak_working_set_bytes":peak_rss(),"alias_gate":alias_counts,"integrity":audit}})


def commit():
    from .staged_assessment import _current, _insert, _interpret

    output = read(OUTPUT/"corrected_predictions.json")
    validation = read(OUTPUT/"validation.json")
    version = _version()
    if (output["statistics"]["version"]!=version or validation["corrected_sha256"]!=digest(OUTPUT/"corrected_predictions.json")
            or validation["critical_errors"] or not validation["historical_safety_preserved"]):
        raise ValueError("Corrected dry run failed the policy, evidence or critical-safety gate")
    before = {**protected_paths(),str(REGISTRY):digest(REGISTRY)}
    registry = StagedRegistry(DESIGNATED) if DESIGNATED.exists() else _copy(DESIGNATED)
    _,selected,overlay,_ = _inputs(registry)
    predictions = {row["concept_id"]:row for row in output["predictions"]}
    if len(predictions)!=len(selected) or len(predictions)!=len(output["predictions"]):
        raise ValueError("Corrected output does not cover the selected cohort")
    baseline = _baseline_state(StagedRegistry(REGISTRY),version)
    if _baseline_state(registry,version)!=baseline:
        raise ValueError("The designated copy differs from the source registry")
    start = perf_counter()
    inserted = 0
    with registry.writer() as db:
        for row in selected:
            pred = predictions[row["concept_id"]]
            if not _current(db,row,False) or pred["revision"]!=row["observed_revision"] or pred["summary"]["stage"]!="INTERPRETATION":
                raise ValueError("Dry-run result is stale or outside Stage B")
            inserted += _insert(db,row,version,False,pred["attributes"],pred["roles"],pred["summary"],pred["trace"])
            stored = db.execute("SELECT * FROM assessment WHERE concept_id=? AND revision=? AND pipeline_version=?",
                                (row["concept_id"],row["observed_revision"],version)).fetchone()
            if any(json.loads(stored[k+"_json"])!=pred[k] for k in ("attributes","roles","summary","trace")):
                raise ValueError("An assessment already exists with incompatible contents")
    commit_seconds = perf_counter()-start
    audit = _audit(registry,version,baseline,len(selected))
    start = perf_counter()
    replay = _interpret(registry,selected,version,typed_only=False,pending=False,capability=None,overlay=overlay)
    warm = perf_counter()-start
    after = {**protected_paths(),str(REGISTRY):digest(REGISTRY)}
    if before!=after or replay!={"cached":len(selected)}:
        raise ValueError("Protected inputs changed or persisted replay was incomplete")
    write(OUTPUT/"persistence_audit.json",{"database":DESIGNATED.name,"version":version,"inserted":inserted,
         "commit_seconds":commit_seconds,"warm_seconds":warm,"replay":replay,"integrity":audit,
         "protected_before":before,"protected_after":after,"protected_changes":[]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("reference","baseline","corrected","commit"))
    mode = parser.parse_args().mode
    if mode=="reference":
        freeze_reference()
    elif mode=="commit":
        commit()
    else:
        dry_run(mode)


if __name__=="__main__":
    main()
