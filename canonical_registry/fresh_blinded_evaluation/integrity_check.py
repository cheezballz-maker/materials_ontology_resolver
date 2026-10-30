"""Post-run freeze and prior-snapshot verification; no secrets are read or printed."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
f=read(B/'FRESH_BLINDED_EVALUATION_FREEZE.json');r=read(H/'REFERENCE_FROZEN.json');s=read(H/'SAMPLE_FROZEN.json');start=read(H/'RUN_STARTED.json');end=read(H/'RUN_FINISHED.json')
source=B.parent.parent/'cuma/CUMA v1 (ENG Only).xlsx'
checks=dict(implementation_unchanged=all(sha(B/n)==v for n,v in f['implementation_hashes'].items()),contract_and_runtime_configuration_unchanged=all(sha(v['path'])==v['sha256'] for v in f['external_hashes'].values()),sample_unchanged=sha(H/'fresh_sample.json')==s['sample_sha256']==start['sample_sha256'],source_workbook_unchanged=sha(source)==s['source_sha256'],reference_files_unchanged=all(sha(H/n)==v for n,v in r['files'].items()),reference_freeze_unchanged=sha(H/'REFERENCE_FROZEN.json')==start['reference_freeze_sha256'],quality_notes_unchanged=sha(H/'REFERENCE_QUALITY_NOTES.json')==read(H/'QUALITY_REVIEW_FROZEN.json')['notes_sha256'],blind_ambiguity_audit_unchanged=sha(H/'BLIND_SOURCE_AMBIGUITY_AUDIT.json')==read(H/'BLIND_SOURCE_AUDIT_FROZEN.json')['notes_sha256'],watchdog_reported_no_code_change=not end['changed_files'],resolver_completed=end['returncode']==0,registry_integrity=read(H/'run/verification.json')['result']=='PASS')
old=read(B/'provider_correspondence_remediation/frozen.json')
checks['prior_registry_unchanged']=sha(B/'provider_qualification/run/registry.sqlite')==old['prior_registry_sha256']
checks['prior_candidate_workspace_unchanged']=sha(B/'provider_qualification/run/candidates.sqlite')==old['prior_candidate_sha256']
out=dict(result='PASS' if all(checks.values()) else 'FAIL',checks=checks)
(H/'integrity_check.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
if not all(checks.values()):raise SystemExit(1)
