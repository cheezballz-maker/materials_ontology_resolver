"""Review-pending numbered IUPAC parent templates, not name-to-product maps."""
from rdkit import Chem
PARENTS={'pyrazole':('N1N=CC=C1',0),'imidazole':('N1C=NC=C1',0)}
ALKYL={'methyl':1,'ethyl':2,'propyl':3,'butyl':4}
def parent(name):
    smiles,target=PARENTS[name];mol=Chem.MolFromSmiles(smiles)
    if mol is None or mol.GetAtomWithIdx(target).GetSymbol()!='N' or mol.GetAtomWithIdx(target).GetTotalNumHs()!=1:raise ValueError('INVALID_PARENT_TEMPLATE')
    return mol,target
