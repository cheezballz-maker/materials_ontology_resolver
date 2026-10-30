"""Materialize control evidence and explicit not-run outcomes without cohort replay."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
write=lambda n,x:(H/n).write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
controls=read(H/'frozen_controls.json');obs=read(H/'development_observations.json');byname={x['name']:x for x in obs}
schema={'status':'INVESTIGATIVE_ONLY','fields':{'source_locant_span':'original locant token span','substituent_source_span':'contiguous surviving group stem and inline suffix token spans, where verified','parse_node':'OPSIN substituent XML','substituent_fragment':'parsed group and attachment atom','parent_target_atom':'same-result OPSIN atom','indicated_h_parent':'same-object H trace when present','structural_operation':'locanted join and resulting final CML bond','mapping_status':'observational only','operation_lineage_complete':'NOT_PROVEN','mobile_h_completeness':'UNKNOWN','operation_state':'UNKNOWN','identity_dimension_state':'UNKNOWN'},'note':'No admission result or confidence is produced.'}
write('substitution_trace_schema.json',schema)
positive=[];negative=[];unknown=[]
for c in controls['development']:
 x=byname[c['source']];r={'source':c['source'],'candidate':c['candidate'],'expected':c['expected'],'actual_operation':'UNKNOWN','actual_dimension':'UNKNOWN','goal':'NOT_MET' if c['expected'].startswith(('SUPPORTED','DIFFERENT')) else 'ABSTAINED','evidence':x}
 if c['expected'].startswith('SUPPORTED'):positive.append(r)
 elif c['expected'].startswith('DIFFERENT'):
  candidate=byname[c['candidate']];sys_path=str(B/'nomenclature_semantic_integration')
  import sys;sys.path.insert(0,sys_path)
  from graph_correspondence import correspond
  r['contradiction_graph_correspondence']=correspond(x['cml'],candidate['resolver_snapshot_candidate']['smiles']);r['reason']='Complete graph isomorphism is unavailable; no validated common-parent mapping proves the differing source attachment.';negative.append(r)
 else:unknown.append(r)
write('substitution_positive_controls.json',{'cases':positive,'expected_supported':len(positive),'observed_supported':0,'status':'ACCEPTANCE_NOT_MET'})
write('substitution_negative_controls.json',{'cases':negative,'expected_different':len(negative),'observed_different':0,'status':'ACCEPTANCE_NOT_MET'})
write('substitution_unknown_controls.json',{'cases':unknown,'abstained':len(unknown),'not_independently_demonstrated':['missing substituent provenance beyond tested paths','symmetry with divergent operation conclusions','complete mobile-H coverage','arbitrary atom replacement']})
write('substitution_holdout_controls.json',{'status':'NOT_RUN','reason':'Independent SUPPORTED and DIFFERENT acceptance controls did not both pass; holdout remains frozen.','controls':controls['holdout']})
write('substitution_81_case_replay.json',{'status':'NOT_RUN','reason':'User explicitly forbids corpus replay until independent SUPPORTED and DIFFERENT controls both pass.','historical_corpus_size':81,'applicability':None,'complete_provenance':None,'operation_supported':None,'dimension_supported':None,'recovered':None})
prior=read(B/'semantic_cohort_metrics.json');write('substitution_cohort_metrics.json',{'status':'NOT_REPLAYED','historical_only':{'correct_eligible':prior['correct_retained'],'correct_withheld':prior['correct_newly_withheld'],'incorrect_eligible':prior['incorrect_retained'],'eligible_total':prior['local_eligible'],'local_precision':prior['local_precision'],'local_recall':prior['local_recall']}})
gate=read(B/'semantic_gate_value.json');write('substitution_gate_value.json',{'status':'HISTORICAL_ONLY_NOT_RECALCULATED','categories':gate['categories'],'new_provider_queries':0})
oldbuild=read(B/'opsin_build_manifest.json');build=read(H/'build.json');rebuild=read(H/'rebuild.json');equiv=read(H/'public_output_equivalence.json')
manifest={'source_commit':build['upstream'],'official_release_sha256':oldbuild['release_sha256'],'prior_token_patch_sha256':oldbuild['poc_patch_sha256'],'operation_patch_sha256':sha(B/'operation_semantic_poc/operation-instrumentation.patch'),'substitution_patch_sha256':sha(H/'substitution-instrumentation.patch'),'frozen_controls_sha256':sha(H/'frozen_controls.json'),'development_public_output_equivalence':equiv,'rebuild':rebuild,'reproduction':'Reproduce the pinned token/operation POCs first, then run build_probe.py, analyze_development.py and check_public_outputs.py in this directory.'}
write('substitution_build_manifest.json',manifest)
f=read(B/'FRESH_BLINDED_EVALUATION_FREEZE.json');s=read(B/'deterministic_value_analysis/input_snapshot.json');allowed={'resolver.py','source_form.py','test_evidence_retrieval.py','test_source_form.py'}
unexpected=[n for n,v in f['implementation_hashes'].items() if n not in allowed and (not (B/n).exists() or sha(B/n)!=v)]
external={n:sha(Path(v['path']))==v['sha256'] for n,v in f['external_hashes'].items()};inputs=all(sha(B/n)==v for n,v in s['input_hashes'].items());F=B/'fresh_blinded_evaluation';rows=[]
for n in ('http_cache','chebi_cache','gsrs_cache','comptox_cache'):
 for p in sorted((F/'run'/n).glob('*.json')):rows.append(n+'/'+p.name+':'+sha(p))
cache={'file_count':len(rows),'digest':hashlib.sha256('\n'.join(rows).encode()).hexdigest()}==s['provider_cache']
terms=['17504','4373','30832','5684','5997','23839','30142','terephthalate','pyrazole','imidazole']
runtime=(H/'substitution-instrumentation.patch').read_text(encoding='utf8').lower();hits=[x for x in terms if x in runtime]
key=None;env=B/'.env.local'
if env.exists():
 for line in env.read_text(encoding='utf-8-sig').splitlines():
  if line.strip().startswith('CTX_API_KEY='):key=line.split('=',1)[1].strip().strip('"\'')
files=[p for p in H.glob('*') if p.is_file() and p.suffix.lower() in ('.py','.json','.log','.patch','.tsv')]+[B/'SOURCE_AWARE_SUBSTITUTION_SEMANTICS_REPORT.md']
leaks=[str(p.relative_to(B)) for p in files if p.exists() and key and len(key)>=12 and key.encode() in p.read_bytes()]
integrity={'external_contract_hashes':external,'unexpected_frozen_code_changes':unexpected,'frozen_inputs_unchanged':inputs,'provider_cache_unchanged':cache,'case_specific_runtime_tokens':hits,'credential_leak_files':leaks,'credential_scan':'PASS' if key and not leaks else ('FAIL' if leaks else 'NO_KEY_AVAILABLE'),'resolver_or_provider_modified_this_task':False}
integrity['pass']=all(external.values()) and not unexpected and inputs and cache and not hits and not leaks;write('substitution_integrity.json',integrity);assert integrity['pass']
print(json.dumps({'positive_expected':len(positive),'supported':0,'different':0,'integrity':integrity['pass'],'holdout':'NOT_RUN','corpus':'NOT_RUN'},indent=2))
