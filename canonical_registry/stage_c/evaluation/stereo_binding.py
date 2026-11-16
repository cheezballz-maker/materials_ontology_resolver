"""Qualify fully specified linear dienols from a source name and a species record."""

import re

from canonical_registry.authoritative_lookup.lookup import AuthorityRecord, _attach
from canonical_registry.chemistry import describe, parse
from canonical_registry.identity_sufficiency.contract import digest
from identity_comparator import compare
from rdkit import Chem


STEMS = {"hexa": 6, "hepta": 7, "octa": 8, "nona": 9, "deca": 10, "undeca": 11, "dodeca": 12}
DIENOL = re.compile(
    r"([1-9]\d?)-(cis|trans)\s*,\s*([1-9]\d?)-(cis|trans)-("
    + "|".join(STEMS) + r")dienol", re.I
)


def systematic_name(name):
    # Each alkene carbon bears one hydrogen in this narrow linear primary
    # alcohol grammar. Accordingly cis is Z and trans is E at both positions.
    if not (match := DIENOL.fullmatch(name.strip())):
        return None
    left, right = int(match[1]), int(match[3])
    stem = match[5].lower()
    if not 2 <= left < right - 1 or right >= STEMS[stem] - 1:
        return None
    geometry = {"cis": "Z", "trans": "E"}
    return f"({left}{geometry[match[2].lower()]},{right}{geometry[match[4].lower()]})-{stem}-{left},{right}-dien-1-ol"


class StereoSpeciesBinding:
    """Add a revision-bound nomenclature receipt through the existing evaluator."""

    def __init__(self, lookup, evaluator, references, name_parser):
        self.lookup = lookup
        self.authorities = lookup.authorities
        self.rejected = lookup.rejected
        self.evaluator = evaluator
        self.references = references
        self.name_parser = name_parser

    def evaluate(self, source, candidates, total, *, authority_source=False):
        decision, receipt, diagnostics = self.lookup.evaluate(source, candidates, total, authority_source=authority_source)
        evidence = source.evidence
        if (authority_source or total != len(candidates) or receipt or
                decision["eligibility"] != "NEEDS_MORE_EVIDENCE" or evidence.holds or
                evidence.material_scope != "UNESTABLISHED" or source.definition):
            return decision, receipt, diagnostics
        if any({"SOURCE_GRAPH_FORM_DISAGREEMENT", "TYPED_IDENTIFIER_DISAGREEMENT",
                "AUTHORITY_AND_WAREHOUSE_FORM_DISAGREE", "AUTHORITY_STRUCTURE_DESCRIPTOR_DISAGREES"}
               .intersection(row["assessment"]) for row in diagnostics):
            return decision, receipt, diagnostics
        name = systematic_name(evidence.designation)
        codes = source.identifiers.get("CAS", ())
        if (not name or len(codes) != 1 or any(len(values) > 1 for values in source.identifiers.values()) or
                not any(claim.kind == "NAME" and claim.entity == evidence.referent
                        and claim.revision == evidence.source_revision and claim.value == evidence.designation
                        and claim.qualified("SOURCE_RECORD") for claim in evidence.claims)):
            return decision, receipt, diagnostics
        ref = self.references.get(codes[0], {})
        diagnostic = {"assessment": ["STEREO_SPECIES_REFERENCE_UNAVAILABLE"], "source_name": evidence.designation,
                      "systematic_name": name, "cas": codes[0]}
        diagnostics.append(diagnostic)
        if (ref.get("status") != "STRUCTURAL_REFERENCE" or ref.get("cas") != codes[0] or
                not ref.get("sha256") or ref.get("url") !=
                "https://webbook.nist.gov/cgi/cbook.cgi?ID=C" + codes[0].replace("-", "")):
            return decision, receipt, diagnostics
        parsed = self.name_parser(name)
        try:
            if parsed["status"] != "SUCCESS":
                raise ValueError("SYSTEMATIC_NAME_PARSE_FAILED")
            graph = describe(parsed["smiles"])
            reference = describe(ref["inchi"], "inchi")
            stereo = Chem.FindPotentialStereo(parse(graph["smiles"]))
            if (len(stereo) != 2 or any(item.type != Chem.StereoType.Bond_Double or
                    item.specified != Chem.StereoSpecified.Specified for item in stereo)):
                raise ValueError("SOURCE_STEREOCHEMISTRY_UNESTABLISHED")
            if (reference["inchikey"] != ref["inchikey"] or compare(graph, reference)["assessment"] != "EXACT"):
                raise ValueError("SOURCE_SPECIES_STRUCTURE_DISAGREES")
            if any(other[2] != graph["inchikey"] or compare(graph, describe(other[0]))["assessment"] != "EXACT"
                   for other in source.graph_signatures):
                raise ValueError("SOURCE_GRAPH_FORM_DISAGREEMENT")
            for candidate in candidates:
                if not any(route.startswith(("PREFERRED_NAME:", "REPORTED_ALIAS:NAME:", "REPORTED_IDENTIFIER:"))
                           for route in candidate["routes"]):
                    continue
                if (candidate["substance_type"] != "chemical" or candidate["ingredient_type"] != "INGREDIENT SUBSTANCE"
                        or candidate["inchikey"] != graph["inchikey"] or
                        compare(graph, describe(candidate["smiles"]))["assessment"] != "EXACT"):
                    raise ValueError("COMPETING_REPORTED_SOURCE_IDENTITY")
        except (ValueError, RuntimeError, KeyError, TypeError) as exc:
            diagnostic["assessment"] = ["STEREO_SPECIES_BINDING_WITHHELD"]
            diagnostic["reason"] = str(exc)
            return decision, receipt, diagnostics

        authority = AuthorityRecord(
            "NIST:CAS:" + codes[0], "NIST Chemistry WebBook", "INCHI", ref["inchi"], ref["inchikey"],
            (ref["title"],), {"CAS": codes}, ref["url"], "CAS Registry Number and Standard InChI", ref
        )
        attached, candidate_receipt = _attach(
            evidence, authority, None, reference, "EXPLICIT_STEREO_NAME_AND_SPECIES_CAS",
            {"binding_value": evidence.designation, "systematic_name": name, "parser_result": parsed,
             "matching_identifiers": {"CAS": codes}, "compared_source_graphs": source.graph_signatures},
            ["Exact binding is restricted to the original fully specified linear dienol designation and revision."],
        )
        qualified = self.evaluator.evaluate(attached)
        diagnostic["assessment"] = ["STEREO_SPECIES_BINDING_ESTABLISHED"]
        if qualified["eligibility"] != "CANDIDATE_READY":
            return qualified, None, diagnostics
        candidate_receipt["validation"] = {"eligibility": qualified["eligibility"], "reasons": qualified["reasons"],
                                           "official_inchi": qualified.get("official_validation")}
        candidate_receipt["receipt_sha256"] = digest(candidate_receipt)
        return qualified, candidate_receipt, diagnostics
