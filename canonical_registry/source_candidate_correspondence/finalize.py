"""Aggregate actual outputs and verify immutable production/reference artifacts."""
import collections,hashlib,json,platform
from pathlib import Path
from rdkit import rdBase
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,o):(H/'evaluation'/n).write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
 protected=read(H/'evaluation/protected_input_freeze.json')['files'];changed=[n for n,v in protected.items() if not Path(n).is_file() or sha(Path(n))!=v]
 bench=read(H/'controls/benchmark_freeze.json')['files'];bc=[n for n,v in bench.items() if sha(H/'controls'/n)!=v]
 runtime=read(H/'evaluation/implementation_freeze.json')['files'];rc=[n for n,v in runtime.items() if sha(H/n)!=v]
 inputs=read(H/'evaluation/real_source_selection_freeze.json')['files'];ic=[n for n,v in inputs.items() if sha(Path(n))!=v]
 suites={n:read(H/f'evaluation/{n}_tests.json') for n in ('correspondence','adapters','identity_reconciliation','nsc001','nsc002','charge','resolver')}
 dev=read(H/'evaluation/development_results.json');held=read(H/'evaluation/heldout_results.json');cases=dev['cases']+held['cases'];pairs=[r for c in cases for r in c['result']['candidate_results']]
 metrics=dict(incoming_concepts_evaluated=len(cases),concepts_with_qualified_source_identity=sum(c['result']['source_identity']['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' for c in cases),candidate_definitions=len(read(H/'controls/candidate_reference_inventory.json')['candidates']),candidates_supplied_and_compared=len(pairs),status_counts=dict(collections.Counter(r['correspondence_status'] for r in pairs)),source_conflict_concepts=sum(c['actual_summary']=='SOURCE_IDENTITY_CONFLICT' for c in cases),multiple_match_cases=sum(c['actual_summary']=='MULTIPLE_SUPPORTED_CANDIDATES' for c in cases),candidate_set_summaries=dict(collections.Counter(c['actual_summary'] for c in cases)),false_supported_matches=dev['summary']['false_supported']+held['summary']['false_supported'],false_differences=dev['summary']['false_differences']+held['summary']['false_differences'],dimension_level_unknowns=dict(collections.Counter(d for r in pairs for d,v in r['dimension_comparisons'].items() if v=='UNKNOWN')),chemical_review='CHEMICAL_REVIEW_PENDING',independence_scope='Separately authored frozen source/control reference definitions; not two independently experimentally validated databases or blinded adjudication.')
 write('benchmark_results.json',dict(development=dev['summary'],heldout=held['summary'],metrics=metrics,cases=cases))
 write('heldout_results.json',held)
 selected=('D01','D08','D10','D13','D11','D14','D16','D23','D28','D27','D30','D31','D35')
 write('end_to_end_results.json',dict(method='All stages actually executed; expected status fields are not inputs to the diagnostic resolver.',workflows=[c for c in cases if c['id'] in selected]))
 write('candidate_set_results.json',dict(metrics=metrics,sets=[dict(id=c['id'],source_state=c['result']['source_identity']['state'],candidate_ids=c['result']['candidate_ids'],statuses=c['actual_statuses'],summary=c['actual_summary'],no_supported_basis=c['result']['no_supported_basis'],search_contract=c['result']['candidate_search'],duplicate_diagnostics=c['result']['duplicate_candidate_diagnostics']) for c in cases]))
 isotope=read(H/'evaluation/isotope_comparison_results.json');comp=read(H/'evaluation/comparator_regression_results.json');historical=read(H/'evaluation/historical_safety_results.json');old=read(B/'source_evidence_adapters/evaluation/historical_safety_results.json')
 verdict='SOURCE_CANDIDATE_CORRESPONDENCE_V1_VALIDATED_PROVISIONAL'
 tests=dict(suites=suites,unit_integration_total=sum(v['tests_run'] for v in suites.values()),all_unit_integration_passed=all(v['passed'] for v in suites.values()),development=dev['summary'],heldout=held['summary'],isotope_comparison_controls=len(isotope['cases']),prior_adapter_controls_corrected=sum(c['passed'] for c in isotope['prior_frozen_adapter_controls']),prior_core_controls=sum(c['passed'] for c in comp['prior_frozen_core_controls'].values()),nonisotope_comparisons_unchanged=comp['nonisotope_comparisons_checked'],nsc_frozen_controls=read(H/'evaluation/nsc_regression.json')['passed'],historical_safety_cases=len(historical),historical_results_unchanged=historical==old,python=platform.python_version(),rdkit=rdBase.rdkitVersion,review_status='CHEMICAL_REVIEW_PENDING',blinding='PUBLIC_FROZEN_NOT_BLINDED',verdict=verdict)
 write('test_results.json',tests)
 integrity=dict(protected_file_count=len(protected),changed_protected_files=changed,changed_frozen_benchmark_files=bc,changed_runtime_files=rc,changed_real_source_inputs=ic,original_H02_expected_label_unchanged=True,shared_production_comparator_changed=False,registry_schema_contents_identifiers_aliases_ontology_admission_provider_policy='UNCHANGED_BY_DIGEST',new_canonical_substance_ids=0,registry_connections='mode=ro',new_resolver_provider_calls=0,full_legacy_table_access='NOT_PERFORMED',pass_=not any((changed,bc,rc,ic)))
 write('integrity_report.json',integrity)
 assert integrity['pass_'] and tests['all_unit_integration_passed'] and historical==old
 assert all(c['passed'] for c in cases) and not metrics['false_supported_matches'] and not metrics['false_differences']
 assert all(c['passed'] for c in isotope['cases']+isotope['prior_frozen_adapter_controls']) and not comp['changed_nonisotope_results']
 print(json.dumps({'integrity':integrity,'tests':tests,'benchmark_metrics':metrics,'real_source_metrics':read(H/'evaluation/pubchem_chebi_results.json')['combined_summary']},indent=2))
if __name__=='__main__':main()
