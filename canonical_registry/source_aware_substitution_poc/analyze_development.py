"""Inspect development-only high-level source substitution events."""
import base64,json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path.insert(0,str(B/'nomenclature_semantic_integration'))
from graph_correspondence import correspond
d=lambda s:base64.b64decode(s).decode('utf8') if s else ''
def parse(path):
 out=[];current=None
 for line in path.read_text(encoding='utf8').splitlines():
  p=line.split('\t')
  if p[0]=='R':current=dict(name=d(p[1]),status=p[2],message=d(p[3]),smiles=d(p[4]),cml=d(p[5]),warnings=d(p[6]),ambiguous=p[7]=='true',events=[],h_claims=[],parse_alternatives=[]);out.append(current)
  elif p[0]=='P':current['parse_alternatives'].append(dict(attempt=int(p[1]),selected=p[2]=='true'))
  elif p[0]=='S':
   nodes=[]
   for token in d(p[7]).split(';'):
    if token:
     a,b,t=token.split(':',2);nodes.append(dict(start=int(a),end=int(b),text=t))
   current['events'].append(dict(locant_span=[int(p[1]),int(p[2])],locant_token=d(p[3]),group_span=[int(p[4]),int(p[5])],group_token=d(p[6]),source_nodes=nodes,substituent_parse_xml=d(p[8]),group_name=d(p[9]),locant=d(p[10]),parent_atom='a'+p[11],attachment_atom='a'+p[12],bond_observed=p[13]=='true',same_h_atom=p[14]=='true',parent_atom_in_final=p[15]=='true',attachment_atom_in_final=p[16]=='true',clone_activity=p[17]=='true',mutation_cursor=int(p[18]),parse_attempt=int(p[19])))
  elif p[0]=='E':current['h_claims'].append(dict(start=int(p[1]),end=int(p[2]),text=d(p[3]),kind=d(p[4]),locant=d(p[5]),fragment=d(p[6]),atom='a'+p[7],same_result=p[11]=='true',clone_activity=p[12]=='true',parent_operation_cursor=int(p[15])))
 return out
t=parse(H/'development_trace.tsv');b=parse(H/'development_baseline.tsv');assert len(t)==len(b)
V=B/'nomenclature_semantic_integration';old=B.parent/'opsin-master/opsin-cli/target/opsin-cli-3.0-SNAPSHOT-jar-with-dependencies.jar'
payload=''.join(base64.b64encode(x['name'].encode('utf8')).decode('ascii')+'\n' for x in t)
p=subprocess.run(['java','-cp',str(V)+__import__('os').pathsep+str(old),'VersionProbe'],input=payload,text=True,encoding='utf8',capture_output=True,check=True,timeout=90)
records=p.stdout.splitlines();assert len(records)==len(t)
candidate={x['name']:{'status':d(parts[1]),'smiles':d(parts[5])} for x,line in zip(t,records) for parts in [line.split('\t')]}
fields=('name','status','message','smiles','cml','warnings','ambiguous')
for x,y in zip(t,b):
 x['public_equal']=all(x[k]==y[k] for k in fields)
 x['single_selected_parse']=len(x['parse_alternatives'])==1 and x['parse_alternatives'][0]['selected']
 for e in x['events']:
  n=x['name'];a,z=e['locant_span'];e['locant_span_verified']=a>=0 and n[a:z]==e['locant_token']
  a,z=e['group_span'];e['group_span_verified']=a>=0 and n[a:z]==e['group_token']
  e['all_source_nodes_verified']=all(i['start']>=0 and n[i['start']:i['end']]==i['text'] for i in e['source_nodes'])
  # Evidence only: capture a contiguous stem + yl span for the narrowly
  # observed parsed grammar, not a rule that admits its molecular identity.
  parsed=ET.fromstring(e['substituent_parse_xml']);groups=parsed.findall('group');suffixes=parsed.findall('suffix')
  y=[v for v in e['source_nodes'] if v['start']==z and v['text']=='yl']
  complete=(len(groups)==1 and groups[0].get('subType')=='alkaneStem' and len(suffixes)==1 and suffixes[0].get('value')=='yl' and len(y)==1 and e['group_span_verified'] and e['all_source_nodes_verified'])
  e['substituent_source_span']=[a,y[0]['end']] if complete else None
  e['substituent_source_text']=n[a:y[0]['end']] if complete else None
  e['substituent_span_status']='OBSERVED_CONTIGUOUS_PARSER_TOKENS' if complete else 'UNKNOWN'
  e['graph_bond_verified']=False
  if x['cml']:
   ns={'c':'http://www.xml-cml.org/schema'};root=ET.fromstring(x['cml'])
   e['graph_bond_verified']=any(set(bond.get('atomRefs2').split())=={e['parent_atom'],e['attachment_atom']} for bond in root.findall('.//c:bond',ns))
  e['source_provenance']='LOCANT_AND_GROUP_TOKEN_ONLY' if e['locant_span_verified'] and e['group_span_verified'] else 'UNKNOWN'
  matching=[h for h in x['h_claims'] if h['kind']=='indicatedHydrogen' and h['atom']==e['parent_atom']]
  e['parent_before_substitution']=bool(len(matching)==1 and matching[0]['parent_operation_cursor']<e['mutation_cursor'])
 old_candidate=candidate[x['name']];x['resolver_snapshot_candidate']=old_candidate
 x['candidate_correspondence']=correspond(x['cml'],old_candidate['smiles']) if x['cml'] and old_candidate['smiles'] else {'status':'UNKNOWN','reason':'NO_SUCCESSFUL_GRAPH','mappings':[]}
 x['operation_state']='UNKNOWN';x['dimension_state']='UNKNOWN';x['reason']='FULL_SUBSTITUENT_LINEAGE_AND_MOBILE_H_COMPLETENESS_NOT_PROVEN'
assert all(x['public_equal'] for x in t)
(H/'development_observations.json').write_text(json.dumps(t,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps([{'name':x['name'],'status':x['status'],'events':x['events'],'h_claims':x['h_claims'],'candidate_correspondence':x['candidate_correspondence']['status']} for x in t],indent=2,ensure_ascii=True))
