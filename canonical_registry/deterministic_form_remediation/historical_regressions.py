"""Run historical safety cases with offline providers in a new workspace."""
import json,sqlite3,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path.insert(0,str(B))
from providers import Bridge,PubChem,ChEBI,GSRS
from comptox import CompTox
from resolver import Resolver
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
old=[]
for n in (1,2,3):old+=read(B/f'second_form_aware_holdout/packet_{n}/records.json')
cases=[x for x in old if x['cuma_index'] in (5684,5997,23839,30142)]
assert len(cases)==4
db=sqlite3.connect((B/'form_aware_evaluation/run/candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
name,aliases=db.execute('select name,aliases from candidate where cuma_index=5').fetchone();db.close()
cases.append(dict(cuma_index=5,preferred_name=name,aliases=json.loads(aliases)))
cache=B/'grounding_remediation_final_scored/run';bridge=Bridge()
try:
    engine=Resolver(bridge,PubChem(cache/'http_cache',offline=True),ChEBI(cache/'chebi_cache',offline=True),gsrs=GSRS(cache/'gsrs_cache',offline=True),comptox=CompTox(H/'historical_ctx_cache',offline=True))
    output=[]
    for case in cases:
        r=engine.evaluate(case['preferred_name'],case['aliases'])
        output.append(dict(cuma_index=case['cuma_index'],name=case['preferred_name'],status=r['status'],reason_codes=r['reason_codes']))
finally:bridge.close()
(H/'historical_regressions.json').write_text(json.dumps(output,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(output,indent=2,ensure_ascii=False))
assert all(x['status'] not in ('EXACT','AUTO_ACCEPT') for x in output)
