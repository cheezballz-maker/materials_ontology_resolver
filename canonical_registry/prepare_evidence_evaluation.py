"""Prepare original holdout inputs only. Never loads reference labels into resolution."""
import hashlib,json,shutil,sqlite3
from datetime import datetime,timezone
from pathlib import Path

B=Path(__file__).resolve().parent;H=B/'evidence_upgrade';F=B/'form_aware_holdout'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

if __name__=='__main__':
    out=H/'run'
    if out.exists():raise FileExistsError('Select a fresh evaluation; never overwrite a run')
    sample=read(F/'SAMPLE_FROZEN.json');source=[]
    for f,digest in sample['packets'].items():
        assert sha(F/f)==digest;source.extend(read(F/f))
    assert len(source)==360 and {r['cuma_index'] for r in source}==set(sample['indices'])
    out.mkdir();db=sqlite3.connect(out/'candidates.sqlite')
    db.execute('CREATE TABLE candidate(cuma_index INTEGER PRIMARY KEY,name TEXT,aliases TEXT,status TEXT,diagnostic TEXT,evidence_json TEXT)')
    errors=read(F/'steward/selection.json')['input_errors']
    for r in source:
        db.execute('INSERT INTO candidate VALUES(?,?,?,?,?,?)',(r['cuma_index'],r['preferred_name'],json.dumps(r['aliases'],ensure_ascii=False),'UNRESOLVED','Original frozen input; development re-evaluation',json.dumps({'claims':[],'input_error':errors.get(str(r['cuma_index']))})))
    db.commit();db.close()
    cache_hashes={}
    for folder in ('http_cache','chebi_cache'):
        src=F/'predictions'/folder;shutil.copytree(src,out/folder)
        for p in src.glob('*.json'):cache_hashes[str(p.relative_to(F/'predictions'))]=sha(p)
    runtime=['providers.py','resolver.py','evidence_retrieval.py','pipeline.py','verify.py','registry_builder.py','chemistry.py','form_characterizer.py','identity_comparator.py','policy.py','schema.sql','test_registry.py','test_forms.py','test_evidence_retrieval.py']
    data=dict(prepared_at_utc=datetime.now(timezone.utc).isoformat(),evaluation_type='development re-evaluation',records=360,
              sample_sha256=sha(F/'SAMPLE_FROZEN.json'),source_input_hashes=sample['packets'],runtime_hashes={f:sha(B/f) for f in runtime},
              baseline_cache_hashes=cache_hashes,request_budgets={'PubChem':1800,'ChEBI':3000,'GSRS':500},
              command='python pipeline.py build --output evidence_upgrade/run --budget 1800 --chebi-budget 3000 --gsrs-budget 500',
              references_used_by_runtime=False,reference_labels_changed=False)
    (H/'IMPLEMENTATION_FROZEN.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print('Prepared 360 original inputs; copied baseline HTTP evidence; implementation frozen.')
