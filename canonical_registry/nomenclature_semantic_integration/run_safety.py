"""Historical controls with opt-in tracing; providers offline or call-forbidden."""
import json,sqlite3,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;F=B/'fresh_blinded_evaluation';sys.path.insert(0,str(B));sys.path.insert(0,str(H))
from resolver import Resolver
from providers import Bridge,PubChem,ChEBI,GSRS
from comptox import CompTox
import semantic_adapter
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
class NoCalls:
 def __getattr__(self,name):
  def fail(*args,**kwargs):raise AssertionError('Unexpected parser/provider call '+name)
  return fail
samples={x['cuma_index']:x for x in read(F/'fresh_sample.json')}
db=sqlite3.connect((F/'run/candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
evs={i:json.loads(raw) for i,raw in db.execute('select cuma_index,evidence_json from candidate')};db.close();out=[]
for i in (17504,4373,30832):
 s=samples[i];r=Resolver(NoCalls(),NoCalls(),NoCalls(),semantic_adapter=semantic_adapter)
 r.claim_cache={c['original']:c for c in evs[i]['claims']}
 x=r.evaluate(s['preferred_name'],s['aliases']);out.append(dict(cuma_index=i,status=x['status'],reason_codes=x['reason_codes'],trace=x['evidence'].get('nomenclature_semantics')))
old=[]
for n in (1,2,3):old+=read(B/f'second_form_aware_holdout/packet_{n}/records.json')
cases=[x for x in old if x['cuma_index'] in (5684,5997,23839,30142)];assert len(cases)==4
db=sqlite3.connect((B/'form_aware_evaluation/run/candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
name,aliases=db.execute('select name,aliases from candidate where cuma_index=5').fetchone();db.close()
cases.append(dict(cuma_index=5,preferred_name=name,aliases=json.loads(aliases)))
cache=B/'grounding_remediation_final_scored/run';bridge=Bridge()
try:
 engine=Resolver(bridge,PubChem(cache/'http_cache',offline=True),ChEBI(cache/'chebi_cache',offline=True),gsrs=GSRS(cache/'gsrs_cache',offline=True),comptox=CompTox(H/'safety_ctx_cache',offline=True),semantic_adapter=semantic_adapter)
 for case in cases:
  x=engine.evaluate(case['preferred_name'],case['aliases']);out.append(dict(cuma_index=case['cuma_index'],status=x['status'],reason_codes=x['reason_codes'],trace=x['evidence'].get('nomenclature_semantics')))
finally:bridge.close()
assert len(out)==8 and all(x['status'] not in ('AUTO_ACCEPT','EXACT') for x in out)
(H/'safety_results.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps([dict(cuma_index=x['cuma_index'],status=x['status']) for x in out],indent=2))
