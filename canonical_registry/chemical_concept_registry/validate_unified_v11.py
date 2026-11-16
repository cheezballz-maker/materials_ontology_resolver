"""Replay the exact frozen cohort without overwriting its original results."""
import hashlib
import json
import sqlite3
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

from registry import BASE, FIXTURES, initialize, sha
from unified_chemical import UnifiedChemicalResolver
from providers import Bridge
from rdkit import RDLogger

sys.path.insert(0, str(BASE/'unified_substance_resolution'))
from unified_resolver import SubstanceResolver
from warehouse_sample_adapter import TrustedWarehouseAdapter
from registry_identity_adapter import RegistrySnapshot
from registry_matching_models import RetrievalPolicy

H = Path(__file__).resolve().parent
P = BASE/'real_world_normalization/pilot_readonly_20261103'
PILOT = BASE/'warehouse_admission_consolidation/output/normalized_pilot.sqlite'
BASELINE = H/'evaluation_v11.json'


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def main():
    RDLogger.DisableLog('rdApp.*')
    start = time.perf_counter()
    baseline = read(BASELINE)
    cohort = baseline['records']
    assert len(cohort) == len({r['source_id'] for r in cohort}) == 65
    guards = {**baseline['protected_hashes_after'], baseline['fixture_database']: sha(Path(baseline['fixture_database']))}
    before = {p: sha(Path(p)) for p in guards}
    assert before == guards
    packets = {p['source_record_id']: p for p in map(json.loads, (P/'sampled_records.jsonl').read_text(encoding='utf8').splitlines())}
    with sqlite3.connect(PILOT.as_uri()+'?mode=ro&immutable=1', uri=True) as db:
        historical = {sid: json.loads(r) for sid,r in db.execute('select original_substance_id,result_json from warehouse_pilot')}
    snapshot = RegistrySnapshot(PILOT)
    assert snapshot.sqlite_integrity == [('ok',)] and not snapshot.foreign_key_errors
    registry = initialize(FIXTURES/('validation_'+uuid.uuid4().hex+'.sqlite'))
    bridge = Bridge(timeout=5)
    router = UnifiedChemicalResolver(registry, snapshot, name_adapter=bridge, substance_resolver=SubstanceResolver(official_validator=bridge.official))
    adapter = TrustedWarehouseAdapter(batch_file=P/'sampled_records.json', expected_sha256=read(P/'sampling_manifest.json')['source_json_sha256'])
    rows = []
    try:
        for old in cohort:
            sid = old['source_id']
            packet = packets[sid]
            previous = historical[sid]
            pilot_id = previous.get('canonical_substance_id') or previous.get('creation',{}).get('substance_id')
            r = router.resolve(packet, source_adapter=adapter, request_key='validation:'+sid,
                               retrieval_policy=RetrievalPolicy(allow_exploratory_names=False))
            search = r.get('substance_search')
            if search:
                comparisons = search.pop('comparisons')
                search['comparison_counts'] = dict(Counter(x['chemical_status'] for x in comparisons))
                search['relevant_comparisons'] = [x for x in comparisons if x['candidate_substance_id']==pilot_id
                     or x['chemical_status']!='CHEMICALLY_DIFFERENT']
            raw = packet['record']
            rows.append({'source_id':sid,'stratum':old['stratum'],'previous_pilot_outcome':old['previous_pilot_outcome'],
                'pilot_substance_id':pilot_id,'pilot_registry_structure':snapshot.entries[pilot_id]['candidate'].structure if pilot_id in snapshot.entries else None,
                'source_fields':{k:v for k,v in raw.items() if k in ('isometric_smiles','jchem_smiles','inchi_key','inchi_id','mol_formula','substance_master_name_en','iupac_name','jchem_name','name','scientificname')},
                'baseline':{k:old[k] for k in ('outcome','diagnostics','substance_comparisons','elapsed_seconds')},
                'corrected':r})
            print(len(rows), old['stratum'], r['outcome'], pilot_id, r['substance_id'], r['elapsed_seconds'], flush=True)
    finally:
        bridge.close()
    after = {p: sha(Path(p)) for p in guards}
    assert after == before
    with sqlite3.connect(registry.path.as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    payload = dict(frozen_baseline_sha256=sha(BASELINE), registry_sha256=snapshot.sha256,
                   registry_count=len(snapshot.entries), fixture_database=str(registry.path),
                   hashes_before=before, hashes_after=after, elapsed_seconds=time.perf_counter()-start,
                   outcomes=dict(Counter(r['corrected']['outcome'] for r in rows)), records=rows)
    (H/'unified_validation_v11.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(payload['outcomes'],flush=True)


if __name__ == '__main__':
    main()
