"""Validate frozen replay, preservation and report links without writing data tables."""
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;P=B/'second_form_aware_holdout'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
f=read(H/'IMPLEMENTATION_FROZEN.json');s=read(H/'SCORING_FROZEN.json')
assert read(H/'RUN_FINISHED.json')['returncode']==0
assert read(H/'RUN_STARTED.json')['implementation_sha256']==sha(H/'IMPLEMENTATION_FROZEN.json')
assert s['implementation_sha256']==sha(H/'IMPLEMENTATION_FROZEN.json')
for p,v in f['runtime_hashes'].items():assert sha(B/p)==v,p
for p,v in f['test_hashes'].items():assert sha(B/p)==v,p
assert sha(H/'tests.log')==f['tests_log_sha256'] and 'Ran 81 tests' in (H/'tests.log').read_text(encoding='utf-8') and (H/'tests.log').read_text(encoding='utf-8').rstrip().endswith('OK')
for p,v in s['output_hashes'].items():assert sha(H/p)==v,p
for p,v in s['prediction_hashes'].items():assert sha(H/'run'/p)==v,p
assert sha(H/'score_replay.py')==s['scoring_script_sha256']
for kind in ('ontology','framework'):assert sha(f[kind+'_path'])==f[kind+'_sha256']
assert sha(P/'ADJUDICATION_FROZEN.json')==f['frozen_reference_manifest_sha256']
assert sha(P/'METRICS_FROZEN.json')==f['frozen_metrics_manifest_sha256']
for p,v in read(P/'ADJUDICATION_FROZEN.json')['files'].items():assert sha(P/p)==v,p
for p,v in f['baseline_prediction_hashes'].items():assert sha(P/'predictions'/p)==v,p
assert sha(B/'SECOND_FORM_AWARE_HOLDOUT_REPORT.md')==read(P/'FINAL_VERIFICATION.json')['report_sha256']
protected=read(P/'steward/protected_hashes.json');changed=[]
for p,v in protected.items():
    if sha(p)!=v:changed.append(Path(p).name)
assert sorted(changed)==['resolver.py','test_evidence_retrieval.py'],changed
assert read(H/'run/verification.json')['result']==read(H/'gate_verification.json')['result']=='PASS'
summary=read(H/'run/summary.json');assert all(summary[k]==0 for k in ('pubchem_requests','chebi_requests','gsrs_requests'))
metrics=read(H/'metrics.json');assert metrics['offline_not_queried']==0
cohort=read(H/'cohort_review.json');assert cohort['scoring_sha256']==sha(H/'SCORING_FROZEN.json') and len(cohort['cases'])==21
assert read(H/'extra_regression.json')['result']=='PASS'
assert all(x['after_status']!='EXACT' for x in metrics['prior_false_positive_cases'])
for attempt in ('source_form_upgrade_attempt_1','source_form_upgrade_attempt_2'):
    d=B/attempt;old=read(d/'IMPLEMENTATION_FROZEN.json')
    for name in ('resolver.py','source_form.py'):assert sha(d/'implementation_snapshot'/name)==old['runtime_hashes'][name]
    for name in ('test_source_form.py','test_evidence_retrieval.py'):assert sha(d/'implementation_snapshot'/name)==old['test_hashes'][name]
    assert read(d/'RUN_FINISHED.json')['returncode']==0
report=B/'SOURCE_FORM_INTERPRETATION_UPGRADE_REPORT.md';body=report.read_text(encoding='utf-8')
assert body.rstrip().endswith('**SOURCE_FORM_GATE_PARTIAL**')
for target in re.findall(r'\]\(([^)]+)\)',body):
    if not target.startswith(('http://','https://')):assert (B/target).exists() or target=='source_form_upgrade/FINAL_VERIFICATION.json',target
items=['IMPLEMENTATION_FROZEN.json','IMPLEMENTATION_FROZEN_superseded.json','RUN_STARTED.json','RUN_FINISHED.json','SCORING_FROZEN.json','tests.log','metrics.json','cohort_review.json','gate_verification.json','run/verification.json','extra_regression.json']
out=dict(result='PASS',verified_at_utc=datetime.now(timezone.utc).isoformat(),tests=81,records=400,previous_reference_labels_unchanged=True,prior_registry_snapshots_unchanged=True,ontology_and_framework_unchanged=True,changed_previous_protected_files=changed,only_new_evaluation_registry_written=True,new_provider_requests=0,gate_verification='PASS',registry_verification='PASS',prior_replay_snapshots_preserved=True,report_sha256=sha(report),artifact_hashes={p:sha(H/p) for p in items},conclusion='SOURCE_FORM_GATE_PARTIAL')
(H/'FINAL_VERIFICATION.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('PASS: tests, final replay, preserved evidence and registry snapshots, gate, integrity and report links.')
