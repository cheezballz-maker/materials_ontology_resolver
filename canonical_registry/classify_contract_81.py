"""Lexical applicability assessment, never semantic validation or admission."""
import collections, hashlib, json, re
from pathlib import Path

H=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
freeze=load(H/'nomenclature_contract_freeze.json')
for name, expected in freeze['sha256'].items():
    assert hashlib.sha256((H/name).read_bytes()).hexdigest() == expected, name
data=load(H/'NOMENCLATURE_FALSE_HOLD_TAXONOMY.json')
assert len(data)==81 and len({x['record_id'] for x in data})==81
grammar=re.compile(r'1-(?:methyl|ethyl|propyl|butyl)-1H-(?:pyrazole|imidazole)')
out=[]
for record in data:
    names=[('preferred_name',record.get('preferred_name'))]+[('alias',a.get('text')) for a in record.get('aliases',[])]
    names=[(role,text) for role,text in names if isinstance(text,str) and text.strip()]
    exact=[{'role':role,'name':text} for role,text in names if grammar.fullmatch(text)]
    near=[{'role':role,'name':text} for role,text in names if not grammar.fullmatch(text) and grammar.fullmatch(text.strip().lower().replace('1h-','1H-'))]
    if exact:
        status='WITHIN_CONTRACT';reason='At least one complete source string meets the frozen lexical grammar; chemical guards and other source claims are not established.'
    elif near:
        status='POTENTIALLY_WITHIN_CONTRACT';reason='A complete case or boundary-whitespace variant resembles the frozen grammar but is not accepted by it; normalization and meaning require independent validation.'
    elif not names:
        status='INSUFFICIENT_EVIDENCE';reason='No available preferred name or alias.'
    else:
        status='OUTSIDE_CONTRACT';reason='No complete preferred-name or alias string meets the frozen pilot grammar; this does not imply chemical ambiguity.'
    out.append({'cuma_index':record['record_id'],'preferred_name':record.get('preferred_name'), 'previous_blocker':record['primary_blocker'], 'classification':status,'reason':reason,'matching_claims':exact,'near_claims':near,'identity_recovered':False})
counts=dict(collections.Counter(x['classification'] for x in out))
byblock={k:dict(collections.Counter(x['classification'] for x in out if x['previous_blocker']==k)) for k in sorted({x['previous_blocker'] for x in out})}
payload={'contract':'NSC-001 v1.0','source':'NOMENCLATURE_FALSE_HOLD_TAXONOMY.json','method':'After checking frozen contract digests, inspect whole preferred-name and alias strings; no source/candidate semantic validity inferred. Strictly lexical lower bound; other source conflicts not evaluated.','records':len(out),'counts':counts,'counts_by_previous_blocker':byblock,'cases':out,'recovered':0,'recovered_meaning':'No admission replay was run; zero asserted recoveries.'}
(H/'contract_81_case_applicability.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps({'counts':counts,'by_blocker':byblock,'matches':[x for x in out if x['classification']!='OUTSIDE_CONTRACT']},indent=2))
