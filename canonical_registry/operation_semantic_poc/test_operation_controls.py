import json,unittest
from pathlib import Path
H=Path(__file__).resolve().parent

class OperationObservationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cases=json.loads((H/'operation_lineage_controls.json').read_text(encoding='utf8'))['cases']
 def find(self,name):return next(x for x in self.cases if x['name']==name)
 def test_explicit_parent_and_ordered_observations(self):
  c=self.find('3H-pyrrole')['claims'][0];self.assertEqual(c['source_text'],'3H-');self.assertTrue(c['parent_state']);self.assertTrue(c['same_result_object'])
  self.assertGreaterEqual(sum(x['event']=='BOND_CREATE_1' and x['relative_to_parent']=='AFTER' for x in c['operations']),2)
 def test_substitution_is_observed_but_source_provenance_unknown(self):
  c=self.find('1-methyl-1H-pyrazole');self.assertEqual(c['constraint_state'],'UNKNOWN')
  self.assertTrue(any(o['event'].startswith('BOND_CREATE') for o in c['claims'][0]['operations']))
  self.assertTrue(all(o['source_provenance']=='NOT_CAPTURED' for o in c['claims'][0]['operations']))
 def test_added_h_and_suffix_still_incomplete(self):
  c=self.find('pyridin-2(1H)-one');self.assertEqual(c['claims'][0]['semantic_type'],'addedHydrogen');self.assertFalse(c['operation_lineage_complete']);self.assertEqual(c['constraint_state'],'UNKNOWN')
 def test_all_controls_fail_closed(self):
  self.assertTrue(all(c['constraint_state']=='UNKNOWN' for c in self.cases))
  for name in ('9H-pyrazole','methyl-1H-pyrazole','1H−pyrazole','1H-pyrazole - water (2:1)'):
   self.assertEqual(self.find(name)['constraint_state'],'UNKNOWN')
 def test_ordered_nested_claims_not_collapsed(self):
  c=self.find('3-(1H-imidazol-2-yl)-1H-pyrazole');self.assertEqual(len(c['claims']),2);self.assertEqual(len({x['atom'] for x in c['claims']}),2)

if __name__=='__main__':unittest.main()
