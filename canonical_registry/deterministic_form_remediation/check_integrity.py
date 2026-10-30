"""Check frozen artifacts and unchanged code without reading credentials."""
import hashlib, json
from pathlib import Path
H=Path(__file__).resolve().parent; B=H.parent; F=B/'fresh_blinded_evaluation'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
freeze=read(B/'FRESH_BLINDED_EVALUATION_FREEZE.json')
allowed={'resolver.py','source_form.py','test_evidence_retrieval.py','test_source_form.py'}
changed=[n for n,v in freeze['implementation_hashes'].items() if not (B/n).exists() or sha(B/n)!=v]
unexpected=[n for n in changed if n not in allowed]
external={n:sha(Path(v['path']))==v['sha256'] for n,v in freeze['external_hashes'].items()}
ref=read(F/'REFERENCE_FROZEN.json')
reference_ok=all(sha(F/n)==v for n,v in ref['files'].items())
snapshot=read(B/'deterministic_value_analysis/input_snapshot.json')
inputs_ok=all(sha(B/n)==v for n,v in snapshot['input_hashes'].items())
rows=[]
for dirname in ('http_cache','chebi_cache','gsrs_cache','comptox_cache'):
    for p in sorted((F/'run'/dirname).glob('*.json')):rows.append(dirname+'/'+p.name+':'+sha(p))
cache=dict(file_count=len(rows),digest=hashlib.sha256('\n'.join(rows).encode()).hexdigest())
cache_ok=cache==snapshot['provider_cache']
supplement_ok=sha(B/'deterministic_value_analysis/completed_exact_adjudications.json')==snapshot['supplemental_adjudication_sha256']
key=None
env=B/'.env.local'
if env.exists():
    for line in env.read_text(encoding='utf-8-sig').splitlines():
        if line.strip().startswith('CTX_API_KEY='):key=line.split('=',1)[1].strip().strip('"\'')
leaks=[]
if key and len(key)>=12 and 'placeholder' not in key.lower():
    for p in list(H.rglob('*'))+[B/'DETERMINISTIC_FORM_SAFETY_REMEDIATION_REPORT.md']:
        if p.is_file() and key.encode() in p.read_bytes():leaks.append(str(p.relative_to(B)))
out=dict(changed_frozen_code=changed,unexpected_frozen_code_changes=unexpected,external=external,reference_files_unchanged=reference_ok,input_hashes_unchanged=inputs_ok,provider_cache_unchanged=cache_ok,supplemental_reference_unchanged=supplement_ok,credential_scan='PASS' if key and not leaks else ('FAIL' if leaks else 'NOT_SCANNED_NO_KEY'),credential_leak_files=leaks)
out['pass']=not unexpected and all(external.values()) and reference_ok and inputs_ok and cache_ok and supplement_ok and not leaks
(H/'integrity_results.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
if not out['pass']:raise SystemExit(1)
