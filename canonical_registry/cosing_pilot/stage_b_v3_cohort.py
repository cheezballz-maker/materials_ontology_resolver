"""Deterministic source-only selection for the monitored Stage B expansion."""

from collections import Counter, defaultdict
from hashlib import sha256
import re

from .full_capture import digest, read, write
from .stage_b_cohort import DATA, OUTPUT as V1, PARENT_ARCHIVE, classify
from .stage_b_score import _additional_archived_keys
from .stage_b_v2 import DESIGNATED as V2_DB
from .stage_b_v2_cohort import OUTPUT as V2
from .staged_registry import StagedRegistry

OUTPUT = DATA/"stage_b_v3"
DEVELOPMENT = {
    "SORBETH-7","RHAMNOLIPIDS","HC BLUE NO. 16","GLYCINE SOJA HULL","POLYURETHANE-46",
    "ALUMINUM HYDROXIDE","ACACIA FARNESIANA STEM BARK EXTRACT","AVENA SATIVA KERNEL EXTRACT",
    "BOSWELLIA CARTERII GUM WATER","SD ALCOHOL 39-C","CALCIUM OXIDE","ILLITE",
}
RISK = (
    ("inorganic",r"HYDROXIDE|(?:MAGNESIUM|CALCIUM|ZINC|TITANIUM|IRON) (?:DI)?OXIDE|SILICATE|\bCLAY\b",12),
    ("botanical",r"STEM BARK|ROOT BARK|KERNEL (?:EXTRACT|OIL)|(?:VAR|SUBSP)\.|[A-Z]+/[A-Z]+ (?:FRUIT|LEAF|FLOWER) (?:EXTRACT|JUICE)",12),
    ("polymer",r"^(?:POLYURETHANE|POLYQUATERNIUM)-\d+$|\bGLYCOLIPIDS?\b|\b[A-Z]+ETH-\d+\b",12),
    ("colorant",r"^HC [A-Z]+ (?:NO\.? )?\d+|^CI\s*\d+|\b(?:ALUMINIUM|CALCIUM) LAKE\b",12),
    ("preparation",r"FERMENT FILTRATE|CONDITIONED MEDIA|GUM WATER|RESIN WATER|SD ALCOHOL",12),
)
FALLBACK_POSITIVE = re.compile(r"\b(?:obtained by (?:the )?fermentation|growth media removed from cultures|"
                              r"filtrate of|aqueous (?:solution|preparation) of (?:the )?steam distillates?|"
                              r"(?:polyethylene glycol ether|ethoxylated)|glycolipids?)\b",re.I)


def _already_seen():
    excluded = _additional_archived_keys()
    excluded.update(r["inci_id"] for r in read(DATA/"source_rows.json"))
    for path in (V1/"cohort.json",V2/"cohort.json",V2/"confirmation/cohort.json"):
        excluded.update(x["parent"]["inci_id"] for x in read(path)["records"])
    evaluation = DATA.parents[1]/"nomenclature_interpretation/evaluation"
    for path in (evaluation/"inci_records.json",evaluation/"coverage_v1/development.json",
                 evaluation/"coverage_v1/holdout.json"):
        rows = read(path)
        if isinstance(rows,dict):
            rows = rows.get("rows",[])
        excluded.update(x["inci_id"] for x in rows if isinstance(x,dict) and "inci_id" in x)
    with StagedRegistry(V2_DB).reader() as db:
        assessed = {r[0].split(":",1)[1] for r in db.execute("""SELECT DISTINCT source_reference
                  FROM assessment JOIN domain_concept USING(concept_id)""")}
    return excluded|assessed, assessed


def _allocate(population,total,floor):
    remaining = total-floor*len(population)
    denominator = sum(population.values())
    weights = {k:remaining*n/denominator for k,n in population.items()}
    quotas = {k:floor+int(v) for k,v in weights.items()}
    for key in sorted(weights,key=lambda k:(-(weights[k]%1),k))[:total-sum(quotas.values())]:
        quotas[key]+=1
    return quotas


def freeze():
    source = read(PARENT_ARCHIVE)
    excluded,assessed = _already_seen()
    eligible = sorted((r for r in source if r["inci_id"] not in excluded),
                      key=lambda r:sha256(("cosing-stage-b-v3:"+r["inci_id"]).encode()).digest())
    groups = {r["inci_id"]:classify(r) for r in source}
    regressions = {r["parent"]["inci_id"] for r in read(V2/"cohort.json")["records"] if r["cohort"]=="regression"}
    records, used = [], set()

    def append(row,cohort,challenge=None):
        key = row["inci_id"]
        records.append({"parent":row,"cohort":cohort,"stratum":groups[key],"challenge":challenge})
        used.add(key)

    for row in source:
        if row["inci"] in DEVELOPMENT:
            append(row,"development")
        elif row["inci_id"] in regressions:
            append(row,"regression")
    for label,pattern,n in RISK:
        for row in [r for r in eligible if r["inci_id"] not in used and re.search(pattern,r["inci"],re.I)][:n]:
            append(row,"high_risk",label)
    positive = [r for r in eligible if groups[r["inci_id"]] in {"other_or_incomplete","chemical_identifier"}
                and FALLBACK_POSITIVE.search(r["description"] or "")]
    for row in [r for r in positive if r["inci_id"] not in used][:55]:
        append(row,"high_risk","fallback_definition")
    for row in [r for r in eligible if r["inci_id"] not in used and groups[r["inci_id"]]=="other_or_incomplete"
                and not r["description"] and not any(r[k] for k in ("cas_nos","ec_nos"))][:55]:
        append(row,"high_risk","fallback_sparse")
    shortfall = 170-sum(r["cohort"]=="high_risk" for r in records)
    for row in [r for r in eligible if r["inci_id"] not in used and groups[r["inci_id"]]=="other_or_incomplete"
                and (r["description"] or not any(r[k] for k in ("cas_nos","ec_nos")))][:max(0,shortfall)]:
        append(row,"high_risk","fallback_scope")
    pools = defaultdict(list)
    for row in eligible:
        if row["inci_id"] not in used:
            pools[groups[row["inci_id"]]].append(row)
    population = {k:len(rows) for k,rows in sorted(pools.items())}
    quota = _allocate(population,1330,25)
    for group,rows in sorted(pools.items()):
        if len(rows)<quota[group]:
            raise ValueError(f"Insufficient source stratum {group}")
        for row in rows[:quota[group]]:
            append(row,"representative")
    fresh = {r["parent"]["inci_id"] for r in records if r["cohort"] in {"representative","high_risk"}}
    if fresh&excluded or len(fresh)!=1500:
        raise ValueError(f"Fresh cohort failed its coverage or history check: {len(fresh)}, {len(pools)}, {len(fresh&excluded)}")
    OUTPUT.mkdir(exist_ok=True)
    write(OUTPUT/"cohort.json",{"seed":"cosing-stage-b-v3:","parent_sha256":digest(PARENT_ARCHIVE),
        "source_database_sha256":digest(V2_DB),"excluded_known_keys":len(excluded),"previously_assessed_keys":len(assessed),
        "representative_sampling_frame":population,"representative_quotas":quota,
        "exhausted_strata":sorted(set(groups.values())-set(pools)),
        "counts":dict(Counter(r["cohort"] for r in records)),"records":records})


if __name__=="__main__":
    freeze()
