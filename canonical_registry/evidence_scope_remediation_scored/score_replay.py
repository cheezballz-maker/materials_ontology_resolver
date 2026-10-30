"""Score the development replay against frozen, unchanged reference judgments."""
import hashlib,json,sqlite3,sys
from collections import Counter,defaultdict
from datetime import datetime,timezone
from itertools import combinations
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;P=B/'second_form_aware_holdout';sys.path.insert(0,str(B))
from form_aware_holdout.score_holdout import metrics,same,nonadmissible

read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
save=lambda p,x:Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
freeze=read(H/'IMPLEMENTATION_FROZEN.json');assert read(H/'RUN_FINISHED.json')['returncode']==0
for name,value in freeze['runtime_hashes'].items():assert sha(B/name)==value,name
for name,value in freeze['test_hashes'].items():assert sha(B/name)==value,name
assert sha(P/'ADJUDICATION_FROZEN.json')==freeze['frozen_reference_manifest_sha256']
assert sha(P/'METRICS_FROZEN.json')==freeze['frozen_metrics_manifest_sha256']
for name,value in freeze['baseline_prediction_hashes'].items():assert sha(P/'predictions'/name)==value,name
for p,value in read(P/'ADJUDICATION_FROZEN.json')['files'].items():assert sha(P/p)==value,p
for kind in ('ontology','framework'):assert sha(freeze[kind+'_path'])==freeze[kind+'_sha256']
assert not (H/'SCORING_FROZEN.json').exists()
refs={};source={}
for n in (1,2,3):
    refs.update({r['cuma_index']:r for r in read(P/f'packet_{n}/reference.json')})
    source.update({r['cuma_index']:r for r in read(P/f'packet_{n}/records.json')})
before={r['cuma_index']:r for r in read(B/'grounding_remediation_final_scored/comparison.json')};rows=[];aliases=[]
c=sqlite3.connect((H/'run/candidates.sqlite').as_uri()+'?mode=ro',uri=True)
r=sqlite3.connect((H/'run/registry.sqlite').as_uri()+'?mode=ro',uri=True)
for i,name,raw_alias,status,reason,raw in c.execute('SELECT * FROM candidate ORDER BY cuma_index'):
    ref=refs[i];original=source[i];ev=json.loads(raw);assert name==original['preferred_name'] and json.loads(raw_alias)==original['aliases']
    sid,rs,rr=r.execute('SELECT substance_id,resolution_status,reason FROM substance_reconciliation WHERE cuma_index=?',(i,)).fetchone();assert (status,reason)==(rs,rr)
    structs=[x[0] for x in r.execute("SELECT structure_value FROM substance_structure WHERE substance_id=? AND structure_type='SMILES'",(sid,))]
    verdict=av=None
    if status=='EXACT':
        assert structs and ev.get('source_form',{}).get('status')=='SUPPORTED'
        verdict=('CORRECT' if all(same(s,ref['expected_smiles']) for s in structs) else 'INCORRECT') if ref['expected_status']=='EXACT' else 'INCORRECT' if nonadmissible(ref) else 'UNVERIFIED'
    else:av='EXCESSIVE' if ref['expected_status']=='EXACT' else 'CORRECT' if nonadmissible(ref) else 'UNVERIFIED'
    item=dict(cuma_index=i,preferred_name=name,expected_status=ref['expected_status'],expected_smiles=ref.get('expected_smiles'),expected_inchikey=ref.get('expected_inchikey'),predicted_status=status,predicted_smiles=structs,substance_id=sid,exact_verdict=verdict,abstention_verdict=av,reference_nonadmissible=nonadmissible(ref),resolver_reason=reason,reference_reason=ref['reason'],source_form=ev.get('source_form',{}),name_interpretation=ev.get('name_interpretation',{}),reference_categories=ref['form_categories'])
    rows.append(item)
    positions=defaultdict(list);seen=Counter()
    for j,a in enumerate(original['aliases']):positions[a].append(j)
    for a in ev.get('alias_decisions',[]):
        j=positions[a['alias']][seen[a['alias']]];seen[a['alias']]+=1
        if not a.get('accepted'):continue
        ar=ref['alias_judgments'][j];v='UNVERIFIED'
        if verdict=='CORRECT' and ar['judgment'] in ('SAME','DIFFERENT'):v='CORRECT' if ar['judgment']=='SAME' else 'INCORRECT'
        elif verdict=='INCORRECT' and ref['expected_status']=='EXACT' and ar['judgment']=='SAME':v='INCORRECT'
        aliases.append(dict(cuma_index=i,alias_position=j,alias=a['alias'],reference_judgment=ar['judgment'],verdict=v))
assert len(rows)==400
after={x['cuma_index']:x for x in rows};m=metrics(rows,aliases);before_m=read(B/'grounding_remediation_final_scored/metrics.json')['after']
changes=[];lost=[];new=[];gate_abstentions=[]
for i in sorted(after):
    b,a=before[i],after[i]
    old_ok=b['exact_verdict']=='CORRECT';new_ok=a['exact_verdict']=='CORRECT'
    same_graph=old_ok and new_ok and all(same(x,y) for x in b['predicted_smiles'] for y in a['predicted_smiles'])
    if old_ok and not same_graph:lost.append(dict(cuma_index=i,preferred_name=a['preferred_name'],after_status=a['predicted_status'],reason=a['resolver_reason'],after_verdict=a['exact_verdict']))
    if not old_ok and new_ok:new.append(i)
    if b['predicted_status']=='EXACT' and a['predicted_status']!='EXACT' and 'SOURCE_' in a['resolver_reason']:gate_abstentions.append(i)
    if b['predicted_status']!=a['predicted_status'] or b['exact_verdict']!=a['exact_verdict']:
        changes.append(dict(cuma_index=i,preferred_name=a['preferred_name'],expected_status=a['expected_status'],before_status=b['predicted_status'],before_verdict=b['exact_verdict'],after_status=a['predicted_status'],after_verdict=a['exact_verdict'],reason=a['resolver_reason']))
cohort=[]
pairs=[];groups=defaultdict(list)
for x in rows:
    if x['predicted_status']=='EXACT':groups[x['substance_id']].append(x)
for sid,g in groups.items():
    for a,b in combinations(g,2):
        assessable=a['expected_status']==b['expected_status']=='EXACT';equivalent=same(a['expected_smiles'],b['expected_smiles']) if assessable else None
        pairs.append(dict(substance_id=sid,a=a['cuma_index'],b=b['cuma_index'],assessable=assessable,equivalent=equivalent))
oldpairs=read(B/'grounding_remediation_final_scored/exact_cluster_transitions.json');clusters=[]
for p in oldpairs:
    a,b=after[p['a']],after[p['b']];both=a['predicted_status']==b['predicted_status']=='EXACT'
    outcome='CORRECT_EXACT_CLUSTER' if both and a['substance_id']==b['substance_id'] else 'BOTH_ADMITTED_DISTINCT' if both else 'ONE_WITHHELD' if (a['predicted_status']=='EXACT')!=(b['predicted_status']=='EXACT') else 'BOTH_WITHHELD'
    clusters.append(dict(a=p['a'],b=p['b'],before=p['after'],after=outcome))
four=[dict(cuma_index=i,preferred_name=after[i]['preferred_name'],expected_status=after[i]['expected_status'],before_status=before[i]['predicted_status'],before_verdict=before[i]['exact_verdict'],after_status=after[i]['predicted_status'],after_verdict=after[i]['exact_verdict'],reason=after[i]['resolver_reason']) for i in [5684,5997,23839,30142]]
summary=dict(before=before_m,after=m,previously_correct_lost=len(lost),previously_correct_retained=sum(x['exact_verdict']=='CORRECT' for x in rows)-len(new),new_confirmed_correct=len(new),source_gate_abstentions_from_previous_exact=len(gate_abstentions),source_gate_abstention_indices=gate_abstentions,prior_false_positive_cases=four,name_interpretation_counts=dict(Counter(x['name_interpretation'].get('status','MISSING') for x in rows)),coassigned_pairs=pairs,exact_cluster_transitions=clusters,offline_not_queried=sum(q.get('status')=='NOT_QUERIED' for _,raw in c.execute('SELECT cuma_index,evidence_json FROM candidate') for q in json.loads(raw).get('retrieval',{}).get('queries',[])))
outputs={'metrics.json':summary,'comparison.json':rows,'alias_comparison.json':aliases,'changes.json':changes,'previously_correct_lost.json':lost,'exact_cluster_transitions.json':clusters}
for name,data in outputs.items():save(H/name,data)
c.close();r.close()
save(H/'SCORING_FROZEN.json',dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),implementation_sha256=sha(H/'IMPLEMENTATION_FROZEN.json'),reference_manifest_sha256=sha(P/'ADJUDICATION_FROZEN.json'),output_hashes={name:sha(H/name) for name in outputs},prediction_hashes={name:sha(H/'run'/name) for name in ('registry.sqlite','candidates.sqlite')},scoring_script_sha256=sha(__file__)))
print(json.dumps(summary,ensure_ascii=False,indent=2))
