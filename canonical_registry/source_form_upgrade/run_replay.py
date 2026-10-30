"""One cache-controlled development replay, never writes old data."""
import hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;P=B/'second_form_aware_holdout'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
save=lambda p,x:Path(p).write_text(json.dumps(x,indent=2),encoding='utf-8')
f=read(H/'IMPLEMENTATION_FROZEN.json');assert not (H/'RUN_STARTED.json').exists()
assert sha(H/'run/candidates.sqlite')==f['original_input_sha256']
for name,v in f['runtime_hashes'].items():assert sha(B/name)==v,name
for name,v in f['test_hashes'].items():assert sha(B/name)==v,name
for name,v in f['baseline_prediction_hashes'].items():assert sha(P/'predictions'/name)==v,name
assert sha(P/'ADJUDICATION_FROZEN.json')==f['frozen_reference_manifest_sha256']
assert not (H/'run/registry.sqlite').exists()
cmd=[sys.executable,'pipeline.py','build','--output',str(H/'run'),'--budget','2400','--chebi-budget','4000','--gsrs-budget','800','--offline']
save(H/'RUN_STARTED.json',dict(started_at_utc=datetime.now(timezone.utc).isoformat(),implementation_sha256=sha(H/'IMPLEMENTATION_FROZEN.json'),command=cmd))
with (H/'run.log').open('w',encoding='utf-8') as log:r=subprocess.run(cmd,cwd=B,stdout=log,stderr=subprocess.STDOUT)
save(H/'RUN_FINISHED.json',dict(finished_at_utc=datetime.now(timezone.utc).isoformat(),returncode=r.returncode,log_sha256=sha(H/'run.log')))
print('Development replay exit code:',r.returncode);sys.exit(r.returncode)
