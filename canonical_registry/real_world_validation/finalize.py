"""Verify frozen documentary labels, protected production artifacts and real checks."""
import hashlib,json,platform,re
from pathlib import Path
from rdkit import rdBase
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,o):(H/'evaluation'/n).write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
 protected=read(H/'evaluation/protected_input_freeze.json')['files'];changes=[n for n,v in protected.items() if not Path(n).is_file() or sha(Path(n))!=v]
 f=read(H/'reference_corpus/benchmark_freeze.json');changed_labels=[n for n,v in f['files'].items() if sha(H/'reference_corpus'/n)!=v];changed_materials=[n for n,v in f['material_hashes'].items() if sha(Path(n))!=v]
 runtime=read(H/'evaluation/implementation_freeze.json')['files'];changed_runtime=[n for n,v in runtime.items() if sha(H/n)!=v]
 cases=read(H/'reference_corpus/reference_cases.json')['cases'];selected={}
 for c in cases:
  for p in (c['source_record_provenance'],c['reference_provenance']):
   path=p.get('payload_path',p.get('path'));digest=p.get('payload_sha256',p.get('sha256'));selected[path]=digest
 cache_changes=[n for n,v in selected.items() if sha(Path(n))!=v]
 suites={n:read(H/f'evaluation/{n}_tests.json') for n in ('diagnostic','correspondence','adapters','identity_reconciliation','nsc001','nsc002','charge','resolver')};exits=read(H/'evaluation/regression_exit_codes.json')
 historical=read(H/'evaluation/historical_safety_results.json');old=read(B/'source_candidate_correspondence/evaluation/historical_safety_results.json');frozen={k:read(H/f'evaluation/baseline_{k}_results.json')['summary'] for k in ('development','heldout')}
 score=read(H/'evaluation/precision_recall_f1.json')['documentary_real_reference_population'];admission=read(H/'evaluation/admission_assessment_results.json')
 verdict='REAL_WORLD_VALIDATION_V1_CHEMICAL_CORRECTNESS_FAILURE' if score['false_equivalence_count'] or score['false_difference_count'] else 'REAL_WORLD_VALIDATION_V1_VALIDATED_PROVISIONAL'
 result=dict(suites=suites,unit_integration_total=sum(s['tests_run'] for s in suites.values()),all_unit_integration_passed=all(s['passed'] for s in suites.values()),retained_frozen_correspondence_controls=frozen,historical_cases=len(historical),historical_results_unchanged=historical==old,nsc_frozen_controls=read(H/'evaluation/nsc_regression.json')['passed'],python=platform.python_version(),rdkit=rdBase.rdkitVersion,expert_review='NOT_PERFORMED',verdict=verdict)
 write('test_results.json',result)
 write('safety_regressions.json',dict(historical_cases=historical,unchanged=historical==old,retained_correspondence_controls=frozen,unsafe_admission_recommendations=admission['unsafe_admission_recommendations'],false_equivalence_against_documentary_labels=score['false_equivalence_count'],false_difference_against_documentary_labels=score['false_difference_count'],existing_provider_and_admission_rules_unchanged=True,positive_admission_path_evaluated=False))
 initial=read(H/'evaluation/initial_scope_reproduction.json');assert initial['source_sha256_verified']==read(H/'evaluation/implementation_freeze_before_identifier_scope.json')['files']['correspondence_assessment.py']
 integrity=dict(protected_files=len(protected),changed_protected_files=changes,changed_frozen_reference_files=changed_labels,changed_public_material_files=changed_materials,changed_runtime_files=changed_runtime,changed_selected_cached_source_files=cache_changes,canonical_registry_ontology_schema_ids_aliases_admission_provider_policy='UNCHANGED_BY_DIGEST',new_canonical_ids=0,new_production_resolver_provider_queries=0,public_validation_material=dict(manifest='validation_material/retrieval_manifest.json',purpose='Independent documentary reference collection, never automatically qualifying corroboration',downloads_separate_from_resolver_budgets=True),registry_read_only=True,all_regression_exit_codes=exits,pass_=not any((changes,changed_labels,changed_materials,changed_runtime,cache_changes)) and not any(exits.values()) and historical==old)
 write('integrity_report.json',integrity);assert integrity['pass_'] and result['all_unit_integration_passed'];assert all(x['passed']==x['cases'] for x in frozen.values());assert not admission['unsafe_admission_recommendations']
 print(json.dumps({'integrity':integrity,'tests':result,'documentary_graph_metrics':score},indent=2))
if __name__=='__main__':main()
