"""Validate Stage B claims against source evidence and reconciliation decisions."""

from collections import Counter
import re

from canonical_registry.nomenclature_interpretation.cosing_preview_adapter import ALIASES
from canonical_registry.nomenclature_interpretation.specialists import Botanical

from .organization import SUPPORTED_DESCRIPTORS
from .registry import canonical

IDENTITY_PREDICATES = {"molecular_graph","reported_taxon_text","reported_taxon_rank",
                       "canonical_identity","substance_id","chemical_concept_id"}


def _source_values(parent, aliases, reference):
    values = {(reference,parent[k]) for k in ("inci","description") if parent[k]}
    values.update((reference,v) for k in ("cas_nos","ec_nos","functions") for v in (parent[k] or []) if v)
    values.update((f'{ALIASES}:{a["inci_alias_id"]}',a["alias"]) for a in aliases)
    return values


def _key(claim):
    return claim["predicate"],canonical(claim["value"]),claim["method"]


def check(row, parent, aliases, prediction, manifest_hash, version):
    failures = set()
    review = set()
    if row["source_reference"].partition(":")[2]!=parent["inci_id"] or prediction["concept_id"]!=row["concept_id"]:
        failures.add("BINDING")
    if not row["present"] or row["continuity_hold"] or not (
        prediction["revision"]==row["observed_revision"]==row["registered_revision"]
    ):
        failures.add("REVISION")
    if prediction["version"]!=version or prediction["summary"].get("stage")!="INTERPRETATION":
        failures.add("VERSION")
    trace = prediction["trace"]
    provenance = trace["companion_evidence"]
    if (provenance["manifest_sha256"]!=manifest_hash or provenance["parent_revision"]!=row["observed_revision"]
            or sorted(provenance["used_original_alias_ids"])!=sorted(a["inci_alias_id"] for a in aliases)):
        failures.add("EVIDENCE")
    interpretation = trace["interpretation"]
    if (interpretation["designation"]["source_reference"],interpretation["designation"]["original_value"])!=(
            row["source_reference"],parent["inci"]):
        failures.add("BINDING")
    allowed = _source_values(parent,aliases,row["source_reference"])
    retained, withheld = interpretation["assertions"],interpretation["withheld_assertions"]
    for claim in (*retained,*withheld,*interpretation["functions"]):
        ev = claim["evidence"]
        if (ev["source_reference"],ev["original_value"]) not in allowed:
            failures.add("EVIDENCE")
    structures = [a for a in (*retained,*withheld) if a["category"]=="STRUCTURAL"]
    guarded = (interpretation["state"]=="CONFLICT" or
               any(m["whole_referent_graph_unestablished"] for m in interpretation["modules"]) or
               any(a["type"] in {"SMILES","INCHI","INCHI_KEY","MOLECULAR_FORMULA"} for a in provenance["held_aliases"]))
    if (any(a["evidence_role"]!="CANDIDATE_ONLY" for a in structures) or
            guarded and any(a["category"]=="STRUCTURAL" for a in retained)):
        failures.add("WHOLE_REFERENT")
    if any(a["predicate"] in {"reported_taxon_text","reported_taxon_rank"} and
           a["evidence_role"]!="CANDIDATE_ONLY" for a in (*retained,*withheld)):
        failures.add("MATERIAL_SCOPE")
    blocked = {s for i in interpretation["issues"] if i["conflict"] for s in i["affected_slots"]}
    if any(a["exclusive_slot"] in blocked or blocked.intersection(a["depends_on"]) for a in retained):
        failures.add("CONFLICT_ISOLATION")
    allowlisted = {_key(a) for a in retained if a["predicate"] in SUPPORTED_DESCRIPTORS and
                   a["evidence_role"]!="CANDIDATE_ONLY"}
    actual = {_key(a) for a in prediction["attributes"]}
    audit = {_key(a) for a in trace["assertion_audit"] if a["decision"]=="PERSISTED_DESCRIPTOR"}
    if actual!=allowlisted or actual!=audit:
        failures.add("CONFLICT_ISOLATION")
    for descriptor in prediction["attributes"]:
        if descriptor["predicate"] in IDENTITY_PREDICATES or descriptor["subject"]!=row["source_reference"]:
            failures.add("MATERIAL_SCOPE")
        if descriptor["predicate"] in {"reported_mineral_name","reported_oxide_name"} and (
            re.search(r"\b(?:extract|filtrate|ferment|preparation)\s*$",parent["inci"],re.I) or
            re.search(r"\bsurface[- ]treated with\b",parent["description"] or "",re.I)
        ):
            failures.add("MATERIAL_SCOPE")
        if (descriptor["source_reference"],descriptor["reported_text"]) not in allowed:
            failures.add("EVIDENCE")
        value = descriptor["value"]
        text = " ".join(descriptor["reported_text"].casefold().split())
        explicit = isinstance(value,str) and " ".join(value.casefold().split()) in text
        expected = "SOURCE_REPORTED" if explicit else "INTERPRETER_INFERRED"
        if descriptor["qualification"]!="SUPPORTED_SOURCE_DESCRIPTOR" or descriptor["evidence_qualification"]!=expected:
            failures.add("QUALIFICATION")
        if descriptor["predicate"]=="source_anatomical_structure":
            codes = {f"http://purl.obolibrary.org/obo/PO_{code}" for part,code in Botanical._parts.items()
                     if re.search(rf"\b{re.escape(part)}\b",text)}
            if value not in codes:
                failures.add("QUALIFICATION")
    for role in prediction["roles"]:
        if (not role["qualified_vocabulary_labels"] or not role["vocabulary_reference"] or
                not role["qualification"].startswith("VOCABULARY_")):
            failures.add("QUALIFICATION")
    if withheld or interpretation["state"]=="CONFLICT":
        review.add("WITHHELD_OR_CONFLICTING_EVIDENCE")
    if "generic_ingredient" in prediction["summary"]["modules"]:
        review.add("GENERIC_FALLBACK")
    if provenance["held_aliases"]:
        review.add("SOURCE_ALIAS_HOLDS")
    return sorted(failures),sorted(review)


def decision(checks):
    unsafe = [r for r in checks if r["failures"]]
    unavailable = [r for r in checks if r.get("retry")]
    failed = Counter(code for row in unsafe for code in row["failures"])
    affected = Counter(family for row in unsafe for family in row.get("interpreter_families",[])
                       if {"MATERIAL_SCOPE","WHOLE_REFERENT","CONFLICT_ISOLATION"}.intersection(row["failures"]))
    held_families = sorted(f for f,n in affected.items() if n>1)
    global_stop = bool(set(failed)&{"REGISTRY","TRANSACTION","VERSION","EVIDENCE"})
    return {"decision":"REJECT" if unsafe else "HOLD" if unavailable else "ACCEPT",
            "critical_checks":dict(failed),"quarantine":unsafe,
            "retry_records":unavailable,"review_required":[r for r in checks if r["review"]],
            "held_families":held_families,
            "eligible_for_rebatch":[r["id"] for r in checks if not global_stop and (unsafe or unavailable) and
                not r["failures"] and not r.get("retry") and not set(held_families).intersection(r.get("interpreter_families",[]))]}
