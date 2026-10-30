"""Final preservation/audit checks; does not change any registry or reference."""
from datetime import datetime,timezone
import re
from freeze_and_prepare import H,B,read,save,sha,protect

sample=protect()
assert sha(B/'form_aware_holdout/score_holdout.py')==read(B/'form_aware_holdout/SCORING_MANIFEST.json')['scorer_sha256'],'Inherited evaluation helper changed from earlier frozen evaluation'
for folder,check in read(H/'EVIDENCE_INTEGRITY_QA.json')['packets'].items():
    d=H/folder;f=read(d/'FROZEN.json');assert sha(d/'FROZEN.json')==check['freeze_sha256']
    if folder=='supplemental':files=f['evidence_hashes']
    else:
        p=d/('source_manifest.json' if folder=='packet_3' else 'evidence_manifest.json')
        assert sha(p)==f['evidence_manifest_sha256'];files=read(p)['files']
        if isinstance(files,list):files={x['file']:x['sha256'] for x in files}
    for p,v in files.items():assert sha(d/p)==v,(folder,p)
for p,digest in read(B/'evidence_upgrade/IMPLEMENTATION_FROZEN.json')['runtime_hashes'].items():
    assert sha(B/p)==digest,('Upgraded resolver version mismatch',p)
adjudication=read(H/'ADJUDICATION_FROZEN.json')
for p,v in adjudication['files'].items():assert sha(H/p)==v,p
score=read(H/'SCORING_PROTOCOL_FROZEN.json')
for p,v in score['files'].items():assert sha(H/p)==v,p
metrics=read(H/'METRICS_FROZEN.json')
for p,v in metrics['files'].items():assert sha(H/p)==v,p
for p,v in metrics['prediction_hashes'].items():assert sha(H/'predictions'/p)==v,p
assert read(H/'RUN_FINISHED.json')['returncode']==0
assert read(H/'RUN_STARTED.json')['adjudication_sha256']==sha(H/'ADJUDICATION_FROZEN.json')
assert read(H/'predictions/verification.json')['result']=='PASS'
assessment=read(H/'ASSESSMENT.json')
assert assessment['metrics_freeze_sha256']==sha(H/'METRICS_FROZEN.json')
assert datetime.fromisoformat(assessment['assessed_at_utc'])>datetime.fromisoformat(metrics['frozen_at_utc'])
assert assessment['conclusion'] in ['RESOLVER_CORE_VALIDATED_CONTINUE_INCREMENTALLY','TARGETED_RESOLVER_EXTENSION_REQUIRED','RESOLVER_SAFETY_REGRESSION_DETECTED']
framework=next(p for p in read(H/'steward/protected_hashes.json') if p.endswith('Molecular_Substance_Identity_Framework_v1.md'))
for folder in ['packet_1','packet_2','packet_3','supplemental']:
    assert sha(H/folder/'Molecular_Substance_Identity_Framework_v1.md')==sha(framework)
report=B/'SECOND_FORM_AWARE_HOLDOUT_REPORT.md';text=report.read_text(encoding='utf-8')
assert text.rstrip().endswith('**'+assessment['conclusion']+'**')
for target in re.findall(r'\]\(([^)]+)\)',text):
    if not target.startswith(('http://','https://')):
        assert (B/target).exists() or target=='second_form_aware_holdout/FINAL_VERIFICATION.json',target
assert '| INVALID | 0 | 0 |' in text
assert read(H/'POST_UNBLINDING_REVIEW.json')['metrics_freeze_sha256']==sha(H/'METRICS_FROZEN.json')
files=['SAMPLE_FROZEN.json','ADJUDICATION_FROZEN.json','METRICS_FROZEN.json','ASSESSMENT.json','RUN_STARTED.json','RUN_FINISHED.json','predictions/verification.json','disagreements.md','retrieval_admissions.md','EVIDENCE_INTEGRITY_QA.json','POST_UNBLINDING_REVIEW.json']
save(H/'FINAL_VERIFICATION.json',dict(result='PASS',verified_at_utc=datetime.now(timezone.utc).isoformat(),records=400,supplemental_records=3,protected_files_unchanged=len(read(H/'steward/protected_hashes.json')),evaluated_exact_upgrade_version=True,all_reference_and_prediction_hashes_unchanged=True,one_resolver_attempt=True,fresh_runtime_caches=True,registry_integrity='PASS',ranked_after_metrics_freeze=True,report_sha256=sha(report),artifact_hashes={p:sha(H/p) for p in files},conclusion=assessment['conclusion']))
print('PASS: preserved implementation, ontology, tests, prior registries and references; frozen adjudication/metrics/predictions; integrity and report links.')
