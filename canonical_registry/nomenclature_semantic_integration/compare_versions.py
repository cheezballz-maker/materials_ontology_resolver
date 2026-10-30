"""Compare public outputs only, using non-development independent controls."""
import base64,json,subprocess,sys,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path.insert(0,str(B))
from chemistry import describe
from identity_comparator import compare
old=B.parent/'opsin-master/opsin-cli/target/opsin-cli-3.0-SNAPSHOT-jar-with-dependencies.jar'
new=H/'opsin-core-2.9.0-jar-with-dependencies.jar'
names=['1H-pyrrole','3H-pyrrole','pyridin-2(1H)-one','quinolin-2(1H)-one','1-methyl-1H-pyrazole','1-methyl-1H-imidazole','3-(1H-imidazol-2-yl)-1H-pyrazole','2-(1H-pyrazol-3-yl)-1H-imidazole','anthrone','pyrazole','1H-pyrazole 1H-pyrazole','1H−pyrazole','methyl-1H-pyrazole','9H-pyrazole','1H-pyrazole - water (2:1)']
subprocess.run(['javac','-encoding','UTF-8','-cp',str(new),'-d',str(H),str(H/'VersionProbe.java')],check=True)
keys=['version','status','message','warnings','ambiguous','smiles','cml']
def run(jar):
 data=''.join(base64.b64encode(n.encode()).decode()+'\n' for n in names)
 p=subprocess.run(['java','-cp',str(H)+';'+str(jar),'VersionProbe'],input=data,text=True,capture_output=True,timeout=120,check=True)
 lines=p.stdout.splitlines();assert len(lines)==len(names),(len(lines),p.stderr)
 result=[]
 for line in lines:
  vals=line.split('\t');assert len(vals)==len(keys),line
  result.append({k:base64.b64decode(v).decode('utf8') for k,v in zip(keys,vals)})
 return result
a,b=run(old),run(new);rows=[]
for name,x,y in zip(names,a,b):
 c=None
 if x['smiles'] and y['smiles']:
  try:c=compare(describe(x['smiles']),describe(y['smiles']))['assessment']
  except ValueError:c='VALIDATION_ERROR'
 rows.append(dict(name=name,old=x,new=y,status_equal=x['status']==y['status'],message_equal=x['message']==y['message'],warning_equal=x['warnings']==y['warnings'],ambiguity_equal=x['ambiguous']==y['ambiguous'],smiles_equal=x['smiles']==y['smiles'],cml_equal=x['cml']==y['cml'],structure_comparison=c))
out={'purpose':'public-output comparison, not semantic-trace validation','count':len(rows),'cases':rows,'offline':True}
(H/'version_comparison.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'count':len(rows),'status_differences':sum(not x['status_equal'] for x in rows),'warning_differences':sum(not x['warning_equal'] for x in rows),'smiles_differences':sum(not x['smiles_equal'] for x in rows),'cml_differences':sum(not x['cml_equal'] for x in rows),'comparisons':{v:sum(x['structure_comparison']==v for x in rows) for v in set(x['structure_comparison'] for x in rows)}},indent=2))
