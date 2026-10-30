"""Hash frozen inputs and production files; checks never read secrets."""
import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;F=B/'fresh_blinded_evaluation'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
f=read(B/'FRESH_BLINDED_EVALUATION_FREEZE.json');r=read(F/'REFERENCE_FROZEN.json')
changed=[n for n,v in f['implementation_hashes'].items() if not (B/n).exists() or sha(B/n)!=v]
if changed:
 print('DETERMINISTIC_INTERPRETATION_ANALYSIS_INVALIDATED',changed);sys.exit(2)
assert all(sha(v['path'])==v['sha256'] for v in f['external_hashes'].values())
assert all(sha(F/n)==v for n,v in r['files'].items())
inputs=['FRESH_BLINDED_RESOLVER_EVALUATION_REPORT.md','FRESH_BLINDED_EVALUATION_FREEZE.json','PROVIDER_CORRESPONDENCE_REMEDIATION_REPORT.md','fresh_blinded_evaluation/fresh_sample.json','fresh_blinded_evaluation/SAMPLE_FROZEN.json','fresh_blinded_evaluation/REFERENCE_FROZEN.json','fresh_blinded_evaluation/reference_adjudication.json','fresh_blinded_evaluation/run/candidates.sqlite','fresh_blinded_evaluation/run/registry.sqlite','fresh_blinded_evaluation/evaluation_metrics.json','fresh_blinded_evaluation/REFERENCE_QUALITY_NOTES.json','fresh_blinded_evaluation/BLIND_SOURCE_AMBIGUITY_AUDIT.json']
def cache_digest():
    rows=[]
    for dirname in ('http_cache','chebi_cache','gsrs_cache','comptox_cache'):
        for p in sorted((F/'run'/dirname).glob('*.json')):rows.append(dirname+'/'+p.name+':'+sha(p))
    return dict(file_count=len(rows),digest=hashlib.sha256('\n'.join(rows).encode()).hexdigest())
current=dict(input_hashes={p:sha(B/p) for p in inputs},provider_cache=cache_digest(),supplemental_adjudication_sha256=sha(H/'completed_exact_adjudications.json'))
path=H/'input_snapshot.json'
if path.exists():
    initial=read(path);assert current==initial,'FROZEN_INPUT_OR_PROVIDER_CACHE_CHANGED'
    print('PASS: implementation, contracts, input snapshots and provider caches unchanged')
else:
    path.write_text(json.dumps(current,indent=2),encoding='utf-8');print('Baseline input hashes recorded')
