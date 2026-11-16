"""Evaluate and persist only Stage B for the verified CosIng evidence cohort."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing, nullcontext
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from time import perf_counter

from .benchmark_readiness import peak_rss
from .cosing_source import PARENT, observation
from .full_capture import digest, read, write
from .full_registration import protected_paths
from .readiness import register
from .registry import canonical, fingerprint
from .stage_b_cohort import OUTPUT
from .stage_b_evidence import verified
from .staged_registry import StagedRegistry

REGISTRY = OUTPUT.parents[1]/"local/cosing_full_registration_v1.sqlite"
CORE = ("domain_type","domain_concept","source_revision","source_payload","source_head","source_review",
        "registration_run","registration_member","review_comparison")
REFERENCE = OUTPUT/"reference.json"
SPECIALISTS = OUTPUT.parents[2]/"nomenclature_interpretation/specialists.py"
MANUAL = OUTPUT/"review_controls.json"


def _checksum(db, tables):
    hashes = {}
    for table in tables:
        stream = sha256()
        for row in db.execute(f"SELECT * FROM {table} ORDER BY rowid"):
            stream.update(canonical(tuple(row)).encode()+b"\n")
        hashes[table] = stream.hexdigest()
    return hashes


def _sources():
    return read(OUTPUT/"cohort.json")["records"]


def freeze_reference():
    from rdkit import rdBase
    from canonical_registry.nomenclature_interpretation.reliability_reference import annotate

    _, aliases, _, _ = verified()
    controls = read(MANUAL)
    references = []
    with rdBase.BlockLogs():
        for item in _sources():
            parent = item["parent"]
            row = {**parent,"stratum":item["stratum"].upper(),"alias_claims":aliases[parent["inci_id"]]}
            label = annotate(row)
            if not label["assertions"].get("molecular_chemical"):
                label["routes"]["molecular_chemical"] = None
            for role in label["roles"]:
                if role["reported_function"].strip().upper()=="PERFUMING":
                    role.update(qualification="VOCABULARY_VALIDATED",qualified_vocabulary_labels=["PERFUMING"])
            manual = controls.get(parent["inci"],{})
            for module in manual.get("routes",[]):
                label["routes"][module] = True
            for module,predicate,value in manual.get("attributes",[]):
                facts = label["assertions"].setdefault(module,[])
                fact = [predicate,value,"SOURCE_REVIEW_CONTROL"]
                if not any(p==predicate and str(v).casefold()==str(value).casefold() for p,v,_ in facts):
                    facts.append(fact)
            if any(value is True for value in label["routes"].values()):
                label["fallback"] = False
            if "fallback" in manual:
                label["fallback"] = manual["fallback"]
            references.append({"cohort":item["cohort"],"stratum":item["stratum"],"reference":label,"manual":manual,
                               "missing_parent_identifiers":not any(parent.get(k) for k in ("cas_nos","ec_nos"))})
    if REFERENCE.exists():
        raise FileExistsError("The provisional reference has already been frozen")
    write(REFERENCE,{"status":"PROVISIONAL_SOURCE_ANNOTATION_NO_INDEPENDENT_REVIEWER",
                     "companion_manifest_sha256":digest(OUTPUT/"companion_manifest.json"),
                     "manual_controls_sha256":digest(MANUAL),"records":references})


def _overlay(parents, evidence, held, manifest_digest):
    original = {r["inci_id"]:r for r in parents}
    expected = {r["inci_id"]:observation(r).payload["source"] for r in parents}

    def apply(row,packet):
        key = row["source_reference"].removeprefix(PARENT+":")
        if key not in expected or packet["source"]!=expected[key]:
            raise ValueError(f"Captured evidence does not match current registered parent {key}")
        aliases = evidence[key]
        return original[key],aliases,{"manifest_sha256":manifest_digest,"parent_revision":row["observed_revision"],
                                      "used_original_alias_ids":[r["inci_alias_id"] for r in aliases],
                                      "held_aliases":held[key],"source_chemistry_use":"ARCHIVE_ONLY"}
    return apply


def _assess(registry, mode, output):
    from .staged_assessment import _interpret, _select, interpretation_version

    clock = perf_counter()
    manifest,evidence,held,alias_counts = verified()
    manifest_digest = digest(OUTPUT/"companion_manifest.json")
    reference = read(REFERENCE)
    if reference["companion_manifest_sha256"] != manifest_digest or reference["manual_controls_sha256"]!=digest(MANUAL):
        raise ValueError("Frozen reference and evidence bundle do not match")
    source = _sources()
    by_key = {r["parent"]["inci_id"]:r for r in source}
    selected = _select(registry,(),list(by_key),None)
    if len(selected)!=len(source) or any(r["continuity_hold"] or not r["present"] or
       r["registered_revision"]!=r["observed_revision"] for r in selected):
        raise ValueError("Cohort includes missing or held registered concepts")
    overlay = _overlay([r["parent"] for r in source],evidence,held,manifest_digest)
    for row in selected:
        overlay(row,json.loads(row["payload_json"]))
    preparation = perf_counter()-clock
    version = "cosing-stage-b-v1:"+fingerprint([interpretation_version(False),manifest_digest,digest(Path(__file__))])
    rules_digest = digest(SPECIALISTS)
    print(f"Starting {mode} Stage B on {len(selected)} concepts",flush=True)
    with registry.reader() as db:
        before_core = _checksum(db,CORE)
        previous = [tuple(r) for r in db.execute("SELECT * FROM assessment WHERE pipeline_version<>? ORDER BY rowid",(version,))]
        start_bytes = registry.path.stat().st_size
    timing = Counter()
    interrupted = None
    if mode=="baseline":
        def interrupt(counts):
            if counts["assessed"]==7:
                raise KeyboardInterrupt

        clock = perf_counter()
        try:
            _interpret(registry,selected,version,typed_only=False,pending=False,capability=None,
                       overlay=overlay,after_commit=interrupt)
        except KeyboardInterrupt:
            with registry.reader() as db:
                count = db.execute("SELECT count(*) FROM assessment WHERE pipeline_version=?",(version,)).fetchone()[0]
                if count!=7:
                    raise ValueError("Interrupted Stage B checkpoint did not retain exactly seven committed assessments")
            interrupted = {"committed_before_interruption":count,"seconds":perf_counter()-clock}
    clock = perf_counter()
    results = _interpret(registry,selected,version,typed_only=False,pending=False,capability=None,
                         overlay=overlay,timings=timing)
    elapsed = perf_counter()-clock
    clock = perf_counter()
    replay = _interpret(registry,selected,version,typed_only=False,pending=False,capability=None,overlay=overlay)
    replay_seconds = perf_counter()-clock
    with registry.reader() as db:
        rows = db.execute("""SELECT a.*,d.source_reference,d.preferred_label FROM assessment a
            JOIN domain_concept d USING(concept_id) WHERE pipeline_version=? ORDER BY a.concept_id""",(version,)).fetchall()
        after_core = _checksum(db,CORE)
        preserved = [tuple(r) for r in db.execute("SELECT * FROM assessment WHERE pipeline_version<>? ORDER BY rowid",(version,))]
        statuses = dict(db.execute("SELECT canonical_status,count(*) FROM domain_concept GROUP BY canonical_status"))
        if (before_core!=after_core or previous!=preserved or db.execute("PRAGMA integrity_check").fetchone()[0]!="ok"
                or db.execute("PRAGMA foreign_key_check").fetchone()):
            raise ValueError("Stage B modified protected registry rows or failed integrity")
        if len(rows)!=len(selected) or replay.get("cached",0)!=len(selected):
            raise ValueError(f"Stage B cohort incomplete or replay missed cache: {results}, {replay}")
        predictions = []
        for row in rows:
            key = row["source_reference"].removeprefix(PARENT+":")
            predictions.append({"inci_id":key,"concept_id":row["concept_id"],"name":row["preferred_label"],
                "revision":row["revision"],"cohort":by_key[key]["cohort"],"stratum":by_key[key]["stratum"],
                **{k:json.loads(row[k+"_json"]) for k in ("attributes","roles","summary","trace")}})
    statistics = {"mode":mode,"pipeline_version":version,"rule_sha256":rules_digest,
          "source_preparation_seconds":preparation,"elapsed_seconds":elapsed,"replay_seconds":replay_seconds,
          "interpreter_and_provider_timings":dict(timing),"results":results,"replay":replay,"interruption":interrupted,
          "cohort_size":len(predictions),"alias_gate":alias_counts,"canonical_statuses":statuses,"existing_assessments":len(previous),
          "new_assessment_bytes":registry.path.stat().st_size-start_bytes,"peak_working_set_bytes":peak_rss(),
          "core_before":before_core,"core_after":after_core,"reference_sha256":digest(REFERENCE)}
    if interrupted is not None:
        statistics["revised_source_fixture"] = _revision_probe(registry,selected[-1],version)
    write(output,{"statistics":statistics,"predictions":predictions})


def _revision_probe(registry,row,version):
    from .staged_assessment import _interpret, _select

    source = json.loads(row["payload_json"])["source"]
    revised = {**source,"description":"Synthetic fixture revision for Stage B recovery only."}
    changed = observation(revised)
    register(registry,[changed],"stage-b-synthetic-revision")
    selected = _select(registry,[row["concept_id"]],(),None)
    options = dict(typed_only=False,pending=False,capability=None)
    held = _interpret(registry,selected,version,**options)
    if held!={"source_held_or_payload_unavailable":1}:
        raise ValueError("Changed fixture source did not enter review")
    registry.review_source(row["concept_id"],changed.content_key,action="adopt",actor="fixture",
                           note="Synthetic controlled revision")
    selected = _select(registry,[row["concept_id"]],(),None)
    clock = perf_counter()
    result = _interpret(registry,selected,version+":revision-control",**options)
    elapsed = perf_counter()-clock
    if result!={"assessed":1}:
        raise ValueError("Reviewed revised input did not receive a fresh assessment")
    return {"held_before_review":held,"result_after_review":result,"single_record_cold_seconds":elapsed,
            "prior_assessment_retained":True,"companion_evidence":"none in synthetic revision"}


def run(mode,output):
    before = protected_paths()
    registry = StagedRegistry(REGISTRY)
    context = TemporaryDirectory(dir=OUTPUT.parents[1]) if mode=="baseline" else nullcontext(None)
    with context as temp:
        if temp is not None:
            copied = StagedRegistry(Path(temp)/"baseline.sqlite")
            with registry.reader() as source, closing(sqlite3.connect(copied.path)) as destination:
                source.backup(destination)
            registry = copied
        _assess(registry,mode,output)
    after = protected_paths()
    if before!=after:
        raise ValueError("Stage B changed a protected path")
    if mode=="corrected":
        write(OUTPUT/"protected_integrity.json",{"before":before,"after":after,"changes":[]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("reference","baseline","corrected"))
    args = parser.parse_args()
    if args.mode=="reference":
        freeze_reference()
    else:
        run(args.mode,OUTPUT/f"{args.mode}_predictions.json")


if __name__=="__main__":
    main()
