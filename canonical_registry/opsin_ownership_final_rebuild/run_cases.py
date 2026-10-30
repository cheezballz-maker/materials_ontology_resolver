"""Run five fixed names; compare source builds and record selected parse traces."""
import base64,collections,hashlib,json,re,subprocess,xml.etree.ElementTree as ET
from pathlib import Path

H=Path(__file__).resolve().parent;B=H.parent;ROOT=B.parent
J=ROOT/'opsin-master/opsin-cli/target/opsin-cli-3.0-SNAPSHOT-jar-with-dependencies.jar'
identity=json.loads((H/'BUILD_IDENTITY.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(J)==identity['dependency_jar_sha256']
assert sha(H/'baseline_core.jar')==identity['baseline_jar_sha256']
assert sha(H/'diagnostic_core.jar')==identity['diagnostic_jar_sha256']
prior=json.loads((B/'opsin_fragment_feasibility/observations.json').read_text(encoding='utf-8'))
by_label={x['case']:x for x in prior['cases']}
triage=json.loads((B/'stereo_locant_upgrade_complete/stereo_analysis.json').read_text(encoding='utf-8'))
unresolved=[x for x in triage['details'] if x['before_mapping'].get('reason')=='LOCANT_NOT_UNIQUE' and x['after_mapping'].get('reason')=='GRAPH_MAPPING_AMBIGUOUS']
assert len(unresolved)==2
cases=[dict(label='simple control',name=by_label['unique control']['name'],origin='prior diagnostic'),
       dict(label='nested duplicate stereo fixture',name=by_label['nested duplicate potentially stereogenic']['name'],origin='OPSIN flavonoids fixture line 262')]
cases += [dict(label='remaining unresolved scope',name=x['name'],cuma_index=x['cuma_index'],prior_status=x['after_status'],prior_reason=x['reason'],origin='previous stereo analysis') for x in unresolved]
cases += [dict(label='unsupported relative control',name=by_label['unsupported relative stereo']['name'],origin='prior diagnostic')]
assert len(cases)<=6 and len({x['name'] for x in cases})==len(cases)
fields=('attempt','event','node_id','scope_id','descriptor_xml','scope_xml','fragment_id','fragment_xml','locant','atom_id','potential','unassigned','path','prior_assigned_atom_ids')

def run(name,mode):
    core={'baseline':H/'baseline_core.jar','diagnostic':H/'diagnostic_core.jar','installed':None}[mode]
    cp=[str(H/'runner_classes')]+([str(core)] if core else [])+[str(J)]
    p=subprocess.run(['java','-cp',';'.join(cp),'Runner',name],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45)
    if p.returncode:raise RuntimeError((mode,p.returncode,p.stderr))
    public={}
    for line in p.stdout.splitlines():
        a=line.split('\t',1)
        if len(a)!=2:continue
        k,v=a
        public[k]=base64.b64decode(v).decode('utf-8') if k in ('MESSAGE','WARNINGS','SMILES','CML') else v
    events=[];begins=[];success=[];other=[]
    for line in p.stderr.splitlines():
        row=line.split('\t')
        if row[0]=='OWNERSHIP_BEGIN':begins.append(int(row[1]))
        elif row[0]=='OWNERSHIP_SUCCESS':success.append(int(row[1]))
        elif row[0]=='OWNERSHIP_EVENT':
            values=[base64.b64decode(x).decode('utf-8') for x in row[1:]]
            if len(values)!=len(fields):raise ValueError('trace schema mismatch')
            d=dict(zip(fields,values));d['attempt']=int(d['attempt']);d['potential']=d['potential']=='true';d['unassigned']=d['unassigned']=='true';events.append(d)
        else:other.append(line)
    complete=(mode=='diagnostic' and public.get('STATUS')=='SUCCESS' and len(begins)==len(success)==1 and begins==success and all(e['attempt']==success[0] for e in events))
    if not complete:events=[]
    return dict(public=public,selected_parse_trace_complete=complete,trace_attempt=success[0] if complete else None,events=events,other_stderr=other)

def classify(trace):
    if not trace['selected_parse_trace_complete']:return []
    atoms={};cml=trace['public'].get('CML')
    if cml:
        root=ET.fromstring(cml);ns={'c':'http://www.xml-cml.org/schema'}
        for a in root.findall('.//c:atom',ns):
            atoms[a.get('id')]=dict(locants=[l.get('value') for l in a.findall('c:label',ns)],has_parity=a.find('c:atomParity',ns) is not None)
    groups=collections.defaultdict(list)
    for e in trace['events']:groups[e['node_id']].append(e)
    records=[]
    for node,evs in groups.items():
        descriptors=[x for x in evs if x['event']=='DESCRIPTOR'];selected=[x for x in evs if x['event']=='SELECT'];candidates=[x for x in evs if x['event']=='CANDIDATE']
        if len(descriptors)!=1 or len(selected)!=1:
            records.append(dict(node_id=node,classification='PROVENANCE_INCOMPLETE',reason='descriptor or selection missing'));continue
        d=descriptors[0];s=selected[0]
        potential_pairs=sorted({(x['fragment_id'],x['atom_id']) for x in candidates if x['potential'] and x['atom_id']})
        potential_ids=sorted({x['atom_id'] for x in candidates if x['potential'] and x['atom_id']})
        unassigned_ids=sorted({x['atom_id'] for x in candidates if x['potential'] and x['unassigned'] and x['atom_id']})
        prior_ids=re.findall(r'\d+',d['prior_assigned_atom_ids']);prior_competitors=sorted(set(prior_ids)&set(potential_ids))
        cml_id='a'+s['atom_id'];final_atom=atoms.get(cml_id);cml_ok=bool(final_atom and d['locant'] in final_atom['locants'] and final_atom['has_parity'])
        if not cml_ok or not s['atom_id'] or not candidates:classification='PROVENANCE_INCOMPLETE'
        elif s['path']=='FALLBACK' or len(potential_pairs)>1:classification='ORDERED_OR_FALLBACK_SELECTION'
        elif prior_competitors or len(potential_ids)!=1 or unassigned_ids!=potential_ids:classification='PROVENANCE_INCOMPLETE'
        elif potential_pairs==[(s['fragment_id'],s['atom_id'])]:classification='UNIQUELY_SCOPED'
        else:classification='PROVENANCE_INCOMPLETE'
        records.append(dict(node_id=node,scope_id=d['scope_id'],descriptor_xml=d['descriptor_xml'],scope_xml=d['scope_xml'],locant=d['locant'],
            candidates=candidates,all_scoped_potential_fragment_atom_pairs=potential_pairs,all_scoped_potential_atom_ids=potential_ids,unassigned_scoped_atom_ids=unassigned_ids,prior_assigned_atom_ids=prior_ids,prior_competitors=prior_competitors,
            selected_fragment_id=s['fragment_id'],selected_fragment_xml=s['fragment_xml'],selected_atom_id=s['atom_id'],assignment_path=s['path'],
            final_cml_id=cml_id,final_cml_atom=final_atom,final_cml_correspondence=cml_ok,classification=classification))
    return records

out=[]
for case in cases:
    baseline=run(case['name'],'baseline');diag=run(case['name'],'diagnostic');installed=run(case['name'],'installed')
    records=classify(diag)
    # A cloned or repeated processed descriptor has no proven original-token lineage.
    # Record this observation; do not assign processed nodes to source spans.
    locants=collections.Counter((x.get('locant'),re.search(r'value="([RS])"',x.get('descriptor_xml','')).group(1)) for x in records if re.search(r'value="([RS])"',x.get('descriptor_xml','')))
    raw_counts={f'{l}{v}':len(re.findall(r'\b'+re.escape(l+v)+r'\b',case['name'])) for l,v in locants}
    repeated=[f'{l}{v}' for (l,v),n in locants.items() if n>raw_counts[f'{l}{v}']]
    if repeated:
        for r in records:
            r['lineage_warning']='Processed descriptor count exceeds visible tokens; clone/token lineage not tracked.'
            r['scope_only_classification']=r['classification'];r['classification']='PROVENANCE_INCOMPLETE'
    item={**case,'baseline':baseline['public'],'diagnostic':diag['public'],'installed':installed['public'],
          'baseline_equals_diagnostic':baseline['public']==diag['public'],'baseline_equals_installed':baseline['public']==installed['public'],
          'selected_parse_trace_complete':diag['selected_parse_trace_complete'],'trace_attempt':diag['trace_attempt'],
          'events':diag['events'],'descriptor_records':records,'visible_descriptor_counts':raw_counts,'repeated_processed_descriptors':repeated,
          'diagnostic_other_stderr':diag['other_stderr']}
    out.append(item)
    print(case['label'],case.get('cuma_index',''),diag['public'].get('STATUS'),'trace',diag['selected_parse_trace_complete'],
          'base=diag',item['baseline_equals_diagnostic'],'base=installed',item['baseline_equals_installed'],
          'classifications',[r['classification'] for r in records],flush=True)
result=dict(build_identity=identity,source_snapshot_sha256=identity['source_manifest_sha256'],cases=out,distinct_names=len(out),maximum_names=6)
(H/'observations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
