"""Independently replay the source gate on the evaluation snapshot; read-only."""
import json,sqlite3,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path.insert(0,str(B))
from source_form import assess,DIMENSIONS
from identity_comparator import compare

c=sqlite3.connect((H/'run/candidates.sqlite').as_uri()+'?mode=ro',uri=True)
r=sqlite3.connect((H/'run/registry.sqlite').as_uri()+'?mode=ro',uri=True)
subjects=promoted=0
for i,name,aliases,status,reason,raw in c.execute('SELECT * FROM candidate ORDER BY cuma_index'):
    if status!='EXACT':continue
    ev=json.loads(raw);original=json.loads(aliases);claims=ev['claims'];assert len(claims)==len(original)+1
    candidate=ev['decision']['structure'];intent=ev['decision'].get('form',{}).get('source_assertion',{})
    fresh=assess(name,claims[0],list(zip(original,claims[1:])),candidate,intent,ev.get('local_source_support'))
    assert fresh==ev['source_form'],i
    assert fresh['status']=='SUPPORTED' and set(fresh['dimensions'])==set(DIMENSIONS),i
    assert all(x['compatibility'] in ('SUPPORTED','NOT_APPLICABLE') for x in fresh['dimensions'].values()),i
    for a,claim in zip(ev['alias_decisions'],claims[1:]):
        if a['accepted']:
            assert claim['status']=='SUCCESS' and compare(candidate,claim['structure'])['assessment']=='EXACT',i
            assert assess(a['alias'],claim,[],claim['structure'])['status']=='SUPPORTED',(i,a['alias'])
            promoted+=1
    subjects+=1
assert subjects==r.execute("SELECT count(*) FROM substance_reconciliation WHERE resolution_status='EXACT'").fetchone()[0]
c.close();r.close()
out=dict(result='PASS',admissions_rechecked=subjects,promoted_aliases_rechecked=promoted,method='Recomputed source-claim compatibility and alias-specificity gate using saved input claims; no provider requests',limitations='Gate consistency does not independently prove source-intent interpretation is complete.')
(H/'gate_verification.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
