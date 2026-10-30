import subprocess,json,base64,xml.etree.ElementTree as ET
from pathlib import Path
P=Path(__file__).resolve().parent
names=['1H-pyrazole','2H-pyrazole','1H-imidazole','1H-pyrrole','3H-pyrrole','pyrazole','pyrrole','triazine','pyridin-2(1H)-one','pyridin-2-ol','quinolin-2(1H)-one','1-methyl-1H-pyrazole','1-methyl-1H-imidazole','3-(1H-imidazol-2-yl)-1H-pyrazole','2-(1H-pyrazol-3-yl)-1H-imidazole','2,2\'-bipyridine','1H-pyrazole hydrochloride','1H-pyrazole - water (1:2)','1H-pyrazole - water (2:1)','1H-pyrazole 1H-pyrazole','9H-pyrazole','1H-pyrazole garbage','anthrone','1H−pyrazole','methyl-1H-pyrazole','3,4-dimethyl-1H-pyrazole','1H-pyrazole']
def dec(s):return base64.b64decode(s).decode() if s else ''
def run(mode):
 cp=[P/'runner-classes']+([] if mode=='released' else [P/(('diagnostic' if mode=='trace' else 'baseline')+'-classes'),P/'source/opsin-core/src/main/resources'])+[P/'opsin-core-2.9.0.jar']
 # diagnostic must precede runner helper (same bytes); Runner itself is identical.
 x=subprocess.run(['java','-Dprobe.trace='+str(mode=='trace').lower(),'-cp',':'.join(map(str,cp)),'uk.ac.cam.ch.wwmm.opsin.Runner',*names],capture_output=True,text=True,check=True)
 (P/f'{mode}.tsv').write_text(x.stdout);(P/f'{mode}.stderr').write_text(x.stderr)
 out=[]
 for line in x.stdout.splitlines():
  v=line.split('\t')
  if v[0]=='R':out.append(dict(name=dec(v[1]),status=v[2],message=dec(v[3]),smiles=dec(v[4]),cml=dec(v[5]),warnings=dec(v[6]),ambiguous=v[7]=='true',events=[]))
  elif v[0]=='P':out[-1].setdefault('parse_alternatives',[]).append(dict(attempt=int(v[1]),selected=v[2]=='true',xml=dec(v[3])))
  elif v[0]=='E':
   e=dict(start=int(v[1]),end=int(v[2]),source_token=dec(v[3]),kind=dec(v[4]),locant=dec(v[5]),owner=dec(v[6]),atom_id='a'+v[7],element=v[8],charge=int(v[9]),pre_spare_valency=v[10]=='true',same_final_object=v[11]=='true',clone_activity=v[12]=='true',selected_attempt=int(v[13]))
   cml=ET.fromstring(out[-1]['cml']);ns={'c':'http://www.xml-cml.org/schema'}; atoms={a.get('id'):a for a in cml.findall('.//c:atom',ns)}
   h=0
   for bond in cml.findall('.//c:bond',ns):
    pair=bond.get('atomRefs2').split()
    if e['atom_id'] in pair:
     other=pair[1] if pair[0]==e['atom_id'] else pair[0]
     h+=atoms[other].get('elementType')=='H'
   e['final_explicit_h_neighbors']=h
   e['cml_locant_matches']=any(a.get('value')==e['locant'] for a in atoms[e['atom_id']].findall('c:label',ns)) if e['atom_id'] in atoms else False
   e['span_verified']=e['start']>=0 and out[-1]['name'][e['start']:e['end']]==e['source_token']
   e['bounded_mapping']=e['span_verified'] and e['same_final_object'] and not e['clone_activity'] and e['atom_id'] in atoms and e['cml_locant_matches']
   out[-1]['events'].append(e)
 return out
baseline=run('baseline');trace=run('trace');released=run('released')
for b,t,r in zip(baseline,trace,released):
 t['release_equal']=all(r[k]==t[k] for k in ['name','status','message','smiles','cml','warnings','ambiguous'])
 t['baseline_equal']=all(b[k]==t[k] for k in ['name','status','message','smiles','cml','warnings','ambiguous'])
 t['mapping_only_status']='MAPPED_BOUNDED' if t['events'] and all(e['bounded_mapping'] for e in t['events']) else ('ABSTAIN_CLONE' if any(e['clone_activity'] for e in t['events']) else 'NO_COMPLETE_TRACE')
(P/'probe_results.json').write_text(json.dumps(trace,indent=2))
print(json.dumps([{k:r[k] for k in ['name','status','baseline_equal','mapping_only_status']}|{'events':[{k:e[k] for k in ['source_token','locant','owner','atom_id','final_explicit_h_neighbors','clone_activity']} for e in r['events']]} for r in trace],indent=2))
assert all(r['baseline_equal'] for r in trace)

assert all(r['release_equal'] for r in trace)
