import concurrent.futures,unittest
from semantic_adapter import trace

class SemanticAdapterTests(unittest.TestCase):
 def test_indicated_and_added_distinct(self):
  for name,kind in [('1H-pyrrole','INDICATED_HYDROGEN'),('3H-pyrrole','INDICATED_HYDROGEN'),('pyridin-2(1H)-one','ADDED_INDICATED_HYDROGEN'),('quinolin-2(1H)-one','ADDED_INDICATED_HYDROGEN')]:
   with self.subTest(name=name):
    r=trace(name);self.assertEqual(r['constraint'],'UNKNOWN');self.assertEqual(r['claims'][0]['semantic_type'],kind);self.assertEqual(r['claims'][0]['mapping_status'],'MAPPED_BOUNDED')
 def test_substitution_has_no_literal_final_h_inference(self):
  for n in ('1-methyl-1H-pyrazole','1-methyl-1H-imidazole'):
   r=trace(n);self.assertEqual(r['constraint'],'UNKNOWN');self.assertEqual(r['claims'][0]['operations'],'NOT_CAPTURED')
 def test_nested_ownership(self):
  for n in ('3-(1H-imidazol-2-yl)-1H-pyrazole','2-(1H-pyrazol-3-yl)-1H-imidazole'):
   r=trace(n);claims=r['claims'];self.assertEqual(len(claims),2);self.assertEqual(len({c['cml_atom'] for c in claims}),2);self.assertTrue(all(c['mapping_status']=='MAPPED_BOUNDED' for c in claims))
 def test_generated_default_no_explicit_support(self):
  for n in ('anthrone','pyrazole'):
   r=trace(n);self.assertEqual(r['constraint'],'UNKNOWN');self.assertFalse(any(c['explicit_or_generated']=='EXPLICIT' for c in r['claims']))
 def test_warning_failure_unicode_abstain(self):
  for n in ('methyl-1H-pyrazole','9H-pyrazole','1H−pyrazole'):
   r=trace(n);self.assertEqual(r['status'],'UNRESOLVED');self.assertEqual(r['constraint'],'UNKNOWN')
 def test_repeated_words_and_clone_do_not_map(self):
  for n in ('1H-pyrazole 1H-pyrazole','1H-pyrazole - water (2:1)'):
   r=trace(n);self.assertEqual(r['constraint'],'UNKNOWN');self.assertFalse(any(c['mapping_status']=='MAPPED_BOUNDED' for c in r['claims']))
 def test_process_isolation_parallel(self):
  names=['1H-pyrrole','pyridin-2(1H)-one','anthrone','9H-pyrazole']
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(trace,names))
  self.assertEqual(results[0]['claims'][0]['semantic_type'],'INDICATED_HYDROGEN')
  self.assertEqual(results[1]['claims'][0]['semantic_type'],'ADDED_INDICATED_HYDROGEN')
  self.assertFalse(any(c['explicit_or_generated']=='EXPLICIT' for c in results[2]['claims']))
  self.assertEqual(results[3]['status'],'UNRESOLVED')
 def test_missing_runtime_failure_is_closed(self):
  import semantic_adapter
  original=semantic_adapter.TRACE
  try:
   from pathlib import Path
   semantic_adapter.TRACE=Path('missing-artifact.jar');r=trace('1H-pyrrole')
   self.assertEqual(r['status'],'UNRESOLVED');self.assertEqual(r['constraint'],'UNKNOWN')
  finally:semantic_adapter.TRACE=original

if __name__=='__main__':unittest.main()
