import copy,json,unittest
from pathlib import Path
import bootstrap
from correspondence_models import EvidencePolicy,IncomingConcept,CanonicalCandidate
from control_inputs import incoming,candidates
from diagnostic_resolver import resolve_correspondence
from evidence_adapter_contract import EvidencePackage,structural_field,associated_name
from evidence_adapters import source_structure
from semantic_bridges import interpret
H=Path(__file__).resolve().parent
INV=json.loads((H/'controls/candidate_reference_inventory.json').read_text())
DEV={c['id']:c for c in json.loads((H/'controls/development_controls.json').read_text())['cases']}
class CorrespondenceTests(unittest.TestCase):
 def pair(self,key='D01'):
  c=DEV[key];return incoming(c),candidates(c['candidate_ids'],INV)
 def run_enabled(self,s,cs,**kw):return resolve_correspondence(s,cs,EvidencePolicy(enabled=True,**kw))
 def test_default_off(self):
  s,cs=self.pair();self.assertFalse(resolve_correspondence(s,cs)['diagnostic_enabled'])
 def test_partial_dimensions_cannot_be_called_full_correspondence(self):
  s,cs=self.pair()
  with self.assertRaises(ValueError):resolve_correspondence(s,cs,EvidencePolicy(enabled=True,required_dimensions=('constitution',)))
 def test_actual_independent_graph_matching(self):
  s,cs=self.pair();out=self.run_enabled(s,cs);self.assertEqual(out['unique_supported_candidate_id'],'REF_ETHANOL');self.assertEqual(out['canonical_admission'],'NOT_PERFORMED')
 def test_candidate_derived_copy_never_supported(self):
  s,cs=self.pair('D31');self.assertEqual(self.run_enabled(s,cs)['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')
 def test_shared_root_overrides_claimed_independence(self):
  s,cs=self.pair();cs[0].provenance['lineage_roots']=s.provenance['lineage_roots'];out=self.run_enabled(s,cs)
  self.assertEqual(out['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED');self.assertTrue(out['candidate_results'][0]['provenance']['shared_lineage_roots'])
 def test_missing_candidate_provenance_blocks_support(self):
  s,cs=self.pair();cs[0].provenance={};self.assertEqual(self.run_enabled(s,cs)['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')
 def test_invalid_source_binding_not_source_conflict(self):
  s,cs=self.pair('D23');s.binding['evidence_ids']=['missing'];out=self.run_enabled(s,cs)
  self.assertNotEqual(out['candidate_set_summary'],'SOURCE_IDENTITY_CONFLICT');self.assertEqual(out['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')
 def test_membership_route_cannot_be_marked_exact_by_flag(self):
  s,cs=self.pair();s.binding['kind']='ASSOCIATED_NAME_MEMBERSHIP';out=self.run_enabled(s,cs);self.assertEqual(out['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')
 def test_missing_candidate_is_bounded_no_candidate_result(self):
  s,_=self.pair();out=self.run_enabled(s,[]);self.assertEqual(out['no_supported_basis'],'NO_CANDIDATES_SUPPLIED');self.assertFalse(out['candidate_search']['global_no_match_established'])
 def test_candidate_budget_prevents_false_uniqueness(self):
  s,cs=self.pair('D28');out=self.run_enabled(s,cs,max_candidates=1);self.assertIsNone(out['unique_supported_candidate_id']);self.assertTrue(out['candidate_search']['budget_exhausted'])
 def test_duplicate_candidate_ids_rejected(self):
  s,cs=self.pair()
  with self.assertRaises(ValueError):self.run_enabled(s,[cs[0],cs[0]])
 def test_contradictory_candidate_evidence_is_not_silently_ignored(self):
  s,cs=self.pair();cs[0].evidence=[source_structure('CanonicalCandidate',cs[0].candidate_substance_id,'contradictory_graph','COC')]
  out=self.run_enabled(s,cs);self.assertEqual(out['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED');self.assertTrue(out['candidate_results'][0]['candidate_evidence']['identity_evidence_conflicted'])
 def test_inconsistent_candidate_identifier_blocks_support(self):
  s,cs=self.pair();cs[0].provenance['identifiers']=[['InChIKey','LCGLNKUTAGEVQW-UHFFFAOYSA-N']];self.assertEqual(self.run_enabled(s,cs)['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')
 def test_source_conflict_is_distinct_from_candidate_difference(self):
  s,cs=self.pair('D23');out=self.run_enabled(s,cs);self.assertEqual(out['candidate_set_summary'],'SOURCE_IDENTITY_CONFLICT');self.assertEqual(out['candidate_results'][0]['correspondence_status'],'SOURCE_CONFLICT')
 def test_reported_association_retained_outside_structural_referent(self):
  s,cs=self.pair('D37');out=self.run_enabled(s,cs);self.assertEqual(out['candidate_set_summary'],'UNIQUE_SUPPORTED_CANDIDATE');self.assertTrue(out['source_identity']['excluded_claims']);self.assertTrue(out['source_identity']['excluded_claims'][0]['unresolved_dependencies'])
 def test_unknown_potential_alias_is_not_silently_excluded(self):
  s,cs=self.pair('D38');self.assertEqual(self.run_enabled(s,cs)['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')
 def test_name_field_membership_does_not_bind_to_record_graph(self):
  pkg=EvidencePackage('test','record','1',{});g=structural_field(pkg,'g','CCO','$.structure');name=associated_name(pkg,'name','ethanol','$.synonym')
  s=IncomingConcept('incoming:name',pkg,dict(status='ESTABLISHED',kind='QUALIFIED_NAME_IDENTITY',evidence_ids=[name.evidence_id],document='User selected name only'),provenance={'lineage_roots':['name:1']});cs=candidates(['REF_ETHANOL'],INV)
  self.assertEqual(self.run_enabled(s,cs)['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')
 def test_nsc_partial_operation_cannot_establish_whole_identity(self):
  pkg=EvidencePackage('test','record','1',{});n=interpret(pkg,'name','1-bromo-3-chlorobenzene','$.name',charge=False)
  s=IncomingConcept('nsc:name',pkg,dict(status='ESTABLISHED',kind='QUALIFIED_NAME_IDENTITY',evidence_ids=[n.evidence_id],document='Source name is the incoming referent'),provenance={'lineage_roots':['nsc:name']})
  self.assertEqual(self.run_enabled(s,candidates(['REF_META_BROMOCHLORO'],INV))['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')
 def test_unestablished_multicomponent_kind_abstains(self):
  s,cs=self.pair('D40');self.assertEqual(self.run_enabled(s,cs)['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')
 def test_all_candidates_different_despite_other_source_unknown(self):
  s,cs=self.pair('D16');cs=candidates(['REF_ETHANOL'],INV);out=self.run_enabled(s,cs);self.assertEqual(out['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_DIFFERENT');self.assertEqual(out['candidate_set_summary'],'NO_SUPPORTED_CANDIDATE_IN_SET');self.assertFalse(out['candidate_search']['global_no_match_established'])
 def test_duplicate_equivalent_candidates_are_diagnostic_only(self):
  s,cs=self.pair('D28');out=self.run_enabled(s,cs);self.assertIsNone(out['unique_supported_candidate_id']);self.assertEqual(out['candidate_set_summary'],'MULTIPLE_SUPPORTED_CANDIDATES');self.assertTrue(out['duplicate_candidate_diagnostics']);self.assertFalse(out['duplicate_candidate_diagnostics'][0]['merge_performed'])
 def test_mutating_results_does_not_mutate_source(self):
  s,cs=self.pair();out=self.run_enabled(s,cs);out['source_identity']['claims'][0]['dimension_assertions'].clear();self.assertTrue(s.evidence_package.claims[0].dimension_assertions)
 def test_tautomer_and_counterion_loss_not_exact(self):
  for key in ('D12','D14','D15'):
   s,cs=self.pair(key);self.assertEqual(self.run_enabled(s,cs)['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_DIFFERENT')
 def test_source_and_candidate_inputs_not_modified(self):
  s,cs=self.pair();before=copy.deepcopy(s.evidence_package.to_dict());cp=copy.deepcopy(cs[0].provenance);self.run_enabled(s,cs);self.assertEqual(before,s.evidence_package.to_dict());self.assertEqual(cp,cs[0].provenance)
 def test_evidence_level_shared_root_blocks_self_confirmation(self):
  s,cs=self.pair();cs[0].provenance['lineage_roots']=[s.evidence_package.claims[0].evidence_id];self.assertEqual(self.run_enabled(s,cs)['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')
 def test_known_source_derived_route_overrides_independence_flag(self):
  s,cs=self.pair();cs[0].provenance['definition_kind']='SOURCE_DERIVED';self.assertEqual(self.run_enabled(s,cs)['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')
 def component_source(self,graph,unknown=()):
  pkg=EvidencePackage('test','record','composition',{});c=structural_field(pkg,'s',graph,'$.source')
  for d in unknown:c.dimension_assertions[d]={'state':'UNKNOWN','rule_id':'EXPLICIT_SOURCE_UNCERTAINTY'}
  return IncomingConcept('test:composition',pkg,dict(status='ESTABLISHED',kind='EXPLICIT_SOURCE_ASSERTION',evidence_ids=[c.evidence_id],document='Explicit independently supplied source composition'),identity_scope='DEFINED_MULTICOMPONENT_COMPOSITION',provenance={'lineage_roots':['test:composition']})
 def component_candidate(self,graph):
  p=copy.deepcopy(candidates(['REF_ETHANOL'],INV)[0].provenance);return CanonicalCandidate('REF:component','Independent explicit comparison composition',graph,p,'DEFINED_MULTICOMPONENT_COMPOSITION')
 def test_unspecified_stereo_components_do_not_create_false_difference(self):
  s=self.component_source('CC(O)CC.O');r=self.run_enabled(s,[self.component_candidate('C[C@H](O)CC.O')]);self.assertEqual(r['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')
 def test_unknown_isotope_scope_cannot_leak_through_components(self):
  s=self.component_source('CCO.O',['isotope']);r=self.run_enabled(s,[self.component_candidate('[13CH3]CO.O')]);self.assertEqual(r['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')
 def test_broad_component_form_and_specific_source_claim_are_not_conflict(self):
  s=self.component_source('CCO.O',['isotope']);structural_field(s.evidence_package,'specific','[13CH3]CO.O','$.specific');r=self.run_enabled(s,[self.component_candidate('[13CH3]CO.O')]);self.assertNotEqual(r['candidate_set_summary'],'SOURCE_IDENTITY_CONFLICT')
 def test_specific_component_stereo_difference_is_preserved(self):
  s=self.component_source('C[C@H](O)CC.O');r=self.run_enabled(s,[self.component_candidate('C[C@@H](O)CC.O')]);self.assertEqual(r['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_DIFFERENT')
 def test_unknown_isotope_does_not_suppress_constitution_difference(self):
  s=self.component_source('CCO.O',['isotope']);r=self.run_enabled(s,[self.component_candidate('COC.O')]);self.assertEqual(r['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_DIFFERENT')
 def test_unspecified_candidate_component_stereo_is_unresolved(self):
  s=self.component_source('C[C@H](O)CC.O');r=self.run_enabled(s,[self.component_candidate('CC(O)CC.O')]);self.assertEqual(r['candidate_results'][0]['correspondence_status'],'CORRESPONDENCE_UNRESOLVED')

if __name__=='__main__':unittest.main()
