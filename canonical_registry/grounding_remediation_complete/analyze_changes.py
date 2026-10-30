"""Compare frozen replay with its predecessor; report evidence, not causal certainty."""
import json,sqlite3,collections,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;OLD=B/'explicit_multicomponent_upgrade_release2'
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def candidates(path):
 c=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
 return {i:dict(name=n,status=s,reason=r,evidence=json.loads(e)) for i,n,s,r,e in c.execute('select cuma_index,name,status,diagnostic,evidence_json from candidate')}
a,b=candidates(OLD/'run/candidates.sqlite'),candidates(H/'run/candidates.sqlite')
rows=[];unchanged_reasons=[];pairs=collections.Counter()
for i in sorted(a):
 x,y=a[i],b[i];pairs[(x['status'],y['status'])]+=1
 if x['status']==y['status']:
  if x['reason']!=y['reason']:unchanged_reasons.append(dict(cuma_index=i,name=y['name'],status=y['status'],before=x['reason'],after=y['reason']))
  continue
 ev=y['evidence'];mapping=ev.get('source_name_profile',{}).get('stereo_locant_mapping') or {};cause='OTHER; inspect evidence'
 if y['reason']=='SOURCE_CONSTITUTION_CONFLICT':cause='GENERAL_PARSED_SOURCE_ALIAS_CONFLICT'
 elif any(z.get('reason')=='NAME_CASE_VARIANT_UNVERIFIED' for q in ev.get('retrieval',{}).get('queries',[]) for z in q.get('excluded_records',[])):cause='CASE_ONLY_PROVIDER_HOLD'
 elif 'SOURCE_STEREO_PARTIALLY_SPECIFIED' in y['reason'] or 'SOURCE_STEREO_UNSPECIFIED' in y['reason']:cause='CASE_SENSITIVE_OR_DL_SCOPE_HOLD'
 elif mapping.get('reason')=='LOCANT_SCOPE_UNRESOLVED':cause='DUPLICATE_LOCANT_OWNERSHIP_HOLD'
 elif 'HYDRATION_STOICHIOMETRY_UNKNOWN' in y['reason']:cause='HYDRATE_SEMANTICS_HOLD'
 elif y['reason']=='SOURCE_PREFERRED_INTERPRETATION_UNKNOWN':cause='SOURCE_NAME_UNSUPPORTED_AFTER_LEXICAL_REMOVAL'
 if x['status']=='EXACT':
  classification='PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL' if cause in ('CASE_SENSITIVE_OR_DL_SCOPE_HOLD','DUPLICATE_LOCANT_OWNERSHIP_HOLD','SOURCE_NAME_UNSUPPORTED_AFTER_LEXICAL_REMOVAL','CASE_ONLY_PROVIDER_HOLD') else 'OTHER'
 elif x['status']=='CONFLICT' and y['status']!='CONFLICT':classification='PRIOR_CONFLICT_REMOVED'
 else:classification='OTHER'
 rows.append(dict(cuma_index=i,name=y['name'],before=x['status'],after=y['status'],before_reason=x['reason'],after_reason=y['reason'],classification=classification,likely_cause=cause,source_conflicts=ev.get('source_form',{}).get('source_claim_conflicts',[])))
aa=load(OLD/'alias_comparison.json');bb=load(H/'alias_comparison.json')
key=lambda r:(r['cuma_index'],r['alias_position'],r['alias'])
old={key(r):r for r in aa};new={key(r):r for r in bb};removed=[old[x] for x in old.keys()-new.keys()];added=[new[x] for x in new.keys()-old.keys()]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=load(OLD/'SCORING_FROZEN.json');prior_integrity={x:sha(OLD/'run'/x)==v for x,v in manifest['prediction_hashes'].items()}
f=load(H/'IMPLEMENTATION_FROZEN.json');base=load(OLD/'IMPLEMENTATION_FROZEN.json')
integrity={'previous_databases_unchanged':prior_integrity,'schema_unchanged':f['runtime_hashes']['schema.sql']==base['runtime_hashes']['schema.sql'],'ontology_unchanged':f['ontology_sha256']==base['ontology_sha256'],'framework_unchanged':f['framework_sha256']==base['framework_sha256']}
result=dict(transitions={f'{k[0]}->{k[1]}':v for k,v in pairs.items()},changed=rows,unchanged_reason_changes=unchanged_reasons,alias_removed=removed,alias_added=added,integrity=integrity)
(H/'change_analysis.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'transitions':result['transitions'],'changed':len(rows),'unchanged_reason_changes':len(unchanged_reasons),'alias_removed':len(removed),'alias_added':len(added),'integrity':integrity},indent=2))
