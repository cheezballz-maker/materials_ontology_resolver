"""Freeze source-only expansion and regression membership for Stage B v2."""

from collections import Counter, defaultdict
from hashlib import sha256
import re

from .full_capture import digest, read, write
from .stage_b_cohort import OUTPUT as V1, PARENT_ARCHIVE, classify
from .stage_b_score import _additional_archived_keys

OUTPUT = V1.with_name("stage_b_v2")
REGRESSION = {
    "CALCIUM OXIDE","ILLITE","CI 77491","CI 77492","ALUMINUM HYDROXIDE","STRONTIUM HYDROXIDE","THORIUM DIOXIDE",
    "ACACIA FARNESIANA STEM BARK EXTRACT","AVENA SATIVA KERNEL EXTRACT","ALOE BARBADENSIS EXTRACT",
    "ALOE BARBADENSIS LEAF EXTRACT","CITRUS HASSAKU/NATSUDAIDAI FRUIT JUICE","SOLANUM LYCOPERSICON FRUIT JUICE VESICLES",
    "POLYURETHANE-46","BOSWELLIA CARTERII GUM WATER","SD ALCOHOL 39-C",
    "SOLANUM LYCOPERSICUM MERISTEM CELL CULTURE CONDITIONED MEDIA","PARFUM","CI 77891","WATER",
    "CANNABIS SATIVA SEED OIL GLYCERIDES","HEXAPEPTIDE-42","CI 24790","ACID YELLOW 36","OLIGOPEPTIDE-41",
    "BENZOIC ACID","CYCLOHEXANONE","METHYL ACETATE","CETYL DIMETHICONE","ALCOHOL DENAT.",
}
CHALLENGES = (
    ("inorganic",r"HYDROXIDE|HYDROXYCARBONATE|HYDROXYCHLORIDE|\b(?:ILLITE|SMECTITE|KAOLIN)\b|(?:CALCIUM|TITANIUM|ZIRCONIUM|MAGNESIUM|MANGANESE) (?:MON|DI|TRI)?OXIDE",9),
    ("botanical",r"STEM BARK|ROOT BARK|KERNEL (?:EXTRACT|OIL)|[A-Z]+/[A-Z]+ (?:FRUIT|LEAF|FLOWER) (?:EXTRACT|JUICE)|JUICE VESICLES",10),
    ("polyurethane",r"^POLYURETHANE-\d+$",9),
    ("polymer_control",r"^POLY(?:ACRYLATE|ACRYLAMIDE|QUATERNIUM)-\d+$",4),
    ("preparation",r"\b(?:GUM WATER|RESIN WATER|SD ALCOHOL|JUICE VESICLES|CONDITIONED MEDI[AU]|FERMENT FILTRATE)\b",9),
)


def freeze():
    source = read(PARENT_ARCHIVE)
    v1 = read(V1/"cohort.json")
    previous = {r["parent"]["inci_id"] for r in v1["records"]}
    prior_data = V1.parent
    previous.update(r["inci_id"] for r in read(prior_data/"source_rows.json"))
    previous.update(_additional_archived_keys())
    evaluation = V1.parents[2]/"nomenclature_interpretation/evaluation"
    for path in (evaluation/"inci_records.json",*(evaluation/"coverage_v1").glob("development.json"),
                 *(evaluation/"coverage_v1").glob("holdout.json")):
        rows = read(path)
        if isinstance(rows,dict):
            rows = rows.get("rows",[])
        previous.update(r["inci_id"] for r in rows if isinstance(r,dict) and "inci_id" in r)
    eligible = [r for r in source if r["inci_id"] not in previous]
    eligible.sort(key=lambda r:sha256(("cosing-stage-b-v2:"+r["inci_id"]).encode()).digest())
    pool = defaultdict(list)
    for row in eligible:
        pool[classify(row)].append(row)
    records = [{"cohort":"regression","stratum":classify(r),"parent":r}
               for r in source if r["inci"] in REGRESSION]
    used = {r["parent"]["inci_id"] for r in records}
    if len(records)!=len(REGRESSION):
        raise ValueError("A protected regression designation is missing")
    for name,pattern,n in CHALLENGES:
        chosen = [r for r in eligible if r["inci_id"] not in used and re.search(pattern,r["inci"],re.I)][:n]
        for row in chosen:
            records.append({"cohort":"fresh_challenge","stratum":classify(row),"challenge":name,"parent":row})
            used.add(row["inci_id"])
    for category,n in (("other_or_incomplete",16),("chemical_identifier",8)):
        selected = [r for r in pool[category] if r["inci_id"] not in used][:n]
        for row in selected:
            records.append({"cohort":"fresh_challenge","stratum":category,"challenge":"fallback","parent":row})
            used.add(row["inci_id"])
    for category,rows in sorted(pool.items()):
        chosen = [r for r in rows if r["inci_id"] not in used][:49]
        if len(chosen)!=49:
            raise ValueError(f"Incomplete stratum {category}")
        for rank,row in enumerate(chosen,1):
            records.append({"cohort":"fresh_stratified","stratum":category,"rank":rank,"parent":row})
    OUTPUT.mkdir(exist_ok=True)
    write(OUTPUT/"cohort.json",{"seed":"cosing-stage-b-v2:","parent_sha256":digest(PARENT_ARCHIVE),
          "excluded_known_keys":len(previous),"counts":dict(Counter(r["cohort"] for r in records)),
          "population_by_stratum":dict(Counter(map(classify,source))),"records":records})


if __name__=="__main__":
    freeze()
