"""Aggregate the completed offline replay without altering its databases."""
import collections,json,sqlite3
from pathlib import Path
H=Path(__file__).resolve().parent
db=sqlite3.connect((H/'run/candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
records=[dict(index=i,name=n,status=s,reason=r,evidence=json.loads(e)) for i,n,s,r,e in db.execute('select cuma_index,name,status,diagnostic,evidence_json from candidate')];db.close()
states=collections.Counter();admissions=[]
for row in records:
    ev=row['evidence'];retrieval=ev.get('retrieval',{})
    for q in retrieval.get('provider_states',[]):states[(q['provider'],q['state'])]+=1
    if row['status']=='EXACT':
        d=ev.get('decision',{}); admissions.append(dict(cuma_index=row['index'],name=row['name'],source_evidence_type='preferred name',source_interpretation=ev.get('name_interpretation'),source_form=ev.get('source_form'),decision_reason=row['reason'],evidence_states=d.get('evidence_states',[]),provider_states=retrieval.get('provider_states',[])))
result=dict(count=len(records),status_counts=dict(collections.Counter(x['status'] for x in records)),provider_query_states={f'{p}:{s}':v for (p,s),v in sorted(states.items())},admissions=admissions,historical=[{k:x[k] for k in ('index','name','status','reason')} for x in records if x['index'] in (5684,5997,23839,30142)],reason_counts=dict(collections.Counter(x['reason'] for x in records)))
(H/'analysis.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('count','status_counts','provider_query_states','historical')},indent=2));print('admissions',len(admissions))
