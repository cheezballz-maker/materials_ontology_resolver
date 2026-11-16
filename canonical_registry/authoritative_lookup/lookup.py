"""Qualify a retrieved authority record against a source referent and revision."""

from dataclasses import asdict, dataclass, replace
import unicodedata

from canonical_registry.chemistry import describe
from canonical_registry.identity_sufficiency.contract import Claim, Evidence, WHOLE, digest, structure_signature

VERSION = "authoritative-identity-receipt-v1"
UNKNOWN = "SCOPE_UNESTABLISHED"


def normalize(value):
    return " ".join(unicodedata.normalize("NFC", value).split()).casefold()


@dataclass(frozen=True)
class SourceReferent:
    evidence: Evidence
    record_type: str
    names: tuple[str, ...]
    definition: str
    identifiers: dict[str, tuple[str, ...]]
    graph_signatures: tuple[tuple, ...] = ()
    preferred_name_graph_retained: bool = False


@dataclass(frozen=True)
class AuthorityRecord:
    entity: str
    authority: str
    structure_type: str
    structure: str
    inchikey: str
    names: tuple[str, ...]
    identifiers: dict[str, tuple[str, ...]]
    document: str
    locator: str
    provenance: dict
    complete_composition: bool = False


def _reconcile_record(authority, candidate):
    if candidate["substance_type"] != "chemical" or candidate["ingredient_type"] != "INGREDIENT SUBSTANCE":
        return None, "WAREHOUSE_RECORD_ROLE_NOT_WHOLE_MOLECULAR"
    if not authority.document or not authority.provenance.get("sha256"):
        return None, "AUTHORITY_PROVENANCE_MISSING"
    unii = authority.identifiers.get("UNII")
    cas = authority.identifiers.get("CAS", ())
    if (unii and unii != (candidate["source_id"],)) or (not unii and
            not any("REPORTED_IDENTIFIER:CAS:" + code in candidate["routes"] for code in cas)):
        return None, "AUTHORITY_ACCESSION_MISMATCH"
    try:
        graph = describe(authority.structure, authority.structure_type.lower())
        warehouse = describe(candidate["smiles"] or "")
    except (ValueError, RuntimeError):
        return None, "AUTHORITY_OR_WAREHOUSE_STRUCTURE_INVALID"
    if not (structure_signature(graph) == structure_signature(warehouse) and
            graph["inchikey"] == authority.inchikey == candidate["inchikey"]):
        return None, "AUTHORITY_AND_WAREHOUSE_FORM_DISAGREE"
    if authority.provenance.get("FDA_key") not in (None, graph["inchikey"]):
        return None, "AUTHORITY_STRUCTURE_DESCRIPTOR_DISAGREES"
    if authority.provenance.get("formula") not in (None, graph["formula"]):
        return None, "AUTHORITY_STRUCTURE_DESCRIPTOR_DISAGREES"
    return graph, None


def _attach(evidence, authority, candidate, graph, basis, proof, notes):
    revision = digest(asdict(authority))
    grants = ("STRUCTURE", "COMPLETE_COMPOSITION") if authority.complete_composition else ("STRUCTURE",)
    if basis == "SOURCE_NATIVE_STRUCTURE_WHOLE":
        scope = WHOLE
        grants += ("REFERENT",)
    else:
        scope = UNKNOWN
    structure = Claim("lookup:structure", authority.structure_type, authority.structure, scope, authority.entity,
                      authority.authority, grants, authority.document, authority.locator, revision,
                      binding_revision=evidence.source_revision)
    extra = [structure]
    if basis != "SOURCE_NATIVE_STRUCTURE_WHOLE":
        id_binding = basis in {"SOURCE_UNII_CROSS_REFERENCE", "NATIVE_TYPED_IDENTIFIER_AND_SOURCE_GRAPH"}
        kind, grant = ("IDENTIFIER_LINK", "IDENTIFIER") if id_binding else ("NOMENCLATURE_LINK", "NOMENCLATURE")
        extra.append(Claim("lookup:binding", kind, proof["binding_value"], WHOLE, authority.entity,
                           authority.authority, (grant, "REFERENT"), authority.document, basis, revision,
                           namespace=proof.get("binding_namespace", "UNII") if id_binding else "",
                           identity_scope="DEFINED_CHEMICAL",
                           binding_revision=evidence.source_revision))
    receipt = {"receipt_version": VERSION, "source_record": evidence.source_reference,
               "source_revision": evidence.source_revision, "original_designation": evidence.designation,
               "authority_entity": authority.entity, "authority_record_revision": revision,
               "authority": authority.authority, "record_reference": authority.document,
               "assertion_type": basis, "relationship": "WHOLE_REFERENT_EXACT_CHEMICAL_IDENTITY",
               "referent_scope": WHOLE, "structure_reference": authority.locator,
               "specificity": dict(zip(("smiles", "inchi", "inchikey", "fixed_h_inchi"), structure_signature(graph))),
               "authority_provenance": authority.provenance, "warehouse_candidate": candidate,
               "supporting_source_evidence": proof, "limitations": notes,
               "qualified_claims": [asdict(c) for c in extra]}
    return replace(evidence, claims=(*evidence.claims, *extra)), receipt


class IdentityLookup:
    """Consume explicitly bounded candidate results. Ranking never qualifies a record."""

    def __init__(self, evaluator, authorities):
        self.evaluator = evaluator
        self.authorities = authorities

    def evaluate(self, source, candidates, total, *, authority_source=False):
        evidence = source.evidence
        outcomes, support = [], []
        limit = total != len(candidates)
        if limit and not evidence.holds:
            evidence = replace(evidence, holds=("AUTHORITY_CANDIDATE_RETRIEVAL_TRUNCATED",))
        for candidate in candidates:
            reasons = []
            records = list(self.authorities.get(candidate["source_id"], ()))
            if not authority_source:
                for route in candidate["routes"]:
                    if route.startswith("REPORTED_IDENTIFIER:CAS:"):
                        records.extend(self.authorities.get(route.removeprefix("REPORTED_IDENTIFIER:"), ()))
            for authority in records:
                graph, issue = _reconcile_record(authority, candidate)
                if issue:
                    reasons.append(issue)
                    continue
                exact_names = {normalize(n) for n in authority.names if n}
                exact_designation = normalize(evidence.designation) in exact_names
                exact_definition = normalize(source.definition) in exact_names
                preferred = normalize(candidate["chemical_name"]) in exact_names
                paired_reference = bool(authority.provenance.get("stage_c_cas_cross_reference") and
                                        not authority_source and source.graph_signatures and
                                        normalize(candidate["chemical_name"]) == normalize(evidence.designation) and
                                        "PREFERRED_NAME:NAME:" + candidate["chemical_name"].strip().upper() in candidate["routes"])
                native_capture = bool(authority.provenance.get("stage_c_live_native"))
                if not preferred and not paired_reference and not native_capture:
                    reasons.append("WAREHOUSE_AND_AUTHORITY_PREFERRED_NAME_DISAGREE")
                    continue
                if authority_source:
                    if (source.identifiers.get("UNII") != (candidate["source_id"],) or
                            authority.identifiers.get("UNII") != (candidate["source_id"],)):
                        reasons.append("ORIGINAL_AUTHORITY_ACCESSION_UNBOUND")
                        continue
                    basis = ("SOURCE_NATIVE_STRUCTURE_WHOLE" if authority.complete_composition
                             else "SOURCE_UNII_CROSS_REFERENCE")
                    proof = {"binding_value": candidate["source_id"], "original_UNII": candidate["source_id"],
                             "designation": evidence.designation}
                else:
                    typed = {n: v for n, v in source.identifiers.items() if v}
                    if any(len(v) != 1 for v in typed.values()):
                        reasons.append("WHOLE_NAME_OR_SINGLETON_TYPED_IDENTIFIERS_UNESTABLISHED")
                        continue
                    shared = {n: v for n, v in typed.items() if authority.identifiers.get(n) == v}
                    if any(authority.identifiers.get(n) and n not in shared for n in typed):
                        reasons.append("TYPED_IDENTIFIER_DISAGREEMENT")
                        continue
                    signature = structure_signature(graph)
                    if any(other != signature for other in source.graph_signatures):
                        reasons.append("SOURCE_GRAPH_FORM_DISAGREEMENT")
                        continue
                    if any(c.kind == "INCHIKEY" and c.value != graph["inchikey"] for c in evidence.claims):
                        reasons.append("SOURCE_GRAPH_FORM_DISAGREEMENT")
                        continue
                    native_name = native_capture and preferred and exact_designation and bool(source.graph_signatures)
                    native_id = (native_capture and bool(source.graph_signatures) and
                                 shared.get("UNII") == (candidate["source_id"],))
                    typed_cas = "CAS" in shared and "REPORTED_IDENTIFIER:CAS:" + shared["CAS"][0] in candidate["routes"]
                    if not (native_name or native_id or (typed_cas and (exact_designation or exact_definition or paired_reference))):
                        reasons.append("QUALIFIED_NAME_OR_IDENTIFIER_BINDING_UNESTABLISHED")
                        continue
                    if not source.graph_signatures and "EC" not in shared:
                        reasons.append("NO_SOURCE_GRAPH_OR_INDEPENDENT_EC_BINDING")
                        continue
                    if graph["components"] > 1 and not source.graph_signatures:
                        reasons.append("MULTICOMPONENT_SOURCE_FORM_UNESTABLISHED")
                        continue
                    basis = ("NATIVE_TYPED_IDENTIFIER_AND_SOURCE_GRAPH" if native_id else
                             "NATIVE_PREFERRED_NAME_AND_SOURCE_GRAPH" if native_name else
                             "PREFERRED_NAME_AND_TYPED_IDENTIFIER" if exact_designation or paired_reference else
                             "SOURCE_DEFINITION_AND_TYPED_IDENTIFIER")
                    proof = {"binding_value": evidence.designation if exact_designation or paired_reference else source.definition,
                             "exact_authority_names": authority.names, "matching_identifiers": shared,
                             "compared_source_graphs": source.graph_signatures,
                             "authority_name_cross_reference_via_typed_cas": paired_reference}
                    if native_id:
                        proof.update(binding_value=candidate["source_id"], binding_namespace="UNII")
                support.append((authority, candidate, graph, basis, proof))
                reasons.append("AUTHORITY_RECORD_AND_SOURCE_BINDING_AGREE")
            outcomes.append({"candidate": candidate, "assessment": sorted(set(reasons)) or
                             ["CANDIDATE_ONLY_AUTHORITY_FIELD_ROLES_UNESTABLISHED"]})

        receipt = None
        if not evidence.holds and evidence.material_scope == "UNESTABLISHED":
            if len({structure_signature(item[2]) for item in support}) > 1:
                evidence = replace(evidence, holds=("COMPETING_AUTHORITY_STRUCTURAL_FORMS",))
            elif support:
                # Compatible authority records can corroborate the same identity.
                # A second candidate with a direct name claim and a distinct or
                # missing graph prevents binding the original referent.
                chosen = sorted(support, key=lambda item: (not item[0].complete_composition, item[0].entity))[0]
                same_ids = {item[1]["chemical_id"] for item in support}
                conflicts = {"AUTHORITY_AND_WAREHOUSE_FORM_DISAGREE", "AUTHORITY_STRUCTURE_DESCRIPTOR_DISAGREES",
                             "SOURCE_GRAPH_FORM_DISAGREEMENT", "TYPED_IDENTIFIER_DISAGREEMENT"}
                conflicting_authority = any(item["candidate"]["chemical_id"] in same_ids and
                                            conflicts.intersection(item["assessment"]) for item in outcomes)
                competing = [c for c in candidates if c["chemical_id"] not in same_ids and
                             any(x.startswith(("PREFERRED_NAME:", "REPORTED_ALIAS:NAME:")) for x in c["routes"])]
                conflicting = any(not _same_graph(c, chosen[2]) for c in competing)
                if conflicting_authority:
                    evidence = replace(evidence, holds=("SOURCE_AND_AUTHORITY_CLAIMS_DISAGREE",))
                elif conflicting:
                    evidence = replace(evidence, holds=("ALTERNATE_FORM_NAME_CANDIDATE_UNRESOLVED",))
                else:
                    evidence, receipt = _attach(evidence, *chosen, [
                        "Retrieved names, identifiers and projected structures retain candidate-only status independently.",
                        "Cross-reference describes the chemical referent at this source revision.",
                    ])
            elif any("SOURCE_GRAPH_FORM_DISAGREEMENT" in item["assessment"] or
                     "TYPED_IDENTIFIER_DISAGREEMENT" in item["assessment"] for item in outcomes):
                evidence = replace(evidence, holds=("SOURCE_AND_AUTHORITY_CLAIMS_DISAGREE",))
        decision = self.evaluator.evaluate(evidence)
        if receipt:
            receipt["validation"] = {"eligibility": decision["eligibility"],
                                     "reasons": decision["reasons"],
                                     "official_inchi": decision.get("official_validation")}
            if receipt["assertion_type"] == "NATIVE_TYPED_IDENTIFIER_AND_SOURCE_GRAPH":
                # The typed identifier binds the referent. It does not grant
                # exact chemical alias status to its displayed designation.
                receipt["supporting_source_evidence"] = {
                    **receipt["supporting_source_evidence"], "binding_value": None,
                    "bound_identifier": receipt["qualified_claims"][1]["value"],
                }
            receipt["receipt_sha256"] = digest(receipt)
        return decision, receipt, outcomes


def _same_graph(candidate, graph):
    if candidate["inchikey"] != graph["inchikey"] or not candidate["smiles"]:
        return False
    try:
        return structure_signature(describe(candidate["smiles"])) == structure_signature(graph)
    except (ValueError, RuntimeError):
        return False
