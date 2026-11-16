"""Freeze a bounded cross-source cohort and evaluate eligibility without matching."""

import argparse
from collections import Counter
from contextlib import ExitStack, closing
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
from time import perf_counter
from xml.etree import ElementTree

from rdkit import rdBase
from canonical_registry.cosing_pilot.full_capture import digest as file_digest, read, write
from canonical_registry.cosing_pilot.full_stage_b_enrichment import _protected
from canonical_registry.cosing_pilot.stage_b_handoff import INDEX, _inventory
from canonical_registry.cosing_pilot.stage_b_handoff_recovery import REGISTRY
from canonical_registry.cosing_pilot.staged_assessment import _bridge
from canonical_registry.cosing_pilot.staged_registry import StagedRegistry
from providers import GSRS

from .adapters import cosing, gsrs, COSING_DOC
from .contract import Evaluator, digest, POLICY

DATA = Path(__file__).with_name("data")
NATIVE = DATA.parents[1]/"evidence_upgrade/provider_probe/gsrs_complete.txt"
NATIVE_URL = "https://gsrs.ncats.nih.gov/ginas/app/api/v1/substances(10dfa22e-ca56-40bf-b0b5-4f92a36ede90)?view=full"
DEV = {"WATER","AQUA","GLYCERIN","UREA","ACETONE","SODIUM CHLORIDE","TITANIUM DIOXIDE",
       "DIECKOL","L-LACTIC ACID","CI 74160","DIRECT RED 80","POLYETHYLENE GLYCOL 400",
       "KAOLIN","LAVANDULA ANGUSTIFOLIA FLOWER EXTRACT","SODIUM ACETATE","CITRIC ACID"}
READY = "CANDIDATE_READY"
NEEDS = "NEEDS_MORE_EVIDENCE"
HOLD = "REVIEW_HOLD"
OUT = "NOT_APPLICABLE_TO_EXACT_MOLECULAR_RESOLUTION"
REFERENCES = {
    "WATER":{"entity":"NIST:C7732185","unii":"059QF0KO0R","cas":"7732-18-5","ec":"231-791-2",
             "echa":"https://echa.europa.eu/substance-information/-/substanceinfo/100.028.902",
             "structure":{"url":"https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185",
                          "inchi":"InChI=1S/H2O/h1H2","key":"XLYOFNOQVPJJNP-UHFFFAOYSA-N","formula":"H2O"}},
    "GLYCERIN":{"entity":"NIST:C56815","unii":"PDC6A3C0OX","cas":"56-81-5","ec":"200-289-5",
                "echa":"https://echa.europa.eu/substance-information/-/substanceinfo/100.000.263",
                "structure":{"url":"https://webbook.nist.gov/cgi/cbook.cgi?ID=C56815",
                    "inchi":"InChI=1S/C3H8O3/c4-1-3(6)2-5/h3-6H,1-2H2",
                    "key":"PEDCQBHIVMGVHV-UHFFFAOYSA-N","formula":"C3H8O3"}},
}


def _guards():
    return {**_protected(),str(REGISTRY):file_digest(REGISTRY),str(INDEX):file_digest(INDEX)}


def _inputs():
    warehouse = read(DATA/"gsrs_inventory.json")["rows"]
    companions = {}
    ids = {r["chemical_id"] for r in warehouse}
    for kind in ("aliases","identifiers"):
        entries = read(DATA/f"gsrs_{kind}.json")["rows"]
        if len(entries)!=len(ids) or {r["chemical_id"] for r in entries}!=ids:
            raise ValueError("Companion query does not cover the frozen sample")
        found = set()
        for row in entries:
            records = json.loads(row["packets"])
            if (len(records)!=int(row["rows_total"]) or any(r[1]!=row["chemical_id"] for r in records)
                    or any(r[0] in found for r in records) or len({r[0] for r in records})!=len(records)):
                raise ValueError("GSRS companion count or parent binding mismatch")
            found.update(r[0] for r in records)
            companions.setdefault(row["chemical_id"],{})[kind] = records
    native = read(DATA/"gsrs_native.json")["rows"]
    if len(native)!=1 or native[0]["chemical_id"] in ids:
        raise ValueError("Native development row missing or overlaps sample")
    return warehouse+native,companions


def _choose(parents, index):
    dev, pool = [],{}
    for cid,ref,rev,version,old_status,old_json in index.execute("""SELECT concept_id,source_reference,source_revision,
            stage_b_version,eligibility,evidence_json FROM stage_c_eligibility ORDER BY concept_id"""):
        key = ref.rsplit(":",1)[1]
        parent = parents[key]
        e = json.loads(old_json)
        record = {"concept_id":cid,"source_reference":ref,"revision":rev,"stage_b_version":version,
                  "old_status":old_status,"old_evidence":e}
        if parent["inci"] in DEV:
            record.update(cohort="development",stratum="named_reference")
            dev.append(record)
            continue
        if old_status==OUT:
            stratum = "explicit_broad"
        elif not version:
            stratum = "processing_hold"
        elif old_status==HOLD:
            stratum = "identity_review"
        elif e["reason"]=="ORIGINAL_SOURCE_GRAPH_BINDING_UNESTABLISHED":
            stratum = "name_and_reported_structure"
        elif e["graph_evidence"]:
            stratum = "graph_candidate_other"
        elif parent["cas_nos"] or parent["ec_nos"]:
            stratum = "identifier_only"
        else:
            stratum = "unqualified_or_sparse"
        record.update(cohort="held_out_for_this_contract",stratum=stratum)
        pool.setdefault(stratum,[]).append(record)
    quotas = {"explicit_broad":30,"processing_hold":4,"identity_review":30,"name_and_reported_structure":36,
              "graph_candidate_other":33,"identifier_only":28,"unqualified_or_sparse":25}
    return dev+[r for key,n in quotas.items() for r in sorted(
        pool.get(key,[]),key=lambda x:digest(["cosing-sufficiency-v1",x["concept_id"]]))[:n]]


def _receipts(selected, parents):
    result = {"cosing":{},"gsrs":{}}
    for name,ref in REFERENCES.items():
        result["gsrs"][ref["unii"]] = {**ref,"preferred_name":name,
            "fda_url":f"https://precision.fda.gov/uniisearch/srs/unii/{ref['unii']}",
            "fda_formula":ref["structure"]["formula"],"fda_key":ref["structure"]["key"]}
    for r in selected:
        p = parents[r["source_reference"].rsplit(":",1)[1]]
        name = p["inci"]
        if name not in {"WATER","AQUA","GLYCERIN"}:
            continue
        ref = REFERENCES["WATER" if name=="AQUA" else name]
        if p["cas_nos"]!=[ref["cas"]] or p["ec_nos"]!=[ref["ec"]]:
            raise ValueError("Curated source identifiers disagree with the authority receipt")
        if name=="AQUA" and p["description"]!="Water":
            raise ValueError("Explicit AQUA naming bridge changed")
        binding = ({"kind":"NOMENCLATURE_LINK","value":"AQUA → Water","authority":"CosIng source definition",
                    "url":COSING_DOC,"locator":r["source_reference"]+"#definition",
                    "grants":["NOMENCLATURE","REFERENT"]} if name=="AQUA" else
                   {"kind":"IDENTIFIER_LINK","value":ref["ec"],"namespace":"EC",
                    "authority":"CosIng source designation and ECHA EC Inventory","url":ref["echa"],
                    "locator":"EC/List number, CAS number and substance name",
                    "grants":["IDENTIFIER","REFERENT"]})
        result["cosing"][r["concept_id"]] = {**ref,"source_revision":r["revision"],"binding":binding,
            "source_conditions":{"designation":name,"definition":p["description"],"cas":p["cas_nos"],"ec":p["ec_nos"]},
            "fda_scope_reference":result["gsrs"][ref["unii"]]["fda_url"],
            "review_basis":"Exact parent designation or explicit definition and matched singleton EC/CAS, plus independent structure reference."}
    if len(result["cosing"])!=3:
        raise ValueError("Curated CosIng development controls missing")
    return result


def freeze():
    if (DATA/"frozen_reference.json").exists():
        raise FileExistsError("The reference and source packets are frozen")
    before = _guards()
    parents,aliases,_ = _inventory()
    with closing(sqlite3.connect(INDEX.as_uri()+"?mode=ro",uri=True)) as idx:
        selected = _choose(parents,idx)
    receipts = _receipts(selected,parents)
    with StagedRegistry(REGISTRY).reader() as db:
        for row in selected:
            key = row["source_reference"].rsplit(":",1)[1]
            parent = parents[key]
            row["parent"] = parent
            row["aliases"] = aliases[key]
            a = None
            if row["stage_b_version"]:
                a = db.execute("SELECT attributes_json,summary_json,trace_json FROM assessment WHERE concept_id=? AND revision=? AND pipeline_version=?",
                               (row["concept_id"],row["revision"],row["stage_b_version"])).fetchone()
                if a is None:
                    raise ValueError("Frozen Stage B assessment unavailable")
            row["attributes"],row["summary"],row["trace"] = [json.loads(v) for v in a] if a else ([],{},{})
    inventory,companions = _inputs()
    cos_refs = {r["concept_id"]:{"expected":READY if r["concept_id"] in receipts["cosing"] else r["old_status"],
                 "basis":"authority-backed development adjudication" if r["concept_id"] in receipts["cosing"] else
                         "provisional prior-scope comparator; no independent exact-identity adjudication",
                 "group":r["cohort"],"stratum":r["stratum"]} for r in selected}
    gs_refs = {}
    for g in inventory:
        cid = g["chemical_id"]
        qualified = g["source_id"] in receipts["gsrs"] or g["cohort"]=="native_development"
        expected = READY if qualified else OUT if g["substance_type"] in {"mixture","polymer","structurallyDiverse"} else NEEDS
        gs_refs[cid] = {"expected":expected,"group":"development" if g["cohort"] in {"named","native_development"} else
            "held_out_for_this_contract","stratum":g["cohort"],"basis":"source record type and available scope/authority, provisional"}
    write(DATA/"cosing_cohort.json",selected)
    write(DATA/"authority_receipts.json",receipts)
    write(DATA/"frozen_reference.json",{"cosing":cos_refs,"gsrs":gs_refs,"independent_specialist":False,
        "source_hashes":{name:file_digest(DATA/name) for name in ("cosing_cohort.json","authority_receipts.json",
                        "gsrs_inventory.json","gsrs_aliases.json","gsrs_identifiers.json","gsrs_native.json")},
        "native_record_sha256":file_digest(NATIVE),"protected_before":before})
    if _guards()!=before:
        raise ValueError("Protected inputs changed during cohort freeze")
    print("Frozen",len(cos_refs),"CosIng and",len(gs_refs),"GSRS cases")


def evaluate():
    reference = read(DATA/"frozen_reference.json")
    if any(file_digest(DATA/name)!=sha for name,sha in reference["source_hashes"].items()):
        raise ValueError("Frozen source or authority receipt changed")
    if file_digest(NATIVE)!=reference["native_record_sha256"] or _guards()!=reference["protected_before"]:
        raise ValueError("Protected or native evidence changed")
    receipts = read(DATA/"authority_receipts.json")
    inventory,companions = _inputs()
    old = read(DATA/"cosing_cohort.json")
    with ExitStack() as stack,rdBase.BlockLogs():
        bridge = _bridge(stack)
        evaluator = Evaluator(bridge.official)
        native = GSRS.record(json.loads(NATIVE.read_text(encoding="utf-8-sig")),NATIVE_URL)
        output = {"cosing":[],"gsrs":[]}
        for row in old:
            e = cosing(row,row["parent"],row["aliases"],receipts["cosing"].get(row["concept_id"]))
            d = evaluator.evaluate(e)
            output["cosing"].append({"name":e.designation,"reference":reference["cosing"][e.referent],
                 "old":{"status":row["old_status"],"reason":row["old_evidence"]["reason"],
                        "graph_evidence":row["old_evidence"]["graph_evidence"],
                        "issues":row["old_evidence"]["issues"]},"packet":asdict(e),"decision":d})
        for row in inventory:
            e = gsrs(row,companions.get(row["chemical_id"],{}),receipts["gsrs"].get(row["source_id"]),
                     native if row["cohort"]=="native_development" else None)
            output["gsrs"].append({"name":e.designation,"reference":reference["gsrs"][e.referent],
                                   "packet":asdict(e),"decision":evaluator.evaluate(e)})
    after = _guards()
    if after!=reference["protected_before"]:
        raise ValueError("Protected files changed during eligibility evaluation")
    metrics = {"policy_version":POLICY,"policy_sha256":file_digest(Path(__file__).with_name("contract.py")),
        "adapter_sha256":file_digest(Path(__file__).with_name("adapters.py")),"protected_after":after,
        "reference_sha256":file_digest(DATA/"frozen_reference.json"),"official_graphs":len(evaluator.official),
        "groups":{}}
    pool = []
    for source,rows in output.items():
        statuses = Counter(x["decision"]["eligibility"] for x in rows)
        errors = [dict(id=x["packet"]["referent"],name=x["name"],expected=x["reference"]["expected"],
                       actual=x["decision"]["eligibility"],reasons=x["decision"]["reasons"])
                  for x in rows if x["decision"]["eligibility"]!=x["reference"]["expected"]]
        counts = {}
        for group in {x["reference"]["group"] for x in rows}:
            subset = [x for x in rows if x["reference"]["group"]==group]
            counts[group] = {"total":len(subset),"agreements":sum(x["decision"]["eligibility"]==x["reference"]["expected"] for x in subset),
                             "statuses":dict(Counter(x["decision"]["eligibility"] for x in subset))}
        metrics["groups"][source] = {"total":len(rows),"statuses":dict(statuses),"by_group":counts,"disagreements":errors,
            "reasons":dict(Counter(reason for x in rows for reason in x["decision"]["reasons"]))}
        pool.extend({"source":source,"name":x["name"],**x["decision"]} for x in rows if x["decision"]["eligibility"]==READY)
    write(DATA/"eligibility.json",output)
    write(DATA/"candidate_pool.json",pool)
    write(DATA/"metrics.json",metrics)
    print("Evaluated",*(f"{k}={len(v)}" for k,v in output.items()),"candidate pool",len(pool))


def inventory_screen():
    """Screen available frozen evidence. Uncurated records cannot acquire a new authority grant."""
    start = perf_counter()
    result = read(DATA/"metrics.json")
    reference = read(DATA/"frozen_reference.json")
    tests = ElementTree.parse(DATA/"tests.xml").getroot()[0].attrib
    if (int(tests["failures"])+int(tests["errors"]) or
            any(d["actual"]==READY for source in result["groups"].values() for d in source["disagreements"])
            or result["policy_sha256"]!=file_digest(Path(__file__).with_name("contract.py"))
            or result["adapter_sha256"]!=file_digest(Path(__file__).with_name("adapters.py"))
            or file_digest(DATA/"authority_receipts.json")!=reference["source_hashes"]["authority_receipts.json"]
            or _guards()!=reference["protected_before"]):
        raise ValueError("Bounded evaluation or inventory screening preconditions failed")
    parents,aliases,_ = _inventory()
    receipts = read(DATA/"authority_receipts.json")["cosing"]
    previous = {}
    with closing(sqlite3.connect(INDEX.as_uri()+"?mode=ro",uri=True)) as index:
        for cid,old_status,evidence in index.execute("SELECT concept_id,eligibility,evidence_json FROM stage_c_eligibility"):
            previous[cid] = old_status,json.loads(evidence)
    counts,transitions,reasons,routes,paths = (Counter() for _ in range(5))
    destination = DATA/"cosing_inventory_eligibility.jsonl"
    temp = destination.with_suffix(".building")
    with ExitStack() as stack,rdBase.BlockLogs(),StagedRegistry(REGISTRY).reader() as db, temp.open("w",encoding="utf-8") as stream:
        bridge = _bridge(stack)
        evaluator = Evaluator(bridge.official)
        rows = db.execute("""WITH latest AS (
            SELECT a.*,row_number() OVER (PARTITION BY a.concept_id ORDER BY a.rowid DESC) AS rn
            FROM assessment a JOIN source_head h ON h.concept_id=a.concept_id AND h.observed_revision=a.revision
            WHERE a.attempted=0 AND json_extract(a.summary_json,'$.stage')='INTERPRETATION')
          SELECT d.concept_id,d.source_reference,h.observed_revision,a.pipeline_version,
                 a.attributes_json,a.summary_json,a.trace_json
          FROM domain_concept d JOIN source_head h USING(concept_id)
          LEFT JOIN latest a ON a.concept_id=d.concept_id AND a.rn=1 ORDER BY d.concept_id""")
        for cid,ref,rev,version,attrs,summary,trace in rows:
            prior,old = previous[cid]
            key = ref.rsplit(":",1)[1]
            row = {"concept_id":cid,"source_reference":ref,"revision":rev,"stage_b_version":version,
                   "attributes":json.loads(attrs) if attrs else [],"summary":json.loads(summary) if summary else {},
                   "trace":json.loads(trace) if trace else {},"old_evidence":old}
            decision = evaluator.evaluate(cosing(row,parents[key],aliases[key],receipts.get(cid)))
            status = decision["eligibility"]
            if status==READY and cid not in receipts:
                raise ValueError("Unexpected grant outside the bounded authority receipts")
            counts[status]+=1
            transitions[(prior,status)]+=1
            reasons.update(decision["reasons"])
            if decision["resolution_pathway"]:
                routes[decision["resolution_pathway"]]+=1
                paths[decision["evidence_pathway"]]+=1
            compact = {k:v for k,v in decision.items() if k!="authority_assessment"}
            compact.update(stage_b_version=version,previous_eligibility=prior)
            stream.write(json.dumps(compact,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")
    if sum(counts.values())!=30360 or _guards()!=reference["protected_before"]:
        raise ValueError("Inventory scan coverage or protected integrity failed")
    temp.replace(destination)
    write(DATA/"cosing_inventory_metrics.json",{"total":sum(counts.values()),"statuses":dict(counts),
        "transitions":{f"{a} -> {b}":n for (a,b),n in transitions.items()},"reasons":dict(reasons),
        "resolution_paths":dict(routes),"evidence_paths":dict(paths),"results_sha256":file_digest(destination),
        "elapsed_seconds":perf_counter()-start,"policy_sha256":result["policy_sha256"],
        "scope":"Frozen evidence availability, with three bounded authority receipts. No additional external adjudication."})
    print("Inventory",dict(counts))


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("freeze","evaluate","inventory"))
    {"freeze":freeze,"evaluate":evaluate,"inventory":inventory_screen}[parser.parse_args().action]()
