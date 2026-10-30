import collections,json,sqlite3
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
def records(p):
    db=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True)
    rows={i:dict(index=i,name=n,status=s,reason=r,evidence=json.loads(e)) for i,n,s,r,e in db.execute('select cuma_index,name,status,diagnostic,evidence_json from candidate')};db.close();return rows
new=records(H/'run/candidates.sqlite');old=records(B/'provider_qualification/run/candidates.sqlite');assert len(new)==len(old)==400
states=collections.Counter();admissions=[];previous=[]
for i,x in new.items():
    ev=x['evidence'];d=ev.get('decision',{});retr=ev.get('retrieval',{});routes=retr.get('provider_states',[])
    for q in routes:states[(q['provider'],q['state'])]+=1
    if x['status']=='EXACT':
        good=[z for z in d.get('evidence_states',[]) if z['state']=='CORROBORATES' and any(r['state']=='CORROBORATES' and (r['provider'],r['route'],r['query'],r['query_origin'])==(z.get('provenance',{}).get('retrieved_via'),z.get('provenance',{}).get('query_type'),z.get('provenance',{}).get('query'),z.get('provenance',{}).get('query_origin')) for r in d.get('provider_routes',[]))]
        assert good and all(z['provenance']['query_origin']!='validated_hypothesis' for z in good),i
        admissions.append(dict(index=i,name=x['name'],status=x['status'],reason=x['reason'],source_evidence_type='source preferred name',source_interpretation=ev.get('name_interpretation',{}).get('status'),source_form=ev.get('source_form',{}).get('status'),qualifying=good,provider_routes=d.get('provider_routes',[]),query_states=routes))
    if old[i]['status']=='EXACT':
        oldgood=[z for z in old[i]['evidence'].get('decision',{}).get('evidence_states',[]) if z.get('state')=='CORROBORATES']
        previous.append(dict(index=i,name=x['name'],prior_routes=[dict(provider=z.get('provider'),basis=z.get('correspondence_basis'),query_origin=z.get('provenance',{}).get('query_origin'),record_id=z.get('record_id')) for z in oldgood],new_status=x['status'],new_reason=x['reason']))
out=dict(record_count=len(new),statuses=dict(collections.Counter(x['status'] for x in new.values())),provider_route_states={f'{p}:{s}':v for (p,s),v in sorted(states.items())},admissions=admissions,previous_admissions=previous,historical=[{k:x[k] for k in ('index','name','status','reason')} for x in new.values() if x['index'] in (5684,5997,23839,30142)])
(H/'analysis.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:out[k] for k in ('record_count','statuses','provider_route_states','historical','previous_admissions')},indent=2));print('admissions',len(admissions))
