"""Verify read-only integrity, proposal safety, frozen expectations and tests."""
import collections,hashlib,json,platform,sqlite3
from pathlib import Path
from rdkit import rdBase
H=Path(__file__).resolve().parent;B=H.parent
read=lambda n:json.loads((H/'evaluation'/n).read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,o):(H/'evaluation'/n).write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
 protected=read('protected_input_freeze.json')['files'];changes=[p for p,d in protected.items() if not Path(p).is_file() or sha(Path(p))!=d]
 frozen=json.loads((H/'controls/benchmark_freeze.json').read_text())['files'];changed_controls=[n for n,d in frozen.items() if sha(H/'controls'/n)!=d]
 registry=B/'output/registry.sqlite';before=sha(registry);db=sqlite3.connect(registry.resolve().as_uri()+'?mode=ro',uri=True)
 try:
  integrity=db.execute('PRAGMA integrity_check').fetchall();fk=db.execute('PRAGMA foreign_key_check').fetchall();counts={}
  for table,cols in [('substance_identity','substance_id'),('substance_alias','substance_id,alias'),('substance_identifier','substance_id,identifier_type,identifier_value'),('substance_structure','substance_id,structure_type,structure_value'),('substance_reconciliation','cuma_index')]:
   counts['duplicate_'+table]=db.execute(f'SELECT count(*) FROM (SELECT {cols} FROM {table} GROUP BY {cols} HAVING count(*)>1)').fetchone()[0]
  for table in ('substance_alias','substance_identifier','substance_structure','substance_reconciliation'):
   counts['orphan_'+table]=db.execute(f'SELECT count(*) FROM {table} t LEFT JOIN substance_identity s ON t.substance_id=s.substance_id WHERE t.substance_id IS NOT NULL AND s.substance_id IS NULL').fetchone()[0]
 finally:db.close()
 actual=read('real_registry_results.json');benchmark=read('benchmark_results.json');violations=[]
 for row in actual['records']:
  r=row['result'];comparison=r['candidate_results'];ids=[c['candidate_substance_id'] for c in comparison]
  if len(ids)!=len(set(ids)):violations.append([r['source_concept_id'],'DUPLICATE_CANDIDATE_EVALUATION'])
  if r['status']=='UNIQUE_CANONICAL_MATCH':
   equivalent=[c for c in comparison if c['chemical_status']=='CHEMICALLY_EQUIVALENT' and c['source_identity_status']=='SOURCE_IDENTITY_SUPPORTED']
   if len(equivalent)!=1 or equivalent[0]['candidate_substance_id']!=r['unique_matched_substance_id'] or any(c['chemical_status']=='CHEMICALLY_UNRESOLVED' for c in comparison) or not r['retrieval']['search_complete'] or not r['uniqueness']['source_sufficient']:violations.append([r['source_concept_id'],'UNPROVEN_UNIQUE_MATCH'])
  if r['status']=='NO_MATCH_IN_SEARCHED_REGISTRY' and (not r['retrieval']['search_complete'] or not r['uniqueness']['source_sufficient'] or any(c['chemical_status']!='CHEMICALLY_DIFFERENT' for c in comparison)):violations.append([r['source_concept_id'],'UNPROVEN_BOUNDED_ABSENCE'])
  if r['diagnostic_reuse_proposal'] and (r['status']!='UNIQUE_CANONICAL_MATCH' or not r['admission']['admission_eligible']):violations.append([r['source_concept_id'],'UNSAFE_REUSE_PROPOSAL'])
  if r['id_reuse_authorized'] or r['registry_mutations'] or r['new_ids_created']:violations.append([r['source_concept_id'],'MUTATION_OR_AUTHORIZATION'])
 suites={n:read(n+'_tests.json') for n in ('diagnostic','correspondence','adapters','identity_reconciliation','nsc001','nsc002','charge','resolver','stereo','corrected_interface','policy','matching')}
 exits=read('regression_exit_codes.json');baseline={k:read(f'baseline_{k}_results.json')['summary'] for k in ('development','heldout')};hardened={k:read(f'corrected_{k}_results.json')['summary'] for k in ('development','heldout')}
 historical=read('historical_safety_results.json');historical_unchanged=historical==json.loads((B/'chemical_correspondence_hardening/evaluation/historical_safety_results.json').read_text())
 world=read('retained_real_world_results.json')
 tests=dict(suites=suites,unit_integration_total=sum(s['tests_run'] for s in suites.values()),retained_unit_integration_total=sum(s['tests_run'] for n,s in suites.items() if n!='matching'),all_unit_integration_passed=all(s['passed'] for s in suites.values()),matching_benchmark=benchmark['summary'],retained_original_controls=baseline,retained_hardened_controls=hardened,nsc_controls=read('nsc_regression.json')['passed'],historical_cases=len(historical),historical_results_unchanged=historical_unchanged,original_real_world_agreement=world['original_agreement'],hardened_real_world_agreement=world['hardened_agreement'],real_world_scored=world['scored'],python=platform.python_version(),rdkit=rdBase.rdkitVersion)
 write('test_results.json',tests)
 ok=not changes and not changed_controls and not violations and integrity==[('ok',)] and not fk and not any(counts.values()) and not any(exits.values()) and tests['all_unit_integration_passed'] and benchmark['summary']['passed']==benchmark['summary']['cases'] and historical_unchanged and all(v['cases']==v['passed'] for v in list(baseline.values())+list(hardened.values()))
 result=dict(protected_files=len(protected),changed_protected_files=changes,changed_frozen_matching_controls=changed_controls,registry_connection='mode=ro',registry_sha256_before=before,registry_sha256_after=sha(registry),sqlite_integrity=integrity,foreign_key_errors=fk,registry_integrity_counts=counts,proposal_invariant_violations=violations,independently_measured_real_world_false_unique_rate=None,independent_benchmark_false_unique=benchmark['summary']['unsafe_unique_match_proposals'],registry_writes=0,existing_ids_assigned=0,new_substance_ids_created=0,production_provider_requests=0,production_ontology_schema_admission_provider_policy_budgets_historical_results='UNCHANGED_BY_DIGEST',fixture_scope=str((H/'fixtures').resolve()),pass_=ok)
 result['pass_']=result['pass_'] and before==result['registry_sha256_after'];write('integrity_report.json',result)
 verdict='CANONICAL_REGISTRY_MATCHING_V1_VALIDATED_PROVISIONAL' if result['pass_'] else 'CANONICAL_REGISTRY_MATCHING_V1_PARTIAL'
 write('readiness_assessment.json',dict(verdict=verdict,read_only_matching='READY_WITHIN_VALIDATED_SCOPE',controlled_existing_id_reuse='READY_FOR_SEPARATELY_AUTHORIZED_BOUNDED_POC_ON_VERIFIED_EXPLICIT_STRUCTURES_SUBJECT_TO_TRANSACTIONAL_INTEGRATION_TESTS',existing_id_reuse_authorized=False,new_id_creation_authorized=False,name_derived_inputs='Existing corroboration/specificity requirements retained; positive matching policy path demonstrated with synthetic provider fixtures, not independently audited real provider pairs.',later_policy_decisions=['Review existing SOURCE_DEPENDENCE_UNKNOWN acceptance separately from audited independence','Define snapshot/transaction/idempotency/audit requirements before persistent ID assignment','Broader chemical scope and independent expert or blind validation before general scaling'],recommendation='Separately authorize a controlled existing-ID reuse POC for qualified explicit structures; keep this implementation read-only.'))
 write('implementation_manifest.json',dict(files={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.json','.md') and 'evaluation' not in p.parts},scope='New read-only implementation and matching control expectations; existing protected baseline separately hashed.'))
 print(json.dumps(dict(tests=tests,integrity=result,verdict=verdict),indent=2));assert result['pass_']
if __name__=='__main__':main()
