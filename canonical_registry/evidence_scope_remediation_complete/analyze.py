"""Read-only development replay analysis against both earlier freezes."""
import json,sqlite3,collections,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def get(path):
 c=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
 return {i:dict(name=n,status=s,reason=r,evidence=json.loads(e)) for i,n,s,r,e in c.execute('select cuma_index,name,status,diagnostic,evidence_json from candidate')}
old=get(B/'grounding_remediation_final_scored/run/candidates.sqlite');pre=get(B/'explicit_multicomponent_upgrade_release2/run/candidates.sqlite');new=get(H/'run/candidates.sqlite')
prior=load(B/'grounding_remediation_final_scored/change_analysis.json')
blocked={x['cuma_index'] for x in prior['changed'] if x['likely_cause']=='SOURCE_PROVIDER_FAILURE_HOLD'}
recovered=[];transitions=collections.Counter();baseline=collections.Counter();provider=collections.Counter();case=[];capability=collections.Counter()
for i,y in new.items():
 x=old[i];transitions[(x['status'],y['status'])]+=1;baseline[(pre[i]['status'],y['status'])]+=1
 if i in blocked:case.append(dict(cuma_index=i,name=y['name'],before=x['status'],after=y['status'],reason=y['reason']))
 if 'UNSUPPORTED_' in y['reason']:
  for reason in y['reason'].split(';'):
   if reason.startswith('UNSUPPORTED_'):capability[reason]+=1
 ev=y['evidence']
 for q in ev.get('retrieval',{}).get('queries',[]):
  if q.get('provider')=='CompTox':
   provider['adapter_queries']+=1;provider['status:'+q['status']]+=1;provider['records']+=len(q.get('rows',[]))
 for state in ev.get('decision',{}).get('evidence_states',[]):
  if state.get('provider')=='CompTox':provider['state:'+state['state']]+=1
 if y['status']=='EXACT' and x['status']!='EXACT':
  dec=ev.get('decision',{});recovered.append(dict(cuma_index=i,name=y['name'],source_type='typed' if ev.get('claims',[{}])[0].get('origin')=='explicit typed source structure' else 'name',source_interpretation=ev.get('name_interpretation',{}).get('status'),structure=dec.get('structure',{}).get('smiles'),evidence_states=dec.get('evidence_states'),providers=ev.get('retrieval',{}).get('provider_states'),reason=y['reason']))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
integrity={}
for folder,manifest,subdir in [('explicit_multicomponent_upgrade_release2','SCORING_FROZEN.json','run'),('stereo_locant_upgrade_complete','SCORING_FROZEN.json','run'),('grounding_remediation_final_scored','SCORING_FROZEN.json','run'),('second_form_aware_holdout','METRICS_FROZEN.json','predictions')]:
 base=B/folder;data=load(base/manifest);integrity[folder]={n:sha(base/subdir/n)==v for n,v in data['prediction_hashes'].items()}
f=load(H/'IMPLEMENTATION_FROZEN.json');before=load(B/'grounding_remediation_final_scored/IMPLEMENTATION_FROZEN.json')
integrity['schema_unchanged']=f['runtime_hashes']['schema.sql']==before['runtime_hashes']['schema.sql'];integrity['ontology_unchanged']=f['ontology_sha256']==before['ontology_sha256']
result=dict(previous_partial_transitions={f'{k[0]}->{k[1]}':v for k,v in transitions.items()},previous_stable_transitions={f'{k[0]}->{k[1]}':v for k,v in baseline.items()},provider_failure_cohort=case,cohort_status_counts=dict(collections.Counter(x['after'] for x in case)),new_admissions=recovered,comptox=dict(provider),capability_reasons=dict(capability),integrity=integrity)
(H/'analysis.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('previous_partial_transitions','previous_stable_transitions','cohort_status_counts','comptox','capability_reasons','integrity')},indent=2));print('cohort',len(case),'new admissions',len(recovered))
