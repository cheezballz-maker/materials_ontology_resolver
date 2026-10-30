import copy,sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path[:0]=[str(H),str(B/'nsc002_experiment'),str(B/'nsc_architecture_experiment'),str(B)]
from build_evidence import build
from diagnostic_evidence_consumer import consume
from run_evaluation import baseline_source
from charge_comparison_attribution import compare
from chemistry import describe
from source_form import assess
N='1-chloro-2-nitrobenzene';S='Clc1ccccc1[N+](=O)[O-]'
class ChargeTests(unittest.TestCase):
 def test_actual_source_guard_and_default_off(self):
    src=baseline_source(N,S,[]);e=build(N,[],S)
    self.assertEqual(src['status'],'UNRESOLVED');self.assertIn('SOURCE_PROTONATION_SPECIFICITY_UNKNOWN',src['reason_codes'])
    before=consume(src,src['reason_codes'],e);after=consume(src,src['reason_codes'],e,enable_charge_dimension_evidence=True)
    self.assertFalse(before['consumed']);self.assertTrue(after['consumed']);self.assertTrue(after['local_eligible']);self.assertEqual(src['status'],'UNRESOLVED')
 def test_other_obligations_survive(self):
    src=baseline_source(N,S,[]);src['dimensions']['tautomer']={'source':'UNSPECIFIED','compatibility':'UNKNOWN'};src['reason_codes'].append('SOURCE_TAUTOMER_SPECIFICITY_UNKNOWN')
    v=consume(src,src['reason_codes'],build(N,[],S),enable_charge_dimension_evidence=True)
    self.assertTrue(v['consumed']);self.assertFalse(v['local_eligible']);self.assertIn('SOURCE_TAUTOMER_SPECIFICITY_UNKNOWN',v['remaining_reasons'])
 def test_alias_unknown_and_conflict_are_not_discarded(self):
    for alias in ('nitrobenzene','1-chloro-3-nitrobenzene'):
        e=build(N,[alias],S);self.assertEqual(e.operation_result,'SUPPORTED');self.assertEqual(e.dimension_result,'UNKNOWN')
 def test_proof_forgery_and_binding(self):
    e=build(N,['unsupported'],S);e.dimension_result='SUPPORTED'
    with self.assertRaises(ValueError):e.validate()
    src=baseline_source(N,S,[]);src['claims'][0]['text']='different';self.assertFalse(consume(src,src['reason_codes'],build(N,[],S),enable_charge_dimension_evidence=True)['consumed'])
 def test_comparator_preserves_real_distinctions(self):
    r=compare(describe('CCO'),describe('COC'));self.assertEqual(r['assessment'],'DISTINCT');self.assertEqual(r['dimensions']['protonation_charge'],'UNKNOWN')
    for a,b in [('O=C(O)c1ccccc1','O=C([O-])c1ccccc1'),('NCC(=O)O','[NH3+]CC(=O)[O-]')]:self.assertEqual(compare(describe(a),describe(b))['dimensions']['protonation_charge'],'DIFFERENT')
 def test_exact_alias_constitution_conflict_survives(self):
    alias='1-chloro-3-nitrobenzene';d=describe(S);other=describe('Clc1cccc([N+](=O)[O-])c1')
    src=assess(N,{'status':'SUCCESS','structure':d},[(alias,{'status':'SUCCESS','structure':other})],d)
    self.assertEqual(src['status'],'CONFLICT')
    v=consume(src,src['reason_codes'],build(N,[alias],S),enable_charge_dimension_evidence=True)
    self.assertFalse(v['consumed']);self.assertEqual(v['source_form']['status'],'CONFLICT')
 def test_established_charge_contradiction_cannot_be_overridden(self):
    src=baseline_source(N,S,[]);src['dimensions']['protonation_charge']={'source':'CONFLICTING','compatibility':'DIFFERENT'};src['reason_codes'].append('PROTONATION_DIFFERENT');src['status']='CONFLICT'
    v=consume(src,src['reason_codes'],build(N,[],S),enable_charge_dimension_evidence=True)
    self.assertFalse(v['consumed']);self.assertEqual(v['source_form']['dimensions']['protonation_charge']['compatibility'],'DIFFERENT');self.assertIn('PROTONATION_DIFFERENT',v['remaining_reasons'])
if __name__=='__main__':unittest.main()
