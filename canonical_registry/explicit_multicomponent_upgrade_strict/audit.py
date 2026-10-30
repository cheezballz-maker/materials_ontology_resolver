"""Read-only evidence audit of the frozen development replay."""
import json,sqlite3,collections,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
old={r['cuma_index']:r for r in read(B/'stereo_locant_upgrade_complete/comparison.json')}
new={r['cuma_index']:r for r in read(H/'comparison.json')}
c=sqlite3.connect((H/'run/candidates.sqlite').as_uri()+'?mode=ro',uri=True)
summary=collections.Counter();rejections=[];improved=[];hydrates=[];missing=[]
for i,name,status,reason,raw in c.execute('select cuma_index,name,status,diagnostic,evidence_json from candidate order by cuma_index'):
    ev=json.loads(raw);p=ev.get('source_name_profile',{}).get('composition_constraints');q=ev.get('composition_comparison')
    if not p:missing.append(i);continue
    summary['profiles']+=1
    for k in ('components','component_counts','component_ratios','formal_charges','fixed_water_count'):
        summary[k+':'+p[k]['status']]+=1
    if p['fixed_water_count'].get('source_equivalents'):summary['hydrate_suffix_equivalents']+=1
    if q:
        summary['comparison:'+q['status']]+=1
        if status=='EXACT' and q['status']!='SUPPORTED':raise AssertionError((i,q))
        if q['status']=='CONFLICT':
            rejections.append(dict(cuma_index=i,name=name,before=old[i]['predicted_status'],after=status,reason=reason,composition=q))
        if q['status']!='SUPPORTED' and old[i]['predicted_status']==status:
            improved.append(dict(cuma_index=i,name=name,status=status,composition=q))
    else:summary['comparison:MISSING']+=1
    if p['fixed_water_count']['status']!='NOT_APPLICABLE':
        checks=[x for x in (q or {}).get('checked',[]) if x['kind']=='water']
        hydrates.append(dict(cuma_index=i,name=name,before=old[i]['predicted_status'],after=status,reason=reason,water=p['fixed_water_count'],comparison=q and q['status'],checks=checks))
        for x in checks:summary['water_correct' if x['expected']==x['observed'] else 'water_wrong']+=1
        if p['fixed_water_count']['status']=='UNSPECIFIED' and not p['fixed_water_count'].get('source_equivalents') and status!='EXACT':summary['generic_hydrate_abstentions']+=1
        if status=='CONFLICT':summary['hydrate_final_conflicts']+=1
newly=[dict(cuma_index=i,name=x['preferred_name'],before=old[i]['predicted_status'],after=x['predicted_status'],verdict=x['exact_verdict']) for i,x in new.items() if x['predicted_status']=='EXACT' and old[i]['predicted_status']!='EXACT']
f=read(H/'IMPLEMENTATION_FROZEN.json');baseline=read(B/'stereo_locant_upgrade_complete/IMPLEMENTATION_FROZEN.json')
common={k:v==baseline['runtime_hashes'].get(k) for k,v in f['runtime_hashes'].items() if k in baseline['runtime_hashes']}
result=dict(counts=dict(summary),missing_profiles=missing,rejected_candidates=rejections,diagnostic_only=improved,hydrates=hydrates,new_admissions=newly,baseline_runtime_equal=common)
(H/'audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('counts','missing_profiles','new_admissions','baseline_runtime_equal')},indent=2))
print('rejected_candidates',len(rejections),'diagnostic_only',len(improved),'hydrates',len(hydrates))
