"""Explicitly synthetic policy inputs; never real chemical corroborations."""
import copy,json,unittest
from pathlib import Path
import bootstrap
from chemistry import describe
from policy import decision
from test_provider_qualification import row
from evidence_independence_audit import classify,REQUIRED
H=Path(__file__).resolve().parent
def fixtures():
 official={'status':'SUCCESS','agrees':True,'fixture':'SYNTHETIC_SATISFIED_OFFICIAL_VALIDATION_INPUT_NOT_A_REAL_OBSERVATION'}
 common=dict(local=describe('CCO'),official=official,external={'status':'SUCCESS','rows':[row('CCO')]},name='ethanol',source_complete=True)
 cases=[]
 def add(case_id,expected,reason,**overrides):
  args=copy.deepcopy(common);args.update(overrides);r=decision(**args)
  cases.append(dict(id=case_id,origin='SYNTHETIC_POLICY_FIXTURE',count_as_real_corroboration=False,inputs=args,expected=expected,expected_reason=reason,actual=r,passed=r['status']==expected and reason in r['reason_codes']))
 add('qualified_route_unknown_upstream_dependence','AUTO_ACCEPT','INDEPENDENT_EXACT_FORM_CORROBORATION')
 independent=row('CCO');independent['provenance']['source_dependence_classification']='SOURCE_INDEPENDENT'
 add('qualified_route_declared_independence','AUTO_ACCEPT','INDEPENDENT_EXACT_FORM_CORROBORATION',external={'status':'SUCCESS','rows':[independent]})
 add('no_external_evidence_nontyped','UNRESOLVED','NO_QUALIFYING_CORROBORATION',external={'status':'NOT_QUERIED','rows':[]})
 dependent=row('CCO');dependent['provenance']['source_dependence_classification']='SOURCE_DEPENDENCE_KNOWN'
 add('known_dependence_rejected','UNRESOLVED','NO_QUALIFYING_CORROBORATION',external={'status':'SUCCESS','rows':[dependent]})
 add('official_validation_missing','UNRESOLVED','OFFICIAL_INCHI_NOT_CONFIRMED',official=None)
 add('incomplete_source_not_filled','UNRESOLVED','SOURCE_INTERPRETATION_INCOMPLETE',source_complete=False)
 add('verified_stereo_contradiction','CONFLICT','VERIFIED_SOURCE_IDENTITY_CONTRADICTION',local=describe('CC[C@@H](C)O'),name='(R)-butan-2-ol',external={'status':'SUCCESS','rows':[row('CC[C@H](C)O',name='(R)-butan-2-ol')]})
 add('existing_explicit_structure_exemption','AUTO_ACCEPT','SOURCE_STRUCTURE_VALIDATED',external={'status':'NOT_QUERIED','rows':[]},assertion={'explicit_structure':True})
 add('NIST_has_no_qualifying_profile','UNRESOLVED','NO_QUALIFYING_CORROBORATION',external={'status':'SUCCESS','rows':[row('CCO',provider='NIST_VALIDATION_MATERIAL')]})
 add('candidate_derived_key_lookup_insufficient','UNRESOLVED','NO_QUALIFYING_CORROBORATION',external={'status':'SUCCESS','rows':[row('CCO',kind='InChIKey',origin='validated_hypothesis',value=describe('CCO')['inchikey'])]})
 return cases
class PolicyTests(unittest.TestCase):
 def test_policy_fixtures(self):
  for r in fixtures():
   with self.subTest(r=r['id']):self.assertTrue(r['passed'],r['actual']['reason_codes'])
 def test_different_database_roots_not_independence(self):
  self.assertEqual(classify({'upstream_roots':['PubChem:1']},{'upstream_roots':['ChEBI:2']})['status'],'INDEPENDENCE_UNESTABLISHED')
 def test_shared_graph_origin_dependent(self):
  self.assertEqual(classify({'upstream_roots':['depositor:X']},{'upstream_roots':['depositor:X']})['status'],'KNOWN_DEPENDENT')
 def test_audited_synthetic_provenance(self):
  a={k:'SYNTHETIC_AUDIT_DOCUMENT' for k in REQUIRED};a.update(upstream_roots=['ORIGINAL:A'],documented_no_shared_structural_origin=True)
  b={**a,'upstream_roots':['ORIGINAL:B']}
  self.assertEqual(classify(a,b)['status'],'INDEPENDENTLY_ESTABLISHED')
 def test_matching_descriptors_not_independence(self):
  self.assertEqual(classify({'inchikey':'same'},{'inchikey':'same'})['status'],'INDEPENDENCE_UNESTABLISHED')
 def test_missing_transform_history_not_independence(self):
  a={k:'SYNTHETIC_AUDIT_DOCUMENT' for k in REQUIRED};a.update(upstream_roots=['ORIGINAL:A'],documented_no_shared_structural_origin=True)
  b={**a,'upstream_roots':['ORIGINAL:B'],'standardization_history':None}
  self.assertEqual(classify(a,b)['status'],'INDEPENDENCE_UNESTABLISHED')
def main():
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PolicyTests));cases=fixtures()
 real=json.loads((H/'evaluation/chemical_correspondence_results.json').read_text())['cases']
 (H/'evaluation/admission_policy_results.json').write_text(json.dumps(dict(synthetic_policy_fixtures=cases,real_corpus_admission=[dict(case_id=c['case_id'],independence=c['result']['evidence_independence'],corroboration=c['result']['corroboration_qualification'],admission=c['result']['admission_eligibility']) for c in real],real_independently_established_pairs=0,synthetic_fixtures_count_as_real_positive_pairs=False,policy_modified=False,important_existing_policy_behavior=['Explicit typed structural sources have an existing corroboration exemption after official validation and specificity checks.','For non-typed sources the existing qualifying_lineage accepts SOURCE_DEPENDENCE_UNKNOWN as well as SOURCE_INDEPENDENT on qualifying routes. Its reason label is not audited independence proof.']),indent=2)+'\n',encoding='utf8')
 (H/'evaluation/policy_tests.json').write_text(json.dumps(dict(tests_run=r.testsRun,failures=len(r.failures),errors=len(r.errors),passed=r.wasSuccessful()),indent=2)+'\n');assert r.wasSuccessful()
if __name__=='__main__':main()
