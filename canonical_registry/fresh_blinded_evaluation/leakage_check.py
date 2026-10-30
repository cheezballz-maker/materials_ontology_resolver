"""Check source-record overlap without loading any prediction files."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sample=read(H/'fresh_sample.json');ids={x['cuma_index'] for x in sample};previous={}
for folder in ('blinded_validation','form_aware_holdout','second_form_aware_holdout'):
    prior=set()
    for p in (B/folder).glob('packet_*/records.json'):prior.update(x['cuma_index'] for x in read(p))
    previous[folder]=dict(prior_count=len(prior),overlap_count=len(ids&prior))
hist=ids&{5,5684,5997,23839,30142,9152,46724,52217}
manifest=read(H/'SAMPLE_FROZEN.json');actual=hashlib.sha256((H/'fresh_sample.json').read_bytes()).hexdigest()
result=dict(sample_sha256_matches=actual==manifest['sample_sha256'],prior_packet_overlap=previous,historical_target_overlap_count=len(hist),qualified_rule='Known-artifact checks; cannot exclude undisclosed informal prior exposure.')
(H/'leakage_check.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
