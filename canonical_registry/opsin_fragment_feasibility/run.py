"""Run six preselected names with isolated diagnostic and unmodified OPSIN."""
from pathlib import Path
import base64,hashlib,json,subprocess,xml.etree.ElementTree as ET,re
H=Path(__file__).resolve().parent;B=H.parent.parent;J=B/'opsin-master/opsin-cli/target/opsin-cli-3.0-SNAPSHOT-jar-with-dependencies.jar'
ns={'c':'http://www.xml-cml.org/schema'}
fixture=(B/'opsin-master/opsin-inchi/src/test/resources/uk/ac/cam/ch/wwmm/opsin/flavonoids.txt').read_text(encoding='utf-8').splitlines()[261].split('\t')[0]
cases=[
 ('unique control','(2R,3S)-2-bromo-3-chloropentane','project test_systematic_notation.py'),
 ('bridgehead control','(3aR,4S,5R,6aS)-4-(tert-Butyldimethylsilyloxy)methyl-5-hydroxy-hexahydro-2H-cyclopenta[b]furan-2-one','project test_stereo_propagation.py'),
 ('duplicate locant one eligible','(2S)-amino[2-(trifluoromethyl)phenyl]ethanoic acid','project prior replay CUMA 23002'),
 ('nested duplicate potentially stereogenic',fixture,'OPSIN flavonoids.txt line 262'),
 ('nested multicomponent previous unresolved','Succinic acid - (2S)-1-(isopropylamino)-3-[4-(2-methoxyethyl)phenoxy]-2-propanol (1:2)','project prior replay CUMA 41891'),
 ('unsupported relative stereo','1-N-BOC-1,2-TRANS-CYCLOHEXYLDIAMINE','project prior replay CUMA 5997/23839')]
assert len(cases)<=8

def java(name,patched):
 cp=str(H/('classes' if patched else 'baseline_classes'))+';'+str(J)
 p=subprocess.run(['java','-cp',cp,'InspectOpsin',name],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
 out={}
 for line in p.stdout.splitlines():
  fields=line.split('\t',1)
  if len(fields)==2:
   k,v=fields;out[k]=base64.b64decode(v).decode() if k in ('WARNING','SMILES','CML') else v
 events=[]
 for line in p.stderr.splitlines():
  if line.startswith('TRACE_STEREO '):events.append({'kind':'STEREO','value':base64.b64decode(line.split(' ',1)[1]).decode('utf-8')})
  elif line.startswith('TRACE_PARSE_'):events.append({'kind':line})
 return dict(returncode=p.returncode,stdout=out,events=events,other_stderr=[x for x in p.stderr.splitlines() if not x.startswith('TRACE_')])
results=[]
for label,name,origin in cases:
 patched=java(name,True);baseline=java(name,False)
 assert patched['returncode']==baseline['returncode']==0,(label,patched,baseline)
 actual=patched['stdout'];other=baseline['stdout'];match=actual==other
 cml=actual.get('CML',''); atoms={}
 if cml:
  root=ET.fromstring(cml)
  for a in root.findall('.//c:atom',ns):
   atoms[a.get('id')]=dict(element=a.get('elementType'),locants=[x.get('value') for x in a.findall('c:label',ns)],has_parity=a.find('c:atomParity',ns) is not None)
 for event in patched['events']:
  if event['kind']=='STEREO':
   m=re.search(r'\|selectedAtom=(\d+)',event['value'])
   if m:event['final_cml_atom_id']='a'+m.group(1);event['final_cml_atom']=atoms.get(event['final_cml_atom_id'])
 results.append(dict(case=label,name=name,origin=origin,patched=patched,baseline=other,identical_public_output=match,cml_atoms=atoms))
 print(label,actual.get('STATUS'),'equal_public',match,'trace_events',sum(x['kind']=='STEREO' for x in patched['events']),flush=True)
summary=dict(jar_sha256=hashlib.sha256(J.read_bytes()).hexdigest(),cases=results,maximum_names=8,no_external_queries=True)
(H/'observations.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
