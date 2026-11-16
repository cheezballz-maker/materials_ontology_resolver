"""Compare frozen provisional source annotations with Stage B traces."""

from collections import Counter, defaultdict

from .full_capture import digest, read, write
from .stage_b_cohort import OUTPUT


def _counts(want, got):
    return "UNKNOWN" if want is None else "TP" if want and got else "FN" if want else "FP" if got else "TN"


def _rates(counts):
    tp, fp, fn = (counts[k] for k in ("TP","FP","FN"))
    return {"counts":dict(counts),"precision":tp/(tp+fp) if tp+fp else None,"recall":tp/(tp+fn) if tp+fn else None}


def _atom(predicate,value):
    if isinstance(value,dict) and predicate=="molecular_graph":
        value = value["smiles"]
    return (predicate,value if predicate=="molecular_graph" else " ".join(str(value).casefold().split()))


def _additional_archived_keys():
    root = OUTPUT.parents[2]/"nomenclature_interpretation/evaluation"
    files = [root/"coverage_v1/correction_holdout.json",root/"reliability_v1/population.json",
             *(root/"reliability_v1").glob("challenge_*.json"),*(root/"reliability_v1").glob("confirm_*.json")]
    keys = set()
    for path in files:
        rows = read(path)
        if isinstance(rows,dict):
            rows = rows.get("rows",[])
        keys.update(r["inci_id"] for r in rows if isinstance(r,dict) and "inci_id" in r)
    return keys


def score(bundle, reference, previously_seen, selections=None):
    from .organization import SUPPORTED_DESCRIPTORS

    predictions = {item["inci_id"]:item for item in bundle["predictions"]}
    rows = reference["records"]
    if set(predictions)!={item["reference"]["id"] for item in rows}:
        raise ValueError("Prediction and reference cohort differ")
    modules = sorted(rows[0]["reference"]["routes"])
    scored = {m:{p for row in rows for p,_,_ in row["reference"]["assertions"].get(m,[])} for m in modules}
    groups = {}
    stratified = [r for r in rows if r["cohort"]=="stratified"]
    if selections is None:
        selections = (("all",rows),("stratified",stratified),
                           ("fresh_stratified",[r for r in stratified if r["reference"]["id"] not in previously_seen]),
                           ("challenges",[r for r in rows if r["cohort"]!="stratified"]))
    for name, selected in selections:
        routes, attrs, qualified = defaultdict(Counter),defaultdict(Counter),defaultdict(Counter)
        totals, functions, fallback, errors = Counter(),Counter(),Counter(),[]
        strata, controls = defaultdict(Counter),[]
        for row in selected:
            ref = row["reference"]
            pred = predictions[ref["id"]]
            result = pred["trace"]["interpretation"]
            active = {m["module"]:m for m in result["modules"]}
            slot = strata[row["stratum"]]
            flags = {"records":1,"qualified_attribute_records":bool(pred["attributes"]),
                     "qualified_role_records":bool(pred["roles"]),"generic_fallback":("generic_ingredient" in active),
                     "multiple_specialists":len(set(active)&set(modules))>1,"conflicts":result["state"]=="CONFLICT",
                     "withheld_graph_records":any(a["category"]=="STRUCTURAL" for a in result["withheld_assertions"]),
                     "missing_parent_identifiers":row["missing_parent_identifiers"]}
            for k,value in flags.items():
                totals[k] += value
                slot[k] += value
            totals["qualified_attributes"] += len(pred["attributes"])
            totals["qualified_roles"] += len(pred["roles"])
            totals["reported_roles"] += len(result["functions"])
            totals["retained_graphs"] += sum(a["category"]=="STRUCTURAL" for a in result["assertions"])
            totals["withheld_graphs"] += sum(a["category"]=="STRUCTURAL" for a in result["withheld_assertions"])
            totals["graph_promotion_errors"] += sum(a["category"]=="STRUCTURAL" and a["evidence_role"]!="CANDIDATE_ONLY"
                for a in (*result["assertions"],*result["withheld_assertions"]))
            fallback[_counts(ref["fallback"],"generic_ingredient" in active)] += 1
            persisted = {(a["predicate"],str(a["value"]),a["source_reference"],a["method"])
                         for a in pred["attributes"]}
            for module in modules:
                expected = ref["routes"][module]
                observed = active.get(module)
                outcome = _counts(expected,observed is not None)
                routes[module][outcome] += 1
                if outcome in {"FP","FN"}:
                    errors.append({"id":ref["id"],"name":ref["name"],"module":module,"issue":"route_"+outcome})
                if expected is None:
                    continue
                want = {_atom(p,v) for p,v,_ in ref["assertions"].get(module,[])}
                got = {_atom(a["predicate"],a["value"]) for a in (observed or {}).get("assertions",[])
                       if a["predicate"] in scored[module] and (a["predicate"]!="molecular_graph"
                           or a["method"]=="STRICT_RDKIT_STRUCTURE")}
                attrs[module].update({"TP":len(want&got),"FP":len(got-want),"FN":len(want-got)})
                expected_qualified = {a for a in want if a[0] in SUPPORTED_DESCRIPTORS}
                observed_qualified = {_atom(a["predicate"],a["value"]) for a in (observed or {}).get("assertions",[])
                                      if a["predicate"] in scored[module] and
                                      (a["predicate"],str(a["value"]),a["evidence"]["source_reference"],a["method"]) in persisted}
                qualified[module].update({"TP":len(expected_qualified&observed_qualified),
                                          "FP":len(observed_qualified-expected_qualified),
                                          "FN":len(expected_qualified-observed_qualified)})
                if got!=want:
                    errors.append({"id":ref["id"],"name":ref["name"],"module":module,"issue":"attributes",
                                   "extra":sorted(got-want),"missing":sorted(want-got)})
            for got in result["functions"]:
                expected = next((r for r in ref["roles"] if r["reported_function"]==got["reported_function"]),None)
                if expected is None:
                    functions["unexpected"] += 1
                    continue
                approved = bool(got["qualified_vocabulary_labels"])
                wanted = bool(expected["qualified_vocabulary_labels"])
                functions[_counts(wanted,approved)] += 1
                functions["labels_and_qualification_agree"] += (
                    expected["qualification"]==got["qualification"] and
                    expected["qualified_vocabulary_labels"]==got["qualified_vocabulary_labels"])
            manual = row["manual"]
            if manual:
                checks = {"routes":all(m in active for m in manual.get("routes",[])),
                          "attributes":all(_atom(p,v) in {_atom(a["predicate"],a["value"])
                              for a in active.get(m,{}).get("assertions",[])} for m,p,v in manual.get("attributes",[]))}
                if manual.get("whole_hold"):
                    checks["whole_referent_withheld"] = not any(a["category"]=="STRUCTURAL" for a in result["assertions"])
                if manual.get("preserve_conflict"):
                    checks["conflict_preserved"] = result["state"]=="CONFLICT"
                if "fallback" in manual:
                    checks["fallback"] = ("generic_ingredient" in active)==manual["fallback"]
                controls.append({"id":ref["id"],"name":ref["name"],"checks":checks,"state":result["state"],
                                 "issues":[i["code"] for i in result["issues"]]})
        groups[name] = {"totals":dict(totals),"strata":dict(strata),"roles":_rates(functions),
                        "fallback":_rates(fallback),"routing":{m:_rates(routes[m]) for m in modules},
                        "attributes":{m:_rates(attrs[m]) for m in modules},
                        "persisted_supported_attributes":{m:_rates(qualified[m]) for m in modules},
                        "manual_controls":controls,"errors":errors}
    return groups


def main():
    reference_path = OUTPUT/"reference.json"
    reference = read(reference_path)
    previously_seen = _additional_archived_keys()
    findings = {}
    for mode in ("baseline","corrected"):
        bundle = read(OUTPUT/f"{mode}_predictions.json")
        if bundle["statistics"]["reference_sha256"]!=digest(reference_path):
            raise ValueError("Reference changed after prediction generation")
        findings[mode] = {"statistics":bundle["statistics"],"evaluation":score(bundle,reference,previously_seen)}
    findings["stratified_overlap_with_additional_archives"] = [
        {"inci_id":r["reference"]["id"],"name":r["reference"]["name"]} for r in reference["records"]
        if r["cohort"]=="stratified" and r["reference"]["id"] in previously_seen]
    write(OUTPUT/"validation.json",findings)


if __name__=="__main__":
    main()
