"""Pre-admission scope and identifier checks for Stage C correspondence."""

from dataclasses import replace
import re
from time import perf_counter

from rdkit import Chem
from canonical_registry.authoritative_lookup.lookup import _reconcile_record
from canonical_registry.chemistry import describe, parse
from canonical_registry.identity_sufficiency.contract import Claim, WHOLE, digest, structure_signature
from identity_comparator import compare

VERSION = "stage-c-source-identity-safety-v1"
FORM_VERSION = "stage-c-source-identity-safety-v2"
ESTER = Chem.MolFromSmarts("[CX3](=[OX1])[OX2][#6]")
BASIC_SITE = Chem.MolFromSmarts("[$([NX3;!$(N-C=O);!$(N-S=O)]),$([nH0;+0])]")
ASSOCIATION = re.compile(r"\b(?:salt|ion pair|complex|adduct|hydrate|solvate|mixture)\b", re.I)
V4_SCOPE = re.compile(
    r"\b(?:reaction products? (?:with|of)|average molar ratio|doped|"
    r"(?:C\s*)?\d{1,2}\s*[-–]\s*\d{1,2}\s+(?:alkyl|alkan\w+|alkox\w+|fatty)|"
    r"(?:mixture|blend) of|esters? of a mixture)\b", re.I)
FORM_COMPETITION = {"COMPETING_AUTHORITY_STRUCTURAL_FORMS", "ALTERNATE_FORM_NAME_CANDIDATE_UNRESOLVED"}
FORM_CONFLICT = {"SOURCE_AND_AUTHORITY_CLAIMS_DISAGREE", "CONFLICTING_STRUCTURE_DIMENSIONS",
                 "CONTRADICTORY_EXCLUSIVE_ASSERTIONS", "INCHIKEY_DISAGREES_WITH_ALL_GRAPHS"}
SCOPE_SIGNALS = (
    ("VARIABLE_COMPOSITION_OR_DISTRIBUTION", re.compile(
        r"\b(?:is (?:an? |the )?(?:mixture|blend|extract|preparation|copolymer)\s+(?:of|from)|"
        r"(?:(?:di|tri|tetra|poly)?esters?|salts?|products?)\b[^.;]{0,100}\bbranched[- ]chain\s+[\w -]+\s+acids\b|"
        r"(?:mixture|distribution|series)\s+of\s+(?:constitutional |structural |stereo)?(?:isomers|homologues|homologs)|"
        r"variable (?:composition|proportions))\b", re.I)),
    ("CONSTITUENT_OR_REPRESENTATIVE_STRUCTURE", re.compile(
        r"\b(?:representative|idealized|illustrative) (?:molecular |chemical )?(?:structure|graph|formula)\b", re.I)),
    ("MULTIPLE_POSSIBLE_CHEMICAL_FORMS", re.compile(
        r"\b(?:anhydrous (?:or|and) (?:the )?hydrat\w+|either (?:stereo)?isomer)\b", re.I)),
)
# Common branched-chain descriptors can encode a single branch convention in a
# parser while naming a feedstock class in a material designation. This is a
# proof obligation, with an escape for a revision-bound whole specification.
OPEN_BRANCH = re.compile(
    r"\b(?:di|tri|tetra|poly)?iso(?:oct|non|dec|undec|dodec|tridec|tetradec|"
    r"pentadec|hexadec|heptadec|octadec|nonadec|eicos|cet|stear)[a-z]+\b", re.I)


def scope_observations(evidence, designation):
    rows = []
    for claim in evidence.claims:
        if claim.kind != "DEFINITION" or not claim.qualified("SOURCE_RECORD"):
            continue
        for category, pattern in SCOPE_SIGNALS:
            if match := pattern.search(claim.value):
                rows.append({"category": category, "claim_id": claim.claim_id, "text": match[0]})
    if match := OPEN_BRANCH.search(designation):
        rows.append({"category": "SCOPE_UNESTABLISHED", "claim_id": "designation", "text": match[0],
                     "obligation": "SOURCE_BOUND_EXACT_BRANCH_SPECIFICATION_REQUIRED"})
    return rows


def exact_scope_specification(evidence, graph):
    for c in evidence.claims:
        if (c.kind not in {"SMILES", "INCHI"} or c.scope != WHOLE or c.entity != evidence.referent or
                not c.qualified("STRUCTURE", "REFERENT", "SPECIFICATION") or
                (c.binding_revision or c.revision) != evidence.source_revision):
            continue
        try:
            if structure_signature(describe(c.value, c.kind.lower())) == structure_signature(graph):
                return c.claim_id
        except (ValueError, RuntimeError):
            continue
    return None


def identifier_observations(source, graph, candidates, authorities, references, *, exact_reference=False):
    observations = []
    for namespace, values in sorted(source.identifiers.items()):
        if len(values) > 1:
            observations.append({"category": "SOURCE_IDENTIFIER_SCOPE_AMBIGUOUS", "namespace": namespace,
                                 "values": values, "basis": "MULTIPLE_REPORTED_VALUES"})
            continue
        for value in values:
            linked = [c for c in candidates if f"REPORTED_IDENTIFIER:{namespace}:{value}" in c["routes"]]
            matches = []
            for candidate in linked:
                for record in authorities.get(candidate["source_id"], ()):
                    if record.identifiers.get(namespace) != (value,):
                        continue
                    other, issue = _reconcile_record(record, candidate)
                    if not issue:
                        matches.append((record, other))
            for record, other in matches:
                exact = structure_signature(graph) == structure_signature(other)
                comparison = compare(graph, other) if not exact else None
                observations.append({"category": "CONSISTENT_EXACT_IDENTITY" if exact else "DISTINCT_CHEMICAL_FORMS",
                                     "namespace": namespace, "value": value, "authority": record.authority,
                                     "entity": record.entity, "document": record.document,
                                     "provenance": record.provenance, "signature": structure_signature(other),
                                     "comparison": comparison and comparison["assessment"]})
            ref = references.get(value) if namespace == "CAS" else None
            if ref and ref.get("status") == "STRUCTURAL_REFERENCE" and ref.get("cas") == value:
                try:
                    reference_graph = describe(ref.get("inchi") or "", "inchi")
                except (ValueError, RuntimeError):
                    reference_graph = None
                if not reference_graph or reference_graph["inchikey"] != ref["inchikey"]:
                    observations.append({"category": "INSUFFICIENT_CORRESPONDENCE", "namespace": namespace,
                                         "value": value, "basis": "INVALID_OR_MISSING_REFERENCE_STRUCTURE", "reference": ref})
                    continue
                different = reference_graph["inchikey"] != graph["inchikey"]
                exact = exact_reference and not different and compare(graph, reference_graph)["assessment"] == "EXACT"
                observations.append({"category": "CONFLICTING_IDENTITY_ASSERTIONS" if different else
                                     "CONSISTENT_EXACT_IDENTITY" if exact else "INSUFFICIENT_CORRESPONDENCE",
                                     "namespace": namespace, "value": value,
                                     "basis": "NIST_SPECIES_CAS_FULL_STANDARD_KEY", "reference": ref})
            elif not matches:
                observations.append({"category": "INSUFFICIENT_CORRESPONDENCE", "namespace": namespace, "value": value,
                                     "basis": "NO_QUALIFIED_IDENTIFIER_STRUCTURE"})
    return observations


def form_evidence(source, graph, receipt, specification, identifiers, scopes, name_parser):
    """Decide whether the original source revision selects the represented form."""
    evidence = source.evidence
    signals = []
    mol = parse(graph["smiles"])
    if mol.HasSubstructMatch(ESTER) and mol.HasSubstructMatch(BASIC_SITE):
        signals.append("COVALENT_ESTER_WITH_BASIC_SITE")
    if graph["components"] > 1 or any(atom.GetFormalCharge() for atom in mol.GetAtoms()):
        signals.append("COMPONENT_OR_CHARGE_SPECIFICATION_REQUIRED")
    if ASSOCIATION.search(evidence.designation):
        signals.append("ASSOCIATION_OR_FORM_DESIGNATION")
    binding = (receipt or {}).get("assertion_type")
    if binding == "AUTHORITY_PREFERRED_NAME_AND_SOURCE_GRAPH" and (receipt or {}).get("authority") == "PubChem":
        signals.append("COMPUTED_AUTHORITY_NAME_AND_PARSER_GRAPH")

    supporting = (receipt or {}).get("supporting_source_evidence", {})
    typed = supporting.get("matching_identifiers", {})
    qualified_id = next((r for r in identifiers if r["category"] == "CONSISTENT_EXACT_IDENTITY"
                         and source.identifiers.get(r["namespace"]) == (r["value"],)), None)
    if specification:
        basis = {"kind": "REVISION_BOUND_WHOLE_STRUCTURE", "claim": specification}
    elif qualified_id or (typed and binding in {"PREFERRED_NAME_AND_TYPED_IDENTIFIER",
                                               "SOURCE_DEFINITION_AND_TYPED_IDENTIFIER",
                                               "NATIVE_TYPED_IDENTIFIER_AND_SOURCE_GRAPH"}):
        basis = {"kind": "QUALIFIED_EXACT_FORM_IDENTIFIER", "observation": qualified_id, "linked_identifiers": typed}
    elif source.definition and name_parser and signals and not scopes:
        # Parse the complete source definition only. Free prose or a truncated
        # formula reference cannot qualify as a systematic molecular name.
        definition = next((c for c in evidence.claims if c.kind == "DEFINITION" and c.entity == evidence.referent
                           and c.qualified("SOURCE_RECORD") and c.revision == evidence.source_revision
                           and c.value == source.definition and c.value.casefold() != evidence.designation.casefold()), None)
        parsed = name_parser(definition.value) if definition and len(definition.value) <= 350 else {}
        try:
            exact_definition = (parsed.get("status") == "SUCCESS" and
                                compare(graph, describe(parsed["smiles"]))["assessment"] == "EXACT")
        except (ValueError, RuntimeError, KeyError):
            exact_definition = False
        basis = {"kind": "EXACT_SYSTEMATIC_SOURCE_DEFINITION", "claim": definition.claim_id} if exact_definition else None
    else:
        basis = None
    if basis is None and not signals and binding:
        basis = {"kind": "EXISTING_QUALIFIED_WHOLE_REFERENT", "binding": binding}
    return {"signals": signals, "positive_form_basis": basis}


class SourceIdentitySafety:
    """Re-evaluate scoped evidence before the existing matching/write path."""

    def __init__(self, lookup, evaluator, references, *, form_gate=False, name_parser=None):
        self.lookup = lookup
        self.evaluator = evaluator
        self.authorities = lookup.authorities
        self.references = references
        self.form_gate = form_gate
        self.name_parser = name_parser

    def evaluate(self, source, candidates, total, *, authority_source=False):
        decision, receipt, diagnostics = self.lookup.evaluate(source, candidates, total, authority_source=authority_source)
        evidence = source.evidence
        started = perf_counter()
        scopes = scope_observations(evidence, evidence.designation)
        if self.form_gate:
            for claim in evidence.claims:
                if claim.kind == "DEFINITION" and claim.qualified("SOURCE_RECORD") and (match := V4_SCOPE.search(claim.value)):
                    scopes.append({"category": "VARIABLE_COMPOSITION_OR_DISTRIBUTION", "claim_id": claim.claim_id,
                                   "text": match[0]})
        identifiers = []
        reasons = []
        specification = None
        form = {"assessment": "FORM_SCOPE_UNESTABLISHED"} if self.form_gate else None
        version = FORM_VERSION if self.form_gate else VERSION
        if decision["eligibility"] == "CANDIDATE_READY":
            graph = describe(decision["specificity"]["smiles"])
            specification = exact_scope_specification(evidence, graph)
            if decision["evidence_pathway"] == "A_DIRECT_STRUCTURE" and authority_source:
                specification = specification or "QUALIFIED_NATIVE_WHOLE_STRUCTURE"
            if any(r["category"] != "SCOPE_UNESTABLISHED" for r in scopes):
                reasons.append("SOURCE_DEFINITION_SCOPE_CONFLICT")
            if not authority_source and not specification and any("obligation" in r for r in scopes):
                reasons.append("SOURCE_WHOLE_BRANCH_SPECIFICATION_MISSING")
            identifiers = identifier_observations(source, graph, candidates, self.authorities, self.references,
                                                 exact_reference=self.form_gate)
            if any(r["category"] in {"DISTINCT_CHEMICAL_FORMS", "CONFLICTING_IDENTITY_ASSERTIONS"} for r in identifiers):
                reasons.append("SOURCE_IDENTIFIER_STRUCTURE_CONFLICT")
            if any(r["category"] == "SOURCE_IDENTIFIER_SCOPE_AMBIGUOUS" for r in identifiers):
                reasons.append("SOURCE_IDENTIFIER_SCOPE_AMBIGUOUS")
            if self.form_gate and decision["resolution_pathway"] == "SUBSTANCE":
                form.update(form_evidence(source, graph, receipt, specification, identifiers, scopes, self.name_parser))
                if "SOURCE_IDENTIFIER_STRUCTURE_CONFLICT" in reasons:
                    form["assessment"] = "IDENTITY_CONFLICT"
                elif any(r["category"] == "MULTIPLE_POSSIBLE_CHEMICAL_FORMS" for r in scopes):
                    form["assessment"] = "MULTIPLE_FORMS_PLAUSIBLE"
                elif not reasons and not form["positive_form_basis"]:
                    form["assessment"] = "EXACT_FORM_UNSUPPORTED_BY_SOURCE"
                    reasons.append(form["assessment"])
                elif not reasons:
                    form["assessment"] = "EXACT_FORM_ESTABLISHED"
        elif any(r["category"] != "SCOPE_UNESTABLISHED" for r in scopes):
            reasons.append("SOURCE_DEFINITION_SCOPE_REQUIRES_REVIEW")
        if self.form_gate and decision["eligibility"] != "CANDIDATE_READY":
            if FORM_CONFLICT.intersection(decision["reasons"]):
                form["assessment"] = "IDENTITY_CONFLICT"
            elif FORM_COMPETITION.intersection(decision["reasons"]):
                form["assessment"] = "MULTIPLE_FORMS_PLAUSIBLE"
        proof = {"version": version, "source_revision": evidence.source_revision, "scope_observations": scopes,
                 "identifier_observations": identifiers, "whole_specification_claim": specification,
                 "positive_binding": receipt and receipt["assertion_type"], "proposed_graph": decision["specificity"],
                 "scope": "EXACT_MOLECULAR_REFERENT" if not reasons and decision["eligibility"] == "CANDIDATE_READY"
                 and decision["resolution_pathway"] == "SUBSTANCE" else "SCOPE_UNESTABLISHED", "reasons": reasons}
        if self.form_gate:
            proof["chemical_form"] = form
        if reasons:
            claim = Claim("source-safety:" + digest(proof), "DEFINITION", digest(proof), "SCOPE_UNESTABLISHED",
                          evidence.referent, version, (), evidence.source_reference, "source identity assessment",
                          evidence.source_revision)
            decision = self.evaluator.evaluate(replace(evidence, claims=(*evidence.claims, claim),
                                                        holds=tuple(dict.fromkeys((*decision["reasons"], *reasons)))
                                                        if decision["eligibility"] != "CANDIDATE_READY" else tuple(reasons)))
            receipt = None
        elif receipt:
            receipt["source_identity_safety"] = proof
            receipt["receipt_sha256"] = digest({k: v for k, v in receipt.items() if k != "receipt_sha256"})
        decision["source_identity_safety"] = proof
        decision["source_identity_safety_seconds"] = perf_counter() - started
        return decision, receipt, diagnostics
