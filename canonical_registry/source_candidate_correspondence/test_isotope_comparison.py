import unittest
import bootstrap
from rdkit import Chem
from evidence_adapters import assertion
from isotope_comparator import compare_assertions,framework,diagnostic
from dimension_claim_comparator import compare_assertions as original

class IsotopeTests(unittest.TestCase):
 def rel(self,a,b,d='isotope'):return compare_assertions(assertion(a,d),assertion(b,d),d)
 def test_heavy_water_explicit_protium(self):self.assertEqual(self.rel('[2H]O[2H]','[1H]O[1H]'),'EXACT_INCOMPATIBLE')
 def test_heavy_water_represented_unlabelled(self):self.assertEqual(self.rel('[2H]O[2H]','O'),'EXACT_INCOMPATIBLE')
 def test_h_representation_only(self):
  for d in ('constitution','isotope'):self.assertEqual(self.rel('[H]O[H]','O',d),'EXACT_COMPATIBLE')
 def test_same_carbon_label(self):self.assertEqual(self.rel('[13CH3]CO','OC[13CH3]'),'EXACT_COMPATIBLE')
 def test_isotope_positions(self):self.assertEqual(self.rel('[13CH3]CO','C[13CH2]O'),'EXACT_INCOMPATIBLE')
 def test_isotope_and_constitution(self):
  for d in ('constitution','isotope'):self.assertEqual(self.rel('[13CH3]CO','COC',d),'EXACT_INCOMPATIBLE')
 def test_isotope_scope_unknown(self):
  self.assertEqual(compare_assertions({'state':'UNKNOWN','rule_id':'UNESTABLISHED_SOURCE_SCOPE'},assertion('[2H]O[2H]','isotope'),'isotope'),'UNKNOWN')
 def test_isotope_explicit_broad_scope_not_specific(self):
  a=assertion(None,'isotope','UNSPECIFIED','O');self.assertEqual(compare_assertions(a,assertion('[2H]O[2H]','isotope'),'isotope'),'BROADER_THAN_CANDIDATE')
 def test_labelled_h_representation(self):self.assertEqual(self.rel('[2H]CO','[H]C([2H])([H])O'),'EXACT_COMPATIBLE')
 def test_original_comparator_is_unchanged(self):
  self.assertEqual(original(assertion('[2H]O[2H]','isotope'),assertion('O','isotope'),'isotope'),'UNKNOWN')
 def test_no_false_isotope_position_claim_on_unlike_framework(self):self.assertEqual(self.rel('[13CH3]CO','[13CH3]OC'),'UNKNOWN')
 def test_frame_preserves_original_isotopes(self):
  text='[2H]O[2H]';before=Chem.MolToSmiles(Chem.MolFromSmiles(text));self.assertEqual(framework(text),'O');self.assertEqual(before,Chem.MolToSmiles(Chem.MolFromSmiles(text)))
 def test_nonisotope_dimensions_unchanged(self):
  pairs=[('CCO','COC'),('[2H]O[2H]','O'),('CC(=O)O','CC(=O)[O-]'),('C[C@H](O)CC','C[C@@H](O)CC'),('C[NH3+].[Cl-]','CN')]
  for a,b in pairs:
   for d in ('constitution','stereochemistry','tautomer','protonation_charge','components','component_stoichiometry','hydration_solvation','electronic_state'):
    with self.subTest(a=a,b=b,dimension=d):self.assertEqual(self.rel(a,b,d),original(assertion(a,d),assertion(b,d),d))

if __name__=='__main__':unittest.main()
