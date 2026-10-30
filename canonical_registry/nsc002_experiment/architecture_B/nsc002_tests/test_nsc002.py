import copy,unittest
from rdkit import Chem
from architecture_B.nsc002_interpreter.grammar import recognize
from architecture_B.nsc002_interpreter.interpreter import interpret_name,validate_candidate
from architecture_B.nsc002_interpreter.schema_validation import validate
from architecture_B.nsc002_interpreter.candidate_comparison import extract

class NSC002Tests(unittest.TestCase):
 def test_multiplicity_and_full_consumption(self):
  for s in ('1,3-dibromobenzene','1-bromo-3-chlorobenzene','1-CHLORO-2-NITROBENZENE'):
   with self.subTest(s=s):self.assertIsNotNone(recognize(s))
  for s in ('1,3-bromobenzene','1-dibromobenzene','1,1-dibromobenzene','1-bromo-2-bromobenzene','1-bromo-3-chlorobenzene hydrochloride','1-bromo-3-chlorobenzene-4-ol'):
   with self.subTest(s=s):self.assertIsNone(recognize(s))
 def test_source_spans_and_cross_references(self):
  x=interpret_name('1,3-dibromobenzene');validate(x)
  y=copy.deepcopy(x);y.structural_constraints[0]['source_claim_ids']=['missing']
  with self.assertRaises(ValueError):validate(y)
  y=copy.deepcopy(x);y.source_claims[0]['source_span']['end']=1
  with self.assertRaises(ValueError):validate(y)
 def test_symmetry_and_position(self):
  x=interpret_name('1-bromo-3-chlorobenzene')
  self.assertEqual(validate_candidate(x,'ClC1=CC=CC(Br)=C1').result,'SUPPORTED')
  v=validate_candidate(x,'Brc1ccc(Cl)cc1');self.assertEqual(v.result,'DIFFERENT');self.assertEqual(v.reason_codes,['SUBSTITUENT_POSITION_DIFFERENT'])
 def test_internal_nitro_and_other_charge(self):
  x=interpret_name('1-chloro-2-nitrobenzene')
  self.assertEqual(validate_candidate(x,'Clc1ccccc1[N+](=O)[O-]').result,'SUPPORTED')
  self.assertEqual(validate_candidate(x,'Clc1ccccc1[N+]([O-])=O').result,'SUPPORTED')
  self.assertEqual(validate_candidate(x,'Clc1ccccc1[NH+](=O)O').result,'UNKNOWN')
 def test_extra_components_and_unsupported_form_abstain(self):
  x=interpret_name('1-bromo-3-chlorobenzene')
  for s in ('Brc1cccc(Cl)c1.Cl','[13c]1(Br)cccc(Cl)c1','Brc1cccc(Cl)c1 garbage','Brc1cccc(Cl)c1O'):
   with self.subTest(s=s):self.assertEqual(validate_candidate(x,s).result,'UNKNOWN')
 def test_identity_boundary_and_joint_operation(self):
  x=interpret_name('1-bromo-3-chlorobenzene');v=validate_candidate(x,'Brc1ccc(Cl)cc1')
  self.assertEqual(v.operation_results[0]['scope'],'joint_ring_pattern');self.assertEqual(v.dimension_results[1]['result'],'NOT_ESTABLISHED')
 def test_reordered_graphs_are_identity_invariant(self):
  x=interpret_name('1-bromo-3-chlorobenzene');m=Chem.MolFromSmiles('Brc1cccc(Cl)c1')
  for shift in range(m.GetNumAtoms()):
   order=list(range(shift,m.GetNumAtoms()))+list(range(shift));variant=Chem.RenumberAtoms(m,order)
   v=validate_candidate(x,Chem.MolToSmiles(variant,canonical=False,kekuleSmiles=bool(shift%2)));self.assertEqual(v.result,'SUPPORTED');self.assertEqual(v.evidence['mapped_ring_automorphisms_considered'],12)
 def test_symmetric_source_locants_do_not_force_difference(self):
  a=interpret_name('1,3-dibromobenzene');b=interpret_name('1,5-dibromobenzene');candidate='Brc1cccc(Br)c1'
  self.assertEqual(validate_candidate(a,candidate).result,'SUPPORTED');self.assertEqual(validate_candidate(b,candidate).result,'SUPPORTED')

if __name__=='__main__':unittest.main()
