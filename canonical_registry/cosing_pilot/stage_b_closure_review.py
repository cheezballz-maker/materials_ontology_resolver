"""Reconstruct the provisional semantic review with exact source and trace evidence."""

from collections import Counter, defaultdict

from .full_capture import digest, read, write
from .stage_b_closure import OUTPUT
from .stage_b_score import _atom
from .stage_b_v3_cohort import OUTPUT as V3

EU = "https://eur-lex.europa.eu/eli/dec_impl/2025/1175/oj/eng"
IUPAC = "https://iupac.qmul.ac.uk/BriefGuide/inorganic.html"
PO = "https://pubmed.ncbi.nlm.nih.gov/23220694/"
TAXON = "https://www.iaptglobal.org/madrid-code-online"

REFERENCE_GAP = "REFERENCE_ANNOTATION_INCOMPLETE"
SUPPORTED = "SUPPORTED_ASSERTION"
UNSUPPORTED = "UNSUPPORTED_ASSERTION"
AMBIGUOUS = "AMBIGUOUS_OR_INSUFFICIENT_EVIDENCE"

# Reviewed judgments about the 38 concrete persisted extras. The recipes only
# retrieve the corresponding source and interpretation records for audit.
DESCRIPTORS = {
    "INORGANIC_OXIDE_NAME": (UNSUPPORTED,"WHOLE_INGREDIENT",
        "The calcination definition and glossary designate a multicomponent oxide material. The final metal plus oxides is an incomplete substring.",[EU,IUPAC]),
    "INORGANIC_SALT_NAME": (REFERENCE_GAP,"NOMENCLATURE",
        "The whole designation directly reports the silicate family. Formula and stoichiometry remain open.",[IUPAC]),
    "BOTANICAL_PART_GRAMMAR": (REFERENCE_GAP,"SOURCE_MATERIAL_OR_PREPARATION",
        "The definition explicitly reports root bark and the final powder or extract. It supplies no independent taxonomic verification.",[PO,TAXON]),
    "NUMBERED_POLYMER_DESIGNATION": (SUPPORTED,"NOMENCLATURE",
        "The number appears in the designation as a polyglyceryl modifier. The transesterification definition describes the resulting esters. No exact chain length is asserted.",[EU]),
    "SOURCE_SUPPORTED_ETHOXYLATE_GRADE": (REFERENCE_GAP,"NOMENCLATURE",
        "The source definition independently describes the ether or ethoxylation. The qualifier records the reported name or nominal grade. It supplies no single molecular graph or exact composition.",[EU]),
    "SOURCE_CULTURE_MEDIUM_DEFINITION": (REFERENCE_GAP,"FINAL_PREPARATION",
        "The definition identifies harvested culture medium. Its cells, supplements and original medium are source or process context, and the descriptor does not assert final composition.",[EU]),
    "REPORTED_GLYCOLIPID_FAMILY": (REFERENCE_GAP,"REPORTED_MATERIAL_FAMILY",
        "The definition explicitly calls the material glycolipids and separately identifies fermentation inputs.",[EU]),
}

FALLBACK_SCOPE = {
    "SODIUM C12-15 ALKETH-3 SULFONATE", "SODIUM C14-15 ALKETH-PG SULFONATE",
    "COCETH-7 CARBOXYLIC ACID","POLYPERFLUOROETHOXYMETHOXY DIFLUOROETHYL PEG ETHER",
}
FOCUSED = {
    "CITRUS HASSAKU/NATSUDAIDAI FRUIT JUICE": (AMBIGUOUS,"SOURCE_TAXON_ATTACHMENT",
        "Slash designation and fruit wording support a lexical plant part. The taxonomy and its attachment require specialist review. A structured anatomy link is held for compound scope.",[PO,TAXON]),
    "SOLANUM LYCOPERSICON FRUIT JUICE VESICLES": (AMBIGUOUS,"SOURCE_MATERIAL_AND_FINAL_TISSUE",
        "The source fruit and isolated vesicles are different levels. Retain the source language and avoid asserting verified taxon or tissue identity.",[PO,TAXON]),
    "CITRUS SUNKI SEED OIL": (SUPPORTED,"SOURCE_ANATOMY",
        "Seed anatomy has support independent of contradictory preparation wording. Conflicting final form assertions stay withheld.",[PO]),
    "ALUMINUM HYDROXIDE": (REFERENCE_GAP,"NOMENCLATURE",
        "The specific hydroxide predicate captures the explicit naming, although the frozen reference expected the generic salt predicate. The name supplies no independent whole-graph verification.",[IUPAC]),
    "HC BLUE NO. 16": (SUPPORTED,"CANDIDATE_DESIGNATION",
        "The EU glossary explicitly lists this numbered HC designation. Typed or formula aliases do not establish a unique ingredient graph.",[EU]),
    "DIRECT RED 23": (AMBIGUOUS,"WHOLE_INGREDIENT_GRAPH",
        "The designation is recognizable colorant nomenclature. The original competing structure claims do not establish a unique ingredient graph and remain candidate evidence.",[EU]),
}


def evaluate():
    bundle = read(V3/"corrected_predictions.json")
    validation = read(V3/"validation.json")["corrected"]
    predictions = {p["inci_id"]:p for p in bundle["predictions"]}
    references = {p["reference"]["id"]:p for p in read(V3/"reference.json")["records"]}
    parents = {x["parent"]["inci_id"]:x["parent"] for x in read(V3/"cohort.json")["records"]}
    aliases = defaultdict(list)
    for alias in read(V3/"aliases.json"):
        aliases[alias["inci_id"]].append(alias)

    def item(key, outcome, scope, basis, authority):
        p = predictions[key]
        return {"source_key":key,"concept_id":p["concept_id"],"inci":p["name"],
                "source_definition":parents[key]["description"],"original_alias_records":aliases[key],
                "disposition":outcome,"assertion_scope":scope,"basis":basis,"authorities":authority,
                "frozen_reference":references[key]["reference"]["assertions"],
                "review_status":"PROVISIONAL_SOURCE_AND_AUTHORITY_REVIEW"}

    extras = []
    for error in validation["metrics"]["high_risk"]["errors"]:
        if error["issue"]!="attributes":
            continue
        key = error["id"]
        p = predictions[key]
        predicates = {tuple(x) for x in error["extra"]}
        module = next((m for m in p["trace"]["interpretation"]["modules"] if m["module"]==error["module"]),{})
        wanted = {(a["predicate"],str(a["value"]),a["evidence"]["source_reference"],a["method"])
                  for a in module.get("assertions",[]) if _atom(a["predicate"],a["value"]) in predicates}
        seen = set()
        for a in p["attributes"]:
            if (a["predicate"],str(a["value"]),a["source_reference"],a["method"]) not in wanted:
                continue
            atom = _atom(a["predicate"],a["value"])
            if atom in seen:
                continue
            seen.add(atom)
            review = item(key,*DESCRIPTORS[a["method"]])
            review.update(attribute=a,module=error["module"])
            extras.append(review)
    if len(extras)!=38:
        raise ValueError(f"Expected 38 persisted reference extras, found {len(extras)}")

    fallback = []
    for case in validation["review"]["fallback_cases"]:
        if case["outcome"]!="MISSED_INTERPRETATION" or not case["generic"]:
            continue
        if case["name"] in FALLBACK_SCOPE:
            disposition = (AMBIGUOUS,"PRECURSOR_OR_MATERIAL_FAMILY",
                "Definition reports a polymeric or ethoxylated component or synthetic precursor. It does not establish a standalone whole-ingredient ethoxylate designation under the bounded rule.",[EU])
        else:
            disposition = (SUPPORTED,"REPORTED_NOMENCLATURE_GRADE",
                "Standalone designation and source definition support the same nominal average grade. The missing source-supported interpretation is lexical and supplies no graph.",[EU])
        review = item(case["id"],*disposition)
        review.update(frozen_fallback=case["reference"],original_active_modules=case["modules"])
        fallback.append(review)
    if len(fallback)!=14:
        raise ValueError("Frozen fallback disagreement count changed")
    focused = []
    for key,p in predictions.items():
        if p["name"] in FOCUSED:
            review = item(key,*FOCUSED[p["name"]])
            review.update(attributes=p["attributes"],trace=p["trace"]["interpretation"])
            focused.append(review)
    write(OUTPUT/"adjudication.json",{"status":"PROVISIONAL_NO_INDEPENDENT_SPECIALIST",
        "descriptor_extras":extras,"generic_fallback_misses":fallback,"scope_controls":focused,
        "frozen_reference_sha256":digest(V3/"reference.json"),
        "v3_predictions_sha256":digest(V3/"corrected_predictions.json"),
        "counts":{k:dict(Counter(row["disposition"] for row in v)) for k,v in
                  (("descriptor_extras",extras),("generic_fallback_misses",fallback),("scope_controls",focused))}})


if __name__=="__main__":
    evaluate()
