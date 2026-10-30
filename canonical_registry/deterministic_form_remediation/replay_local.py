"""Replay only local checks against saved source claims; no providers or OPSIN."""
import collections,json,sqlite3,sys
from pathlib import Path
from scipy.stats import beta
H=Path(__file__).resolve().parent;B=H.parent;F=B/'fresh_blinded_evaluation';sys.path.insert(0,str(B))
from source_form import assess
from form_characterizer import interpret
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
old=read(B/'deterministic_value_analysis/deterministic_interpretation_cases.json');samples={x['cuma_index']:x for x in read(F/'fresh_sample.json')}
assert len(old)==224
db=sqlite3.connect((F/'run/candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
evs={i:json.loads(raw) for i,raw in db.execute('select cuma_index,evidence_json from candidate')};db.close()
results=[]
def blocker(reasons,source):
    r=';'.join(reasons)
    if 'PROTONATION' in r or 'CHARGE' in r:return 'charge/protonation'
    if source['status']=='CONFLICT':return 'alias conflict'
    if 'TAUTOMER' in r:return 'tautomer specificity'
    if 'STEREO' in r:return 'stereochemistry'
    if 'STOICHIOMETRY' in r:return 'stoichiometry'
    if any(x in r for x in ('COMPONENT','HYDRATION','SOLVENT')):return 'components'
    return 'other'
for x in old:
    i=x['cuma_index'];ev=evs[i];claims=ev['claims'];primary=claims[0];candidate=primary['structure'];aliases=samples[i]['aliases']
    assert len(claims[1:])==len(aliases),(i,len(claims)-1,len(aliases))
    pairs=list(zip(aliases,claims[1:]));assert all(a==claim.get('original') for a,claim in pairs),i
    intent=(ev['decision'].get('form') or {}).get('source_assertion') or {};profile=ev['source_name_profile']
    form=interpret(candidate,x['preferred_name'],intent,profile)
    source=assess(x['preferred_name'],primary,pairs,candidate,intent,None,profile)
    reasons=list(source['reason_codes'])
    if ev['name_interpretation']['status']!='ESTABLISHED':reasons.append('SOURCE_INTERPRETATION_INCOMPLETE')
    comp=ev.get('composition_comparison',{}).get('status')
    if comp=='UNRESOLVED':reasons.append('MULTICOMPONENT_SOURCE_INCOMPLETE')
    reasons.extend(v for v in form['reason_codes'] if v not in reasons)
    if source['status']!='SUPPORTED' and not reasons:reasons.append('SOURCE_FORM_UNRESOLVED')
    official=ev.get('official_inchi',{});official_ok=bool(official.get('agrees') and official.get('status') in ('SUCCESS','WARNING'))
    if not official_ok:reasons.append('OFFICIAL_INCHI_NOT_CONFIRMED')
    eligible=not reasons and source['status']=='SUPPORTED'
    v=x['interpretation_verdict'];category=('A' if x['corroboration_gate_pass'] else 'B') if eligible and v=='CORRECT' else ('D' if x['corroboration_gate_pass'] else 'C') if eligible and v=='INCORRECT' else None
    issue=blocker(reasons,source) if not eligible else None
    if issue=='tautomer specificity':assessment='UNDETERMINED_POTENTIALLY_OVERBROAD';explanation='A chemistry toolkit generated alternate tautomers but the current local rule does not map name locants to all mobile positions; actual source insufficiency is not independently proven.'
    elif issue=='alias conflict':assessment='SOURCE_CLAIMS_CONFLICT_PER_PARSER';explanation='Saved parseable source aliases have identity-dimension differences; individual semantic specificity can require further review.'
    elif issue=='charge/protonation':assessment='SOURCE_FORM_DISAGREEMENT_OR_UNVERIFIED_CHARGE';explanation='A specific alias differs in charge/protonation or the name-only charge placement is not independently mapped.'
    else:assessment='REQUIRES_CASE_REVIEW';explanation='The local reason is retained; independent case-specific sufficiency has not been established.'
    results.append(dict(cuma_index=i,name=x['preferred_name'],candidate=candidate['smiles'],prior_verdict=v,reference_smiles=x['reference_smiles'],reference_quality_flag=x['reference_quality_flag'],local_status='DETERMINISTIC_LOCAL_EXACT_ELIGIBLE' if eligible else 'LOCALLY_WITHHELD',reasons=reasons,source_form=source,blocker=issue,blocker_assessment=assessment if not eligible else None,blocker_explanation=explanation if not eligible else None,provider_states=x['all_query_states'],original_qualifying_corroboration=x['corroboration_gate_pass'],post_gate_category=category,prior_outcome=x['final_status']))
assert len(results)==224
correct=[r for r in results if r['prior_verdict']=='CORRECT'];wrong=[r for r in results if r['prior_verdict']=='INCORRECT'];assert len(correct)==183 and len(wrong)==1
retained=sum(r['local_status']=='DETERMINISTIC_LOCAL_EXACT_ELIGIBLE' for r in correct);bad=sum(r['local_status']=='DETERMINISTIC_LOCAL_EXACT_ELIGIBLE' for r in wrong);total=retained+bad
ci=[float(beta.ppf(.025,retained,total-retained+1)) if retained else 0,float(beta.ppf(.975,retained+1,total-retained)) if retained<total else 1] if total else None
blocked=[r for r in results if r['local_status']=='LOCALLY_WITHHELD'];new_correct=[r for r in correct if r['local_status']=='LOCALLY_WITHHELD']
recall_ci=[float(beta.ppf(.025,retained,225-retained+1)),float(beta.ppf(.975,retained+1,225-retained))]
metrics=dict(total_cohort=224,local_eligible=224-len(blocked),local_withheld=len(blocked),previous_correct=183,correct_retained=retained,correct_newly_withheld=len(new_correct),incorrect_retained=bad,local_precision=dict(correct=retained,incorrect=bad,denominator=total,point=retained/total if total else None,clopper_pearson_95=ci),local_recall=dict(correct=retained,reference_exact=225,point=retained/225,clopper_pearson_95=recall_ci),blockers=dict(collections.Counter(r['blocker'] for r in blocked)),correct_blockers=dict(collections.Counter(r['blocker'] for r in new_correct)),post_gate_categories={k:sum(r['post_gate_category']==k for r in results) for k in 'ABCD'},no_new_provider_queries=True,limitations=['Replay applies current local helpers to saved source claims and stored official InChI outcomes, not a full end-to-end rerun.','Reference labels and provider evidence remain frozen.','Non-specific tautomer screening can conservatively hold names whose source specification has not been mapped.'])
(H/'deterministic_form_replay.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
(H/'local_eligibility_metrics.json').write_text(json.dumps(metrics,indent=2,ensure_ascii=False),encoding='utf-8')
(H/'newly_blocked_cases.json').write_text(json.dumps(blocked,indent=2,ensure_ascii=False),encoding='utf-8')
(H/'post_remediation_gate_value.json').write_text(json.dumps(dict(categories=metrics['post_gate_categories'],cases=[r for r in results if r['post_gate_category']],no_new_provider_queries=True),indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(metrics,indent=2))
