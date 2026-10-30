"""Score frozen public controls, then freeze implementation before heldout."""
import hashlib,json,sys
from collections import Counter
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parent;sys.path[:0]=[str(H),str(ROOT/'nsc_architecture_experiment')]
from architecture_B.nsc002_interpreter.interpreter import interpret_name,validate_candidate
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 for n,v in read(H/'NSC-002/benchmark_freeze.json')['sha256'].items():
  if sha(H/'NSC-002'/n)!=v:raise ValueError('FROZEN_BENCHMARK_CHANGED '+n)
def hashes():return {str(p.relative_to(H)).replace('\\','/'):sha(p) for p in sorted((H/'architecture_B/nsc002_interpreter').glob('*.py'))}
def run(kind):
 check();lock=H/'evaluation/implementation_freeze.json'
 if kind=='heldout' and (not lock.exists() or read(lock)['sha256']!=hashes()):raise ValueError('IMPLEMENTATION_NOT_FROZEN')
 cases=read(H/f'NSC-002/{kind}_controls.json')['cases'];out=[]
 for c in cases:
  x=interpret_name(c['source_name']);v=validate_candidate(x,c['candidate_structure'],c['context'])
  out.append({'id':c['id'],'source_name':c['source_name'],'candidate_structure':c['candidate_structure'],'expected':c['expected_operation_result'],'actual':v.result,'scope_expected':c['contract_scope'],'scope_actual':x.scope_status,'scope_correct':c['contract_scope']==x.scope_status,'correct':v.result==c['expected_operation_result'],'source_claims':x.source_claims,'constraints':x.structural_constraints,'operation_results':v.operation_results,'dimension_results':v.dimension_results,'reason_codes':v.reason_codes,'evidence':v.evidence,'unresolved_dependencies':x.unresolved_dependencies,'chemical_review':'PENDING'})
 counts={'total':len(out),'correct':sum(x['correct'] for x in out),'scope_correct':sum(x['scope_correct'] for x in out),'false_supported':sum(x['actual']=='SUPPORTED' and x['expected']!='SUPPORTED' for x in out),'false_different':sum(x['actual']=='DIFFERENT' and x['expected']!='DIFFERENT' for x in out),'results':dict(Counter(x['actual'] for x in out))}
 write(H/f'evaluation/{kind}_results.json',{'review':'CHEMICAL_REVIEW_PENDING','counts':counts,'cases':out})
 if kind=='development':write(lock,{'sha256':hashes(),'stage':'FROZEN_AFTER_DEVELOPMENT_BEFORE_PUBLIC_HOLDOUT'})
 print(json.dumps({'suite':kind,**counts},indent=2))
if __name__=='__main__':run(sys.argv[1])
