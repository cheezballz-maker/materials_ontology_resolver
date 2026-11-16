"""Freeze a bounded CosIng cohort from the registered parent snapshot."""

from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import re

from .full_capture import digest, read, write
from .readiness import DATA

OUTPUT = DATA / "stage_b_v1"
PARENT_ARCHIVE = DATA / "full_registration_v1" / "source_snapshot.json"
PATTERNS = (
    ("colorant",r"^CI[ .]*[0-9]|COLORANT|COLOURANT|LAKE$"),
    ("biological",r"FERMENT|LYSATE|PROTEIN|PEPTIDE|EXOSOME"),
    ("botanical",r"(LEAF|ROOT|FLOWER|FRUIT|SEED|BARK|STEM|RHIZOME|WHOLE PLANT).*(EXTRACT|JUICE|OIL|WATER|POWDER)"),
    ("polymer",r"POLYMER|SILOXANE|DIMETHICONE|^PEG[- /]|^PPG[- /]|^POLYQUATERNIUM"),
    ("lipid_surfactant",r"(CETEARETH|LAURETH|PARETH|STEARETH|GLYCERIDE|STEARATE|OLEATE|PALMITATE|SURFACTANT)"),
    ("inorganic",r"(OXIDE|SILICATE|CARBONATE|PHOSPHATE|SILICA|KAOLIN|MICA|SULFATE)$"),
    ("preparation",r"OIL|EXTRACT|POWDER|BLEND|MIXTURE|DENAT|WAX|WATER|DISTILLATE"),
)
PILOT_CHALLENGES = {
    "PARFUM","WATER","CI 77891","CI 77491","CI 77492","ALCOHOL DENAT.","ACETONE","ETHANOL",
    "CANNABIS SATIVA SEED OIL GLYCERIDES","BERTHOLLETIA EXCELSA SEED OIL PEG-8 ESTERS","DIMETHICONE",
    "ALOE BARBADENSIS LEAF EXTRACT","GLYCERIN",
}


def classify(row):
    label = row["inci"].upper()
    for group, pattern in PATTERNS:
        if re.search(pattern,label):
            return group
    return "chemical_identifier" if any(v and v.strip() for v in (row["cas_nos"] or [])) else "other_or_incomplete"


def freeze():
    sources = read(PARENT_ARCHIVE)
    pilot = read(DATA/"source_rows.json")
    readiness = [*read(DATA/"readiness_validation.json")["rows"],*read(DATA/"readiness_supplement.json")["rows"]]
    old = {r["inci_id"] for r in (*pilot,*readiness)}
    evaluation = DATA.parents[1] / "nomenclature_interpretation/evaluation"
    for file in (evaluation/"inci_records.json", *evaluation.glob("*/development.json"),
                 *evaluation.glob("*/holdout.json"), *evaluation.glob("*/cohort.json")):
        if file.is_file():
            content = read(file)
            if isinstance(content,dict):
                content = content.get("rows",[])
            old.update(r["inci_id"] for r in content if isinstance(r,dict) and "inci_id" in r)
    challenges = {r["inci_id"]:"prior_readiness" for r in readiness}
    challenges.update({r["inci_id"]:"prior_pilot" for r in pilot if r["inci"] in PILOT_CHALLENGES})
    groups, population, items = defaultdict(list), Counter(), []
    for row in sources:
        group, key = classify(row),row["inci_id"]
        population[group] += 1
        if key not in old:
            groups[group].append(row)
        if key in challenges:
            items.append({"cohort":challenges[key],"stratum":group,"rank":None,"parent":row})
    for group, pool in sorted(groups.items()):
        rank = lambda row:sha256(("cosing-stage-b-v1:"+row["inci_id"]).encode()).digest()
        for i,row in enumerate(sorted(pool,key=rank)[:36],1):
            items.append({"cohort":"stratified","stratum":group,"rank":i,"parent":row})
    assert len(groups)==9 and sum(item["cohort"]=="stratified" for item in items)==324
    OUTPUT.mkdir(exist_ok=True)
    write(OUTPUT/"cohort.json",{"parent_sha256":digest(PARENT_ARCHIVE),"population_by_stratum":dict(population),
                                "excluded_previously_seen_keys":len(old),"records":items})


if __name__ == "__main__":
    freeze()
