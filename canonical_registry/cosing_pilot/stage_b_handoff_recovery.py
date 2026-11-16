"""Recover bounded Stage B holds in a separate, verified registry copy."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, closing
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re
import sqlite3
from time import perf_counter

from .full_capture import digest, read, write
from .full_stage_b_capture import CAPTURE, MANIFEST, OUTPUT as FULL, PARENT_ARCHIVE, load_bucket, source_bucket
from .full_stage_b_enrichment import JOURNALS, REGISTRY as SOURCE, _events, _integrity, _protected
from .registry import fingerprint
from .stage_b_closure import MonitoredBatch
from .stage_b_v1 import _overlay
from .stage_b_v2 import _baseline_state
from .stage_b_worker import StageBWorker
from .staged_assessment import _bridge, _select
from .staged_registry import StagedRegistry

OUTPUT = FULL.with_name("stage_b_handoff_v1")
REGISTRY = SOURCE.with_name("cosing_stage_b_completion_v1.sqlite")
PLAN = {
    "CIC_00000200": (45,"Phthalocyanine candidate pair. A bounded native retry tests slow conjugated graph reconciliation."),
    "CIC_00000320": (45,"Phthalocyanine candidate pair. A bounded native retry tests slow conjugated graph reconciliation."),
    "CIC_00000383": (60,"Larger phthalocyanine candidate pair and multiple reported registry identifiers."),
    "CIC_00007163": (120,"Long direct-dye structure candidates. The verified direct-dye control took about a minute."),
    "CIC_00009365": (45,"Highly symmetric cage candidates. The source definition describes a class."),
    "CIC_00010332": (60,"Aromatic multiring candidates. The source definition refers to a reported formula."),
    "CIC_00015232": (120,"Long direct-dye candidate pair, with no source definition to establish whole scope."),
    "CIC_00023298": (6,"Line breaks in the original designation. Retry only with reversible display-whitespace handling."),
    "CIC_00025549": (90,"Long direct-dye candidate pair, with no source definition to establish whole scope."),
    "CIC_00026923": (60,"Cage derivative with long structure candidates and a reported reaction-product definition."),
}


def processing_label(original):
    """Replace embedded ASCII layout whitespace and record reversible code-point edits."""
    if any(ord(c)<32 and c not in "\r\n\t" or 127<=ord(c)<=159 for c in original):
        raise ValueError("Unsupported designation control character")
    changes = [{"offset":m.start(),"original":m.group(),"replacement":" " }
               for m in re.finditer(r"[\r\n\t]+",original)]
    processed = re.sub(r"[\r\n\t]+"," ",original)
    if not processed.strip() or any(c not in " \r\n\t" and ord(c)<32 for c in processed):
        raise ValueError("Unusable processing designation")
    if re.findall(r"\S+",original)!=re.findall(r"\S+",processed):
        raise ValueError("Designation token sequence changed")
    return processed,changes


def rebind_prediction(prediction, reference, original, processed, changes):
    def restore(node):
        if isinstance(node,dict):
            if (node.get("source_reference"),node.get("field"),node.get("original_value"))==(reference,"preferred_label",processed):
                node["original_value"] = original
            if (node.get("source_reference"),node.get("evidence_field"),node.get("reported_text"))==(reference,"preferred_label",processed):
                node["reported_text"] = original
            for v in node.values():
                restore(v)
        elif isinstance(node,(list,tuple)):
            for v in node:
                restore(v)
    restore(prediction)
    prediction["name"] = original
    prediction["trace"]["processing_designation"] = {
        "method":"ASCII_LAYOUT_WHITESPACE_ONLY","original":original,"processing":processed,
        "edits":changes,"unchanged_nonwhitespace_tokens":True,
    }


def isolated(packet,budget, *, preview=False):
    row,item,parent,aliases,provenance,version = packet
    label,changes = processing_label(parent["inci"])
    if changes:
        parent = {**parent,"inci":label}
    if preview:
        aliases = [a for a in aliases if a["alias_type"] not in {"SMILES","INCHI","INCHI_KEY","MOLECULAR_FORMULA"}]
    with ExitStack() as stack:
        worker = stack.enter_context(StageBWorker(_bridge(stack)))
        if preview:
            worker.bridge.opsin = lambda _:{"status":"FAILURE","diagnostic":"MOLECULAR_COMPARISON_NOT_EXECUTED"}
        result = worker.run((row,item,parent,aliases,provenance,version),budget)
    if changes and result.get("prediction"):
        rebind_prediction(result["prediction"],row["source_reference"],packet[2]["inci"],label,changes)
    if preview and result.get("prediction"):
        p = result.pop("prediction")
        result["review_only_preview"] = {"descriptors":p["attributes"],"roles":p["roles"],
            "molecular_dimension":"UNTESTED","publication":"NOT_PERSISTED"}
    return result


def _prior_attempts():
    prior = {cid:[] for cid in PLAN}
    for path in JOURNALS.glob("*.json"):
        for event in _events(path).values():
            for cid in PLAN.keys() & event.get("execution",{}).keys():
                prior[cid].append({"journal":path.name,"event":event["id"],"budget_seconds":event["budget_seconds"],
                                   **event["execution"][cid]})
    return prior


def run():
    start = perf_counter()
    OUTPUT.mkdir(exist_ok=True)
    source = StagedRegistry(SOURCE)
    full_progress = read(FULL/"progress.json")
    if _protected()!=full_progress["protected_after"]:
        raise ValueError("Protected full-run lineage changed")
    full_held = {d["concept_id"] for d in read(FULL/"metrics.json")["unpublished_details"]}
    if full_held!=set(PLAN):
        raise ValueError("Recovery plan differs from the audited full-run hold set")
    protected = {**_protected(),str(SOURCE):digest(SOURCE)}
    manifest = read(MANIFEST)
    manifest_hash = digest(MANIFEST)
    policy = digest(Path(__file__))
    version = "cosing-stage-b-handoff-recovery-v1:"+fingerprint([full_progress["frozen"]["version"],manifest_hash,policy,PLAN])
    history = _baseline_state(source,version)
    if len(history[1])!=30849 or history[0]!=full_progress["integrity"]["core_table_sha256"]:
        raise ValueError("Full-run registry disagrees with the saved integrity evidence")
    if not REGISTRY.exists():
        temp = REGISTRY.with_suffix(".copying")
        with source.reader() as db,closing(sqlite3.connect(temp)) as dest:
            db.backup(dest)
        temp.replace(REGISTRY)
    if REGISTRY.is_symlink() or any(Path(p).is_file() and REGISTRY.samefile(p) for p in protected):
        raise ValueError("Recovery destination aliases a protected input")
    registry = StagedRegistry(REGISTRY)
    if _baseline_state(registry,version)!=history:
        raise ValueError("Recovery database history or policy lineage changed")
    parents = {r["inci_id"]:r for r in read(PARENT_ARCHIVE)}
    prior = _prior_attempts()
    output,packets,pending = {},{},{}
    for r in _select(source,PLAN,(),None):
        row = dict(r)
        cid,key = row["concept_id"],row["source_reference"].rsplit(":",1)[1]
        bucket = source_bucket(key)
        aliases,held,path = load_bucket(manifest,bucket,parents)
        aliases.setdefault(key,[])
        held.setdefault(key,[])
        overlay = _overlay([parents[key]],aliases,held,manifest_hash)
        parent,evidence,provenance = overlay(row,json.loads(row["payload_json"]))
        packets[cid] = row,{"cohort":"handoff_recovery","stratum":"held"},parent,evidence,provenance,version
        output[cid] = {"source_reference":row["source_reference"],"revision":row["observed_revision"],
            "original_designation":parent["inci"],"source_definition":parent["description"],
            "original_typed_evidence":evidence,"held_alias_references":held[key],"prior_attempts":prior[cid],
            "budget_seconds":PLAN[cid][0],"budget_basis":PLAN[cid][1],
            "source_graph_text_lengths":[{"kind":a["alias_type"],"characters":len(a["alias"])}
                                         for a in evidence if a["alias_type"] in {"SMILES","INCHI"}]}
        journal = OUTPUT/f"{cid}.json"
        session = MonitoredBatch(registry,journal,packets,version,manifest_hash,
            lambda path=path,bucket=bucket: digest(MANIFEST)==manifest_hash
                and digest(path)==manifest["buckets"][str(bucket)]["file_sha256"])
        events = _events(journal)
        latest = list(events.values())[-1] if events else None
        pending[cid] = session,latest
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {cid:pool.submit(isolated,packets[cid],PLAN[cid][0])
                   for cid,(_,latest) in pending.items()
                   if not latest or latest["decision"] in {"STARTED","VALIDATED_PENDING_COMMIT"}}
        previews = {}
        for cid,(session,latest) in pending.items():
            if cid in futures:
                compute = lambda *_:futures[cid].result()
                if latest:
                    latest,_,_ = session.resume(latest["id"],compute,PLAN[cid][0])
                else:
                    latest,_,_ = session.submit([cid],compute,PLAN[cid][0])
            if latest["decision"]=="REJECT":
                raise ValueError(f"Existing quality gate rejected {cid}: {latest['critical_checks']}")
            output[cid].update(event=latest["id"],execution=latest["execution"].get(cid,{}),
                disposition="COMPLETED" if latest["decision"]=="ACCEPT" else "DOCUMENTED_HOLD")
            if latest["decision"]!="ACCEPT":
                previews[cid] = pool.submit(isolated,packets[cid],6,preview=True)
        for cid,job in previews.items():
            output[cid]["reduced_scope_review"] = job.result()
            output[cid]["recovery_recommendation"] = (
                "Keep full interpretation held. Review the isolated native comparison or obtain a scope-qualified source structure.")
    completed = sum(r["disposition"]=="COMPLETED" for r in output.values())
    verification = _integrity(registry,version,history,completed)
    if {**_protected(),str(SOURCE):digest(SOURCE)}!=protected:
        raise ValueError("Protected registry files changed during recovery")
    write(OUTPUT/"recovery.json",{"version":version,"manifest":manifest_hash,"policy_sha256":policy,
        "records":output,"dispositions":dict(Counter(r["disposition"] for r in output.values())),
        "protected_before":protected,"protected_after":protected,"integrity":verification,
        "elapsed_seconds":perf_counter()-start})
    print(verification["new_assessments"],"recovered",flush=True)


if __name__=="__main__":
    run()
