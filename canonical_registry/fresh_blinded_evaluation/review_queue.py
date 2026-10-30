"""Produce a complete case-review queue without changing frozen references."""
import json,sqlite3
from pathlib import Path
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
cases=read(H/'resolver_results.json');refs={r['cuma_index']:r for r in read(H/'reference_adjudication.json')}
db=sqlite3.connect((H/'run/candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
ev={i:json.loads(e) for i,e in db.execute('select cuma_index,evidence_json from candidate')};db.close()
queue=[]
for case in cases:
    if 'REQUIRES_REVIEW' not in case['verdict']:continue
    i=case['cuma_index'];r=refs[i];e=ev[i]
    queue.append(dict(case=case,reference_reason=r.get('reason'),reference_evidence=r.get('evidence'),reference_aliases=r.get('alias_judgments'),source_form=e.get('source_form'),decision=e.get('decision'),provider_states=e.get('retrieval',{}).get('provider_states')))
(H/'review_queue.json').write_text(json.dumps(queue,indent=2,ensure_ascii=False),encoding='utf-8')
print('Flagged decisions requiring case review:',len(queue))
