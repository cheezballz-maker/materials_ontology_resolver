"""Three bounded CTX searches. Credentials never enter output."""
import json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent))
from comptox import CompTox
from chemistry import describe
from evidence_retrieval import provenance
from evidence_model import assess,aggregate_route

c=CompTox(H/'ctx_cache',budget=8,timeout=15)
items=[('name','Toluene','Cc1ccccc1','source_preferred_name'),('name','Deuterium oxide','[2H]O[2H]','source_preferred_name'),('DTXSID','DTXSID4051243','[2H]O[2H]','source_identifier')]
out=[]
for kind,query,structure,origin in items:
    result=c.retrieve(kind,query);key=dict(kind=kind,value=query,origin=origin,asserts_source_identity=True)
    checks=[assess(provenance(r,result,key),describe(structure)) for r in result.get('rows',[])]
    out.append(dict(provider='CompTox',route=kind,query=query,status=result['status'],state=aggregate_route(checks,result['status'],bool(result.get('rows'))),records=[dict(record_id=x['record_id'],state=x['state'],reason=x['reason'],structure=x.get('structure'),comparison=x.get('comparison')) for x in checks]))
(H/'live_smoke.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'requests':c.calls,'states':[x['state'] for x in out]}))
