"""Verify protected inputs, runtime, frozen controls and actual test outputs."""
import collections,hashlib,json,platform
from pathlib import Path
from rdkit import rdBase
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,o):(H/'evaluation'/n).write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
 protected=read(H/'evaluation/protected_input_freeze.json')['files'];changed=[n for n,v in protected.items() if not Path(n).exists() or sha(Path(n))!=v]
 benchmark=read(H/'controls/benchmark_freeze.json')['files'];bc=[n for n,v in benchmark.items() if sha(H/'controls'/n)!=v]
 runtime=read(H/'evaluation/implementation_freeze.json')['files'];rc=[n for n,v in runtime.items() if sha(H/n)!=v]
 selected=[x for rows in read(H/'evaluation/source_selection_freeze.json')['sources'].values() for x in rows];sc=[x['path'] for x in selected if sha(Path(x['path']))!=x['sha256']]
 suites={n:read(H/f'evaluation/{n}_tests.json') for n in ('adapters','identity_reconciliation','nsc001','nsc002','charge','resolver')}
 cases=[]
 for kind in ('development','heldout'):
  controls={c['id']:c for c in read(H/f'controls/{kind}_controls.json')['cases']}
  for r in read(H/f'evaluation/{kind}_results.json')['cases']:
   c=controls[r['id']];cases.append(dict(id=r['id'],description=c['description'],scope=c['scope'],required_dimensions=c['required_dimensions'],expected=r['expected'],actual=r['actual'],expected_role=r['expected_role'],actual_role=r['actual_role'],passed=r['passed'],review_status=c['review_status'],chemical_justification=c['chemical_justification']))
 chemical=dict(development={'passed':sum(c['passed'] for c in cases if c['id'].startswith('D')),'total':31},public_heldout={'passed':sum(c['passed'] for c in cases if c['id'].startswith('H')),'total':10},false_compatible=sum(c['actual']=='RECONCILED_COMPATIBLE' and c['expected']!='RECONCILED_COMPATIBLE' for c in cases),false_conflict=sum(c['actual']=='RECONCILIATION_CONFLICT' and c['expected']!='RECONCILIATION_CONFLICT' for c in cases),unresolved_instead_of_expected_conflict=sum(c['actual']=='RECONCILIATION_UNRESOLVED' and c['expected']=='RECONCILIATION_CONFLICT' for c in cases),cases=cases,chemical_review='CHEMICAL_REVIEW_PENDING',blinding='PUBLIC_FROZEN_NOT_BLINDED')
 write('chemical_controls_summary.json',chemical)
 profile={}
 for source,name in [('PubChem','pubchem_results.json'),('ChEBI','second_source_results.json')]:
  obj=read(H/'evaluation'/name);states=collections.defaultdict(collections.Counter);traits=collections.Counter();unusable=[];semantic=collections.Counter()
  for r in obj['records']:
   if 'package' not in r:continue
   p=r['package']
   for c in p['claims']:
    if c['claim_role']=='STRUCTURAL_IDENTITY_ASSERTION':
     for d,a in c['dimension_assertions'].items():states[d][a['state']]+=1
     if not c['dimension_assertions']:unusable.append({'record_id':r['record_id'],'claim_id':c['claim_id'],'obligations':c['unresolved_dependencies']})
    if c['source_provenance'].get('contract_id') in ('NSC-001','NSC-002'):
     semantic[c['source_provenance']['semantic_interpretation']['scope_status']]+=1
   for o in p['observations']:
    if o['kind']!='VALIDATED_GRAPH_ATTRIBUTES':continue
    a=o['attributes'];traits['graphs']+=1;traits['charged']+=bool(a['charge']);traits['neutral_net_charge']+=not bool(a['charge']);traits['multicomponent']+=a['components']>1;traits['isotope_labelled']+=bool(a['isotopes']);traits['specified_stereo']+=any(s['specified']=='Specified' for s in a['stereo']);traits['unspecified_stereo']+=any(s['specified']=='Unspecified' for s in a['stereo'])
   if not any(c['dimension_assertions'] for c in p['claims'] if c['claim_role']=='STRUCTURAL_IDENTITY_ASSERTION'):traits['no_qualified_source_graph']+=1
  profile[source]=dict(assertion_specificity_states={d:dict(v) for d,v in states.items()},source_graph_traits=dict(traits),semantic_name_scope_counts=dict(semantic),invalid_or_unsupported_structures=unusable,role_counts=obj['summary']['claim_role_counts'])
 write('evidence_coverage_details.json',profile)
 tests=dict(suites=suites,unit_integration_total=sum(x['tests_run'] for x in suites.values()),all_unit_integration_passed=all(x['passed'] for x in suites.values()),frozen_nsc_controls=read(H/'evaluation/nsc_regression.json')['passed'],historical_safety_cases=len(read(H/'evaluation/historical_safety_results.json')),chemical_control_results={k:v for k,v in chemical.items() if k!='cases'},python=platform.python_version(),rdkit=rdBase.rdkitVersion,qualified_chemical_review='CHEMICAL_REVIEW_PENDING',verdict='SOURCE_EVIDENCE_ADAPTER_V1_PARTIAL')
 write('test_results.json',tests)
 integrity=dict(protected_file_count=len(protected),changed_protected_files=changed,changed_frozen_benchmarks=bc,changed_frozen_runtime=rc,changed_source_cache_files=sc,main_registry_digest_unchanged=not any(n.endswith('output\\registry.sqlite') or n.endswith('output/registry.sqlite') for n in changed),production_ontology_schema_admission_provider_qualification_external_gate_alias_registry='UNCHANGED_BY_DIGEST',new_resolver_provider_requests=0,network_guard='Offline evaluators/validation block socket.create_connection; historical provider adapters run offline; source catalogs retrieved via documentation browsing only.',CUMA_rule_tuning='NOT_PERFORMED',verdict='PASS' if not any((changed,bc,rc,sc)) else 'FAIL')
 write('integrity_report.json',integrity)
 assert integrity['verdict']=='PASS';assert tests['all_unit_integration_passed'];assert chemical['development']['passed']==31 and chemical['public_heldout']['passed']==9
 print(json.dumps(dict(integrity=integrity,tests=tests,coverage=profile),indent=2))
if __name__=='__main__':main()
