import unittest
from rdkit import Chem
from architecture_B.implementation.interpreter import interpret_name,validate_candidate
from architecture_B.implementation.semantic_operations import compose

class InterpreterTests(unittest.TestCase):
 def test_parent_and_chain_compose_with_correct_valence(self):
  for parent in ('pyrazole','imidazole'):
   for n in range(1,5):
    with self.subTest(parent=parent,n=n):
     m=compose(parent,n);self.assertEqual(m.GetNumAtoms(),5+n);self.assertEqual(m.GetAtomWithIdx(0).GetSymbol(),'N');self.assertEqual(m.GetAtomWithIdx(0).GetTotalNumHs(),0)
 def test_equivalent_graph_and_incorrect_substituent(self):
  x=interpret_name('1-ethyl-1H-imidazole')
  self.assertEqual(validate_candidate(x,'CCN1C=NC=C1').result,'SUPPORTED')
  y=validate_candidate(x,'CN1C=CN=C1');self.assertEqual(y.result,'DIFFERENT');self.assertEqual(y.reason_codes,['SUBSTITUENT_STRUCTURE_DIFFERENT'])
 def test_identity_remains_unresolved(self):
  x=interpret_name('1-methyl-1H-pyrazole');v=validate_candidate(x,'CN1C=CC=N1')
  self.assertEqual(v.dimension_results,[{'dimension':'tautomer','result':'UNKNOWN'},{'dimension':'identity','result':'NOT_ESTABLISHED'}])
if __name__=='__main__':unittest.main()
