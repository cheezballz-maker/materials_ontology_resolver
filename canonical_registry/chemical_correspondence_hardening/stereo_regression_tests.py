import copy,hashlib,json,random,unittest
from pathlib import Path
import bootstrap
import stereo_comparison as stereo
from rdkit import Chem
from assessment import assess
from record_inputs import load
H=Path(__file__).resolve().parent
B=H.parent
CONTROLS=json.loads((H/'controls/stereo_controls.json').read_text())
CASES={c['case_id']:c for c in json.loads((B/'real_world_validation/reference_corpus/reference_cases.json').read_text())['cases']}
class StereoTests(unittest.TestCase):
 def test_prospective_controls(self):
  freeze=json.loads((H/'controls/freeze.json').read_text());self.assertEqual(hashlib.sha256((H/'controls/stereo_controls.json').read_bytes()).hexdigest(),freeze['stereo_controls.json'])
  for c in CONTROLS['cases']:
   with self.subTest(c=c['id']):self.assertEqual(stereo.compare(c['left'],c['right'])['result'],c['expected'])
  from evidence_adapters import assertion
  # Keep the pre-existing NOT_APPLICABLE specificity boundary on malformed
  # assertions as well as ordinary unknown/finite-set source scopes.
  for text,state,expected in [('CCO','NOT_APPLICABLE','NOT_APPLICABLE'),('CC[C@@H](C)O','NOT_APPLICABLE','UNKNOWN'),('CC[C@@H](C)O','UNSPECIFIED','UNKNOWN'),('CC[C@@H](C)O','SET','UNKNOWN')]:
   with self.subTest(assertion_state=state,text=text):self.assertEqual(stereo.compare_assertions(assertion(text,'stereochemistry',state),assertion(text,'stereochemistry'),'stereochemistry'),expected)
 def test_random_atom_order_preserves_constraints(self):
  rng=random.Random(41030)
  for c in CONTROLS['cases']:
   if c['id']=='enhanced_relative':continue
   for _ in range(12):
    graphs=[]
    for text in (c['left'],c['right']):
     m=stereo.parse(text);indices=list(range(m.GetNumAtoms()));rng.shuffle(indices)
     graphs.append(Chem.MolToSmiles(Chem.RenumberAtoms(m,indices),canonical=False,isomericSmiles=True))
    with self.subTest(c=c['id'],graphs=graphs):self.assertEqual(stereo.compare(*graphs)['result'],c['expected'])
 def test_complete_tetrahedral_and_double_bond_enumerations(self):
  from rdkit.Chem.EnumerateStereoisomers import EnumerateStereoisomers
  for framework in ('FC(Cl)C(Br)I','CC(O)C(O)C','FC=CC(O)C(Cl)Br','CC1CCC(C)C1O'):
   variants=list(EnumerateStereoisomers(Chem.MolFromSmiles(framework)))
   for a in variants:
    for b in variants:
     x,y=Chem.MolToSmiles(a),Chem.MolToSmiles(b)
     with self.subTest(x=x,y=y):self.assertEqual(stereo.compare(x,y)['result'],'EQUIVALENT' if x==y else 'DIFFERENT')
 def test_symmetry_bound_abstains(self):
  self.assertEqual(stereo.compare('CC(O)C(O)C','CC(O)C(O)C',mapping_limit=1)['reason'],'SYMMETRY_ENUMERATION_LIMIT')
 def test_unsupported_non_tetrahedral_stereo(self):
  self.assertEqual(stereo.compare('Cl[Pt@SP1](Cl)(N)N','Cl[Pt@SP1](Cl)(N)N')['result'],'UNKNOWN')
 def test_partial_symmetry_mapping_can_avoid_contradiction(self):
  r=stereo.compare('C[C@H](O)C(O)C','C[C@@H](O)[C@@H](O)C')
  self.assertEqual(r['result'],'UNKNOWN');self.assertTrue(any(m['contradictions'] for m in r['mappings']));self.assertTrue(any(not m['contradictions'] for m in r['mappings']))
 def test_no_naive_CIP_comparison(self):
  r=stereo.compare('C[C@H](O)[C@H](O)C','C[C@@H](O)[C@@H](O)C')
  self.assertGreater(r['valid_mapping_count'],1);self.assertTrue(any(m['contradictions'] for m in r['mappings']));self.assertTrue(any(not m['contradictions'] for m in r['mappings']))
 def test_RW30_changed_RW23_RW24_preserved(self):
  for key,expected in [('RW30','CHEMICALLY_DIFFERENT'),('RW23','CHEMICALLY_UNRESOLVED'),('RW24','CHEMICALLY_UNRESOLVED')]:
   with self.subTest(key=key):self.assertEqual(assess(*load(CASES[key]),enabled=True)['represented_structure_comparison']['status'],expected)
 def test_default_off(self):self.assertFalse(assess(*load(CASES['RW30']))['diagnostic_enabled'])
 def test_inputs_unchanged(self):
  s,t=load(CASES['RW30']);before=copy.deepcopy((s.evidence_package.to_dict(),t.provenance));assess(s,t,enabled=True);self.assertEqual(before,(s.evidence_package.to_dict(),t.provenance))
 def test_legacy_comparator_unchanged(self):
  from correspondence_assessment import assess as old
  self.assertEqual(old(*load(CASES['RW30']),enabled=True)['represented_structure_comparison']['status'],'CHEMICALLY_UNRESOLVED')

if __name__=='__main__':unittest.main(verbosity=2)
