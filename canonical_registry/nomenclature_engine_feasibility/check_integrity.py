"""Snapshot and verify protected inputs without reading credentials."""
import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
f=read(B/'FRESH_BLINDED_EVALUATION_FREEZE.json');s=read(B/'deterministic_value_analysis/input_snapshot.json')
allowed={'resolver.py','source_form.py','test_evidence_retrieval.py','test_source_form.py'}
changed=[n for n,v in f['implementation_hashes'].items() if not (B/n).exists() or sha(B/n)!=v]
external={k:sha(Path(v['path']))==v['sha256'] for k,v in f['external_hashes'].items()}
inputs_ok=all(sha(B/n)==v for n,v in s['input_hashes'].items())
supplement=sha(B/'deterministic_value_analysis/completed_exact_adjudications.json')==s['supplemental_adjudication_sha256']
F=B/'fresh_blinded_evaluation';rows=[]
for n in ('http_cache','chebi_cache','gsrs_cache','comptox_cache'):
    for p in sorted((F/'run'/n).glob('*.json')):rows.append(n+'/'+p.name+':'+sha(p))
cache={'file_count':len(rows),'digest':hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
protected=['source_form.py','resolver.py','schema.sql','providers.py','provider_capabilities.py','evidence_retrieval.py','policy.py','NOMENCLATURE_FALSE_HOLD_TAXONOMY.json','false_hold_replay.json','deterministic_form_remediation/newly_blocked_cases.json','deterministic_form_remediation/deterministic_form_replay.json','opsin_ownership_followup_final/observations.json']
current={n:sha(B/n) for n in protected}
snapshot=H/'protected_hashes.json'
if not snapshot.exists():snapshot.write_text(json.dumps(current,indent=2),encoding='utf8')
unchanged=current==read(snapshot)
out={'older_freeze_unexpected_code_changes':[x for x in changed if x not in allowed],'external_contract_hashes':external,'old_frozen_inputs_unchanged':inputs_ok,'supplemental_reference_unchanged':supplement,'frozen_provider_cache_unchanged':cache==s['provider_cache'],'protected_files_unchanged_since_probe_snapshot':unchanged}
out['pass']=not out['older_freeze_unexpected_code_changes'] and all(external.values()) and inputs_ok and supplement and out['frozen_provider_cache_unchanged'] and unchanged
(H/'integrity_results.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out,indent=2));assert out['pass']
