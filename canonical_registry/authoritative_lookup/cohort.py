"""Freeze an evidence-stratified pilot before authoritative retrieval."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3

from canonical_registry.cosing_pilot.full_capture import digest as sha, read, write
from canonical_registry.cosing_pilot.stage_b_handoff import INDEX, _inventory
from canonical_registry.cosing_pilot.stage_b_handoff_recovery import REGISTRY
from canonical_registry.cosing_pilot.staged_registry import StagedRegistry
from canonical_registry.identity_sufficiency.contract import digest
from canonical_registry.identity_sufficiency.evaluate import DATA as PREVIOUS, _guards

DATA = Path(__file__).with_name("data")
NAMED = {"WATER","AQUA","GLYCERIN","ALCOHOL","ALCOHOL DENAT.","ACETAMINOPHEN","PARACETAMOL",
         "UREA","ACETONE","SODIUM CHLORIDE","TITANIUM DIOXIDE","GLUTAMIC ACID","L-GLUTAMIC ACID",
         "D-GLUTAMIC ACID","L-LACTIC ACID","LACTIC ACID","DIECKOL","CAFFEINE","CITRIC ACID",
         "BENZOIC ACID","MAGNESIUM SULFATE","SODIUM ACETATE","CI 74160","DIRECT RED 80",
         "POLYETHYLENE GLYCOL 400","LAVANDULA ANGUSTIFOLIA FLOWER EXTRACT","HYDROGEN PEROXIDE"}
QUOTAS = {"direct_graph":86,"other_graph":72,"identifier_only":66,"conflicting":54,"broad":55,"sparse":25}
TABLE = "delta_lake.mse_dwd."


def literal(v):
    return "'"+v.replace("'","''")+"'"


def build_query(rows):
    values = sorted({(x["concept_id"],k,v) for x in rows for k,vals in x["queries"].items() for v in vals})
    want = ",".join("("+",".join(map(literal,record))+")" for record in values)
    return f"""WITH wanted(ref,kind,value) AS (VALUES {want}),
 hits AS (
 SELECT w.ref,i.chemical_id,w.kind,w.value,'PREFERRED_NAME' AS route
 FROM wanted w JOIN {TABLE}dwd_mse_chemicals_inventory i ON upper(trim(i.chemical_name))=w.value
 WHERE w.kind='NAME' AND i.data_status=1
 UNION ALL
 SELECT w.ref,a.chemical_id,w.kind,w.value,'REPORTED_ALIAS' AS route
 FROM wanted w JOIN {TABLE}dwd_mse_chemical_aliases a ON upper(trim(a.alias))=w.value
 WHERE w.kind='NAME' AND a.data_status=1
 UNION ALL
 SELECT w.ref,d.chemical_id,w.kind,w.value,'REPORTED_IDENTIFIER' AS route
 FROM wanted w JOIN {TABLE}dwd_mse_chemical_identifiers d ON upper(trim(d.identifier_value))=w.value
 WHERE w.kind IN ('CAS','EC','UNII') AND d.data_status=1
   AND ((w.kind='CAS' AND upper(d.identifier_type) IN ('CAS','CAS_NO','CAS REGISTRY NUMBER','CAS_REGISTRY_NUMBER'))
     OR (w.kind='EC' AND upper(d.identifier_type) IN ('EC','EC_NO','EC NUMBER','EC_NUMBER','EINECS'))
     OR (w.kind='UNII' AND upper(d.identifier_type)='UNII'))
 UNION ALL
 SELECT w.ref,i.chemical_id,w.kind,w.value,'FULL_INCHIKEY' AS route
 FROM wanted w JOIN {TABLE}dwd_mse_chemicals_inventory i ON i.inchikey=w.value
 WHERE w.kind='INCHIKEY' AND i.data_status=1
 ), combined AS (
 SELECT h.ref,i.chemical_id,i.source_id,i.chemical_name,i.ingredient_type,i.substance_type,i.smiles,
        i.inchikey,i.molecular_formula,i.source,cast(i.updated_ts AS varchar) AS updated_ts,
        array_sort(array_distinct(array_agg(h.route||':'||h.kind||':'||h.value))) AS receipts
 FROM hits h JOIN {TABLE}dwd_mse_chemicals_inventory i ON h.chemical_id=i.chemical_id
 WHERE i.data_status=1 AND i.source='FDA_GSRS_UNII'
 GROUP BY h.ref,i.chemical_id,i.source_id,i.chemical_name,i.ingredient_type,i.substance_type,i.smiles,
          i.inchikey,i.molecular_formula,i.source,i.updated_ts
 ), ranked AS (
 SELECT *,count(*) OVER(PARTITION BY ref) total_candidates,
   row_number() OVER(PARTITION BY ref ORDER BY chemical_id) rn FROM combined
 )
 SELECT ref,total_candidates,json_format(CAST(array_agg(ARRAY[chemical_id,source_id,chemical_name,
   ingredient_type,substance_type,smiles,inchikey,molecular_formula,source,updated_ts,
   json_format(CAST(receipts AS JSON))] ORDER BY rn) AS JSON)) AS candidates
 FROM ranked WHERE rn<=10 GROUP BY 1,2 ORDER BY 1 LIMIT 75"""


def freeze():
    if (DATA/"freeze.json").exists():
        raise FileExistsError("The source cohort is frozen")
    DATA.mkdir(exist_ok=True)
    protected = _guards()
    parents,aliases,_ = _inventory()
    previous = {r["concept_id"] for r in read(PREVIOUS/"cosing_cohort.json")}
    strata,dev = {},[]
    with closing(sqlite3.connect(INDEX.as_uri()+"?mode=ro",uri=True)) as db:
        for cid,ref,rev,version,status,raw in db.execute("""SELECT concept_id,source_reference,
                source_revision,stage_b_version,eligibility,evidence_json FROM stage_c_eligibility"""):
            p = parents[ref.rsplit(":",1)[1]]
            e = json.loads(raw)
            row = {"concept_id":cid,"source_reference":ref,"revision":rev,"stage_b_version":version,
                   "old_status":status,"old_evidence":e,"parent":p}
            if p["inci"] in NAMED:
                row.update(group="development",stratum="named_challenge")
                dev.append(row)
                continue
            if cid in previous:
                continue
            if status=="REVIEW_HOLD":
                s = "conflicting"
            elif status.startswith("NOT_APPLICABLE"):
                s = "broad"
            elif e["reason"]=="ORIGINAL_SOURCE_GRAPH_BINDING_UNESTABLISHED":
                s = "direct_graph"
            elif e["graph_evidence"]:
                s = "other_graph"
            elif p["cas_nos"] or p["ec_nos"]:
                s = "identifier_only"
            else:
                s = "sparse"
            row.update(group="fresh",stratum=s)
            strata.setdefault(s,[]).append(row)
    rows = sorted(dev,key=lambda r:r["concept_id"])
    for s,n in QUOTAS.items():
        rows.extend(sorted(strata[s],key=lambda r:digest(["authoritative-lookup-v1",r["concept_id"]]))[:n])
    with StagedRegistry(REGISTRY).reader() as db:
        for row in rows:
            p = row["parent"]
            row["aliases"] = aliases[p["inci_id"]]
            a = db.execute("""SELECT attributes_json,summary_json,trace_json FROM assessment
                          WHERE concept_id=? AND revision=? AND pipeline_version=?""",
                           (row["concept_id"],row["revision"],row["stage_b_version"])).fetchone()
            row["attributes"],row["summary"],row["trace"] = [json.loads(v) for v in a] if a else ([],{},{})
            trace = row["trace"].get("interpretation",{})
            names = {p["inci"].strip().upper()}
            definition = (p["description"] or "").strip()
            if 0<len(definition)<=40 and all(c.isalnum() or c in " -()," for c in definition) and len(definition.split())<=4:
                names.add(definition.upper())
            row["queries"] = {
                "NAME":sorted(x for x in names if x and len(x)<=160),
                "CAS":sorted({x.strip().upper() for x in p["cas_nos"] or [] if isinstance(x,str) and x.strip()}),
                "EC":sorted({x.strip().upper() for x in p["ec_nos"] or [] if isinstance(x,str) and x.strip()}),
                "INCHIKEY":sorted({g["value"]["inchikey"] for g in trace.get("assertions",[])
                                    if g["category"]=="STRUCTURAL" and g["value"]["inchikey"]})}
    if len(rows)!=len({r["concept_id"] for r in rows}) or not 300<=len(rows)<=500:
        raise ValueError("Unexpected cohort size or duplicated source key")
    write(DATA/"cohort.json",rows)
    sql = []
    for i in range(0,len(rows),60):
        name = f"lookup_{i//60:02}.sql"
        (DATA/name).write_text(build_query(rows[i:i+60]),encoding="utf-8")
        sql.append(name)
    write(DATA/"freeze.json",{"policy":"lookup-pilot-v1","cohort_sha256":sha(DATA/"cohort.json"),
        "sql":{n:sha(DATA/n) for n in sql},"protected_before":protected,
        "cohort_counts":{"development":len(dev),"fresh":len(rows)-len(dev)},
        "reference":{"positive_targets":{"WATER":"SUB_00000562","AQUA":"SUB_00000562"},
            "safety":"No exact proposal for explicit broad scope, processing hold, unresolved conflict or unqualified graph roles.",
            "independent_positive_holdout":False}})
    print(len(rows),"frozen records",len(sql),"bounded queries")


if __name__=="__main__":
    freeze()
