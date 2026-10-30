import base64,json
from pathlib import Path
from rdkit import Chem
from rdkit.Chem import inchi
H=Path(__file__).resolve().parent
decode=lambda s:base64.b64decode(s).decode('utf8') if s else ''
def read(n):
 result=[]
 for line in (H/n).read_text(encoding='utf8').splitlines():
  p=line.split('\t')
  if p[0]=='R':result.append(dict(name=decode(p[1]),status=p[2],message=decode(p[3]),smiles=decode(p[4]),cml=decode(p[5]),warnings=decode(p[6]),ambiguous=p[7]))
 return result
a,b=read('development_baseline.tsv'),read('development_trace.tsv');assert len(a)==len(b)
out=[]
for x,y in zip(a,b):
 row={'name':x['name'],'public_equal':x==y,'inchi_status':'NOT_APPLICABLE','standard_inchi_equal':None,'fixedh_inchi_equal':None}
 if x['smiles'] and y['smiles']:
  try:
   m,n=Chem.MolFromSmiles(x['smiles']),Chem.MolFromSmiles(y['smiles'])
   if m is None or n is None:raise ValueError('invalid graph')
   row.update(inchi_status='COMPARED',standard_inchi_equal=inchi.MolToInchi(m)==inchi.MolToInchi(n),fixedh_inchi_equal=inchi.MolToInchi(m,options='/FixedH')==inchi.MolToInchi(n,options='/FixedH'))
  except Exception:row['inchi_status']='UNAVAILABLE'
 out.append(row)
summary={'count':len(out),'all_public_equal':all(x['public_equal'] for x in out),'inchi_compared':sum(x['inchi_status']=='COMPARED' for x in out),'inchi_unavailable':sum(x['inchi_status']=='UNAVAILABLE' for x in out),'inchi_differences':sum(x['standard_inchi_equal'] is False or x['fixedh_inchi_equal'] is False for x in out),'source':'RDKit computed from output SMILES; pinned core API does not provide InChI','cases':out}
(H/'public_output_equivalence.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({k:v for k,v in summary.items() if k!='cases'},indent=2));assert summary['all_public_equal'] and summary['inchi_differences']==0
