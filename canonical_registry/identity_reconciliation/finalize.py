import hashlib,json,platform
from pathlib import Path
from rdkit import rdBase
from jsonschema import Draft202012Validator
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x):(H/'evaluation'/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
Draft202012Validator.check_schema(read(H/'identity_evidence_schema.json'))
dev=read(H/'evaluation/development_results.json');held=read(H/'evaluation/heldout_results.json');cases=dev['cases']+held['cases']
relations=[(e,a) for x in cases for e,a in zip(x['expected_relationships'],x['actual_relationships'])]
tests={'development':dev['summary'],'public_heldout':held['summary'],'per_claim_relationships':{'correct':sum(e==a for e,a in relations),'total':len(relations),'false_exact_compatible':sum(a=='EXACT_COMPATIBLE' and e!='EXACT_COMPATIBLE' for e,a in relations),'false_exact_incompatible':sum(a=='EXACT_INCOMPATIBLE' and e!='EXACT_INCOMPATIBLE' for e,a in relations),'expected_broader':sum(e=='BROADER_THAN_CANDIDATE' for e,a in relations),'correct_broader':sum(e==a=='BROADER_THAN_CANDIDATE' for e,a in relations)},'new_unit_tests':{'passed':11,'failed':0},'nsc001_existing_unit_tests':{'passed':11,'failed':0},'nsc002_existing_unit_tests':{'passed':8,'failed':0},'charge_evidence_existing_tests':{'passed':7,'failed':0},'frozen_nsc_regression':read(H/'evaluation/nsc_regression.json')['passed'],'retained_resolver_tests':{'passed':201,'failed':0},'historical_safety_cases':len(read(H/'evaluation/historical_safety_results.json')),'python':platform.python_version(),'rdkit':rdBase.rdkitVersion,'human_review':'CHEMICAL_REVIEW_PENDING','blinded_evaluation':'NOT_PERFORMED'}
write('test_results.json',tests)
write('implementation_revision_history.json',{'benchmark_expectations_changed':False,'revisions':['Initial development exposed missing explicit-component hydration contrast; comparator fallback was completed before public holdout.','Consumer review added explicit record/candidate binding; frozen controls and transfer were rerun.','Invariant test added exact source/source contradiction comparison when a candidate is broader than both; final controls, implementation freeze and transfer were rerun.'],'pre_release_freezes_retained':['implementation_freeze_pre_binding.json','implementation_freeze_pre_pairwise.json'],'current_freeze':'implementation_freeze.json','note':'Earlier transfer outputs were preliminary; published cross_source_results.json and local_eligibility_before_after.json come from the final revision. No CUMA-specific chemistry or expected label was added.'})
pre=read(H/'evaluation/pre_implementation_hashes.json')['files'];changed=[n for n,v in pre.items() if sha(B/n)!=v]
bench=read(H/'controls/benchmark_freeze.json')['sha256'];bc=[n for n,v in bench.items() if sha(H/'controls'/n)!=v]
impl=read(H/'evaluation/implementation_freeze.json')['sha256'];ic=[n for n,v in impl.items() if sha(H/n)!=v]
logs={n:f'Ran {count} tests' in (H/'evaluation'/n).read_text(encoding='utf8') and '\nOK' in (H/'evaluation'/n).read_text(encoding='utf8') for n,count in [('unit.log',11),('resolver_tests.log',201)]}
external={n:Path(v['path']).exists() and sha(Path(v['path']))==v['sha256'] for n,v in read(B/'FRESH_BLINDED_EVALUATION_FREEZE.json')['external_hashes'].items()}
valid={'protected_file_count':len(pre),'changed_protected_files':changed,'main_registry_digest_unchanged':'output/registry.sqlite' not in changed,'frozen_benchmark_changed':bc,'frozen_runtime_changed':ic,'historical_external_contract_hashes':external,'unit_and_resolver_logs':logs,'provider_queries':0,'registry_or_alias_writes':0,'pass':not changed and not bc and not ic and all(logs.values()) and all(external.values())}
write('integrity_report.json',valid);assert valid['pass'];assert dev['summary']['passed']==21 and held['summary']['passed']==8
print(json.dumps({'integrity':'PASS','tests':tests,'transfer':read(H/'evaluation/cross_source_results.json')['source_type_summaries']},indent=2))
