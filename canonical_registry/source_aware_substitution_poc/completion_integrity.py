"""Recheck historic frozen contracts without touching registry/provider data."""
import hashlib
import json
from pathlib import Path

H = Path(__file__).resolve().parent
B = H.parent
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
freeze = read(B / 'FRESH_BLINDED_EVALUATION_FREEZE.json')
snapshot = read(B / 'deterministic_value_analysis/input_snapshot.json')
allowed = {'resolver.py', 'source_form.py', 'test_evidence_retrieval.py', 'test_source_form.py'}
changed = [n for n, v in freeze['implementation_hashes'].items()
           if n not in allowed and (not (B/n).exists() or sha(B/n) != v)]
external = {n: Path(v['path']).exists() and sha(Path(v['path'])) == v['sha256']
            for n, v in freeze['external_hashes'].items()}
inputs = all((B/n).exists() and sha(B/n) == v for n, v in snapshot['input_hashes'].items())
rows = []
for n in ('http_cache', 'chebi_cache', 'gsrs_cache', 'comptox_cache'):
    for p in sorted((B/'fresh_blinded_evaluation'/'run'/n).glob('*.json')):
        rows.append(n+'/'+p.name+':'+sha(p))
cache = {'file_count':len(rows), 'digest':hashlib.sha256('\n'.join(rows).encode()).hexdigest()} == snapshot['provider_cache']
result = {'external_contract_hashes':external, 'unexpected_historical_frozen_code_changes':changed,
          'historical_frozen_inputs_unchanged':inputs, 'provider_cache_unchanged':cache,
          'historical_code_exceptions':sorted(allowed),
          'holdout_frozen_sha256':sha(H/'completion_holdout_frozen.json'),
          'experimental_only':True}
result['pass'] = all(external.values()) and not changed and inputs and cache
(H/'completion_integrity.json').write_text(json.dumps(result, indent=2), encoding='utf8')
print(json.dumps(result, indent=2))
assert result['pass']
