import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'nomenclature_semantic_integration'))
from semantic_adapter import trace
from graph_correspondence import correspond,positions_agree

class GraphTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.source=trace('1H-pyrrole')
 def test_all_isomorphisms_not_atom_order(self):
  m=correspond(self.source['same_result_cml'],self.source['smiles']);self.assertEqual(m['status'],'AMBIGUOUS');self.assertEqual(len(m['mappings']),2)
  self.assertEqual(positions_agree(m,'a1',lambda i:i==0),'ALL_TRUE')
  self.assertEqual(positions_agree(m,'a2',lambda i:i==1),'UNKNOWN')
 def test_mapping_cap_abstains(self):
  self.assertEqual(correspond(self.source['same_result_cml'],self.source['smiles'],1)['reason'],'ISOMORPHISM_LIMIT_REACHED')
 def test_incompatible_candidate_does_not_claim_semantic_difference(self):
  m=correspond(self.source['same_result_cml'],'C1CCNC1');self.assertEqual(m['status'],'UNKNOWN');self.assertEqual(positions_agree(m,'a1',lambda _:False),'UNKNOWN')
 def test_charged_isotope_and_stereo_do_not_silently_match(self):
  for candidate in ('[nH+]1cccc1','[15nH]1cccc1','C[C@H](O)CC'):
   self.assertEqual(correspond(self.source['same_result_cml'],candidate)['status'],'UNKNOWN')
 def test_multicomponent_mismatch(self):
  self.assertEqual(correspond(self.source['same_result_cml'],'c1cc[nH]c1.O')['status'],'UNKNOWN')
 def test_invalid_input_is_unknown(self):
  self.assertEqual(correspond('<bad>',self.source['smiles'])['status'],'UNKNOWN')

if __name__=='__main__':unittest.main()
