import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf8'))
first=Path(read(H/'build-first.json')['temp_build']);second=Path(read(H/'build.json')['temp_build'])
def hashes(p):return {x.relative_to(p).as_posix():hashlib.sha256(x.read_bytes()).hexdigest() for x in p.rglob('*.class')}
def norm(p):
 rows=[]
 for line in p.read_text(encoding='utf8').splitlines():
  fields=line.split('\t')
  if fields[0]=='E' and len(fields)>14:fields[14]='TEMPORARY_OBJECT_ID'
  rows.append(fields)
 return rows
r={'independent_compiled_classes_match':hashes(first/'substitution-classes')==hashes(second/'substitution-classes'),'trace_match_excluding_temporary_object_id':norm(H/'development-trace-first.tsv')==norm(H/'development_trace.tsv')}
r['pass']=all(r.values());(H/'rebuild.json').write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r,indent=2));assert r['pass']
