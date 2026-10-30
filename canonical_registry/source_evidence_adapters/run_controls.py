import hashlib,json,sys
from pathlib import Path
import bootstrap
from control_adapter import adapt
from scoped_evaluator import evaluate
H=Path(__file__).resolve().parent
def run(kind):
 frozen=json.loads((H/'controls/benchmark_freeze.json').read_text())['files']
 for name,digest in frozen.items():assert hashlib.sha256((H/'controls'/name).read_bytes()).hexdigest()==digest
 records=[]
 for c in json.loads((H/f'controls/{kind}_controls.json').read_text())['cases']:
  pkg=adapt(c['input_source_record'],c['candidate']);out=evaluate(pkg,c['candidate'],c['required_dimensions'],c['scope'],enabled=True);rec=out['reconciliation'];roots=len(rec['unique_source_lineages'])
  ok=rec['result']==c['expected_result'] and pkg.claims[0].claim_role==c['expected_first_role'] and (c['expected_dependency_roots'] is None or roots==c['expected_dependency_roots'])
  records.append(dict(id=c['id'],expected=c['expected_result'],actual=rec['result'],expected_role=c['expected_first_role'],actual_role=pkg.claims[0].claim_role,expected_roots=c['expected_dependency_roots'],actual_roots=roots,passed=ok,package=pkg.to_dict(),evaluation=out))
 result=dict(total=len(records),passed=sum(x['passed'] for x in records),cases=records,review_status='CHEMICAL_REVIEW_PENDING',blinding='PUBLIC_FROZEN_NOT_BLINDED')
 (H/f'evaluation/{kind}_results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps({k:v for k,v in result.items() if k!='cases'}));print([(x['id'],x['actual'],x['actual_role'],x['actual_roots']) for x in records if not x['passed']]);return result
if __name__=='__main__':assert run(sys.argv[1])['passed']==(31 if sys.argv[1]=='development' else 10)
