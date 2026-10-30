import collections,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path[:0]=[str(H),str(B/'nsc002_experiment'),str(B/'nsc_architecture_experiment'),str(B)]
from build_evidence import build
from diagnostic_evidence_consumer import consume
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,x):(H/'evaluation'/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
source=B/'deterministic_form_remediation/replay_local.py';code=source.read_text(encoding='utf8')
for n in ('deterministic_form_replay.json','local_eligibility_metrics.json','newly_blocked_cases.json','post_remediation_gate_value.json'):
    old=f"(H/'{n}')";assert code.count(old)==1;code=code.replace(old,f"(OUT/'{n}')")
ctx={'__file__':str(source),'__name__':'__main__','OUT':H/'evaluation'};exec(compile(code,str(source),'exec'),ctx)
samples={x['cuma_index']:x for x in read(B/'fresh_blinded_evaluation/fresh_sample.json')};rows=[]
for r in ctx['results']:
    aliases=samples[r['cuma_index']]['aliases'];e=build(r['name'],aliases,r['candidate']);before=consume(r['source_form'],r['reasons'],e);after=consume(r['source_form'],r['reasons'],e,enable_charge_dimension_evidence=True)
    assert before['local_eligible']==(r['local_status']=='DETERMINISTIC_LOCAL_EXACT_ELIGIBLE')
    rows.append({'cuma_index':r['cuma_index'],'source_name':r['name'],'aliases':aliases,'candidate':r['candidate'],'reference_status':r['prior_verdict'],'saved_provider_corroboration':r['original_qualifying_corroboration'],'before':before,'after':after,'charge_evidence':e.to_dict(),'changes':{'operation_support_gained':e.operation_result=='SUPPORTED','dimension_support_gained':after['consumed'],'local_eligibility_gained':after['local_eligible'] and not before['local_eligible'],'FINAL_EXACT_UNCHANGED':True}})
def counts(key):
    return {'correct_eligible':sum(x[key]['local_eligible'] and x['reference_status']=='CORRECT' for x in rows),'correct_withheld':sum(not x[key]['local_eligible'] and x['reference_status']=='CORRECT' for x in rows),'incorrect_eligible':sum(x[key]['local_eligible'] and x['reference_status']=='INCORRECT' for x in rows),'unadjudicable_eligible':sum(x[key]['local_eligible'] and x['reference_status']=='UNADJUDICABLE' for x in rows),'source_form_status_counts':dict(collections.Counter(x[key]['source_form']['status'] for x in rows))}
summary={'population':224,'before':counts('before'),'after':counts('after'),'operation_supported':sum(x['charge_evidence']['operation_result']=='SUPPORTED' for x in rows),'dimension_supported':sum(x['charge_evidence']['dimension_result']=='SUPPORTED' for x in rows),'consumed':sum(x['after']['consumed'] for x in rows),'eligibility_gained':sum(x['changes']['local_eligibility_gained'] for x in rows),'new_conflicts':sum(x['after']['source_form']['status']=='CONFLICT' and x['before']['source_form']['status']!='CONFLICT' for x in rows),'suppressed_conflicts':sum(x['before']['source_form']['status']=='CONFLICT' and x['after']['source_form']['status']!='CONFLICT' for x in rows),'final_admission':'NOT_RUN; no registry/provider action','review':'CHEMICAL_REVIEW_PENDING'}
write('baseline_reproduction.json',{'metrics':ctx['metrics'],'reproduced_current_counts':summary['before'],'older_reference_population_225':'Not the deterministic cohort denominator.'})
write('local_eligibility_before_after.json',{'summary':summary,'records':rows})
write('charge_evidence_results.json',{'summary':summary,'records':[{'cuma_index':r['cuma_index'],'evidence':r['charge_evidence']} for r in rows]})
ids={r['cuma_index'] for r in read(B/'semantic_gap_analysis/withheld_81_diagnostics.json')['records'] if r['neutral_nitro_only_charged_atoms'] and r['historical_primary_blocker']=='charge/protonation'}
sixteen=[r for r in rows if r['cuma_index'] in ids];assert len(sixteen)==16
nitro_summary={'total':16,'only_source_protonation_reason':sum(r['before']['remaining_reasons']==['SOURCE_PROTONATION_SPECIFICITY_UNKNOWN'] for r in sixteen),'complete_source_context':sum(r['charge_evidence']['site_coverage']['complete'] for r in sixteen),'group_supported':sum(r['charge_evidence']['operation_result']=='SUPPORTED' for r in sixteen),'dimension_supported':sum(r['charge_evidence']['dimension_result']=='SUPPORTED' for r in sixteen),'eligible_gained':sum(r['changes']['local_eligibility_gained'] for r in sixteen),'additional_current_reasons':sum(r['before']['remaining_reasons']!=['SOURCE_PROTONATION_SPECIFICITY_UNKNOWN'] for r in sixteen)}
write('nitro_16_case_analysis.json',{'summary':nitro_summary,'records':sixteen})
print(json.dumps({'cohort':summary,'nitro':nitro_summary},indent=2))
