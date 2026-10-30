"""Turn local trace output into evidence; no admission-changing conclusions."""
import base64,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path.insert(0,str(B/'nomenclature_semantic_integration'))
from graph_correspondence import correspond
decode=lambda s:base64.b64decode(s).decode('utf8') if s else ''
read=lambda p:json.loads(p.read_text(encoding='utf8'))
out=[];current=None
for line in (H/'trace.tsv').read_text(encoding='utf8').splitlines():
 p=line.split('\t')
 if p[0]=='R':current={'name':decode(p[1]),'opsin_status':p[2],'smiles':decode(p[4]),'cml':decode(p[5]),'claims':[],'mutations':[]};out.append(current)
 elif p[0]=='O':
  current['mutations'].append(dict(order=int(p[1]),event=p[2],atom_a='a'+p[3],atom_b='a'+p[4],pre_atom_a=decode(p[5]),post_atom_a=decode(p[6]),pre_atom_b=decode(p[7]),post_atom_b=decode(p[8]),source_provenance='NOT_CAPTURED'))
 elif p[0]=='E':
  current['claims'].append(dict(source_span=[int(p[1]),int(p[2])],source_text=decode(p[3]),semantic_type=decode(p[4]),locant=decode(p[5]),fragment=decode(p[6]),atom='a'+p[7],same_result_object=p[11]=='true',clone_activity=p[12]=='true',parent_operation_cursor=int(p[15]),parent_state=decode(p[16])))
versions=read(B/'nomenclature_semantic_integration/version_comparison.json');old={x['name']:x['old']['smiles'] for x in versions['cases'] if x['old']['smiles']}
graphs=[];semantics=[]
for c in out:
 ns={'c':'http://www.xml-cml.org/schema'};root=ET.fromstring(c['cml']) if c['cml'] else None
 atoms={a.get('id'):a for a in root.findall('.//c:atom',ns)} if root is not None else {}
 for claim in c['claims']:
  claim['operations']=[dict(m,relative_to_parent='AFTER' if m['order']>=claim['parent_operation_cursor'] else 'BEFORE') for m in c['mutations'] if claim['atom'] in (m['atom_a'],m['atom_b'])]
  bonds=[]
  if root is not None:
   for bond in root.findall('.//c:bond',ns):
    pair=bond.get('atomRefs2').split()
    if claim['atom'] in pair:
     other=pair[1] if pair[0]==claim['atom'] else pair[0];bonds.append({'other_atom':other,'element':atoms[other].get('elementType'),'order':bond.get('order')})
  atom=atoms.get(claim['atom']);claim['final_opsin_state']={'element':atom.get('elementType'),'formal_charge':atom.get('formalCharge','0'),'isotope':atom.get('isotopeNumber'),'hydrogen_neighbors':sum(x['element']=='H' for x in bonds),'bonds':bonds} if atom is not None else None
  claim['mobile_h_completeness']='UNKNOWN';claim['constraint_state']='UNKNOWN'
 c['operation_lineage_complete']=False;c['operation_source_provenance']='NOT_CAPTURED';c['constraint_state']='UNKNOWN';c['constraint_reason']='OPERATION_SOURCE_AND_COVERAGE_INCOMPLETE'
 if c['name'] in old and c['cml']:
  g=correspond(c['cml'],old[c['name']]);graphs.append({'name':c['name'],'mapping':g,'candidate':'3.0-SNAPSHOT public result','semantic_conclusion':'UNKNOWN'})
 semantics.append({'name':c['name'],'constraint':'UNKNOWN','reason':'OPERATION_SOURCE_AND_COVERAGE_INCOMPLETE','contradiction_demonstrated':False})
assert len(out)==27
for n,x in [('operation_lineage_controls.json',{'cases':out,'count':len(out),'note':'Raw operations are observations; operation source spans and complete coverage are not established.'}),('graph_correspondence_controls.json',{'cases':graphs,'count':len(graphs),'note':'Non-stereo bounded isomorphism, not proof of source semantics.'}),('semantic_constraint_controls.json',{'cases':semantics,'supported':0,'different':0,'unknown':len(semantics),'known_limitation':'No sound contradictory source constraint is yet implemented.'})]:
 (H/n).write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'controls':len(out),'with_observed_mutations':sum(bool(c['mutations']) for c in out),'mapped_controls':len(graphs),'unknown_semantics':len(semantics)},indent=2))
