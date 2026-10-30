import copy,sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path[:0]=[str(H),str(B/'charge_dimension_evidence'),str(B/'nsc002_experiment'),str(B/'nsc_architecture_experiment'),str(B)]
from evidence_adapters import source_structure,candidate_assertions,assertion,raw_claim,architecture_b_claim
from source_claim_reconciler import reconcile
from dimension_claim_comparator import compare_assertions
class ReconciliationTests(unittest.TestCase):
 def test_missing_evidence_never_equal(self):self.assertEqual(compare_assertions(None,None,'constitution'),'UNKNOWN')
 def test_finite_sets_do_not_select_stereo(self):
    r='CC[C@H](O)C';s='CC[C@@H](O)C';a=assertion(r,'stereochemistry','SET');a['structures']=[r,s]
    self.assertEqual(compare_assertions(a,assertion(r,'stereochemistry'),'stereochemistry'),'BROADER_THAN_CANDIDATE')
    self.assertEqual(compare_assertions(a,a,'stereochemistry'),'UNKNOWN')
 def test_dependency_cycle_and_missing(self):
    x=source_structure('test','r','a','CCO');x.derivation_dependencies=[x.evidence_id]
    result=reconcile([x],candidate_assertions('CCO'),['constitution'],'test:r');self.assertEqual(result['result'],'RECONCILIATION_UNRESOLVED')
 def test_constitution_conflict_not_globally_broad(self):
    x=source_structure('test','r','a','COC');x.dimension_assertions['stereochemistry']=assertion(None,'stereochemistry','UNKNOWN')
    self.assertEqual(reconcile([x],candidate_assertions('CCO'),['constitution'],'test:r')['result'],'RECONCILIATION_CONFLICT')
 def test_untrusted_alias_not_harmless(self):
    x=source_structure('test','r','a','CCO');y=raw_claim('test','r','b','UNVERIFIED_ALIAS','unparsed')
    self.assertEqual(reconcile([x,y],candidate_assertions('CCO'),['constitution'],'test:r')['result'],'RECONCILIATION_UNRESOLVED')
 def test_candidate_derived_dependency_cannot_vote(self):
    a=source_structure('test','r','a','CCO');a.source_provenance['origin']='CANDIDATE_DERIVED';b=source_structure('test','r','b','CCO');b.derivation_dependencies=[a.evidence_id]
    self.assertEqual(reconcile([a,b],candidate_assertions('CCO'),['constitution'],'test:r')['result'],'RECONCILIATION_UNRESOLVED')
 def test_architecture_b_optional_adapter(self):
    e=architecture_b_claim('test','r','name','1-methyl-1H-pyrazole')
    result=reconcile([e],candidate_assertions('CN1C=CC=N1'),['constitution'],'test:r');self.assertEqual(result['result'],'RECONCILED_COMPATIBLE');self.assertEqual(e.evidence_type,'ARCHITECTURE_B_SEMANTIC_INTERPRETATION')
 def test_cross_record_link_must_be_explicit(self):
    e=source_structure('test','r','a','CCO')
    with self.assertRaises(ValueError):reconcile([e],candidate_assertions('CCO'),['constitution'],'different')
 def test_diagnostic_consumer_preserves_active_unknown(self):
    from source_form import assess
    from chemistry import describe
    from diagnostic_reconciliation_consumer import consume
    d=describe('CCO');before=assess('ethanol',{'status':'SUCCESS','structure':d},[('uninterpreted',{'status':'FAILURE'})],d)
    x=source_structure('test','r','a','CCO');y=raw_claim('test','r','b','UNVERIFIED_ALIAS','uninterpreted');rec=reconcile([x,y],candidate_assertions('CCO'),['constitution'],'test:r')
    self.assertEqual(before['status'],'SUPPORTED');self.assertEqual(consume(before,rec)['source_form']['status'],'SUPPORTED');self.assertEqual(consume(before,rec,enabled=True,referent_id='test:r')['source_form']['status'],'UNRESOLVED')
    self.assertEqual(consume(before,rec,enabled=True,referent_id='wrong')['evidence_rejection'],'RECORD_OR_CANDIDATE_BINDING_UNVERIFIED')
 def test_opposite_exact_sources_conflict_even_with_broad_candidate(self):
    a=source_structure('test','r','a','CC[C@H](O)C');b=source_structure('test','r','b','CC[C@@H](O)C')
    r=reconcile([a,b],candidate_assertions('CCC(O)C'),['stereochemistry'],'test:r')
    self.assertEqual(r['result'],'RECONCILIATION_CONFLICT');self.assertTrue(any(x.get('basis')=='ESTABLISHED_SOURCE_SOURCE_CONTRADICTION' for x in r['incompatible_claims']))
 def test_distinct_source_dimensions_combine_only_on_shared_referent(self):
    a=source_structure('test','r','constitution','CCC(O)C');a.dimension_assertions={'constitution':a.dimension_assertions['constitution']}
    b=source_structure('test','r','stereo','CC[C@H](O)C');b.dimension_assertions={'stereochemistry':b.dimension_assertions['stereochemistry']}
    r=reconcile([a,b],candidate_assertions('CC[C@H](O)C'),['constitution','stereochemistry'],'test:r')
    self.assertEqual(r['result'],'RECONCILED_COMPATIBLE');self.assertEqual(set(r['supported_dimensions']),{'constitution','stereochemistry'})
if __name__=='__main__':unittest.main()
