"""Compare frozen references to the completed run; never rewrites either."""
import collections,hashlib,itertools,json,sqlite3
from pathlib import Path
from rdkit import Chem,rdBase
from scipy.stats import beta
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert (H/'REFERENCE_FROZEN.json').exists() and read(H/'RUN_FINISHED.json')['returncode']==0
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
implementation=read(H.parent/'FRESH_BLINDED_EVALUATION_FREEZE.json')
assert rdBase.rdkitVersion==implementation['runtime']['rdkit'],'CHEMISTRY_RUNTIME_CHANGED'
for name,digest in implementation['implementation_hashes'].items():assert sha(H.parent/name)==digest,'BLINDED_EVALUATION_INVALIDATED_BY_CODE_CHANGE: '+name
for name,item in implementation['external_hashes'].items():assert sha(item['path'])==item['sha256'],'CONTRACT_CHANGED: '+name
for name,digest in read(H/'REFERENCE_FROZEN.json')['files'].items():assert sha(H/name)==digest,'FROZEN_REFERENCE_CHANGED: '+name
assert sha(H/'REFERENCE_QUALITY_NOTES.json')==read(H/'QUALITY_REVIEW_FROZEN.json')['notes_sha256']
assert sha(H/'BLIND_SOURCE_AMBIGUITY_AUDIT.json')==read(H/'BLIND_SOURCE_AUDIT_FROZEN.json')['notes_sha256']
assert sha(H/'fresh_sample.json')==read(H/'SAMPLE_FROZEN.json')['sample_sha256']
refs={x['cuma_index']:x for x in read(H/'reference_adjudication.json')};samples={x['cuma_index']:x for x in read(H/'fresh_sample.json')}
quality={x['cuma_index']:x['reason'] for x in read(H/'REFERENCE_QUALITY_NOTES.json')['case_notes']}
for x in read(H/'BLIND_SOURCE_AMBIGUITY_AUDIT.json')['multiple_record_responses']:
    if x['different_graphs']:
        i=x['cuma_index'];quality[i]=(quality.get(i,'')+' Reference name query returned multiple distinct candidate graphs.').strip()
def canon(s):
    m=Chem.MolFromSmiles(s or '')
    return Chem.MolToSmiles(m,isomericSmiles=True,canonical=True) if m is not None else None
def reference_class(ref):
    """Predeclared status mapping; lookup failures never become negative labels."""
    s=ref['reference_status'];u=str(ref.get('reference_uncertainty') or '').upper()
    if s=='EXACT_REFERENCE_AVAILABLE':return 'REFERENCE_EXACT_IDENTITY'
    if s=='OUT_OF_SCOPE_REFERENCE':return 'REFERENCE_OUT_OF_SCOPE'
    # In packet 3 this code means provider candidates disagree, which does not
    # establish that the original source claim itself is contradictory.
    if u=='SOURCE_CONFLICT':return 'UNADJUDICABLE'
    if u=='INHERENTLY_UNDERSPECIFIED' or s=='NOT_EXACT_REFERENCE':return 'REFERENCE_UNRESOLVED'
    return 'UNADJUDICABLE'
db=sqlite3.connect((H/'run/candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
results={i:dict(cuma_index=i,name=n,status=s,reason=d,evidence=json.loads(e)) for i,n,s,d,e in db.execute('select cuma_index,name,status,diagnostic,evidence_json from candidate')};db.close()
assert set(results)==set(refs)==set(samples)
provider=collections.Counter();routes=[];cases=[];cross=collections.Counter();alias=collections.Counter();blockers=collections.Counter();boundaries=collections.Counter();source_alias_conflicts=[]
for i,x in results.items():
    ref=refs[i];ev=x['evidence'];rstatus=ref['reference_status'];rclass=reference_class(ref);cross[(x['status'],rclass)]+=1
    predicted=(ev.get('decision',{}).get('structure') or {}).get('smiles');refsm=ref.get('reference_smiles');equal=canon(predicted)==canon(refsm) if predicted and refsm else None
    if x['status']=='EXACT':
        if rstatus=='EXACT_REFERENCE_AVAILABLE':verdict='CONFIRMED' if equal else 'GRAPH_DIFFERENCE_REQUIRES_REVIEW'
        elif rclass in ('REFERENCE_OUT_OF_SCOPE','REFERENCE_UNRESOLVED','REFERENCE_CONFLICT_AMBIGUOUS'):verdict='REFERENCE_DISAGREEMENT_REQUIRES_REVIEW'
        else:verdict='UNADJUDICABLE'
    elif rstatus=='EXACT_REFERENCE_AVAILABLE':verdict='REFERENCE_IDENTITY_WITHHELD';blockers[x['reason']]+=1
    else:verdict='ABSTENTION_REFERENCE_UNCERTAIN' if rclass=='UNADJUDICABLE' else 'ABSTENTION_CONSISTENT_WITH_REFERENCE'
    for q in ev.get('retrieval',{}).get('provider_states',[]):
        provider[(q['provider'],q['state'])]+=1;routes.append(dict(cuma_index=i,preferred_name=x['name'],resolver_status=x['status'],**q))
    for reason in x['reason'].split(';'):
        if reason.startswith('UNSUPPORTED_'):boundaries[reason]+=1
    expected_aliases={a.get('alias'):a.get('status') for a in ref.get('alias_judgments',[])}
    for a in ref.get('alias_judgments',[]):
        if rstatus=='EXACT_REFERENCE_AVAILABLE' and a.get('status') in ('NOT_EXACT','DIFFERENT'):
            source_alias_conflicts.append(dict(cuma_index=i,name=x['name'],alias=a.get('alias'),resolver_status=x['status'],evidence=a.get('evidence',[])))
    for a in ev.get('alias_decisions',[]):
        alias['source_occurrences']+=1
        if a.get('reason')=='SUBJECT_NOT_ADMITTED':alias['subject_not_admitted']+=1
        else:alias['subject_admitted_decisions']+=1
        if a.get('accepted'):
            alias['promoted']+=1;s=expected_aliases.get(a['alias'],'UNVERIFIED')
            # An alias attached to the wrong subject cannot be a confirmed
            # promotion even if it denotes the independent reference identity.
            verdict_alias='unverified'
            if s=='EXACT' and equal is True:verdict_alias='confirmed'
            elif s in ('NOT_EXACT','DIFFERENT') and equal is True:verdict_alias='incorrect'
            elif equal is False:verdict_alias='subject_mismatch_requires_review'
            alias[verdict_alias]+=1
    cases.append(dict(cuma_index=i,name=x['name'],resolver_status=x['status'],reason=x['reason'],reference_status=rstatus,reference_class=rclass,reference_uncertainty=ref.get('reference_uncertainty'),reference_quality_note=quality.get(i),reference_smiles=refsm,resolver_smiles=predicted,verdict=verdict))
reg=sqlite3.connect((H/'run/registry.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
groups=collections.defaultdict(list)
for i,sid in reg.execute("select cuma_index,substance_id from substance_reconciliation where resolution_status='EXACT'"):groups[sid].append(i)
reg.close();pairs=[]
for sid,ids in groups.items():
    for i,j in itertools.combinations(ids,2):
        a,b=refs[i],refs[j];s1,s2=a.get('reference_smiles'),b.get('reference_smiles')
        verdict='UNADJUDICABLE' if not s1 or not s2 else 'CONFIRMED_SAME' if canon(s1)==canon(s2) else 'GRAPH_DIFFERENCE_REQUIRES_REVIEW'
        pairs.append(dict(substance_id=sid,cuma_indices=[i,j],verdict=verdict))
exact=[c for c in cases if c['resolver_status']=='EXACT'];n_good=sum(c['verdict']=='CONFIRMED' for c in exact);n_diff=sum('REQUIRES_REVIEW' in c['verdict'] for c in exact)
ref_exact=sum(x['reference_status']=='EXACT_REFERENCE_AVAILABLE' for x in refs.values());reference_withheld=sum(c['verdict']=='REFERENCE_IDENTITY_WITHHELD' for c in cases)
preliminary=dict(sample_size=len(cases),resolver_statuses=dict(collections.Counter(c['resolver_status'] for c in cases)),reference_statuses=dict(collections.Counter(c['reference_status'] for c in cases)),cross_tab={f'{p}|{r}':n for (p,r),n in sorted(cross.items())},exact_confirmed=n_good,exact_review_required=n_diff,exact_unadjudicable=sum(c['verdict']=='UNADJUDICABLE' for c in exact),reference_exact=ref_exact,reference_identity_withheld=reference_withheld,alias_counts=dict(alias),source_alias_conflicts=source_alias_conflicts,provider_route_counts={f'{p}|{s}':n for (p,s),n in sorted(provider.items())},withheld_reason_counts=dict(blockers),scope_guard_reason_counts=dict(boundaries),merged_pairs=pairs,precision_not_final='Graph differences and reference conflicts require independent case review; do not count as correct or incorrect automatically.')
(H/'resolver_results.json').write_text(json.dumps(cases,indent=2,ensure_ascii=False),encoding='utf-8')
(H/'provider_route_audit.json').write_text(json.dumps(routes,indent=2,ensure_ascii=False),encoding='utf-8')
(H/'preliminary_metrics.json').write_text(json.dumps(preliminary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:preliminary[k] for k in ('resolver_statuses','reference_statuses','exact_confirmed','exact_review_required','exact_unadjudicable','reference_exact','reference_identity_withheld','alias_counts')},indent=2))
