"""Translate bounded CosIng source rows to the shared interpretation contract."""

import json

from .contracts import Evidence, InterpretationInput, ReportedFunction, ReportedIdentifier, StructureKind, TypedStructure
from .functions import FunctionVocabulary

PARENT = "mse_dwd.dwd_mse_cosmetics_incis"
ALIASES = "mse_dwd.dwd_mse_cosmetics_inci_aliases"
ROLE_REFERENCE = "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A32006D0257#page=4"
PERFUMING_REFERENCE = "https://health.ec.europa.eu/document/download/827f8a57-c6f2-4d6d-9bbd-2ef12384ffbf_en?filename=sccs_o_303.pdf"
COSMETICS_FUNCTIONS = FunctionVocabulary(ROLE_REFERENCE, frozenset("""
ABRASIVE|ABSORBENT|ANTICAKING|ANTICORROSIVE|ANTIDANDRUFF|ANTIFOAMING|ANTIMICROBIAL|
ANTIOXIDANT|ANTIPERSPIRANT|ANTIPLAQUE|ANTISEBORRHOEIC|ANTISTATIC|ASTRINGENT|BINDING|
BLEACHING|BUFFERING|BULKING|CHELATING|CLEANSING|COSMETIC COLORANT|DENATURANT|DEODORANT|
DEPILATORY|DETANGLING|EMOLLIENT|EMULSIFYING|EMULSION STABILISING|FILM FORMING|FOAMING|
FOAM BOOSTING|GEL FORMING|HAIR CONDITIONING|HAIR DYEING|HAIR FIXING|HAIR WAVING OR STRAIGHTENING|
HUMECTANT|HYDROTROPE|KERATOLYTIC|MASKING|MOISTURISING|NAIL CONDITIONING|OPACIFYING|
ORAL CARE|OXIDISING|PEARLESCENT|PERFUMING|PLASTICISER|PRESERVATIVE|PROPELLANT|REDUCING|REFATTING|
REFRESHING|SKIN CONDITIONING|SKIN PROTECTING|SMOOTHING|SOLVENT|SOOTHING|STABILISING|
SURFACTANT|TANNING|TONIC|UV ABSORBER|UV FILTER|VISCOSITY CONTROLLING
""".replace("\n", "").split("|")), {"COLORANT": "COSMETIC COLORANT"}, {"PERFUMING": PERFUMING_REFERENCE})


def _array(value):
    # The bounded read-only MCP can transport array values as JSON strings.
    return (json.loads(value) if isinstance(value, str) else value) or []


def adapt_cosing_preview(row: dict, aliases=None, *, include_registry_claims=False) -> InterpretationInput:
    reference = f"{PARENT}:{row['inci_id']}"
    structures, identifiers = [], []
    for alias in _array(row.get("alias_claims")) if aliases is None else aliases:
        kind = alias["alias_type"]
        evidence = Evidence(alias["alias"], "typed_alias", f"{ALIASES}:{alias['inci_alias_id']}", alias["source"])
        if kind in {"SMILES", "INCHI"}:
            structures.append(TypedStructure(StructureKind(kind.lower()), evidence))
        elif kind == "INCHI_KEY":
            identifiers.append(ReportedIdentifier("InChIKey", evidence))
        elif kind == "MOLECULAR_FORMULA":
            identifiers.append(ReportedIdentifier("MolecularFormula", evidence))
        elif include_registry_claims and kind in {"CAS_NO","EC_NO"}:
            identifiers.append(ReportedIdentifier("CASRegistryNumber" if kind=="CAS_NO" else "ECNumber",evidence))
    if include_registry_claims:
        for field,scheme in (("cas_nos","CASRegistryNumber"),("ec_nos","ECNumber")):
            for index,value in enumerate(_array(row.get(field))):
                if isinstance(value,str) and value.strip():
                    identifiers.append(ReportedIdentifier(scheme,Evidence(value,f"{field}[{index}]",reference)))
    definition = row.get("description")
    return InterpretationInput(
        Evidence(row["inci"], "preferred_label", reference),
        tuple(structures),
        tuple(identifiers),
        tuple(ReportedFunction(Evidence(label, f"functions[{i}]", reference), "cosmetics")
              for i, label in enumerate(_array(row.get("functions"))) if isinstance(label, str) and label.strip()),
        Evidence(definition, "source_definition", reference) if definition and definition.strip() else None,
    )
