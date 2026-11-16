"""Freeze source references and score monitored Stage B outputs."""

from collections import Counter
from math import sqrt
import argparse
import re

from .full_capture import digest, read, write
from .stage_b_score import score
from .stage_b_v2_cohort import OUTPUT as V2
from .stage_b_v2_evidence import verified
from .stage_b_v2_score import _review
from .stage_b_v3 import COHORT, MANIFEST, POLICY, REFERENCE
from .stage_b_v3_cohort import OUTPUT

FALLBACK_NEGATIVES = {
    "ZINC DNA","SODIUM RNA","ARGININE DNA","GLYCOL ROSINATE",
    "PALMITOYL PG-TRIMONIUM CHLORIDE","ISOPROPYL HYDROXYCETYL ETHER",
    "SODIUM STEAROAMPHOHYDROXYPROPYLSULFONATE","ISOSTEARYL ETHYLDIMONIUM CHLORIDE",
    "HYDROXYPROPYL BISOLEYLDIMONIUM CHLORIDE","PHYTOSPHINGOSINE CYCLIC PHOSPHATE HCL",
}
KNOWN_ROUTES = {
    "SORBETH-7":"lipid_surfactant","RHAMNOLIPIDS":"lipid_surfactant","HC BLUE NO. 16":"colorant",
    "GLYCINE SOJA HULL":"botanical","POLYURETHANE-46":"polymer_silicone",
}


def _defined_routes(parent):
    name, definition = parent["inci"],parent["description"] or ""
    routes = set()
    if re.search(r"\b(?:obtained by (?:the )?fermentation|filtrates? of|aqueous (?:solution|preparation) of (?:the )?steam distillates?|hydrolysate of)\b",definition,re.I):
        routes.add("preparation_mixture")
    if re.search(r"\b(?:glycolipids?|ethoxylated|polyethylene glycol ether)\b",definition,re.I):
        routes.add("lipid_surfactant")
    if re.search(r"\bconditioned medi[au]\b",name,re.I) and re.search(r"growth media removed from cultures",definition,re.I):
        routes.add("biological_biotechnological")
    if re.fullmatch(r"HC [A-Z]+ (?:NO\.?\s*)?\d+",name,re.I):
        routes.add("colorant")
    return routes


def freeze():
    from rdkit import rdBase
    from canonical_registry.nomenclature_interpretation.reliability_reference import annotate

    if REFERENCE.exists():
        raise FileExistsError("The v3 references are frozen")
    _,aliases,_,_ = verified(OUTPUT)
    control = read(V2/"review_protocol.json")["controls"]
    references = []
    with rdBase.BlockLogs():
        for item in read(COHORT)["records"]:
            parent, cohort = item["parent"],item["cohort"]
            ref = annotate({**parent,"stratum":item["stratum"].upper(),"alias_claims":aliases[parent["inci_id"]]})
            typed = bool(ref["assertions"].get("molecular_chemical"))
            if not typed:
                ref["routes"]["molecular_chemical"]=None
            for role in ref["roles"]:
                if role["reported_function"].strip().upper()=="PERFUMING":
                    role.update(qualification="VOCABULARY_VALIDATED",qualified_vocabulary_labels=["PERFUMING"])
            manual = control.get(parent["inci"],{}).copy() if cohort in {"development","regression"} else {}
            facts = list(manual.get("facts",[]))
            if re.fullmatch(r"POLYURETHANE-\d+",parent["inci"],re.I):
                facts.extend([["polymer_silicone","reported_polymer_category","polyurethane"],
                              ["polymer_silicone","reported_polymer_designation_number",parent["inci"]]])
                manual["whole_hold"]=True
            required = set(manual.get("routes",[]))|{m for m,_,_ in facts}|_defined_routes(parent)
            if parent["inci"] in KNOWN_ROUTES:
                required.add(KNOWN_ROUTES[parent["inci"]])
            if (item["challenge"] or "").startswith("fallback_"):
                explicit = set(required)
                if typed:
                    explicit.add("molecular_chemical")
                if not explicit:
                    explicit.update(m for m,v in ref["routes"].items() if v is True and m!="molecular_chemical")
                if explicit:
                    expected,basis = "SPECIALIST","Explicit source definition, typed candidate or recognized nomenclature facet."
                elif parent["inci"] in FALLBACK_NEGATIVES:
                    expected,basis = "FALLBACK","Sparse packet with no supported specialist scope in the bounded interpretation contract."
                else:
                    expected,basis = "UNKNOWN","Insufficient source evidence to adjudicate a specialist or fallback."
                manual["fallback_review"]={"expected":expected,"routes":sorted(explicit),"basis":basis}
                ref["fallback"]={"SPECIALIST":False,"FALLBACK":True,"UNKNOWN":None}[expected]
            for m in required:
                ref["routes"][m]=True
            for m,p,v in facts:
                old = ref["assertions"].setdefault(m,[])
                if not any(x==p and str(y).casefold()==str(v).casefold() for x,y,_ in old):
                    old.append([p,v,"SOURCE_REVIEW_CONTROL"])
            if "fallback" in manual:
                ref["fallback"]=manual["fallback"]
            elif required and "fallback_review" not in manual:
                ref["fallback"]=False
            manual["routes"],manual["facts"]=sorted(required),facts
            references.append({"cohort":cohort,"stratum":item["stratum"],"challenge":item["challenge"],
              "required_routes":sorted(required),"reference":ref,"manual":manual,
              "missing_parent_identifiers":not any(parent[k] for k in ("cas_nos","ec_nos"))})
    write(REFERENCE,{"status":"FROZEN_PROVISIONAL_NO_INDEPENDENT_REVIEWER","manifest_sha256":digest(MANIFEST),
                     "policy_sha256":digest(POLICY),"records":references})


def _weighted_coverage(bundle,cohort):
    population = cohort["representative_sampling_frame"]
    rows = [p for p in bundle["predictions"] if p["cohort"]=="representative"]
    total = sum(population.values())
    estimate, variance, samples = 0.0,0.0,{}
    for s,pop in population.items():
        values = [bool(r["attributes"]) for r in rows if r["stratum"]==s]
        n = len(values)
        observed = sum(values)/n
        weight = pop/total
        estimate += weight*observed
        variance += weight**2*(1-n/pop)*observed*(1-observed)/(n-1)
        samples[s]={"population":pop,"sample":n,"with_descriptors":sum(values)}
    width = 1.96*sqrt(variance)
    return {"estimate":estimate,"design_approx_95_interval":[max(0,estimate-width),min(1,estimate+width)],
            "scope":"available representative sampling frame only","strata":samples}


def evaluate():
    reference = read(REFERENCE)
    rows = reference["records"]
    cohort = read(COHORT)
    output = {}
    for phase in ("baseline","corrected"):
        path = OUTPUT/f"{phase}_predictions.json"
        bundle = read(path)
        if bundle["statistics"]["reference_sha256"]!=digest(REFERENCE):
            raise ValueError("Frozen reference changed")
        selections = [("all",rows),*((group,[r for r in rows if r["cohort"]==group])
                                     for group in ("representative","high_risk","regression","development"))]
        selections.extend((f"representative:{s}",[r for r in rows if r["cohort"]=="representative" and r["stratum"]==s])
                          for s in cohort["representative_quotas"])
        keyed = {r["reference"]["id"]:r for r in rows}
        selections.extend((f"batch:{batch}",[keyed[r["inci_id"]] for r in bundle["predictions"] if r["batch"]==batch])
                          for batch in sorted({r["batch"] for r in bundle["predictions"]}))
        output[phase]={"statistics":bundle["statistics"],"metrics":score(bundle,reference,(),selections),
             "review":_review(bundle,reference),"batches":bundle["batches"],"weighted_descriptor_coverage":_weighted_coverage(bundle,cohort)}
    output["critical_errors"]=output["corrected"]["review"]["critical_errors"]
    output["predictions_sha256"]=digest(OUTPUT/"corrected_predictions.json")
    if output["baseline"]["statistics"]["version"]==output["corrected"]["statistics"]["version"]:
        raise ValueError("Policy change did not invalidate the prior cache version")
    write(OUTPUT/"validation.json",output)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("freeze","evaluate"))
    if parser.parse_args().phase=="freeze":
        freeze()
    else:
        evaluate()
