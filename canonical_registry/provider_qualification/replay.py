"""Replay frozen source records and old caches into a new isolated output."""
import hashlib,json,shutil,sqlite3,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;P=B/'second_form_aware_holdout';run=H/'run'
assert not run.exists();run.mkdir()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
f=read(P/'ADJUDICATION_FROZEN.json')
for p,v in f['files'].items():assert sha(P/p)==v,p
selection=read(P/'steward/selection.json');records=sum((read(P/f'packet_{n}/records.json') for n in (1,2,3)),[])
assert len(records)==400 and len({r['cuma_index'] for r in records})==400
db=sqlite3.connect(run/'candidates.sqlite');db.execute('CREATE TABLE candidate(cuma_index INTEGER PRIMARY KEY,name TEXT,aliases TEXT,status TEXT,diagnostic TEXT,evidence_json TEXT)')
for r in records:db.execute('INSERT INTO candidate VALUES(?,?,?,?,?,?)',(r['cuma_index'],r['preferred_name'],json.dumps(r['aliases'],ensure_ascii=False),'UNRESOLVED','Original frozen source input',json.dumps({'claims':[],'input_error':selection['input_errors'].get(str(r['cuma_index']))})))
db.commit();db.close()
for folder in ('http_cache','chebi_cache','gsrs_cache'):shutil.copytree(B/'grounding_remediation_final_scored/run'/folder,run/folder)
files=['provider_capabilities.py','evidence_model.py','evidence_retrieval.py','resolver.py','comptox.py','policy.py','form_characterizer.py','identity_comparator.py']
(H/'frozen.json').write_text(json.dumps(dict(files={p:sha(B/p) for p in files},source_manifest_sha256=sha(P/'ADJUDICATION_FROZEN.json'),offline=True,records=400),indent=2),encoding='utf-8')
with (H/'replay.log').open('w',encoding='utf-8') as log:r=subprocess.run([sys.executable,'pipeline.py','build','--output',str(run),'--budget','2400','--chebi-budget','4000','--gsrs-budget','800','--offline'],cwd=B,stdout=log,stderr=subprocess.STDOUT)
print('replay return code',r.returncode);sys.exit(r.returncode)
