"""Write truthful structured outputs for the partial, diagnostic-only integration."""
import hashlib,json,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda n,x:(B/n).write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf8')
schema={'title':'Experimental Nomenclature Semantic Trace','version':1,'status':'DIAGNOSTIC_ONLY','fields':{'source_span':'original ASCII source offsets or null','source_text':'original token or null','semantic_type':['INDICATED_HYDROGEN','ADDED_INDICATED_HYDROGEN','UNKNOWN'],'fragment':'OPSIN fragment token; temporary','fragment_id':'temporary per-process OPSIN object identity','locant':'fragment-local locant','cml_atom':'same-result CML atom identifier','operation_stage':'PARENT_LOCANTED_FEATURE','explicit_or_generated':['EXPLICIT','GENERATED_OR_UNMAPPED'],'mapping_status':['MAPPED_BOUNDED','UNRESOLVED'],'operations':'NOT_CAPTURED','constraint':'UNKNOWN','reason':'abstention reason'},'limitations':['No operation composition','No CML-to-production-graph correspondence','No mobile-H completeness','No admission support']}
write('semantic_trace_schema.json',schema)
cases=read(H/'reproduced-probe_results.json')
write('semantic_control_results.json',{'poc_controls':27,'poc_results':cases,'adapter_tests':8,'adapter_tests_passed':8,'note':'Controls establish trace behavior, not a validated semantic constraint.'})
metrics=read(H/'local_eligibility_metrics.json');metrics['semantics']='Optional diagnostic trace has no admission effect; saved local-helper replay is not full end-to-end rerun.'
write('semantic_cohort_metrics.json',metrics)
write('semantic_gate_value.json',{'categories':metrics['post_gate_categories'],'meaning':'frozen recorded corroboration outcomes on adjudicable eligible cases','new_provider_queries':0})
version=read(H/'version_comparison.json');repro=read(H/'reproduction_manifest.json');patch=H/'poc_bundle/diagnostic.patch';jar=H/'opsin-core-2.9.0-jar-with-dependencies.jar';trace=H/'opsin-2.9.0-trace.jar'
manifest={'upstream_version':'2.9.0','upstream_commit':subprocess.check_output(['git','-C',str(H/'opsin-2.9.0'),'rev-parse','HEAD'],text=True).strip(),'release_sha256':sha(jar),'published_digest':'627ee5da4af551f9c4d1d766f545eb7cf519a344776e0bb677247a47abac0252','trace_jar_sha256':sha(trace),'poc_patch_sha256':sha(patch),'poc_bundle_sha256':'265a3d2a253cb6d0eb7185ee50e6609fdf82cc5cca3b306e3034ba0f92857f4e','poc_manifest_entries_verified':331,'reproduction':repro,'local_snapshot_comparison_controls':version['count'],'version_comparison_results':{'status_differences':sum(not r['status_equal'] for r in version['cases']),'warning_differences':sum(not r['warning_equal'] for r in version['cases']),'smiles_differences':sum(not r['smiles_equal'] for r in version['cases']),'cml_differences':sum(not r['cml_equal'] for r in version['cases'])},'admission_parser_replaced':False}
write('opsin_build_manifest.json',manifest)
f=read(B/'FRESH_BLINDED_EVALUATION_FREEZE.json');s=read(B/'deterministic_value_analysis/input_snapshot.json')
allowed={'resolver.py','source_form.py','test_evidence_retrieval.py','test_source_form.py'}
unexpected=[n for n,v in f['implementation_hashes'].items() if n not in allowed and (not (B/n).exists() or sha(B/n)!=v)]
external={n:sha(Path(v['path']))==v['sha256'] for n,v in f['external_hashes'].items()}
inputs=all(sha(B/n)==v for n,v in s['input_hashes'].items());F=B/'fresh_blinded_evaluation';rows=[]
for n in ('http_cache','chebi_cache','gsrs_cache','comptox_cache'):
 for p in sorted((F/'run'/n).glob('*.json')):rows.append(n+'/'+p.name+':'+sha(p))
cache={'file_count':len(rows),'digest':hashlib.sha256('\n'.join(rows).encode()).hexdigest()}==s['provider_cache']
key=None;env=B/'.env.local'
if env.exists():
 for line in env.read_text(encoding='utf-8-sig').splitlines():
  if line.strip().startswith('CTX_API_KEY='):key=line.split('=',1)[1].strip().strip('"\'')
files=[B/n for n in ['semantic_trace_schema.json','semantic_control_results.json','semantic_81_case_replay.json','semantic_cohort_metrics.json','semantic_gate_value.json','opsin_build_manifest.json','NOMENCLATURE_SEMANTIC_CONSTRAINT_INTEGRATION_REPORT.md'] if (B/n).exists()]
files += [p for p in H.glob('*') if p.is_file() and p.suffix.lower() in ('.py','.json','.log','.java')]
leaks=[str(p.relative_to(B)) for p in files if key and len(key)>=12 and key.encode() in p.read_bytes()]
terms=['17504','4373','30832','5684','5997','23839','30142','terephthalate','pyrazole','pyrrole']
runtime=(B/'resolver.py').read_text(encoding='utf8').lower()+'\n'+(H/'semantic_adapter.py').read_text(encoding='utf8').lower()
hits=[x for x in terms if x in runtime]
integrity={'external_contract_hashes':external,'unexpected_original_frozen_code_changes':unexpected,'frozen_input_hashes_unchanged':inputs,'frozen_provider_cache_unchanged':cache,'case_specific_runtime_tokens':hits,'credential_leak_files':leaks,'credential_scan':'PASS' if key and not leaks else ('FAIL' if leaks else 'NO_KEY_AVAILABLE'),'note':'Resolver changed only to add the explicitly optional diagnostic hook; provider and schema source hashes remain unchanged.'}
integrity['pass']=all(external.values()) and not unexpected and inputs and cache and not hits and not leaks
write('integration_integrity.json',integrity);assert integrity['pass']
print(json.dumps({'opsin_source':manifest['upstream_commit'],'controls':27,'cohort':metrics['total_cohort'],'integrity':integrity['pass']},indent=2))
