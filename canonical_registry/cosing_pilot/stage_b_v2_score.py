"""Score the frozen v2 reference and enforce the bounded identity-safety gate."""

from collections import Counter, defaultdict

from .full_capture import digest, read, write
from .stage_b_score import _atom, score
from .stage_b_v2 import REFERENCE
from .stage_b_v2_cohort import OUTPUT


def _descriptor_abstentions(bundle,rows):
    from .organization import SUPPORTED_DESCRIPTORS

    predictions = {r["inci_id"]:r for r in bundle["predictions"]}
    counts = defaultdict(Counter)
    for row in rows:
        ref = row["reference"]
        pred = predictions[ref["id"]]
        trace = pred["trace"]
        kept = {_atom(a["predicate"],a["value"]) for a in pred["attributes"]}
        explained = {_atom(a["predicate"],a["value"]) for a in trace.get("assertion_audit",[])
                     if a["decision"]=="WITHHELD" and a["diagnostics"]}
        for module,outcome in ref["routes"].items():
            if outcome is None:
                continue
            expected = {_atom(p,v) for p,v,_ in ref["assertions"].get(module,[]) if p in SUPPORTED_DESCRIPTORS}
            missing = expected-kept
            counts[module].update({"expected_descriptors":len(expected),
                  "withheld_with_diagnostic":len(missing&explained),
                  "missing_without_local_diagnostic":len(missing-explained)})
    return dict(counts)


def _review(bundle,reference):
    predictions = {r["inci_id"]:r for r in bundle["predictions"]}
    manual_cases,fallback_cases,critical,isolations = [],[],[],[]
    for row in reference["records"]:
        ref, manual = row["reference"],row["manual"]
        pred = predictions[ref["id"]]
        interpretation = pred["trace"]["interpretation"]
        retained = interpretation["assertions"]
        withheld = interpretation["withheld_assertions"]
        modules = {m["module"]:m for m in interpretation["modules"]}
        graph_retained = [a for a in retained if a["category"]=="STRUCTURAL"]
        whole_guard = any(m["whole_referent_graph_unestablished"] for m in modules.values())
        if any(a["evidence_role"]!="CANDIDATE_ONLY" for a in (*retained,*withheld) if a["category"]=="STRUCTURAL"):
            critical.append([ref["id"],ref["name"],"PROMOTED_GRAPH"])
        if graph_retained and (whole_guard or manual.get("whole_hold") or interpretation["state"]=="CONFLICT"):
            critical.append([ref["id"],ref["name"],"UNSAFE_WHOLE_REFERENT_GRAPH"])
        if any(a["predicate"]=="molecular_graph" for a in pred["attributes"]):
            critical.append([ref["id"],ref["name"],"PERSISTED_MOLECULAR_IDENTITY"])
        if any(manual.get(k) for k in ("facts","persist","absent","whole_hold","conflict","not_polyurethane")):
            checks = {}
            if manual["routes"]:
                checks["routes"] = all(m in modules for m in manual["routes"])
            if manual["facts"]:
                checks["extracted_facts"] = all(_atom(p,v) in {_atom(a["predicate"],a["value"])
                    for a in modules.get(m,{}).get("assertions",[])} for m,p,v in manual["facts"])
            if manual.get("persist"):
                checks["persisted_descriptors"] = set(manual["persist"])<={a["predicate"] for a in pred["attributes"]}
            if manual.get("absent"):
                checks["unsupported_predicates_absent"] = not set(manual["absent"]).intersection(a["predicate"] for a in retained)
            if manual.get("not_polyurethane"):
                checks["not_polyurethane"] = not any(a["predicate"]=="reported_polymer_category" and
                    str(a["value"]).casefold()=="polyurethane" for a in retained)
            if manual.get("whole_hold"):
                checks["whole_scope_protected"] = not graph_retained
            if manual.get("conflict"):
                checks["conflict_preserved"] = interpretation["state"]=="CONFLICT"
            manual_cases.append({"id":ref["id"],"name":ref["name"],"cohort":row["cohort"],"checks":checks})
        if review := manual.get("fallback_review"):
            expected = review["expected"]
            generic = "generic_ingredient" in modules
            supports = all(any(a["category"]!="IDENTIFIER" or a["method"]!="REPORTED_IDENTIFIER"
                               for a in modules.get(m,{}).get("assertions",[])) for m in review["routes"])
            if expected=="UNKNOWN":
                outcome = "UNADJUDICATED"
            elif expected=="FALLBACK":
                outcome = "CORRECT_FALLBACK" if generic else "INCORRECT_SPECIALIST_ACTIVATION"
            else:
                outcome = "SUPPORTED_SPECIALIST" if supports else "MISSED_INTERPRETATION"
            fallback_cases.append({"id":ref["id"],"name":ref["name"],"cohort":row["cohort"],
                                   "reference":review,"generic":generic,"outcome":outcome,"modules":sorted(modules)})
        if interpretation["state"]=="CONFLICT":
            isolated = {a["predicate"] for a in pred["attributes"]}
            isolations.append({"id":ref["id"],"name":ref["name"],"persisted_descriptors":sorted(isolated),
                "withheld_graphs":sum(a["category"]=="STRUCTURAL" for a in withheld),
                "withheld_nonstructural":sorted({a["predicate"] for a in withheld if a["category"]!="STRUCTURAL"}),
                "diagnostics":[i["code"] for i in interpretation["issues"]]})
    return {"critical_errors":critical,"manual_cases":manual_cases,"fallback_cases":fallback_cases,
            "fallback_outcomes":dict(Counter(r["outcome"] for r in fallback_cases)),"conflict_isolation":isolations}


def main():
    reference = read(REFERENCE)
    rows = reference["records"]
    selections = [("all",rows),*((k,[r for r in rows if r["cohort"]==k])
                                 for k in ("fresh_stratified","fresh_challenge","regression"))]
    strata = sorted({r["stratum"] for r in rows if r["cohort"]=="fresh_stratified"})
    selections.extend((f"fresh_stratum:{stratum}",[r for r in rows if
        r["cohort"]=="fresh_stratified" and r["stratum"]==stratum]) for stratum in strata)
    output = {}
    for phase in ("baseline","corrected"):
        bundle = read(OUTPUT/f"{phase}_predictions.json")
        if bundle["statistics"]["reference_sha256"]!=digest(REFERENCE):
            raise ValueError("Reference changed after prediction")
        output[phase] = {"statistics":bundle["statistics"],"metrics":score(bundle,reference,(),selections),
                         "descriptor_abstentions":{label:_descriptor_abstentions(bundle,selected)
                                                     for label,selected in selections},
                         "review":_review(bundle,reference)}
    old,new = output["baseline"]["statistics"],output["corrected"]["statistics"]
    if old["version"]==new["version"]:
        raise ValueError("Corrected policy reused the baseline cache version")
    output["critical_errors"] = output["corrected"]["review"]["critical_errors"]
    output["historical_safety_preserved"] = (old["integrity"]["core_hashes"]==new["integrity"]["core_hashes"]
        and old["integrity"]["canonical_statuses"]==new["integrity"]["canonical_statuses"]
        and old["integrity"]["historical_assessments"]==new["integrity"]["historical_assessments"]
        and old["integrity"]["canonical_targets"]==new["integrity"]["canonical_targets"]
        and not output["critical_errors"])
    output["corrected_sha256"] = digest(OUTPUT/"corrected_predictions.json")
    write(OUTPUT/"validation.json",output)


if __name__=="__main__":
    main()
