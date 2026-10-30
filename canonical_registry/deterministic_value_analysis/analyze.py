"""Read frozen outputs only; never invoke the resolver or query providers."""
import collections,hashlib,json,sqlite3,sys
from pathlib import Path
from scipy.stats import beta
H=Path(__file__).resolve().parent;B=H.parent;F=B/'fresh_blinded_evaluation';sys.path.insert(0,str(B))
from chemistry import describe
from identity_comparator import compare
from source_form import assess as assess_source_form

read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
freeze=read(B/'FRESH_BLINDED_EVALUATION_FREEZE.json')
def integrity():
    changed=[n for n,v in freeze['implementation_hashes'].items() if not (B/n).exists() or sha(B/n)!=v]
    if changed:raise RuntimeError('DETERMINISTIC_INTERPRETATION_ANALYSIS_INVALIDATED: '+','.join(changed))
    for k,v in freeze['external_hashes'].items():assert sha(v['path'])==v['sha256'],k
    rf=read(F/'REFERENCE_FROZEN.json')
    for k,v in rf['files'].items():assert sha(F/k)==v,k
    assert sha(F/'fresh_sample.json')==read(F/'SAMPLE_FROZEN.json')['sample_sha256']
    prior=read(B/'provider_correspondence_remediation/frozen.json')
    assert sha(B/'provider_qualification/run/registry.sqlite')==prior['prior_registry_sha256']
integrity()
sample={x['cuma_index']:x for x in read(F/'fresh_sample.json')};refs={x['cuma_index']:x for x in read(F/'reference_adjudication.json')}
supp={x['cuma_index']:x for x in read(H/'completed_exact_adjudications.json')}
assert set(supp)=={4570,6634}
for i,x in supp.items():
    d=describe(x['independently_derived_smiles']);assert d['inchikey']==x['inchikey']
    assert refs[i]['reference_status']=='UNADJUDICABLE'
quality={x['cuma_index'] for x in read(F/'REFERENCE_QUALITY_NOTES.json')['case_notes']}
quality.update(x['cuma_index'] for x in read(F/'BLIND_SOURCE_AMBIGUITY_AUDIT.json')['multiple_record_responses'] if x['different_graphs'])
db=sqlite3.connect((F/'run/candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
records=list(db.execute('select cuma_index,name,status,diagnostic,evidence_json from candidate'));db.close();assert len(records)==400
cohort=[];excluded=collections.Counter();mismatch=[]
for i,name,status,reason,raw in records:
    ev=json.loads(raw); interp=ev.get('name_interpretation',{}); pre=ev.get('preliminary_source_form',{});claims=ev.get('claims') or [];primary=claims[0] if claims else {};form=ev.get('decision',{}).get('form') or {}
    if interp.get('status')!='ESTABLISHED' or pre.get('status')!='SUPPORTED' or primary.get('status')!='SUCCESS' or not primary.get('structure') or form.get('specification')!='SPECIFIED':
        excluded[(interp.get('status','MISSING'),pre.get('status','MISSING'),form.get('specification','MISSING'))]+=1;continue
    candidate=primary['structure'];decision=ev.get('decision',{});local=decision.get('structure')
    if not local or compare(candidate,local)['assessment']!='EXACT':
        mismatch.append(i);continue
    expected=refs[i];refstructure=expected.get('reference_smiles');reforigin='FROZEN_REFERENCE'
    if i in supp and supp[i]['status']=='REFERENCE_EXACT_CONFIRMED':refstructure=supp[i]['independently_derived_smiles'];reforigin='SUPPLEMENTAL_BLINDED_ADJUDICATION'
    cmp=compare(candidate,describe(refstructure)) if refstructure else None
    ref_unc=str(expected.get('reference_uncertainty') or '').upper()
    if cmp:
        label={'EXACT':'CORRECT','DISTINCT':'INCORRECT','UNRESOLVED':'UNADJUDICABLE'}[cmp['assessment']]
    elif expected.get('reference_status')=='OUT_OF_SCOPE_REFERENCE':label='OUT_OF_SCOPE_REFERENCE_REVIEW_REQUIRED'
    elif ref_unc=='INHERENTLY_UNDERSPECIFIED':label='SOURCE_UNDERSPECIFICATION_REVIEW_REQUIRED'
    else:label='UNADJUDICABLE'
    routes=decision.get('provider_routes',[]);route_states=[x['state'] for x in routes]
    has_corr='CORROBORATES' in route_states;contradiction='CONTRADICTS' in route_states;gate_pass=has_corr and not contradiction
    states=[dict(provider=x['provider'],route=x['route'],query=x['query'],state=x['state'],record_ids=x.get('record_ids',[])) for x in routes]
    queries=ev.get('retrieval',{}).get('provider_states',[])
    availability=collections.Counter(x['state'] for x in queries)
    if label=='CORRECT':category='A' if has_corr else 'B'
    elif label=='INCORRECT':category='C' if not gate_pass else 'D'
    else:category=None
    alias_claims=[(a,c) for a,c in zip(sample[i]['aliases'],claims[1:])]
    # Evaluate the already-saved source claims only; this does not call OPSIN,
    # providers or Resolver and does not alter admission policy.
    if len(alias_claims)==len(sample[i]['aliases']):
        sf=assess_source_form(name,primary,alias_claims,candidate,form.get('source_assertion') or {},ev.get('local_source_support'),ev.get('source_name_profile'))
        alias_gate=dict(status=sf.get('status'),reason_codes=sf.get('reason_codes',[]),claim_conflicts=sf.get('source_claim_conflicts',[]))
    else:alias_gate=dict(status='UNAVAILABLE',reason_codes=['SAVED_ALIAS_CLAIMS_INCOMPLETE'])
    official=ev.get('official_inchi',{});official_ok=bool(official.get('agrees') and official.get('status') in ('SUCCESS','WARNING'))
    comp=ev.get('composition_comparison',{}).get('status');post_form=alias_gate['status']=='SUPPORTED' and comp!='UNRESOLVED'
    gate_only_withheld=bool(label=='CORRECT' and status=='UNRESOLVED' and reason=='NO_QUALIFYING_CORROBORATION' and not has_corr and not contradiction and official_ok and post_form)
    feature=form.get('features') or {};dimension_keys=('stereo_state','stereo_elements','isotopes','charge','charge_distribution','component_count','component_stoichiometry','hydrogen_placement','tautomer_sensitive','radical_electrons')
    record=dict(cuma_index=i,preferred_name=name,interpretation_status=interp['status'],preliminary_source_form=pre['status'],local_form_status=form['specification'],source_candidate=candidate['smiles'],source_identity_dimensions=pre.get('dimensions',{}),candidate_features={k:feature.get(k) for k in dimension_keys},reference_smiles=refstructure,reference_origin=reforigin,reference_status=expected['reference_status'],reference_quality_flag=i in quality,comparison=cmp,interpretation_verdict=label,final_status=status,final_reason=reason,corroborating_route_available=has_corr,provider_contradiction=contradiction,corroboration_gate_pass=gate_pass,provider_routes=states,all_query_states=dict(availability),alias_source_claim_gate=alias_gate,official_inchi_confirmed=official_ok,composition_status=comp,correct_withheld_solely_for_corroboration=gate_only_withheld,category=category)
    cohort.append(record)
assert not mismatch,('SOURCE_CANDIDATE_MISMATCH',mismatch)
counts=collections.Counter(x['interpretation_verdict'] for x in cohort);cats=collections.Counter(x['category'] for x in cohort if x['category']);corr=sum(x['interpretation_verdict']=='CORRECT' for x in cohort);bad=sum(x['interpretation_verdict']=='INCORRECT' for x in cohort);n=corr+bad
assert all(x['status']=='REFERENCE_EXACT_CONFIRMED' for x in supp.values())
for i,x in supp.items():
    candidate=next(z for z in cohort if z['cuma_index']==i)
    assert candidate['interpretation_verdict']=='CORRECT' and candidate['final_status']=='EXACT',(i,candidate)
refcount=sum(x['reference_status']=='EXACT_REFERENCE_AVAILABLE' for x in refs.values())+sum(x['status']=='REFERENCE_EXACT_CONFIRMED' for x in supp.values())
flagrefs={i for i in quality if refs[i]['reference_status']=='EXACT_REFERENCE_AVAILABLE'}
strict=[x for x in cohort if not x['reference_quality_flag']];sc=sum(x['interpretation_verdict']=='CORRECT' for x in strict);sb=sum(x['interpretation_verdict']=='INCORRECT' for x in strict);sn=sc+sb
interval=lambda a,t:([float(beta.ppf(.025,a,t-a+1)) if a else 0.,float(beta.ppf(.975,a+1,t-a)) if a<t else 1.] if t else None)
sole=[x['cuma_index'] for x in cohort if x['correct_withheld_solely_for_corroboration']]
states=('NO_MATCH','UNAVAILABLE','NON_DISCRIMINATING','PROVIDER_RECORD_AMBIGUOUS','CONTRADICTS','CORROBORATES')
state_analysis={cat:{state:sum(x['all_query_states'].get(state,0)>0 for x in cohort if x['category']==cat) for state in states} for cat in ('A','B','C','D')}
bad_gate=[x for x in cohort if x['category']=='C' and x['alias_source_claim_gate']['status']=='SUPPORTED' and x['official_inchi_confirmed'] and x['composition_status']!='UNRESOLVED']
out=dict(cohort_size=len(cohort),excluded_count=len(records)-len(cohort),excluded_breakdown={' / '.join(k):v for k,v in excluded.items()},interpretation_verdicts=dict(counts),categories={k:cats[k] for k in ('A','B','C','D')},precision=dict(correct=corr,incorrect=bad,adjudicable=n,point=corr/n if n else None,clopper_pearson_95=interval(corr,n)),recall=dict(correct=corr,reference_exact=refcount,point=corr/refcount if refcount else None),quality_sensitivity=dict(excluded_cohort_count=len(cohort)-len(strict),precision_correct=sc,precision_incorrect=sb,precision_denominator=sn,precision_ci=interval(sc,sn),recall_correct=sc,reference_exact=refcount-len(flagrefs),gate_only_correct=sum(x['correct_withheld_solely_for_corroboration'] for x in strict)),reference_quality_flags=sorted(quality),nonexclusive_query_state_record_counts=state_analysis,wrong_interpretations_locally_eligible_if_gate_removed=[x['cuma_index'] for x in bad_gate],correct_withheld_solely_for_corroboration=dict(count=len(sole),indices=sole),supplemental_exact_precision=dict(original_correct=6,original_adjudicable=6,supplemental_correct=2,supplemental_adjudicable=2,total_correct=8,total_adjudicable=8,ci=interval(8,8)),notes=['A/B describe corroboration availability; a separate independently verified provider contradiction can still veto.','C/D isolate the observed corroboration gate; other safeguards, including alias conflicts, remain in force.','Counterfactual solely-gate classification checks saved source aliases and official InChI; it is not a full rerun or a guarantee of registry admission.'])
integrity()
(H/'deterministic_interpretation_cases.json').write_text(json.dumps(cohort,indent=2,ensure_ascii=False),encoding='utf-8')
(H/'deterministic_interpretation_metrics.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
(H/'corroboration_value_analysis.json').write_text(json.dumps({'categories':dict(cats),'gate_only_withheld':out['correct_withheld_solely_for_corroboration'],'cases':[x for x in cohort if x['category']]},indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:out[k] for k in ('cohort_size','interpretation_verdicts','categories','precision','recall','quality_sensitivity','correct_withheld_solely_for_corroboration')},indent=2))
