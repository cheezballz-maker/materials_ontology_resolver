"""Produce aggregate metrics after any flagged disagreements are reviewed."""
import collections,json,sqlite3
from pathlib import Path
from scipy.stats import beta
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
p=read(H/'preliminary_metrics.json');cases=read(H/'resolver_results.json');routes=read(H/'provider_route_audit.json');refs={r['cuma_index']:r for r in read(H/'reference_adjudication.json')}
def blocker(reason):
    r=reason.upper()
    if 'NO_QUALIFYING_CORROBORATION' in r:return 'no qualifying external corroborator'
    if 'SOURCE_INTERPRETATION' in r or 'SOURCE_PREFERRED' in r:return 'source interpretation incomplete'
    if 'STEREO' in r:return 'stereo mapping or specification unsupported'
    if any(x in r for x in ('COMPONENT','COUNTERION','HYDRATION','SOLVATION','SOLVENT')):return 'component or hydration semantics unsupported'
    if 'UNSUPPORTED_' in r:return 'scope or capability guard'
    if any(x in r for x in ('NO_VALIDATED_CANDIDATE','NO_CANDIDATE','PARSER','OPSIN')):return 'parser failure or no validated candidate'
    if 'CONFLICT' in r or 'CONTRADICTION' in r:return 'evidence or source contradiction'
    return 'other'
reviews=read(H/'case_reviews.json') if (H/'case_reviews.json').exists() else []
review_by={r['cuma_index']:r for r in reviews};needs=[x for x in cases if 'REQUIRES_REVIEW' in x['verdict']]
assert all(x['cuma_index'] in review_by for x in needs),'All flagged exact disagreements require case-specific evidence review'
correct=sum(x['verdict']=='CONFIRMED' for x in cases if x['resolver_status']=='EXACT');false=0;unassessable=sum(x['verdict']=='UNADJUDICABLE' for x in cases if x['resolver_status']=='EXACT')
for case in needs:
    r=review_by[case['cuma_index']];assert r['verdict'] in ('FALSE_POSITIVE','CONFIRMED','UNADJUDICABLE')
    if r['verdict']=='CONFIRMED':assert case['reference_status']=='EXACT_REFERENCE_AVAILABLE','Cannot relabel a frozen non-exact reference to match a prediction'
    correct+=r['verdict']=='CONFIRMED';false+=r['verdict']=='FALSE_POSITIVE';unassessable+=r['verdict']=='UNADJUDICABLE'
den=correct+false
ci=[float(beta.ppf(.025,correct,den-correct+1)) if correct else 0.,float(beta.ppf(.975,correct+1,den-correct)) if correct<den else 1.] if den else None
db=sqlite3.connect((H/'run/candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
rows={i:dict(evidence=json.loads(e),reason=d,status=s) for i,e,d,s in db.execute('select cuma_index,evidence_json,diagnostic,status from candidate')};db.close()
name_complete=[];qualifying=[];admissions=[]
for i,row in rows.items():
    ev=row['evidence'];interpretation=ev.get('name_interpretation',{}).get('status');pre=ev.get('preliminary_source_form',{}).get('status')
    if interpretation=='ESTABLISHED' and pre=='SUPPORTED':name_complete.append(i)
    decision=ev.get('decision',{});pr=decision.get('provider_routes',[])
    if any(x['state']=='CORROBORATES' for x in pr) and i in name_complete:qualifying.append(i)
    if row['status']=='EXACT':
        qualifying_rows=[a for a in decision.get('evidence_states',[]) if a.get('state')=='CORROBORATES' and any(q['state']=='CORROBORATES' and (q['provider'],q['route'],q['query'],q['query_origin'])==(a.get('provenance',{}).get('retrieved_via'),a.get('provenance',{}).get('query_type'),a.get('provenance',{}).get('query'),a.get('provenance',{}).get('query_origin')) for q in pr)]
        typed=bool(decision.get('form',{}).get('source_assertion',{}).get('explicit_structure'))
        assert typed or qualifying_rows,('NO_QUALIFYING_ROUTE',i)
        assert all(a.get('provenance',{}).get('query_origin')!='validated_hypothesis' for a in qualifying_rows),('CANDIDATE_KEY_ADMISSION',i)
        truncations=[]
        for a in qualifying_rows:
            prov=a.get('provenance',{})
            truncations.extend(dict(provider=q.get('provider'),query=q.get('retrieval_key'),diagnostic=q.get('diagnostic')) for q in ev.get('retrieval',{}).get('queries',[]) if q.get('search_truncated') and q.get('provider')==prov.get('retrieved_via') and q.get('retrieval_key',{}).get('value')==prov.get('query') and q.get('retrieval_key',{}).get('kind')==prov.get('query_type'))
        admissions.append(dict(cuma_index=i,name=ev.get('name'),typed_source=typed,source_interpretation=interpretation,source_form=pre,reason=row['reason'],qualifying_evidence=qualifying_rows,truncated_qualifying_queries=truncations))
abstain=collections.Counter()
for x in cases:
    if x['resolver_status']=='EXACT':continue
    if x['reference_class']=='REFERENCE_EXACT_IDENTITY':abstain['reference_identity_withheld']+=1
    elif x['reference_class'] in ('REFERENCE_OUT_OF_SCOPE','REFERENCE_UNRESOLVED','REFERENCE_CONFLICT_AMBIGUOUS'):abstain['consistent_with_nonexact_reference']+=1
    else:abstain['unassessable']+=1
ambiguous=[r for r in routes if r['state']=='PROVIDER_RECORD_AMBIGUOUS']
pair_reviews=read(H/'pair_reviews.json') if (H/'pair_reviews.json').exists() else []
pair_map={tuple(sorted(x['cuma_indices'])):x for x in pair_reviews}
for pair in p['merged_pairs']:
    if pair['verdict']=='GRAPH_DIFFERENCE_REQUIRES_REVIEW':
        review=pair_map.get(tuple(sorted(pair['cuma_indices'])));assert review,'Merged-pair graph difference requires independent review'
        assert review['verdict'] in ('CONFIRMED_FALSE_MERGE','CONFIRMED_SAME','UNADJUDICABLE')
        pair['verdict']=review['verdict']
pair_same=sum(x['verdict']=='CONFIRMED_SAME' for x in p['merged_pairs']);pair_false=sum(x['verdict']=='CONFIRMED_FALSE_MERGE' for x in p['merged_pairs'])
withheld=[dict(**x,blocker_category=blocker(x['reason'])) for x in cases if x['verdict']=='REFERENCE_IDENTITY_WITHHELD']
result=dict(sample_size=p['sample_size'],resolver_statuses=p['resolver_statuses'],reference_statuses=p['reference_statuses'],cross_tab=p['cross_tab'],automatic_exact_precision=dict(confirmed=correct,false=false,adjudicable=den,unadjudicable=unassessable,point=correct/den if den else None,clopper_pearson_95=ci),automatic_exact_recall=dict(correct=correct,reference_exact=p['reference_exact'],point=correct/p['reference_exact'] if p['reference_exact'] else None),abstentions=dict(abstain),provider_route_counts=p['provider_route_counts'],ambiguous_routes=ambiguous,alias_counts=p['alias_counts'],false_merge=dict(false=pair_false,assessable_pairs=pair_false+pair_same,unadjudicable_pairs=sum(x['verdict']=='UNADJUDICABLE' for x in p['merged_pairs'])),merged_pairs=p['merged_pairs'],withheld_reasons=p['withheld_reason_counts'],withheld_blockers=dict(collections.Counter(x['blocker_category'] for x in withheld)),scope_guard_reason_counts=p['scope_guard_reason_counts'],name_path=dict(complete_interpretations=len(name_complete),with_qualifying_route=len(qualifying),admitted=len(admissions),admitted_correct=correct,admitted_false=false,admitted_unadjudicable=unassessable,withheld_no_qualifying=sum(x['reason']=='NO_QUALIFYING_CORROBORATION' for i,x in rows.items() if i in name_complete)),typed_source_path=dict(source_count=0,exact=0,confirmed=0,incorrect=0,conflicts=0,abstentions=0,note='The selected CUMA source workbook has name and aliases, no typed structure column.'),admissions=admissions,case_reviews=reviews)
result['source_alias_conflicts']=p['source_alias_conflicts']
reference_exact_conflicts=[x for x in cases if x['resolver_status']=='CONFLICT' and x['reference_class']=='REFERENCE_EXACT_IDENTITY']
result['reference_exact_conflict_holds']=[dict(cuma_index=x['cuma_index'],name=x['name'],independently_confirmed_alias_mismatch=any(a.get('status') in ('NOT_EXACT','DIFFERENT') for a in refs[x['cuma_index']].get('alias_judgments',[]))) for x in reference_exact_conflicts]
result['reference_quality_flagged_admissions']=[dict(cuma_index=x['cuma_index'],name=x['name'],verdict=x['verdict'],note=x['reference_quality_note']) for x in cases if x['resolver_status']=='EXACT' and x.get('reference_quality_note')]
flagged_correct=sum(x['verdict']=='CONFIRMED' for x in cases if x['resolver_status']=='EXACT' and x.get('reference_quality_note'))
flagged_correct+=sum(review_by[x['cuma_index']]['verdict']=='CONFIRMED' for x in needs if x.get('reference_quality_note'))
flagged_false=sum(review_by[x['cuma_index']]['verdict']=='FALSE_POSITIVE' for x in needs if x.get('reference_quality_note'))
result['quality_sensitivity_precision']=dict(confirmed=correct-flagged_correct,adjudicable=den-flagged_correct-flagged_false)
quality_ids={x['cuma_index'] for x in read(H/'REFERENCE_QUALITY_NOTES.json')['case_notes']}
quality_ids.update(x['cuma_index'] for x in read(H/'BLIND_SOURCE_AMBIGUITY_AUDIT.json')['multiple_record_responses'] if x['different_graphs'])
flagged_reference_exact=sum(i in quality_ids and r['reference_status']=='EXACT_REFERENCE_AVAILABLE' for i,r in refs.items())
result['quality_sensitivity_recall']=dict(confirmed=correct-flagged_correct,reference_exact=p['reference_exact']-flagged_reference_exact)
(H/'evaluation_metrics.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
(H/'error_analysis.json').write_text(json.dumps(dict(reviews=reviews,withheld=withheld,scope_guard_reason_counts=p['scope_guard_reason_counts']),indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('resolver_statuses','automatic_exact_precision','automatic_exact_recall','abstentions','alias_counts','name_path')},indent=2))
