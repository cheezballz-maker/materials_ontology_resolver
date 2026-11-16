"""Prepare registry records and independent review comparisons from bounded CosIng inputs."""

from collections import Counter
from dataclasses import asdict, replace

from canonical_registry.ingredient_equivalence.adapters import from_cosing
from canonical_registry.ingredient_equivalence.engine import compare
from canonical_registry.ingredient_equivalence.evaluate import COSMETIC, _real_ingredients, read
from canonical_registry.ingredient_equivalence.retrieval import CandidateIndex
from canonical_registry.ingredient_equivalence.validate_evidence import load_study
from canonical_registry.nomenclature_interpretation import InterpretationFramework
from canonical_registry.nomenclature_interpretation.contracts import Category, Evidence, EvidenceRole, State
from canonical_registry.nomenclature_interpretation.framework import conflict_dimension
from canonical_registry.nomenclature_interpretation.cosing_preview_adapter import ALIASES, COSMETICS_FUNCTIONS, PARENT, _array

from .registry import COSMETICS, Comparison, Registration, fingerprint

SUPPORTED_DESCRIPTORS = {
    "source_anatomical_structure", "reported_plant_part", "reported_botanical_preparation",
    "reported_biological_category", "reported_polymer_category", "reported_polyether_grade",
    "reported_polymer_designation_number", "reported_lipid_surfactant_qualifier", "reported_colorant_qualifier",
    "reported_preparation_qualifier", "reported_preparation_source_phrase", "reported_source_preparation",
    "reported_oxide_name", "reported_mineral_name", "reported_inorganic_salt_name",
    "reported_inorganic_multimetal_oxide", "reported_inorganic_material_form", "reported_hydration_qualifier",
    "reported_hydroxide_name", "reported_oxidation_state", "reported_preparation_process",
    "reported_inorganic_mixed_designation",
}


def supported_attributes(result):
    return tuple({
        "predicate": a.predicate, "value": a.value, "qualification": "SUPPORTED_SOURCE_DESCRIPTOR",
        "source_reference": a.evidence.source_reference, "reported_text": a.evidence.original_value,
        "method": a.method, "subject":result.designation.source_reference,
        "evidence_qualification":_qualification(a),"evidence_field":a.evidence.field,
        "depends_on":list(a.depends_on),"exclusive_slot":a.exclusive_slot,
    } for a in result.assertions if a.predicate in SUPPORTED_DESCRIPTORS
       and a.evidence_role != EvidenceRole.CANDIDATE_ONLY)


def _qualification(assertion):
    value = assertion.value
    text = " ".join(assertion.evidence.original_value.casefold().split())
    explicit = isinstance(value,str) and " ".join(value.casefold().split()) in text
    return "SOURCE_REPORTED" if explicit else "INTERPRETER_INFERRED"


def assertion_audit(result):
    """Keep reconciliation decisions linked to their original source claims."""
    reviewed = []
    for accepted, assertions in ((True,result.assertions),(False,result.withheld_assertions)):
        for a in assertions:
            slots = {a.exclusive_slot,*a.depends_on}
            relevant = []
            for issue in result.issues:
                dimension = conflict_dimension(issue)
                if (slots.intersection(issue.affected_slots) or a.evidence in issue.evidence or
                        a.category==Category.STRUCTURAL and (issue.conflict or dimension=="WHOLE_REFERENT_ATTRIBUTION"
                            or not accepted and dimension=="STRUCTURAL_GRAPH")):
                    relevant.append({"code":issue.code,"dimension":dimension,"evidence":[asdict(e) for e in issue.evidence]})
            descriptor = a.predicate in SUPPORTED_DESCRIPTORS and a.evidence_role!=EvidenceRole.CANDIDATE_ONLY
            reviewed.append({"subject":result.designation.source_reference,"predicate":a.predicate,"value":a.value,
                 "evidence":asdict(a.evidence),"method":a.method,"qualification":_qualification(a),
                 "evidence_role":a.evidence_role,"depends_on":list(a.depends_on)+(
                     ["structural_graph"] if a.category==Category.STRUCTURAL else []),"exclusive_slot":a.exclusive_slot,
                 "decision":("PERSISTED_DESCRIPTOR" if descriptor else "RETAINED_EVIDENCE") if accepted else "WITHHELD",
                 "diagnostics":relevant})
    return reviewed


def _reviewed_inputs():
    originals = {row["inci_id"]: row for row in read("warehouse.json")}
    return originals, _real_ingredients(InterpretationFramework())


def _apply_review(ingredient, source, aliases, review):
    originals, reviewed = review
    old = originals.get(source["inci_id"])
    original = reviewed.get(source["inci"])
    if not old or not original or original.reference != ingredient.reference or old["inci"] != source["inci"]:
        return ingredient
    if old.get("description") != source.get("description") or any(
        _array(old.get(k)) != _array(source.get(k)) for k in ("cas_nos", "ec_nos")
    ):
        return ingredient
    binding = original.molecular
    if binding and not any(
        binding.structure.evidence.source_reference == f"{ALIASES}:{a['inci_alias_id']}"
        and binding.structure.evidence.original_value == a["alias"]
        and binding.structure.kind.value.upper() == a["alias_type"] for a in aliases
    ):
        binding = None
    return replace(ingredient, families=original.families, designations=original.designations,
                   facets=original.facets, molecular=binding)


def organize(sources, evidence, bridge, mapping):
    framework = InterpretationFramework(name_parser=bridge, function_vocabularies={"cosmetics": COSMETICS_FUNCTIONS})
    prior = _reviewed_inputs()
    registrations, ingredients = [], {}
    for row in sources:
        associated = evidence[row["inci_id"]]
        aliases = _array(associated.get("alias_claims"))
        if len(aliases) != int(associated["alias_count"]):
            raise ValueError("Source typed alias payload was truncated")
        item = from_cosing(row, aliases, COSMETIC, framework)
        lexical = tuple(Evidence(a["alias"], a["alias_type"], f"{ALIASES}:{a['inci_alias_id']}", a["source"])
                        for a in aliases if a["alias_type"] in {"INCI_USA", "INN_ISO_AN", "IUPAC"}
                        and a["alias"] and a["alias"].strip())
        item = replace(item, search_aliases=lexical)
        item = _apply_review(item, row, aliases, prior)
        result = item.interpretation
        attributes = supported_attributes(result)
        roles = tuple(asdict(f) for f in result.functions if f.qualification in {
            "VOCABULARY_VALIDATED", "VOCABULARY_COMPONENTS_VALIDATED"})
        modules = [m.module for m in result.modules]
        attempted = ("molecular_chemical" in modules or any(
            a.category == Category.STRUCTURAL for a in (*result.assertions, *result.withheld_assertions)
        ))
        assessment = mapping.assess(result) if attempted else {"disposition": "NOT_EVALUATED"}
        revision = fingerprint({
            "source": {key: row.get(key) for key in (
                "inci_id", "inci", "description", "cas_nos", "ec_nos", "functions", "data_status")},
            "companion_evidence": associated,
        })
        summary = {
            "cohort": row["cohort"], "stratum": row["stratum"], "modules": modules, "state": result.state,
            "typed_alias_count": len(aliases), "reported_functions": len(result.functions),
            "reported_cas_or_ec": any(v for k in ("cas_nos", "ec_nos") for v in _array(row.get(k))),
            "has_companion_classification": str(associated["has_chemistry"]).lower() == "true",
            "candidate_graphs": sum(a.category == Category.STRUCTURAL for a in result.assertions),
            "generic_fallback": "generic_ingredient" in modules,
            "mapping_preview": assessment,
        }
        trace = {"interpretation": asdict(result), "input_provenance": item.reference}
        registrations.append(Registration(COSMETICS, item.reference, row["inci"], revision, row.get("updated_ts"),
                                         attempted, attributes, roles, summary, trace))
        ingredients[item.reference] = item
    return registrations, ingredients


def review_pairs(ingredients, external_reviews):
    index = CandidateIndex(ingredients.values())
    candidates = set()
    for item in ingredients.values():
        candidates.update(tuple(sorted((item.reference, ref))) for ref, _ in index.find(item, limit=3).matches)
    label_counts = Counter(item.label for item in ingredients.values())
    by_label = {item.label: item.reference for item in ingredients.values() if label_counts[item.label] == 1}
    judgments = {
        tuple(sorted((by_label[c["left"]], by_label[c["right"]]))): c
        for c in read("real_reference.json") if c["left"] in by_label and c["right"] in by_label
    }
    comparisons = []
    for left, right in sorted(candidates | judgments.keys()):
        result = compare(ingredients[left], ingredients[right])
        ref = judgments.get((left, right))
        review = None if ref is None else {
            "reference": ref["id"], "expected": ref["expected"], "basis": ref["basis"],
            "agrees": result.verdict == ref["expected"], "status": "PRIOR_PROVISIONAL_REFERENCE",
        }
        comparisons.append(Comparison(left, right, result.verdict, {
            "assessment": asdict(result), "retrieved": (left, right) in candidates,
            "review": review,
        }))
    if external_reviews:
        food, _, _, _ = load_study(None)
    from canonical_registry.ingredient_equivalence.contracts import Facet, Qualification
    for review in external_reviews:
        original = ingredients.get(review["local_source"])
        if original is None or original.molecular is None:
            continue
        external = food[review["external_source"]]
        material = next((f for f in external.facets if f.field == "material" and f.value == review["material"]), None)
        if material is None or original.molecular.structure.evidence.source_reference != review["required_structure"]:
            continue
        local_facet = Facet(original.reference, "material", material.scheme, material.value, Qualification.DESCRIPTIVE,
                            Evidence(review["basis"], "reviewed material correspondence", review["source"]))
        result = compare(replace(original, facets=(*original.facets, local_facet)), external)
        comparisons.append(Comparison(original.reference, external.reference, result.verdict, {
            "assessment": asdict(result), "retrieved": False,
            "review": {**review, "agrees": result.verdict == review["expected"],
                       "status": "PROVISIONAL_CROSS_SCOPE_REVIEW"},
        }, fingerprint(asdict(external))))
    return comparisons, len(candidates)


def coverage(registrations):
    result = Counter()
    for r in registrations:
        s = r.summary
        result["records"] += 1
        for key, predicate in {
            "supported_descriptors": bool(r.attributes),
            "generic_fallback": s["generic_fallback"],
            "qualified_functions": bool(r.roles),
            "reported_functions": bool(s["reported_functions"]),
            "canonical_assessment_attempted": r.attempted,
            "typed_alias_evidence": bool(s["typed_alias_count"]),
            "has_companion_classification": s["has_companion_classification"],
            "structural_or_interpretation_conflict": s["state"] == State.CONFLICT,
            "multiple_specialist_routes": len([m for m in s["modules"] if m != "generic_ingredient"]) > 1,
            "missing_reported_cas_and_ec": not s["reported_cas_or_ec"],
            "validated_existing_target_proposals": s["mapping_preview"]["disposition"] == "PROPOSED_EXISTING_TARGET",
            "preliminarily_eligible": bool(s["mapping_preview"].get("eligibility")),
        }.items():
            result[key] += int(predicate)
    return dict(result)
