"""Run the three full-resolver probes with saved claims and no provider calls."""
import json,sqlite3,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;F=B/'fresh_blinded_evaluation';sys.path.insert(0,str(B))
from resolver import Resolver
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
samples={x['cuma_index']:x for x in read(F/'fresh_sample.json')}
db=sqlite3.connect((F/'run/candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
evs={i:json.loads(raw) for i,raw in db.execute('select cuma_index,evidence_json from candidate')};db.close()
class NoCalls:
    def __getattr__(self,name):
        def fail(*args,**kwargs):raise AssertionError('Unexpected external or parser call: '+name)
        return fail
out=[]
for i in (17504,4373,30832):
    s=samples[i];ev=evs[i];r=Resolver(NoCalls(),NoCalls(),NoCalls())
    r.claim_cache={c['original']:c for c in ev['claims']}
    result=r.evaluate(s['preferred_name'],s['aliases'])
    out.append(dict(cuma_index=i,status=result['status'],local_eligibility=result['evidence']['local_eligibility'],reason_codes=result['reason_codes']))
    assert result['evidence']['local_eligibility']['status']=='NOT_ELIGIBLE'
(H/'regression_probes.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
