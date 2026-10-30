"""Trace the original frozen H02 without changing its labels or old outputs."""
import json,hashlib
from types import FunctionType
from pathlib import Path
import bootstrap
from bootstrap import BASE as B
from isotope_comparator import diagnostic,compare_assertions,reconcile
from evidence_adapters import assertion
from control_adapter import adapt
import scoped_evaluator
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 tests=[]
 for a,b,expected in [('[2H]O[2H]','[1H]O[1H]','EXACT_INCOMPATIBLE'),('[2H]O[2H]','O','EXACT_INCOMPATIBLE'),('[H]O[H]','O','EXACT_COMPATIBLE'),('[13CH3]CO','C[13CH2]O','EXACT_INCOMPATIBLE'),('[13CH3]CO','OC[13CH3]','EXACT_COMPATIBLE'),('[2H]CO','[H]C([2H])([H])O','EXACT_COMPATIBLE'),('[13CH3]CO','COC','EXACT_INCOMPATIBLE')]:
  result=diagnostic(a,b);actual=compare_assertions(assertion(a,'isotope'),assertion(b,'isotope'),'isotope');tests.append(dict(**result,expected=expected,actual=actual,passed=actual==expected))
 fn=scoped_evaluator.evaluate;corrected=FunctionType(fn.__code__,{**fn.__globals__,'reconcile':reconcile},fn.__name__,fn.__defaults__,fn.__closure__);corrected.__kwdefaults__=fn.__kwdefaults__
 old_controls=[]
 for kind in ('development','heldout'):
  for c in read(B/f'source_evidence_adapters/controls/{kind}_controls.json')['cases']:
   pkg=adapt(c['input_source_record'],c['candidate']);old=fn(pkg,c['candidate'],c['required_dimensions'],c['scope'],enabled=True);new=corrected(pkg,c['candidate'],c['required_dimensions'],c['scope'],enabled=True)
   old_controls.append(dict(id=c['id'],original_expected=c['expected_result'],legacy_actual=old['reconciliation']['result'],corrected_actual=new['reconciliation']['result'],passed=new['reconciliation']['result']==c['expected_result']))
 result=dict(root_cause='Isotope-free framework serialization retained formerly isotopic explicit H nodes, while implicit-H water serialized as O. Underlying structural comparator already returned isotope DIFFERENT; wrapper precheck discarded it as UNKNOWN.',fix='Snapshot labels on original graph; clear masses only on a temporary framework copy; collapse ordinary H there; compare original labelled isotope signatures.',source_scope='Represented graph distinctions only. A source isotope UNKNOWN remains UNKNOWN, and no source name receives graph-derived specificity.',cases=tests,prior_frozen_adapter_controls=old_controls,original_H02=next(c for c in old_controls if c['id']=='H02'),original_benchmark_changed=False,production_comparator_changed=False)
 (H/'evaluation/isotope_comparison_results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');assert all(t['passed'] for t in tests+old_controls);print('7 isotope comparisons; 41 original adapter controls with corrected wrapper; all passed')
if __name__=='__main__':main()
