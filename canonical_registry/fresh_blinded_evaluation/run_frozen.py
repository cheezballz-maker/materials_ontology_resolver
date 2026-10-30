"""Run only after a complete independent reference manifest is frozen."""
import hashlib,json,sqlite3,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
freeze=read(B/'FRESH_BLINDED_EVALUATION_FREEZE.json');sample=read(H/'SAMPLE_FROZEN.json');ref=read(H/'REFERENCE_FROZEN.json')
for name,digest in freeze['implementation_hashes'].items():assert sha(B/name)==digest, 'BLINDED_EVALUATION_INVALIDATED_BY_CODE_CHANGE: '+name
for name,item in freeze['external_hashes'].items():assert sha(item['path'])==item['sha256'],'CONTRACT_CHANGED: '+name
assert sha(H/'fresh_sample.json')==sample['sample_sha256']
for name,digest in ref['files'].items():assert sha(H/name)==digest,'REFERENCE_FREEZE_MISMATCH: '+name
records=read(H/'fresh_sample.json');judgments=read(H/'reference_adjudication.json')
assert len(records)==len(judgments)==400 and {r['cuma_index'] for r in records}=={r['cuma_index'] for r in judgments}
assert not (H/'RUN_STARTED.json').exists();run=H/'run';run.mkdir()
db=sqlite3.connect(run/'candidates.sqlite');db.execute('CREATE TABLE candidate(cuma_index INTEGER PRIMARY KEY,name TEXT,aliases TEXT,status TEXT,diagnostic TEXT,evidence_json TEXT)')
for r in records:
    error=r['input_error'];db.execute('INSERT INTO candidate VALUES(?,?,?,?,?,?)',(r['cuma_index'],r['preferred_name'],json.dumps(r['aliases'],ensure_ascii=False),'UNRESOLVED','Frozen source input',json.dumps({'claims':[],'input_error':error})))
db.commit();db.close()
cmd=[sys.executable,'pipeline.py','build','--output',str(run),'--base-registry',str(H/'no_prior_registry.sqlite')]
start=dict(started_utc=datetime.now(timezone.utc).isoformat(),implementation_freeze_sha256=sha(B/'FRESH_BLINDED_EVALUATION_FREEZE.json'),sample_sha256=sha(H/'fresh_sample.json'),reference_freeze_sha256=sha(H/'REFERENCE_FROZEN.json'),command=cmd,provider_budget='Production CLI defaults: PubChem 120, ChEBI 500, GSRS 200, CompTox 20; cache initially empty; ordered by CUMA index.',base_registry='empty fresh registry')
(H/'RUN_STARTED.json').write_text(json.dumps(start,indent=2),encoding='utf-8')
changed=[]
with (H/'run.log').open('w',encoding='utf-8') as log:
    process=subprocess.Popen(cmd,cwd=B,stdout=log,stderr=subprocess.STDOUT)
    started=time.monotonic()
    while process.poll() is None:
        # Bridge compiles its already-frozen Java source at startup; allow that
        # brief write to finish, then verify the class and monitor it normally.
        changed=[name for name,digest in freeze['implementation_hashes'].items() if not (name=='RegistryBridge.class' and time.monotonic()-started<5) and (not (B/name).exists() or sha(B/name)!=digest)]
        if changed:
            process.terminate();process.wait(timeout=30);break
        time.sleep(2)
    returncode=process.wait()
changed=changed or [name for name,digest in freeze['implementation_hashes'].items() if sha(B/name)!=digest]
end=dict(finished_utc=datetime.now(timezone.utc).isoformat(),returncode=returncode,changed_files=changed)
(H/'RUN_FINISHED.json').write_text(json.dumps(end,indent=2),encoding='utf-8')
if changed:print('BLINDED_EVALUATION_INVALIDATED_BY_CODE_CHANGE');sys.exit(2)
print('Resolver return code:',returncode);sys.exit(returncode)
