"""Compare independent builds and trace behavior, excluding temporary object IDs."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf8'))
first=Path(read(H/'build-first.json')['temporary_build']);second=Path(read(H/'build_manifest.json')['temporary_build'])
def hashes(path):return {p.relative_to(path).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*.class')}
def normalized(path):
 result=[]
 for line in path.read_text(encoding='utf8').splitlines():
  p=line.split('\t')
  if p[0]=='E' and len(p)>14:p[14]='TEMPORARY_FRAGMENT_ID'
  result.append(p)
 return result
out={'class_file_maps_identical':hashes(first/'operation-classes')==hashes(second/'operation-classes'),'trace_events_identical_excluding_temporary_fragment_id':normalized(H/'trace-first.tsv')==normalized(H/'trace.tsv')}
out['pass']=all(out.values());(H/'rebuild_verification.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2));assert out['pass']
