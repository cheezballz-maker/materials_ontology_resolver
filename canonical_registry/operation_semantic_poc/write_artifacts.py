"""Write evidence-based artifacts; never call a missing semantic result a replay."""
import hashlib,json,collections
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
write=lambda n,x:(H/n).write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
schema={'fields':{'parent_semantic_state':'source token/span, owning fragment, atom object ID and snapshot at application','operations[]':'ordered observed mutation events with pre/post snapshots; source provenance NOT_CAPTURED','final_opsin_state':'same-result CML element, formal charge, isotope, neighboring bonds and explicit H count','resolver_graph_mapping':'bounded all-isomorphism result or UNKNOWN','mobile_h_completeness':'UNKNOWN','constraint_state':'UNKNOWN','constraint_reason':'operation source provenance, mutation coverage and mobile-H completeness are unproven'},'warnings':'This schema describes an investigative probe, not a production acceptance certificate.'}
write('operation_trace_schema.json',schema)
old=read(B/'semantic_81_case_replay.json');assert len(old['cases'])==81
cases=[{'cuma_index':x['cuma_index'],'preferred_name':x['preferred_name'],'capability_applicable':'NOT_ASSESSED_BY_OPERATION_POC','token_mapping_prior':x['trace_established'],'operation_lineage_complete':False,'graph_correspondence':'NOT_TESTED','mobile_h_completeness':'UNKNOWN','constraint_result':'UNKNOWN','eligibility_before':'LOCALLY_WITHHELD','eligibility_after':'NOT_REPLAYED','reason':'Independent semantic-support and contradiction controls not validated; no feature-gated admission implementation.'} for x in old['cases']]
write('semantic_81_case_replay.json',{'status':'NOT_REPLAYED_WITH_OPERATION_POC','reason':'The required independent semantic admission controls did not pass because operation provenance and completeness remain unimplemented.','cases':cases,'recovered':None})
metrics=read(H/'local_eligibility_metrics.json');metrics['interpretation']='Current-policy saved-evidence helper replay only; no operation-aware eligibility change was implemented or evaluated.'
write('semantic_cohort_metrics.json',metrics)
write('semantic_gate_value.json',{'categories':metrics['post_gate_categories'],'status':'UNCHANGED_SAVED_EVIDENCE','provider_calls':0,'scope':'Current policy, not an operation-aware admission experiment.'})
f=read(B/'FRESH_BLINDED_EVALUATION_FREEZE.json');s=read(B/'deterministic_value_analysis/input_snapshot.json');allow={'resolver.py','source_form.py','test_evidence_retrieval.py','test_source_form.py'}
unexpected=[n for n,v in f['implementation_hashes'].items() if n not in allow and (not (B/n).exists() or sha(B/n)!=v)]
external={n:sha(Path(v['path']))==v['sha256'] for n,v in f['external_hashes'].items()}
inputs=all(sha(B/n)==v for n,v in s['input_hashes'].items());F=B/'fresh_blinded_evaluation';rows=[]
for n in ('http_cache','chebi_cache','gsrs_cache','comptox_cache'):
 for p in sorted((F/'run'/n).glob('*.json')):rows.append(n+'/'+p.name+':'+sha(p))
cache={'file_count':len(rows),'digest':hashlib.sha256('\n'.join(rows).encode()).hexdigest()}==s['provider_cache']
terms=['17504','4373','30832','5684','5997','23839','30142','terephthalate','pyrazole','pyrrole']
runtime='\n'.join(p.read_text(encoding='utf8').lower() for p in [B/'resolver.py',B/'nomenclature_semantic_integration/semantic_adapter.py',B/'nomenclature_semantic_integration/graph_correspondence.py'])
hits=[x for x in terms if x in runtime]
key=None;env=B/'.env.local'
if env.exists():
 for line in env.read_text(encoding='utf-8-sig').splitlines():
  if line.strip().startswith('CTX_API_KEY='):key=line.split('=',1)[1].strip().strip('"\'')
files=[p for p in H.glob('*') if p.is_file() and p.suffix in ('.py','.json','.log','.patch')]+[B/'OPSIN_OPERATION_LINEAGE_SEMANTIC_POC_REPORT.md']
leaks=[str(p.relative_to(B)) for p in files if p.exists() and key and len(key)>=12 and key.encode() in p.read_bytes()]
check={'external_contract_hashes':external,'unexpected_original_frozen_code_changes':unexpected,'frozen_inputs_unchanged':inputs,'frozen_provider_cache_unchanged':cache,'case_specific_runtime_tokens':hits,'credential_leak_files':leaks,'credential_scan':'PASS' if key and not leaks else ('FAIL' if leaks else 'NO_KEY_AVAILABLE')}
check['pass']=all(external.values()) and not unexpected and inputs and cache and not hits and not leaks
write('operation_integrity.json',check);assert check['pass']
manifest=read(H/'build_manifest.json');prior=read(B/'opsin_build_manifest.json')
manifest.update(upstream_commit=prior['upstream_commit'],release_sha256=prior['release_sha256'],prior_instrumentation_patch_sha256=prior['poc_patch_sha256'],operation_instrumentation_patch_sha256=sha(H/'operation-instrumentation.patch'),public_equivalence=read(H/'public_output_equivalence.json'),reproduction='First reproduce the pinned prior trace using nomenclature_semantic_integration/reproduce_windows.py, then run operation_semantic_poc/build_operation_probe.py and analyze_controls.py. Source and patch copies are not the production engine.')
write('opsin_operation_build_manifest.json',manifest)
print(json.dumps({'integrity':check['pass'],'case_replay':'NOT_RUN','saved_cohort':metrics['total_cohort']},indent=2))
