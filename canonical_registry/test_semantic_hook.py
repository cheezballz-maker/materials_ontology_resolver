import unittest
from test_evidence_retrieval import engine,Provider
from nomenclature_semantic_integration import semantic_adapter

class SemanticHookTests(unittest.TestCase):
 def test_experimental_trace_precedes_provider_without_promotion(self):
  p=Provider();r=engine({'pyridin-2(1H)-one':'O=c1cccc[nH]1'},p);r.semantic_adapter=semantic_adapter
  outcome=r.evaluate('pyridin-2(1H)-one')
  self.assertIn('nomenclature_semantics',outcome['evidence'])
  self.assertEqual(outcome['evidence']['nomenclature_semantics']['constraint'],'UNKNOWN')
  self.assertEqual(outcome['evidence']['local_eligibility']['status'],'NOT_ELIGIBLE')
  self.assertEqual(outcome['status'],'UNRESOLVED');self.assertEqual(p.queries,[])
 def test_trace_failure_falls_back_without_impact(self):
  class Broken:
   def trace(self,name):raise RuntimeError('failure')
  e=engine({'ethanol':'CCO'},Provider());before=e.evaluate('ethanol');e.semantic_adapter=Broken();after=e.evaluate('ethanol')
  self.assertEqual(before['status'],after['status']);self.assertEqual(before['reason_codes'],after['reason_codes'])
  self.assertEqual(after['evidence']['nomenclature_semantics']['constraint'],'UNKNOWN')

if __name__=='__main__':unittest.main()
