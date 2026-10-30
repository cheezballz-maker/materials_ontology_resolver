import copy,unittest
from rdkit import Chem
from shared.semantic_interface import validate_interpretation
from shared.structural_comparator import parse,mappings,mapping_outcome,compare_candidate
from architecture_B.implementation.interpreter import interpret_name,validate_candidate
from architecture_B.implementation.semantic_operations import compose

class SharedTests(unittest.TestCase):
 def test_source_span_and_reference_integrity(self):
  x=interpret_name('1-methyl-1H-pyrazole');validate_interpretation(x)
  for mutation in ('span','claim_ref','operation_ref','rule_ref','duplicate'):
   y=copy.deepcopy(x)
   if mutation=='span':y.source_claims[0]['source_span']['end']=9
   elif mutation=='claim_ref':y.structural_constraints[0]['source_claim_ids']=['missing']
   elif mutation=='operation_ref':y.structural_constraints[0]['dependencies']=['missing']
   elif mutation=='rule_ref':y.semantic_operations[0]['rule_ids']=['R99']
   else:y.source_claims[1]['claim_id']=y.source_claims[0]['claim_id']
   with self.subTest(mutation=mutation),self.assertRaises(Exception):validate_interpretation(y)
 def test_benzene_symmetry_and_kekule(self):
  a=parse('c1ccccc1');b=parse('C1=CC=CC=C1');ms=mappings(a,b)
  self.assertEqual(len(ms),12);self.assertEqual(mapping_outcome([True for x in ms]),'SUPPORTED');self.assertEqual(mapping_outcome([x[0]==0 for x in ms]),'UNKNOWN')
 def test_limit_abstains(self):
  with self.assertRaisesRegex(ValueError,'MAPPING_LIMIT'):mappings(parse('c1ccccc1'),parse('c1ccccc1'),1)
 def test_no_trailing_text_or_unapproved_forms(self):
  for s in ('CN1C=CC=N1 garbage','CN1C=CC=N1.Cl','[2H]C1=CC=NN1C','C[NH+]1C=CN=C1'):
   with self.subTest(s=s):self.assertEqual(compare_candidate(compose('pyrazole',1),s)[0],'UNKNOWN')
 def test_representations_and_difference(self):
  a=interpret_name('1-methyl-1H-pyrazole')
  self.assertEqual(validate_candidate(a,'CN1C=CC=N1').result,'SUPPORTED')
  self.assertEqual(validate_candidate(a,'Cn1cccn1').result,'SUPPORTED')
  result=validate_candidate(a,'CC1=CC=NN1');self.assertEqual(result.result,'DIFFERENT');self.assertEqual(result.reason_codes,['ATTACHMENT_POSITION_DIFFERENT'])
 def test_all_eight_scope_variations_generate_single_operation(self):
  for alkyl in ('methyl','ethyl','propyl','butyl'):
   for parent in ('pyrazole','imidazole'):
    x=interpret_name(f'1-{alkyl}-1H-{parent}');self.assertEqual(x.scope_status,'IN_CONTRACT');self.assertEqual(len(x.semantic_operations),1)
 def test_scope_requires_full_input(self):
  for n in ('methyl-1H-pyrazole','1-methyl-1H-pyrazole hydrochloride','1-methyl-1H-pyrazol-3-one'):
   self.assertEqual(interpret_name(n).scope_status,'OUT_OF_CONTRACT')
 def test_conflicting_source_parent_is_not_alias_equivalence(self):
  x=interpret_name('1-methyl-1H-imidazole')
  v=validate_candidate(x,'CN1C=CC=N1')
  self.assertEqual(v.result,'DIFFERENT');self.assertEqual(v.reason_codes,['PARENT_CONNECTIVITY_DIFFERENT'])

if __name__=='__main__':unittest.main()
