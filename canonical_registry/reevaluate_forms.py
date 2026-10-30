"""Prepare/score a development re-evaluation; frozen reference files are read-only.

prepare reads original input packets only, never reference outcomes. build uses
pipeline.py. score is invoked only after the new prediction snapshot exists.
"""
import argparse,hashlib,json,shutil,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WORK=ROOT/'form_aware_evaluation'
FROZEN=ROOT/'blinded_validation'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def prepare(out=None,cache_source=None):
    out=Path(out or WORK/'run');out.mkdir(parents=True,exist_ok=True)
    if (out/'candidates.sqlite').exists():raise FileExistsError('Prepared run exists')
    records=[]
    for n in (1,2,3):records+=read(FROZEN/f'packet_{n}/records.json')
    assert len(records)==len({r['cuma_index'] for r in records})==300
    db=sqlite3.connect(out/'candidates.sqlite')
    db.execute('CREATE TABLE candidate(cuma_index INTEGER PRIMARY KEY,name TEXT,aliases TEXT,status TEXT,diagnostic TEXT,evidence_json TEXT)')
    for r in records:db.execute('INSERT INTO candidate VALUES(?,?,?,?,?,?)',(r['cuma_index'],r['preferred_name'],json.dumps(r['aliases'],ensure_ascii=False),'UNRESOLVED','Original frozen sample input only',json.dumps({'claims':[],'input_error':None})))
    db.commit();db.close()
    for kind in ('http_cache','chebi_cache'):
        cache=out/kind;cache.mkdir(exist_ok=True)
        for file in (Path(cache_source or ROOT/'output')/kind).glob('*.json'):shutil.copyfile(file,cache/file.name)
    if not (WORK/'run_protocol.json').exists():
        (WORK/'run_protocol.json').write_text(json.dumps({'records':300,'pubchem_request_budget':700,'chebi_request_budget':700,'reference_labels_used_by_engine':False,'known_regression_evidence':'reviewed_evidence.json; prior source structures, no labels','sample_role':'development re-evaluation, not a new blinded estimate','original_registry_mutated':False},indent=2),encoding='utf-8')
    print('Prepared 300 original source records; copied bounded prior PubChem HTTP cache.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare']);p.add_argument('--output',type=Path);p.add_argument('--cache-source',type=Path);args=p.parse_args()
    prepare(args.output,args.cache_source)
