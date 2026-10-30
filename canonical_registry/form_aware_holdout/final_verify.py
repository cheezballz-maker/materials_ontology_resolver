"""Audit evaluation outputs without changing databases, references or production files."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

H = Path(__file__).resolve().parent

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    sample = read(H / 'SAMPLE_FROZEN.json')
    freeze = read(H / 'ADJUDICATION_FROZEN.json')
    scoring = read(H / 'SCORING_MANIFEST.json')
    protected = read(H / 'steward/protected_hashes.json')
    assert sha(sample['source_path']) == sample['source_sha256']
    assert sha(H / 'prepare_holdout.py') == sample['sampling_script_sha256']
    assert sha(H / 'steward/selection.json') == sample['selection_sha256']
    assert sha(H / 'steward/exclusions.json') == sample['exclusions_sha256']
    for f, digest in {**sample['packets'], **freeze['files']}.items():
        assert sha(H / f) == digest, f
    for f, digest in protected.items():
        assert sha(f) == digest, f
    for f, digest in scoring['prediction_hashes'].items():
        assert sha(H / 'predictions' / f) == digest, f
    for f, digest in scoring['result_hashes'].items():
        assert sha(H / f) == digest, f
    assert sha(H / 'score_holdout.py') == scoring['scorer_sha256']
    assert sha(H / 'ADJUDICATION_FROZEN.json') == scoring['reference_freeze_sha256']
    execution = read(H / 'EXECUTION.json')
    assert datetime.fromisoformat(freeze['frozen_at_utc']) < datetime.fromisoformat(execution['started_at_utc'])
    inputs = [r for n in (1, 2, 3) for r in read(H / f'packet_{n}/records.json')]
    assert len(inputs) == len({r['cuma_index'] for r in inputs}) == 360
    assert {r['cuma_index'] for r in inputs} == set(sample['indices'])
    exclusions = read(H / 'steward/exclusions.json')
    assert not set(sample['indices']) & set(exclusions['known_development_indices'])
    assert not set(sample['indices']) & {int(i) for i in exclusions['excluded_cuma']}
    with sqlite3.connect((H / 'predictions/candidates.sqlite').as_uri() + '?mode=ro', uri=True) as con:
        actual = {i: (name, json.loads(aliases)) for i, name, aliases in con.execute('SELECT cuma_index,name,aliases FROM candidate')}
        assert set(actual) == set(sample['indices'])
        for r in inputs:
            assert actual[r['cuma_index']] == (r['preferred_name'], r['aliases'])
    report = H.parent / 'FORM_AWARE_HOLDOUT_REPORT.md'
    text = report.read_text(encoding='utf-8')
    rows = read(H / 'disagreements.json')
    for r in rows:
        assert f"| {r['cuma_index']} |" in text, r['cuma_index']
    decision = read(H / 'decision.json')
    assert text.rstrip().splitlines()[-1] == decision['conclusion']
    assert read(H / 'predictions/verification.json')['result'] == 'PASS'
    result = {
        'result': 'PASS', 'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_and_sample_unchanged': True, 'reference_labels_unchanged': True,
        'protected_files_unchanged': len(protected), 'frozen_inputs_exactly_preserved': len(inputs),
        'all_disagreements_present_in_report': len(rows),
        'reference_freeze_precedes_execution': True,
        'prediction_databases_unchanged_since_scoring': True,
        'report_sha256': sha(report), 'decision_sha256': sha(H / 'decision.json'),
        'scoring_manifest_sha256': sha(H / 'SCORING_MANIFEST.json'),
        'registry_verification_sha256': sha(H / 'predictions/verification.json'),
    }
    (H / 'FINAL_VERIFICATION.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
