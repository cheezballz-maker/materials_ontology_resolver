"""Replay frozen core controls and check the isolation of the isotope correction."""
import hashlib,importlib.util,json
from pathlib import Path
import bootstrap
from bootstrap import BASE as B
from isotope_comparator import reconcile,compare_assertions
from dimension_claim_comparator import compare_assertions as original
from evidence_adapters import assertion
H=Path(__file__).resolve().parent
def main():
 path=B/'identity_reconciliation/run_benchmark.py';spec=importlib.util.spec_from_file_location('prior_identity_benchmark',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module.reconcile=reconcile
 def local_write(p,x):
  target=H/'evaluation'/('identity_core_'+p.name);target.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
 module.write=local_write
 for kind in ('development','heldout'):module.run(kind)
 changes=[];checked=0
 inv=json.loads((H/'controls/candidate_reference_inventory.json').read_text())['candidates'];byid={c['candidate_substance_id']:c for c in inv}
 for kind in ('development','heldout'):
  for case in json.loads((H/f'controls/{kind}_controls.json').read_text())['cases']:
   for claim in case['source']['claims']:
    if not claim.get('structure'):continue
    for cid in case['candidate_ids']:
     for dim in ('constitution','stereochemistry','tautomer','protonation_charge','components','component_stoichiometry','hydration_solvation','electronic_state'):
      a,b=assertion(claim['structure'],dim),assertion(byid[cid]['structure'],dim);old,new=original(a,b,dim),compare_assertions(a,b,dim);checked+=1
      if old!=new:changes.append(dict(case=case['id'],candidate=cid,dimension=dim,before=old,after=new))
 summaries={kind:json.loads((H/f'evaluation/identity_core_{kind}_results.json').read_text())['summary'] for kind in ('development','heldout')}
 result=dict(prior_frozen_core_controls=summaries,nonisotope_comparisons_checked=checked,changed_nonisotope_results=changes,original_files_overwritten=False)
 (H/'evaluation/comparator_regression_results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');assert not changes and all(s['passed']==s['total'] for s in summaries.values());print(result)
if __name__=='__main__':main()
