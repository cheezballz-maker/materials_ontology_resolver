import hashlib,json,sys
from pathlib import Path
import bootstrap
from correspondence_models import EvidencePolicy
from diagnostic_resolver import resolve_correspondence
from control_inputs import incoming,candidates
H=Path(__file__).resolve().parent
def run(kind):
 frozen=json.loads((H/'controls/benchmark_freeze.json').read_text())['files']
 for n,v in frozen.items():assert hashlib.sha256((H/'controls'/n).read_bytes()).hexdigest()==v
 data=json.loads((H/f'controls/{kind}_controls.json').read_text());inventory=json.loads((H/'controls/candidate_reference_inventory.json').read_text());out=[]
 for c in data['cases']:
  source=incoming(c);proposals=candidates(c['candidate_ids'],inventory);result=resolve_correspondence(source,proposals,EvidencePolicy(enabled=True));actual=[r['correspondence_status'] for r in result['candidate_results']]
  dimensions=result['candidate_results'][0]['dimension_comparisons'] if actual else {}
  ok=actual==c['expected_candidate_statuses'] and result['candidate_set_summary']==c['expected_set_summary'] and all(dimensions.get(k)==v for k,v in c['expected_dimensions'].items())
  out.append(dict(id=c['id'],description=c['description'],expected_statuses=c['expected_candidate_statuses'],actual_statuses=actual,expected_summary=c['expected_set_summary'],actual_summary=result['candidate_set_summary'],expected_dimensions=c['expected_dimensions'],actual_dimensions=dimensions,passed=ok,result=result))
 summary=dict(cases=len(out),passed=sum(x['passed'] for x in out),false_supported=sum(a=='CORRESPONDENCE_SUPPORTED' and e!='CORRESPONDENCE_SUPPORTED' for r in out for e,a in zip(r['expected_statuses'],r['actual_statuses'])),false_differences=sum(a=='CORRESPONDENCE_DIFFERENT' and e!='CORRESPONDENCE_DIFFERENT' for r in out for e,a in zip(r['expected_statuses'],r['actual_statuses'])),chemical_review='CHEMICAL_REVIEW_PENDING',blinding=data['blinding'])
 (H/f'evaluation/{kind}_results.json').write_text(json.dumps({'summary':summary,'cases':out},indent=2,ensure_ascii=False)+'\n',encoding='utf8');print(summary)
 for r in out:
  if not r['passed']:print(r['id'],r['actual_statuses'],r['actual_summary'],{k:r['actual_dimensions'].get(k) for k in r['expected_dimensions']})
 return summary
if __name__=='__main__':
 s=run(sys.argv[1]);assert s['passed']==s['cases']
