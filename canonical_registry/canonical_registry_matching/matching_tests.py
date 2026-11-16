import copy,hashlib,json,sqlite3,unittest
from pathlib import Path
import bootstrap
import comparison_session as current
import assessment as hardened
from registry_matching_models import MatchingInput,RetrievalPolicy
from registry_identity_adapter import RegistrySnapshot
from registry_matcher import RegistryMatcher,compare_registry_candidate
from matching_control_inputs import matching_input,fixture_registry
from record_inputs import load
H=Path(__file__).resolve().parent;B=H.parent
CONTROLS={c['id']:c for k in ('development','heldout') for c in json.loads((H/f'controls/{k}_controls.json').read_text())['cases']}
class MatchingTests(unittest.TestCase):
 def setup_case(self,key,validator=None):
  c=CONTROLS[key];snapshot=RegistrySnapshot(fixture_registry(c));return c,matching_input(c),RegistryMatcher(snapshot,official_validator=validator)
 def test_frozen_expectations_and_results(self):
  freeze=json.loads((H/'controls/benchmark_freeze.json').read_text())['files']
  for n,d in freeze.items():self.assertEqual(hashlib.sha256((H/'controls'/n).read_bytes()).hexdigest(),d)
  r=json.loads((H/'evaluation/benchmark_results.json').read_text());self.assertEqual(r['summary']['cases'],r['summary']['passed']);self.assertEqual(r['summary']['unsafe_unique_match_proposals'],0)
 def test_read_only_fixture_connection_denies_writes(self):
  _,_,m=self.setup_case('D01');db=sqlite3.connect(m.registry.path.as_uri()+'?mode=ro',uri=True)
  try:
   with self.assertRaises(sqlite3.OperationalError):db.execute("DELETE FROM substance_alias")
  finally:db.close()
  m.registry.assert_unchanged()
 def test_registry_hash_detects_snapshot_change(self):
  _,_,m=self.setup_case('D01');db=sqlite3.connect(m.registry.path)
  try:db.execute("INSERT INTO substance_alias VALUES('FIX_1','unit-only-alias')");db.commit()
  finally:db.close()
  with self.assertRaises(RuntimeError):m.registry.assert_unchanged()
  fixture_registry(CONTROLS['D01'])
 def test_input_not_mutated(self):
  _,s,m=self.setup_case('D01');before=copy.deepcopy(s.concept.evidence_package.to_dict());m.match(s);self.assertEqual(before,s.concept.evidence_package.to_dict())
 def test_shared_ancestry_does_not_block_structural_comparison(self):
  _,s,m=self.setup_case('D01');m.registry.entries['FIX_1']['candidate'].provenance['lineage_roots']=s.concept.provenance['lineage_roots']
  r=m.match(s);self.assertEqual(r['status'],'UNIQUE_CANONICAL_MATCH');self.assertEqual(r['candidate_results'][0]['independence_status'],'KNOWN_DEPENDENT')
 def test_explicit_flag_cannot_convert_name_derivation(self):
  _,s,m=self.setup_case('D18');s.form_assertion={'explicit_structure':True};r=m.match(s)
  self.assertFalse(r['admission']['input_classification']['verified_explicit_structure']);self.assertEqual(r['admission']['external_corroboration_exemption'],'NOT_APPLICABLE')
 def test_successful_name_hypothesis_is_not_binding_source_graph(self):
  _,s,m=self.setup_case('D29');r=m.match(s);self.assertTrue(r['retrieval']['indexed_candidate_ids']);self.assertEqual(r['status'],'MATCH_UNRESOLVED');self.assertIsNone(r['matching_proposal'])
 def test_alias_and_formula_cannot_prove_exact(self):
  _,s,m=self.setup_case('D25');r=m.match(s);self.assertEqual(r['status'],'NO_MATCH_IN_SEARCHED_REGISTRY');self.assertTrue(r['retrieval']['indexed_candidate_ids']);self.assertEqual(r['uniqueness']['accounted_records'],r['uniqueness']['snapshot_records']);self.assertFalse(r['supported_candidate_ids'])
 def test_broad_name_candidates_without_identity_assignment(self):
  _,s,m=self.setup_case('D27');r=m.match(s);self.assertEqual(len(r['retrieval']['indexed_candidate_ids']),2);self.assertEqual(r['status'],'MATCH_UNRESOLVED')
 def test_multiple_and_unresolved_never_pick_first(self):
  for key in ('D12','D13','D26','D28'):
   with self.subTest(key=key):
    c,s,m=self.setup_case(key);r=m.match(s,RetrievalPolicy(**c.get('retrieval',{}),strategy='exhaustive'));self.assertIsNone(r['unique_matched_substance_id']);self.assertIsNone(r['diagnostic_reuse_proposal'])
 def test_empty_indexed_search_not_negative(self):
  _,s,m=self.setup_case('D15');r=m.match(s,RetrievalPolicy(exhaustive=False));self.assertFalse(r['retrieval']['search_complete']);self.assertEqual(r['status'],'MATCH_UNRESOLVED')
 def test_empty_complete_registry_bounded_negative(self):
  _,s,m=self.setup_case('H11');r=m.match(s);self.assertTrue(r['retrieval']['search_complete']);self.assertEqual(r['status'],'NO_MATCH_IN_SEARCHED_REGISTRY');self.assertFalse(r['uniqueness']['global_nonexistence_established'])
 def test_missing_graph_is_retained_as_unknown(self):
  _,s,m=self.setup_case('D28');r=m.match(s);self.assertEqual(len(r['candidate_results']),2);self.assertIn('FIX_2',r['unresolved_possible_candidate_ids'])
 def test_registry_identifier_contradiction_blocks_exact(self):
  _,s,m=self.setup_case('H08');r=m.match(s);self.assertEqual(r['status'],'MATCH_UNRESOLVED');self.assertIn('CANDIDATE_IDENTIFIER_STRUCTURE_INCONSISTENCY',r['candidate_results'][0]['candidate_obligations'])
 def test_equivalent_graph_retrieved_without_structural_identifier(self):
  c=CONTROLS['D01'];path=fixture_registry(c);db=sqlite3.connect(path)
  try:db.execute("DELETE FROM substance_identifier WHERE substance_id='FIX_1'");db.commit()
  finally:db.close()
  try:
   r=RegistryMatcher(RegistrySnapshot(path)).match(matching_input(c));self.assertEqual(r['status'],'UNIQUE_CANONICAL_MATCH')
   routes=r['retrieval']['routes']['FIX_1'];self.assertFalse(any(x['route']=='FULL_INCHIKEY' for x in routes));self.assertTrue(any(x['route']=='EXPLICIT_GRAPH_SERIALIZATION' for x in routes))
   (H/'evaluation/missing_identifier_retrieval_control.json').write_text(json.dumps(dict(origin='ADDITIONAL_SYNTHETIC_UNIT_FIXTURE_NOT_IN_FROZEN_BENCHMARK',expected='UNIQUE_CANONICAL_MATCH',result=r),indent=2)+'\n')
  finally:fixture_registry(c)
 def test_partial_stereo_contradiction_retained(self):
  _,s,m=self.setup_case('D05');r=m.match(s);self.assertEqual(r['candidate_results'][0]['dimension_comparisons']['stereochemistry'],'EXACT_INCOMPATIBLE');self.assertEqual(r['status'],'MATCH_UNRESOLVED')
 def test_unbound_structure_not_exempt(self):
  _,s,m=self.setup_case('D30');r=m.match(s);self.assertFalse(r['admission']['input_classification']['verified_explicit_structure']);self.assertIsNone(r['matching_proposal'])
 def test_official_validation_must_match_source_graph(self):
  _,s,m=self.setup_case('D01');from chemistry import describe
  other=describe('COC');s.official_validation={'status':'SUCCESS','agrees':True,'inchi':other['inchi'],'inchikey':other['inchikey']};r=m.match(s)
  self.assertEqual(r['admission']['existing_policy_result']['status'],'UNRESOLVED');self.assertFalse(r['admission']['official_validation']['agrees'])
 def test_admission_does_not_authorize_reuse(self):
  r=json.loads((H/'evaluation/benchmark_results.json').read_text())['cases'][0]['result'];self.assertTrue(r['admission']['admission_eligible']);self.assertFalse(r['id_reuse_authorized']);self.assertFalse(r['matching_proposal']['persisted'])
 def test_cached_and_uncached_comparators_agree(self):
  # Independent of this matching benchmark: replay all 31 preserved source /
  # reference inputs through both function bindings, comparing full dimensions.
  cases=json.loads((B/'real_world_validation/reference_corpus/reference_cases.json').read_text())['cases']
  for c in cases:
   with self.subTest(case=c['case_id']):
    s,t=load(c);a=hardened.qualify_source(s);b=current.qualify_source(s)
    self.assertEqual(a['state'],b['state']);x=hardened.compare(a,hardened.qualify_candidate(t,a));y=current.compare(b,current.qualify_candidate(t,b))
    self.assertEqual(x['dimension_comparisons'],y['dimension_comparisons']);self.assertEqual(x['correspondence_status'],y['correspondence_status'])
 def test_memoized_values_cannot_be_mutated(self):
  d=current.descriptor('CCO');d['smiles']='COC';self.assertEqual(current.descriptor('CCO')['smiles'],'CCO')
  a=current.assertions('CCO');a['constitution']['state']='UNKNOWN';self.assertEqual(current.assertions('CCO')['constitution']['state'],'EXACT')

def main():
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MatchingTests));(H/'evaluation/matching_tests.json').write_text(json.dumps(dict(tests_run=r.testsRun,failures=len(r.failures),errors=len(r.errors),passed=r.wasSuccessful()),indent=2)+'\n');assert r.wasSuccessful()
if __name__=='__main__':main()
