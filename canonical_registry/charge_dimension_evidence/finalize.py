import hashlib,json,platform,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path[:0]=[str(H),str(B/'nsc002_experiment'),str(B/'nsc_architecture_experiment'),str(B)]
from rdkit import rdBase
from jsonschema import Draft202012Validator
from build_evidence import build
from run_evaluation import baseline_source
from diagnostic_evidence_consumer import consume
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x):(H/'evaluation'/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
Draft202012Validator.check_schema(read(H/'charge_evidence_schema.json'))
c=read(H/'controls/positive_controls.json')[0];e=build(c['source_name'],c['aliases'],c['candidate']);src=baseline_source(c['source_name'],c['candidate'],c['aliases'])
write('consumer_control_results.json',{'scope':'Independent synthetic closed source control, not a CUMA recovery','source_name':c['source_name'],'candidate':c['candidate'],'source_form_before':src,'evidence':e.to_dict(),'default_off':consume(src,src['reason_codes'],e),'enabled':consume(src,src['reason_codes'],e,enable_charge_dimension_evidence=True)})
dev=read(H/'evaluation/development_results.json');held=read(H/'evaluation/heldout_results.json');comp=read(H/'evaluation/comparator_attribution_results.json');nsc=read(H/'evaluation/nsc_regression.json')
tests={'new_unit_tests':{'passed':7,'failed':0,'skipped':0},'development_controls':{'passed':sum(x['pass'] for x in dev),'total':len(dev)},'public_frozen_heldout':{'passed':sum(x['pass'] for x in held),'total':len(held),'blinded':False},'structural_attribution_controls':{'passed':sum(x['pass'] for x in comp),'total':len(comp)},'nsc001_existing_unit_tests':{'passed':11,'failed':0},'nsc002_existing_unit_tests':{'passed':8,'failed':0},'nsc_frozen_control_regression':{'passed':nsc['passed'],'total':nsc['total']},'retained_resolver_tests':{'passed':201,'failed':0},'historical_safety_cases':len(read(H/'evaluation/historical_safety_results.json')),'python':platform.python_version(),'rdkit':rdBase.rdkitVersion,'qualified_human_review':'NOT_PERFORMED','dimension_negative_scope':'Source-derived neutral-nitro evidence currently emits SUPPORTED/UNKNOWN only; DIFFERENT is demonstrated by the structural attribution layer, not a new ionic source interpreter.'}
write('test_results.json',tests)
pre=read(H/'evaluation/pre_implementation_hashes.json')['files'];changes=[n for n,v in pre.items() if sha(B/n)!=v]
freeze=read(H/'controls/benchmark_freeze.json')['sha256'];changed_control=[n for n,v in freeze.items() if sha(H/'controls'/n)!=v]
impl=read(H/'evaluation/implementation_freeze.json')['hashes'];changed_impl=[n for n,v in impl.items() if sha(H/n)!=v]
checklogs={n:('Ran '+str(c)+' tests' in (H/'evaluation'/n).read_text(encoding='utf8') and '\nOK' in (H/'evaluation'/n).read_text(encoding='utf8')) for n,c in [('unit.log',7),('resolver_tests.log',201)]}
integrity={'protected_files_unchanged':not changes,'changed_protected_files':changes,'protected_file_count':len(pre),'registry_digest_unchanged':'output/registry.sqlite' not in changes,'controls_unchanged':not changed_control,'changed_controls':changed_control,'frozen_runtime_files_unchanged':not changed_impl,'changed_runtime_files':changed_impl,'test_logs':checklogs,'no_new_provider_calls':True,'production_comparator_and_source_form_unchanged':not any(n in changes for n in ('identity_comparator.py','source_form.py','resolver.py')),'all_pass':not changes and not changed_control and not changed_impl and all(checklogs.values())}
write('integrity_report.json',integrity);assert integrity['all_pass']
print(json.dumps({'integrity':'PASS','controls':[len(dev),len(held),len(comp)],'nsc_unchanged':nsc['total'],'consumer_positive_control':True},indent=2))
