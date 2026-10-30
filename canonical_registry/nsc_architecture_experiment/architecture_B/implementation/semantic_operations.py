from rdkit import Chem
from .parent_definitions import parent
def compose(parent_name,chain_length):
    mol,target=parent(parent_name);Chem.Kekulize(mol,clearAromaticFlags=True);rw=Chem.RWMol(mol);last=target
    # The parent parser retains the indicated N hydrogen as an explicit atom
    # property after aromaticity perception; substitutive nomenclature removes it.
    rw.GetAtomWithIdx(target).SetNumExplicitHs(0)
    rw.GetAtomWithIdx(target).SetNoImplicit(False)
    for _ in range(chain_length):
        nxt=rw.AddAtom(Chem.Atom('C'));rw.AddBond(last,nxt,Chem.BondType.SINGLE);last=nxt
    result=rw.GetMol();Chem.SanitizeMol(result)
    if result.GetAtomWithIdx(target).GetTotalNumHs()!=0:raise ValueError('SUBSTITUTION_VALENCE_INVALID')
    return result
