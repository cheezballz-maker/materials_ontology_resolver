"""Historical tautomer probe with old cache only; no case-specific runtime data."""
import json,sqlite3,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path.insert(0,str(B))
from providers import Bridge,PubChem,ChEBI
from comptox import CompTox
from resolver import Resolver
p=B/'form_aware_evaluation/run';c=sqlite3.connect((p/'candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
name,aliases=c.execute('select name,aliases from candidate where cuma_index=5').fetchone();c.close()
bridge=Bridge()
try:
 pub=PubChem(p/'http_cache',offline=True);chebi=ChEBI(p/'chebi_cache',offline=True);ctx=CompTox(H/'case5_comptox_cache',offline=True)
 r=Resolver(bridge,pub,chebi,comptox=ctx).evaluate(name,json.loads(aliases));ev=r['evidence']
 result=dict(cuma_index=5,name=name,status=r['status'],reason_codes=r['reason_codes'],structure=r.get('structure',{}).get('smiles'),
  source_interpretation=ev.get('name_interpretation'),source_form=ev.get('source_form'),preliminary_source_form=ev.get('preliminary_source_form'),evidence_states=r.get('evidence_states'),
  provider_states=ev.get('retrieval',{}).get('provider_states'),network_requests=pub.calls+chebi.calls+ctx.calls,
  note='Old offline caches only; no injected reviewed fixture. Missing evidence is not evidence of absence.')
 (H/'case5_probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'status':result['status'],'reason_codes':result['reason_codes'],'network_requests':result['network_requests']},indent=2))
finally:bridge.close()

