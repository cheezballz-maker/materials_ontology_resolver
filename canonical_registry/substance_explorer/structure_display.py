"""Local molecular depictions rendered from a stored SMILES."""

from rdkit import Chem, rdBase
from rdkit.Chem import Draw, rdMolDescriptors

from canonical_registry.chemistry import parse


def molecular_formula(smiles):
    """Return the formula of the represented graph without resolving identity."""
    if not smiles:
        return None
    try:
        with rdBase.BlockLogs():
            return rdMolDescriptors.CalcMolFormula(parse(smiles))
    except (ValueError, RuntimeError):
        return None


def stereo_summary(smiles):
    try:
        with rdBase.BlockLogs():
            mol = parse(smiles)
            rows = []
            for feature in Chem.FindPotentialStereo(mol):
                kind = str(feature.type)
                descriptor = str(feature.descriptor)
                if kind == "Atom_Tetrahedral":
                    atom = mol.GetAtomWithIdx(feature.centeredOn)
                    if atom.HasProp("_CIPCode"):
                        descriptor = atom.GetProp("_CIPCode")
                rows.append((f"{kind} {feature.centeredOn + 1}", str(feature.specified),
                             "—" if descriptor == "NoValue" else descriptor))
            return rows or [("None detected in the stored graph", "—", "—")]
    except (ValueError, RuntimeError):
        return [("Unavailable", "—", "—")]


def depiction(smiles):
    try:
        with rdBase.BlockLogs():
            mol = parse(smiles)
            if mol.GetNumAtoms() > 200:
                return None
            drawer = Draw.rdMolDraw2D.MolDraw2DCairo(440, 300)
            drawer.DrawMolecule(mol)
            drawer.FinishDrawing()
            return drawer.GetDrawingText()
    except (ValueError, RuntimeError):
        return None
