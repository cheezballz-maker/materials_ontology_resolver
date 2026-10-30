import copy,json,unittest
from pathlib import Path
import bootstrap
from correspondence_assessment import assess
from record_inputs import load
from bootstrap import BASE as B
from control_inputs import incoming,candidates
from diagnostic_resolver import resolve_correspondence
from correspondence_models import EvidencePolicy
H=Path(__file__).resolve().parent
CASES={c['case_id']:c for c in json.loads((H/'reference_corpus/reference_cases.json').read_text(encoding='utf8'))['cases']}
OLD={c['id']:c for c in json.loads((B/'source_candidate_correspondence/controls/development_controls.json').read_text())['cases']};INV=json.loads((B/'source_candidate_correspondence/controls/candidate_reference_inventory.json').read_text())
class AssessmentTests(unittest.TestCase):
 def pair(self):return load(CASES['RW01'])
 def legacy(self,key):
  c=OLD[key];return incoming(c),candidates(c['candidate_ids'],INV)
 def test_default_off(self):
  s,c=self.pair();self.assertFalse(assess(s,c)['diagnostic_enabled'])
 def test_unknown_independence_does_not_mask_chemical_equivalence(self):
  s,c=self.pair();r=assess(s,c,enabled=True);self.assertEqual(r['represented_structure_comparison']['status'],'CHEMICALLY_EQUIVALENT');self.assertEqual(r['evidence_independence']['status'],'INDEPENDENCE_UNESTABLISHED');self.assertEqual(r['source_identity_correspondence']['status'],'SOURCE_IDENTITY_CORRESPONDENCE_SUPPORTED');self.assertFalse(r['admission_eligibility']['eligible'])
 def test_known_dependent_graph_equivalence_is_not_corroboration(self):
  s,c=self.pair();c.provenance['lineage_roots']=s.provenance['lineage_roots'];r=assess(s,c,enabled=True);self.assertEqual(r['represented_structure_comparison']['status'],'CHEMICALLY_EQUIVALENT');self.assertEqual(r['evidence_independence']['status'],'KNOWN_DEPENDENT');self.assertEqual(r['source_identity_correspondence']['status'],'SOURCE_IDENTITY_CONSISTENCY_ONLY');self.assertEqual(r['corroboration_qualification']['independent_corroboration'],'NOT_ESTABLISHED')
 def test_control_definition_flag_is_not_real_upstream_independence(self):
  s,c=self.pair();c.provenance['independence_status']='ESTABLISHED_FOR_CONTROL_DEFINITION';r=assess(s,c,enabled=True);self.assertEqual(r['evidence_independence']['status'],'INDEPENDENCE_UNESTABLISHED')
 def test_unsubstantiated_independence_flag_does_not_qualify(self):
  s,c=self.pair();c.provenance['independence_status']='ESTABLISHED_BY_AUDITED_PROVENANCE';r=assess(s,c,enabled=True);self.assertEqual(r['evidence_independence']['status'],'INDEPENDENCE_UNESTABLISHED')
 def test_documented_upstream_audit_still_does_not_bypass_provider_policy(self):
  s,c=self.pair();c.provenance.update(independence_status='ESTABLISHED_BY_AUDITED_PROVENANCE',independence_audit={'original_source_attribution':'unit fixture, not a real audit','mapping_route':'independent-document fixture','documented_derivation_review':'explicit fixture'});r=assess(s,c,enabled=True);self.assertEqual(r['evidence_independence']['status'],'INDEPENDENTLY_ESTABLISHED');self.assertFalse(r['admission_eligibility']['eligible']);self.assertEqual(r['corroboration_qualification']['independent_corroboration'],'NOT_ESTABLISHED')
 def test_name_membership_does_not_inherit_graph_specificity(self):
  s,c=load(CASES['RW26']);r=assess(s,c,enabled=True);self.assertEqual(r['represented_structure_comparison']['status'],'CHEMICALLY_EQUIVALENT');self.assertEqual(r['source_identity_correspondence']['status'],'SOURCE_IDENTITY_UNRESOLVED')
 def test_source_conflict_is_retained(self):
  s,cs=self.legacy('D23');r=assess(s,cs[0],enabled=True);self.assertEqual(r['source_identity_correspondence']['status'],'SOURCE_CONFLICT');self.assertTrue(r['source_conflicts']);self.assertEqual(r['represented_structure_comparison']['status'],'CHEMICALLY_UNRESOLVED')
 def test_broad_source_is_not_narrow_identity(self):
  s,cs=self.legacy('D18');r=assess(s,cs[0],enabled=True);self.assertEqual(r['source_identity_correspondence']['status'],'SOURCE_IDENTITY_UNRESOLVED');self.assertFalse(r['admission_eligibility']['eligible'])
 def test_stereo_isotope_salt_tautomer_distinctions_preserved(self):
  for key in ('D10','D11','D12','D13','D14','D15','D32','D33'):
   with self.subTest(key=key):
    s,cs=self.legacy(key);r=assess(s,cs[0],enabled=True);self.assertEqual(r['represented_structure_comparison']['status'],'CHEMICALLY_DIFFERENT');self.assertFalse(r['admission_eligibility']['eligible'])
 def test_unspecified_stereo_not_exact(self):
  s,cs=self.legacy('D16');r=assess(s,cs[0],enabled=True);self.assertEqual(r['represented_structure_comparison']['status'],'CHEMICALLY_UNRESOLVED')
 def test_candidate_derived_source_is_not_proof(self):
  s,cs=self.legacy('D39');r=assess(s,cs[0],enabled=True);self.assertEqual(r['represented_structure_comparison']['status'],'CHEMICALLY_UNRESOLVED');self.assertEqual(r['source_identity_correspondence']['status'],'SOURCE_IDENTITY_UNRESOLVED')
 def test_original_ambiguity_behavior_unchanged(self):
  s,cs=self.legacy('D28');r=resolve_correspondence(s,cs,EvidencePolicy(enabled=True));self.assertEqual(r['candidate_set_summary'],'MULTIPLE_SUPPORTED_CANDIDATES');self.assertIsNone(r['unique_supported_candidate_id'])
 def test_inputs_not_modified(self):
  s,c=self.pair();p=copy.deepcopy(s.evidence_package.to_dict());q=copy.deepcopy(c.provenance);assess(s,c,enabled=True);self.assertEqual(s.evidence_package.to_dict(),p);self.assertEqual(c.provenance,q)
 def test_reference_identifier_mismatch_is_preserved(self):
  s,c=self.pair();c.provenance['identifiers']=[['InChIKey','LCGLNKUTAGEVQW-UHFFFAOYSA-N']];r=assess(s,c,enabled=True);self.assertEqual(r['represented_structure_comparison']['status'],'CHEMICALLY_EQUIVALENT');self.assertEqual(r['source_identity_correspondence']['status'],'SOURCE_IDENTITY_UNRESOLVED');self.assertIn('CANDIDATE_IDENTIFIER_STRUCTURE_INCONSISTENCY',r['represented_structure_comparison']['candidate_record_obligations'])
 def test_public_validation_download_never_is_qualifying_provider(self):
  s,c=self.pair();r=assess(s,c,enabled=True);self.assertFalse(r['corroboration_qualification']['public_validation_material_is_qualifying_provider']);self.assertEqual(r['admission_eligibility']['existing_policy_result']['status'],'UNRESOLVED')

if __name__=='__main__':unittest.main()
