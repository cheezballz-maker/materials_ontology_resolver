import unittest,json
from pathlib import Path
rows=json.loads((Path(__file__).parent/'probe_results.json').read_text())
def row(name):return next(r for r in rows if r['name']==name)
class TraceTests(unittest.TestCase):
 def test_public_equivalence(self):
  for r in rows:
   with self.subTest(name=r['name']):self.assertTrue(r['baseline_equal'])
 def test_indicated_hydrogen_controls(self):
  for name,locant,element,h in [('1H-pyrrole','1','N',1),('3H-pyrrole','3','C',2),('1H-imidazole','1','N',1)]:
   with self.subTest(name=name):
    e=row(name)['events'][0];self.assertTrue(e['bounded_mapping']);self.assertEqual((e['locant'],e['element'],e['final_explicit_h_neighbors']),(locant,element,h))
 def test_added_hydrogen(self):
  for name in ['pyridin-2(1H)-one','quinolin-2(1H)-one']:
   e=row(name)['events'][0];self.assertEqual(e['kind'],'addedHydrogen');self.assertEqual(e['source_token'],'2(1H)-');self.assertEqual(e['locant'],'1');self.assertTrue(e['bounded_mapping'])
 def test_nested_ownership(self):
  for name,first,second in [('3-(1H-imidazol-2-yl)-1H-pyrazole','imidazol','pyrazol'),('2-(1H-pyrazol-3-yl)-1H-imidazole','pyrazol','imidazol')]:
   es=sorted(row(name)['events'],key=lambda e:e['start']);self.assertEqual([e['owner'] for e in es],[first,second]);self.assertNotEqual(es[0]['atom_id'],es[1]['atom_id']);self.assertTrue(all(e['bounded_mapping'] for e in es));self.assertEqual(len({e['start'] for e in es}),2)
 def test_substitution_consumes_parent_hydrogen(self):
  for name in ['1-methyl-1H-pyrazole','1-methyl-1H-imidazole']:
   e=row(name)['events'][0];self.assertTrue(e['bounded_mapping']);self.assertEqual(e['final_explicit_h_neighbors'],0)
 def test_no_explicit_descriptor_is_not_a_claim(self):
  for name in ['pyrazole','pyrrole','triazine','pyridin-2-ol']:self.assertEqual(row(name)['events'],[])
 def test_generated_hydrogen_is_unattributed(self):
  es=row('anthrone')['events'];self.assertTrue(es);self.assertTrue(all(e['start']==-1 and not e['bounded_mapping'] for e in es))
 def test_clone_abstention(self):
  for name in ['1H-pyrazole - water (1:2)','1H-pyrazole - water (2:1)','3,4-dimethyl-1H-pyrazole']:self.assertEqual(row(name)['mapping_only_status'],'ABSTAIN_CLONE')
 def test_repeated_word_abstention(self):
  es=row('1H-pyrazole 1H-pyrazole')['events'];self.assertEqual(len(es),2);self.assertTrue(all(not e['bounded_mapping'] for e in es))
 def test_normalization_abstention(self):
  self.assertEqual(row('1H−pyrazole')['status'],'SUCCESS');self.assertFalse(row('1H−pyrazole')['events'][0]['bounded_mapping'])
 def test_warning_has_no_selected_evidence(self):
  r=row('methyl-1H-pyrazole');self.assertEqual(r['status'],'WARNING');self.assertTrue(r['ambiguous']);self.assertEqual(r['events'],[]);self.assertIn('APPEARS_AMBIGUOUS',r['warnings'])
 def test_failures_have_no_evidence(self):
  for name in ['9H-pyrazole','1H-pyrazole garbage']:self.assertEqual(row(name)['status'],'FAILURE');self.assertEqual(row(name)['events'],[])
 def test_sequential_parses_are_isolated(self):
  self.assertEqual(rows[0]['events'],rows[-1]['events']);self.assertEqual(rows[-1]['events'][0]['selected_attempt'],1)
 def test_same_result_atom_and_locant(self):
  for r in rows:
   for e in r['events']:self.assertTrue(e['same_final_object']);self.assertTrue(e['cml_locant_matches'])
if __name__=='__main__':unittest.main(verbosity=2)
