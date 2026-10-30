"""Apply frozen diagnostic contract to matched source claims and saved candidates."""
import hashlib,json,sys
from collections import Counter
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parent;sys.path[:0]=[str(H),str(ROOT/'nsc_architecture_experiment')]
from architecture_B.nsc002_interpreter.interpreter import interpret_name,validate_candidate
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
for n,v in read(H/'NSC-002/benchmark_freeze.json')['sha256'].items():assert hashlib.sha256((H/'NSC-002'/n).read_bytes()).hexdigest()==v
saved=read(ROOT/'NOMENCLATURE_FALSE_HOLD_TAXONOMY.json');coverage=read(H/'NSC-002/candidate_scope_comparison.json');byid={x['cuma_index']:x for x in coverage['records']}
out=[]
for item in saved:
 assess=byid[item['record_id']]['candidates']['C'];status=assess['classification'];r={'cuma_index':item['record_id'],'preferred_name':item['preferred_name'],'classification':status,'primary_blocker':item['primary_blocker'],'source_claim_tested':None,'semantic_result':'NOT_EVALUATED','dimension_result':'UNKNOWN','local_eligibility':'NOT_EVALUATED','unresolved':['all other source claims and complete identity dimensions require separate assessment']}
 if status=='FULL_NAME_APPLICABLE':
  name=assess['matched_source'];candidate=item.get('opsin_candidate');interpretation=interpret_name(name);result=validate_candidate(interpretation,candidate)
  r.update({'source_claim_tested':name,'source_claim_role':assess['matched_role'],'semantic_result':result.result,'reason_codes':result.reason_codes,'evidence':result.evidence,'constraints':interpretation.structural_constraints,'unresolved':r['unresolved']+['chemical review pending','external corroboration and identity admission not evaluated']})
 out.append(r)
counts=dict(Counter(x['classification'] for x in out));tested=[x for x in out if x['semantic_result']!='NOT_EVALUATED']
payload={'source':'NOMENCLATURE_FALSE_HOLD_TAXONOMY.json','method':'Frozen grammar lexical opportunity; only complete in-contract source claims evaluated against saved candidate. No production admission, provider access, or partial-name semantics.','records':out,'summary':{'counts':counts,'full_names_tested':len(tested),'operation_results':dict(Counter(x['semantic_result'] for x in tested)),'complete_identity_dimension_support':0,'local_eligibility_evaluated':0,'identity_recovered_claimed':0,'historical_baseline':{'confirmed_correct':183,'previous_eligible':102,'previous_withheld':81}}}
(H/'evaluation/nsc002_81_case_applicability.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps({'summary':payload['summary'],'tested':tested},indent=2))
