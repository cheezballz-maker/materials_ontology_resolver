"""Fresh, frozen confirmation of the anatomy inflection correction."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from .full_capture import digest, read, write
from .stage_b_cohort import DATA, OUTPUT as V1, PARENT_ARCHIVE, classify
from .stage_b_score import _additional_archived_keys
from .stage_b_v1 import _overlay
from .stage_b_v2 import _audit, _baseline_state, _copy
from .stage_b_v2_cohort import OUTPUT
from .stage_b_v2_evidence import assemble, verified

DESTINATION = OUTPUT/"confirmation"
PART_FORM = re.compile(r"^[A-Z-]+ [A-Z-]+ (KERNEL|SPROUT|STEM BARK|ROOT BARK|LEAF|FRUIT|SEED|ROOT|FLOWER) (EXTRACT|OIL|JUICE)$",re.I)
PLURAL = {"leaf":"leaves","kernel":"kernels","sprout":"sprouts","stem bark":"stem barks","root bark":"root barks"}


def select():
    excluded = _additional_archived_keys()
    excluded.update(r["inci_id"] for r in read(DATA/"source_rows.json"))
    for source in (V1/"cohort.json",OUTPUT/"cohort.json"):
        excluded.update(x["parent"]["inci_id"] for x in read(source)["records"])
    evaluation = V1.parents[2]/"nomenclature_interpretation/evaluation"
    for file in (evaluation/"inci_records.json",evaluation/"coverage_v1/development.json",evaluation/"coverage_v1/holdout.json"):
        rows = read(file)
        if isinstance(rows,dict):
            rows = rows.get("rows",[])
        excluded.update(r["inci_id"] for r in rows if isinstance(r,dict) and "inci_id" in r)
    source = sorted((r for r in read(PARENT_ARCHIVE) if r["inci_id"] not in excluded),
                    key=lambda r:sha256(("stage-b-v2-independent-confirmation:"+r["inci_id"]).encode()).digest())
    focus, other = [],defaultdict(list)
    for row in source:
        group = classify(row)
        match = PART_FORM.fullmatch(row["inci"])
        if match:
            part,form = (v.casefold() for v in match.groups())
            inflected = PLURAL.get(part,part+"s")
            definition = row["description"] or ""
            if re.search(rf"\b{form}\s+(?:(?:obtained|derived|expressed)\s+)?(?:of|from)\s+(?:the\s+)?{inflected}\b(?!\s*(?:/|and\b|or\b))",
                         definition,re.I):
                focus.append({"parent":row,"stratum":group,"expected_part":part,"expected_preparation":form})
                continue
        if group!="botanical":
            other[group].append({"parent":row,"stratum":group})
    focus.sort(key=lambda item:item["expected_part"] not in {"kernel","sprout","stem bark","root bark"})
    chosen = focus[:20]+[row for k in sorted(other) for row in other[k][:2]]
    if len(chosen)<36:
        chosen.extend([row for k in sorted(other) for row in other[k][2:]][:36-len(chosen)])
    if len(chosen)!=36:
        raise ValueError("Insufficient fresh confirmation coverage")
    DESTINATION.mkdir(exist_ok=True)
    write(DESTINATION/"cohort.json",{"parent_sha256":digest(PARENT_ARCHIVE),"records":chosen,
        "status":"FROZEN_SOURCE_CONFIRMATION","annotation":"Preferred name and original definition independently express the same plant part and preparation in the 20 focus cases."})


def assess():
    from .staged_assessment import _interpret, _select, interpretation_version

    manifest,evidence,held,counts = verified(DESTINATION)
    file = DESTINATION/"companion_manifest.json"
    source = {r["parent"]["inci_id"]:r for r in read(DESTINATION/"cohort.json")["records"]}
    with TemporaryDirectory(dir=OUTPUT.parents[1]) as temp:
        db = _copy(Path(temp)/"confirmation.sqlite")
        selected = _select(db,(),list(source),None)
        if len(selected)!=len(source):
            raise ValueError("Confirmation registry bindings incomplete")
        overlay = _overlay([r["parent"] for r in source.values()],evidence,held,digest(file))
        version = "cosing-stage-b-v2-confirmation:"+interpretation_version(False).split(":",1)[1]+":"+digest(file)
        baseline = _baseline_state(db,version)
        options = dict(typed_only=False,pending=False,capability=None,overlay=overlay)
        result = _interpret(db,selected,version,**options)
        replay = _interpret(db,selected,version,**options)
        integrity = _audit(db,version,baseline,len(source))
        predictions,issues = [],Counter()
        with db.reader() as connection:
            for row in connection.execute("""SELECT a.*,d.source_reference,d.preferred_label FROM assessment a
                JOIN domain_concept d USING(concept_id) WHERE pipeline_version=? ORDER BY concept_id""",(version,)):
                key = row["source_reference"].split(":",1)[1]
                ref = source[key]
                trace = json.loads(row["trace_json"])
                interpretation = trace["interpretation"]
                attrs = json.loads(row["attributes_json"])
                facts = {(a["predicate"],str(a["value"]).casefold()) for a in attrs}
                checks = {}
                if ref.get("expected_part"):
                    checks = {"part_persisted":("reported_plant_part",ref["expected_part"]) in facts,
                              "preparation_persisted":("reported_botanical_preparation",ref["expected_preparation"]) in facts,
                              "no_false_anatomy_conflict":not any("botanical.anatomy" in i["affected_slots"] for i in interpretation["issues"])}
                unsafe = any(a["evidence_role"]!="CANDIDATE_ONLY" for a in (
                    *interpretation["assertions"],*interpretation["withheld_assertions"]) if a["category"]=="STRUCTURAL")
                unsafe |= any(m["whole_referent_graph_unestablished"] for m in interpretation["modules"]) and any(
                    a["category"]=="STRUCTURAL" for a in interpretation["assertions"])
                issues["critical"] += unsafe
                predictions.append({"inci_id":key,"concept_id":row["concept_id"],"name":row["preferred_label"],
                                    "checks":checks,"attributes":attrs,"trace":trace})
        write(DESTINATION/"results.json",{"version":version,"provisional":True,"cold":result,"replay":replay,"integrity":integrity,
             "typed_alias_gate":counts,"critical_errors":issues["critical"],"predictions":predictions})


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("select","archive","assess"))
    phase = parser.parse_args().phase
    if phase=="select":
        select()
    elif phase=="archive":
        assemble(DESTINATION,1)
    else:
        assess()
