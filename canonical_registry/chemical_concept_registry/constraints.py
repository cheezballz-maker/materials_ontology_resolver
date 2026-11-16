"""Supported concept definitions and conservative meaning comparison."""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "warehouse_admission_consolidation"))
import bootstrap  # noqa: E402,F401
from chemistry import describe, parse
from charge_comparison_attribution import compare as compare_graphs
from stereo_comparison import compare as compare_stereo
from rdkit import Chem
from rdkit.Chem.EnumerateStereoisomers import EnumerateStereoisomers, StereoEnumerationOptions

EQUIVALENT = "EQUIVALENT_CONCEPT"
DISTINCT = "DISTINCT_CONCEPT"
BROADER = "BROADER_CONCEPT"
NARROWER = "NARROWER_CONCEPT"
UNRESOLVED = "CONCEPT_COMPARISON_UNRESOLVED"
STATES = {"SPECIFIED", "UNASSIGNED_IN_REPRESENTATION", "EXPLICITLY_UNSPECIFIED", "UNKNOWN", "NOT_APPLICABLE", "CONFLICT", "UNSUPPORTED"}
SUPPORTED_ELEMENTS = {"C", "H", "N", "O", "F", "Cl", "Br", "I", "S", "P", "Si", "B"}
FAMILIES = {
    "metal_oxides": "Binary materials consisting of oxygen and one metallic element, with no other elements.",
    "iron_oxides": "Binary materials consisting of iron and oxygen, with no other elements.",
    "carboxylic_acids": "Discrete neutral organic molecules containing a covalently represented carboxylic acid group.",
}
ACID = Chem.MolFromSmarts("[CX3](=[OX1])[OX2H1]")


def has_carboxylic_acid(mol):
    for match in mol.GetSubstructMatches(ACID):
        carbon = mol.GetAtomWithIdx(match[0])
        if carbon.GetTotalNumHs() or any(atom.GetAtomicNum() == 6 for atom in carbon.GetNeighbors()):
            return True
    return False


class ProposalError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def molecular(smiles, stereo_state="UNASSIGNED_IN_REPRESENTATION"):
    if stereo_state not in STATES:
        raise ProposalError("INVALID_CONSTRAINT_STATE")
    if stereo_state not in ("EXPLICITLY_UNSPECIFIED", "UNASSIGNED_IN_REPRESENTATION"):
        raise ProposalError("STEREO_" + stereo_state)
    try:
        graph = describe(smiles)
        mol = parse(smiles)
    except (ValueError, RuntimeError) as error:
        raise ProposalError("INVALID_OR_UNSUPPORTED_STRUCTURE") from error
    warnings = {part.strip() for part in graph["inchi_warning"].split(";") if part.strip()}
    if warnings - {"Omitted undefined stereo"}:
        raise ProposalError("INCHI_WARNING_REQUIRES_REVIEW")
    stereo = list(Chem.FindPotentialStereo(mol))
    ordinary_atoms = {Chem.ChiralType.CHI_UNSPECIFIED, Chem.ChiralType.CHI_TETRAHEDRAL_CW,
                      Chem.ChiralType.CHI_TETRAHEDRAL_CCW}
    ordinary_bonds = {Chem.BondStereo.STEREONONE, Chem.BondStereo.STEREOE,
                      Chem.BondStereo.STEREOZ, Chem.BondStereo.STEREOCIS,
                      Chem.BondStereo.STEREOTRANS}
    if (len(Chem.GetMolFrags(mol)) != 1 or Chem.GetFormalCharge(mol) != 0
            or any(a.GetIsotope() or a.GetNumRadicalElectrons() or a.GetFormalCharge() for a in mol.GetAtoms())
            or any(a.GetChiralTag() not in ordinary_atoms for a in mol.GetAtoms())
            or any(b.GetStereo() not in ordinary_bonds for b in mol.GetBonds())
            or not {a.GetSymbol() for a in mol.GetAtoms()} <= SUPPORTED_ELEMENTS
            or not any(a.GetAtomicNum() == 6 for a in mol.GetAtoms())
            or any(str(b.GetBondType()) not in ("SINGLE", "DOUBLE", "TRIPLE", "AROMATIC") for b in mol.GetBonds())
            or mol.GetStereoGroups()
            or any(str(item.type) not in ("Atom_Tetrahedral", "Bond_Double") for item in stereo)
            or any(str(item.type) == "Atom_Tetrahedral" and mol.GetAtomWithIdx(item.centeredOn).GetAtomicNum() != 6 for item in stereo)
            or any(str(item.type) == "Bond_Double" and any(a.GetAtomicNum() != 6 for a in (mol.GetBondWithIdx(item.centeredOn).GetBeginAtom(), mol.GetBondWithIdx(item.centeredOn).GetEndAtom())) for item in stereo)):
        raise ProposalError("UNSUPPORTED_MOLECULAR_SCOPE")
    if not any(str(item.specified) != "Specified" for item in stereo):
        raise ProposalError("DIRECT_TO_SUBSTANCE")
    opts = StereoEnumerationOptions(onlyUnassigned=True, unique=True, maxIsomers=65, tryEmbedding=False)
    isomers = sorted({Chem.MolToSmiles(item, canonical=True, isomericSmiles=True)
                      for item in EnumerateStereoisomers(mol, options=opts)})
    if len(isomers) > 64:
        raise ProposalError("STEREO_ENUMERATION_LIMIT")
    if not isomers:
        raise ProposalError("STEREO_ENUMERATION_FAILED")
    return {"kind": "molecular", "identity_scope": "DISCRETE_MOLECULAR_GRAPH_NOT_MATERIAL_PHASE",
            "smiles": graph["smiles"], "stereo_state": "UNASSIGNED_IN_REPRESENTATION",
            "constitution": "SPECIFIED", "charge": "SPECIFIED", "isotope": "SPECIFIED",
            "tautomer": "SPECIFIED", "components": "SPECIFIED", "phase": "NOT_APPLICABLE",
            "isomers": isomers}


def family(key):
    if key not in FAMILIES:
        raise ProposalError("UNSUPPORTED_FAMILY_DEFINITION")
    return {"kind": "family", "family": key, "definition": FAMILIES[key]}


def validate(proposal):
    if not isinstance(proposal, dict):
        raise ProposalError("INVALID_PROPOSAL")
    if proposal.get("kind") == "family" and set(proposal) == {"kind", "family"}:
        raise ProposalError("NONCANONICAL_BROAD_TERM")
    if proposal.get("kind") == "molecular" and set(proposal) <= {"kind", "smiles", "stereo_state"}:
        return molecular(proposal.get("smiles"), proposal.get("stereo_state", "UNASSIGNED_IN_REPRESENTATION"))
    raise ProposalError("UNSUPPORTED_DEFINITION_OR_CONSTRAINT")


def compare(left, right):
    """Direction describes left relative to right. Unknown never means distinct."""
    if left.get("kind") != "molecular" or right.get("kind") != "molecular":
        return UNRESOLVED
    try:
        comparison = compare_graphs(describe(left["smiles"]), describe(right["smiles"]))
    except (ValueError, RuntimeError):
        return UNRESOLVED
    dimensions = comparison["dimensions"]
    for dimension in ("connectivity", "protonation_charge", "isotope_specification",
                      "tautomeric_form", "electronic_state", "components", "component_stoichiometry"):
        if dimensions[dimension] == "DIFFERENT":
            return DISTINCT
        if dimensions[dimension] not in ("EQUIVALENT", "NOT_APPLICABLE"):
            return UNRESOLVED
    stereo = compare_stereo(left["smiles"], right["smiles"])
    if stereo["result"] == "DIFFERENT":
        return DISTINCT
    if stereo["reason"] not in ("STEREO_NOT_APPLICABLE", "ALL_RELEVANT_STEREO_SUPPORTED",
                                 "STEREO_SPECIFICITY_UNKNOWN"):
        return UNRESOLVED
    a, b = set(left["isomers"]), set(right["isomers"])
    if a == b:
        return EQUIVALENT
    if a > b:
        return BROADER
    if a < b:
        return NARROWER
    if not a.intersection(b):
        return DISTINCT
    return UNRESOLVED


def compare_proposals(left, right):
    """Compare external proposals only when both meanings are supported."""
    try:
        return compare(validate(left), validate(right))
    except ProposalError:
        return UNRESOLVED


def contains_substance(concept, smiles):
    try:
        graph = describe(smiles)
        mol = parse(smiles)
    except (ValueError, RuntimeError):
        return "UNRESOLVED"
    if concept.get("kind") != "molecular":
        return "UNRESOLVED"
    if any(s["specified"] != "Specified" for s in graph["stereo"]):
        return "UNRESOLVED"
    if any(str(s["type"]) not in ("Atom_Tetrahedral", "Bond_Double") for s in graph["stereo"]):
        return "UNRESOLVED"
    if graph["smiles"] in concept["isomers"]:
        return "SUPPORTED"
    try:
        outcome = compare_graphs(describe(concept["smiles"]), graph)
    except (ValueError, RuntimeError):
        return "UNRESOLVED"
    if any(x == "DIFFERENT" for x in outcome["dimensions"].values()):
        return "INCOMPATIBLE"
    return "UNRESOLVED"
