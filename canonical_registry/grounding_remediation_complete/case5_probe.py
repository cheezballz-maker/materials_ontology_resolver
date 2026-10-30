"""Offline regression probe of the historical tautomer case; no fixture injection."""
import json,sqlite3,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path.insert(0,str(B))
from providers import Bridge,PubChem,ChEBI
from resolver import Resolver
p=B/'form_aware_evaluation/run';c=sqlite3.connect((p/'candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
name,aliases=c.execute('select name,aliases from candidate where cuma_index=5').fetchone();c.close()
bridge=Bridge()
try:
 pub=PubChem(p/'http_cache',offline=True);chebi=ChEBI(p/'chebi_cache',offline=True)
 r=Resolver(bridge,pub,chebi).evaluate(name,json.loads(aliases));ev=r['evidence']
 result=dict(cuma_index=5,name=name,status=r['status'],reason_codes=r['reason_codes'],structure=r.get('structure',{}).get('smiles'),
  provider_summaries=[dict(provider=q.get('provider'),status=q.get('status'),query=q.get('query'),rows=len(q.get('rows',[]))) for q in ev.get('retrieval',{}).get('queries',[])],
  network_requests=pub.calls+chebi.calls,note='Old form-aware offline caches only; no injected reviewed fixture or GSRS. Missing cache evidence is not evidence of absence.')
 (H/'historical_case5_probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
finally:bridge.close()
