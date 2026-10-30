"""Run existing saved-claim local evaluation with output redirected to this experiment."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parent
source=ROOT/'deterministic_form_remediation/replay_local.py';code=source.read_text(encoding='utf8')
names=('deterministic_form_replay.json','local_eligibility_metrics.json','newly_blocked_cases.json','post_remediation_gate_value.json')
for name in names:
 old=f"(H/'{name}')";new=f"(OUT/'{name}')";assert code.count(old)==1;code=code.replace(old,new)
context={'__file__':str(source),'__name__':'__main__','OUT':H/'evaluation'}
exec(compile(code,str(source),'exec'),context)
results=context['results'];metrics=context['metrics'];diag=json.loads((H/'evaluation/nsc002_81_case_applicability.json').read_text(encoding='utf8'))
selected={x['cuma_index']:x for x in results};matched=[]
for row in diag['records']:
 if row['semantic_result']!='NOT_EVALUATED':
  previous=selected[row['cuma_index']];matched.append({'cuma_index':row['cuma_index'],'provisional_nsc002_operation':row['semantic_result'],'existing_local_status':previous['local_status'],'existing_reasons':previous['reasons'],'nsc002_connected_to_rules':False})
out={'method':'Executed existing saved-claim source-form and local eligibility rules in isolation. NSC-002 observations are shown beside the existing results, not injected into production or used to alter eligibility.','metrics':metrics,'diagnostic_cases':matched,'recovery_claimed':0,'new_eligibility_policy_tested':False,'chemical_review':'PENDING'}
(H/'evaluation/local_eligibility_comparison.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps({'correct_eligible':metrics['correct_retained'],'correct_withheld':metrics['correct_newly_withheld'],'matched':matched},indent=2))
