"""Launch the unchanged resolver once after the blind-reference gate."""
import subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from freeze_and_prepare import H,B,protect,read,save,sha

protect();f=read(H/'ADJUDICATION_FROZEN.json')
assert sha(H/'PROTOCOL.md')==f['protocol_sha256']
assert sha(H/'SAMPLE_FROZEN.json')==f['sample_sha256']
for p,v in f['files'].items():assert sha(H/p)==v,p
assert not (H/'RUN_STARTED.json').exists(),'Exactly one resolver attempt permitted'
assert not (H/'predictions/registry.sqlite').exists()
for folder in ['http_cache','chebi_cache','gsrs_cache']:
    p=H/'predictions'/folder;assert not p.exists() or not any(p.iterdir()),'Fresh empty caches required'
assert (H/'SCORING_PROTOCOL_FROZEN.json').exists(),'Freeze scoring code before prediction'
scoring=read(H/'SCORING_PROTOCOL_FROZEN.json')
for p,v in scoring['files'].items():assert sha(H/p)==v,p
command=[sys.executable,'pipeline.py','build','--output',str(H/'predictions'),'--budget',str(f['pubchem_budget']),'--chebi-budget',str(f['chebi_budget']),'--gsrs-budget',str(f['gsrs_budget'])]
save(H/'RUN_STARTED.json',dict(started_at_utc=datetime.now(timezone.utc).isoformat(),command=command,adjudication_sha256=sha(H/'ADJUDICATION_FROZEN.json'),scoring_sha256=sha(H/'SCORING_PROTOCOL_FROZEN.json'),fresh_runtime_caches=True))
with (H/'run.log').open('w',encoding='utf-8') as log:
    result=subprocess.run(command,cwd=B,stdout=log,stderr=subprocess.STDOUT)
save(H/'RUN_FINISHED.json',dict(finished_at_utc=datetime.now(timezone.utc).isoformat(),returncode=result.returncode,log_sha256=sha(H/'run.log')))
print('Resolver finished with exit code',result.returncode)
sys.exit(result.returncode)
