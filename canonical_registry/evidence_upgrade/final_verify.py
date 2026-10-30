"""Read-only post-report audit; writes only FINAL_VERIFICATION.json."""
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

B = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(B))
from score_evidence_evaluation import protected_check, read, sha

H = B / 'evidence_upgrade'
F = B / 'form_aware_holdout'
protection = protected_check()
manifest = read(H / 'SCORING_MANIFEST.json')
freeze = read(H / 'IMPLEMENTATION_FROZEN.json')
for name, digest in manifest['reference_hashes'].items():
    assert sha(F / name) == digest, name
for name, digest in freeze['source_input_hashes'].items():
    assert sha(F / name) == digest, name
for name, digest in manifest['prediction_hashes'].items():
    assert sha(H / 'run' / name) == digest, name
assert sha(B / 'score_evidence_evaluation.py') == manifest['scorer_sha256']
assert sha(F / 'score_holdout.py') == manifest['frozen_metric_implementation_sha256']

safety = read(H / 'new_admission_safety.json')
manual = read(H / 'MANUAL_SAFETY_REVIEW.json')
assert manual['reference_labels_revised'] is False
assert len(safety) == len(manual['cases']) == 11
assert {x['cuma_index'] for x in safety} == {x['cuma_index'] for x in manual['cases']}
assert all(all(x['guards'].values()) for x in safety)
assert all(x['engine_guards'] == 'PASS' for x in manual['cases'])
assert Counter(x['frozen_reference_verdict'] for x in manual['cases']) == {'CORRECT': 8, 'UNVERIFIED': 3}
assert read(H / 'revoked_admissions.json') == []
assert read(H / 'changed_retained_identities.json') == []
assert read(H / 'run' / 'verification.json')['result'] == 'PASS'
test_log = (H / 'tests.log').read_text(encoding='utf-8-sig')
assert 'Ran 62 tests' in test_log and test_log.rstrip().endswith('OK')

report_path = B / 'EXACT_FORM_EVIDENCE_UPGRADE_REPORT.md'
report = report_path.read_text(encoding='utf-8')
assert report.rstrip().endswith('**EVIDENCE_RETRIEVAL_INCREMENT_VALIDATED**')
missing = []
for target in re.findall(r'\]\(([^)]+)\)', report):
    if not target.startswith(('https://', 'http://')) and not (B / target).exists():
        if target != 'evidence_upgrade/FINAL_VERIFICATION.json':
            missing.append(target)
assert not missing, missing

artifacts = [report_path, B / 'EVIDENCE_RETRIEVAL.md', B / 'README.md',
             H / 'SCORING_MANIFEST.json', H / 'MANUAL_SAFETY_REVIEW.json',
             H / 'new_admission_safety.json', H / 'before_metrics.json',
             H / 'after_metrics.json', H / 'tests.log', H / 'run' / 'verification.json',
             Path(__file__)]
result = dict(result='PASS', verified_at_utc=datetime.now(timezone.utc).isoformat(),
              evaluation_type='development re-evaluation',
              protection=protection, frozen_runtime_files=len(freeze['runtime_hashes']),
              frozen_sources_and_references_unchanged=True,
              scored_prediction_databases_unchanged=True,
              scorer_unchanged=True, tests_passed=62, registry_integrity='PASS',
              newly_admitted_cases_reviewed=11, confirmed=8, unverified=3,
              revoked_admissions=0, changed_retained_identities=0,
              report_links_valid=True,
              artifact_hashes={str(p.relative_to(B)):sha(p) for p in artifacts})
(H / 'FINAL_VERIFICATION.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('protection', 'artifact_hashes')}, indent=2))
