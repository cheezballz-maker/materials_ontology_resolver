"""Run the actual integrated CLI using a fresh private fixture capability pair."""
import json,subprocess,sys,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent

def main():
 root=H/'evaluation'/('cli_'+uuid.uuid4().hex);root.mkdir(parents=True)
 common=[sys.executable,str(B/'unified_substance_resolution/run.py'),'--persist','--allow-creation','--permit-file',str(root/'association.permit.json'),'--creation-permit-file',str(root/'creation.permit.json'),'--verbosity','summary']
 rows=[]
 for source,out in [('pubchem','cli_created.json'),('pubchem','cli_retry.json'),('chebi','cli_chebi.json')]:
  dest=root/out
  proc=subprocess.run([*common,'--input',str(H/f'examples/{source}_creation_input.json'),'--output',str(dest)],capture_output=True,text=True,encoding='utf8',timeout=120)
  if proc.returncode:raise RuntimeError('CLI_FAILURE:'+proc.stderr)
  r=json.loads(dest.read_text(encoding='utf8'));rows.append(r);(H/'evaluation'/out).write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(out,r['resolution_status'],flush=True)
 assert [r['resolution_status'] for r in rows]==['NEW_SUBSTANCE_CREATED','EXISTING_SUBSTANCE_REUSED','EXISTING_SUBSTANCE_REUSED']
 assert len({r['canonical_substance_id'] for r in rows})==1
 assert rows[0]['source_revision']['recorded_at']==rows[1]['source_revision']['recorded_at']
 assert not rows[1]['association']['association_created'] and rows[2]['association']['association_created']
if __name__=='__main__':main()
