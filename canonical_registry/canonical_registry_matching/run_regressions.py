"""Retained 357 tests and frozen controls, outputs exclusively in this folder."""
import json,os,socket,subprocess,sys,unittest
from pathlib import Path
import bootstrap
H=Path(__file__).resolve().parent;B=H.parent
def deny(*a,**kw):raise AssertionError('LIVE_PROVIDER_NETWORK_DISABLED')
def run(name):
 socket.create_connection=deny
 if name=='retained_policy':
  from admission_policy_checks import PolicyTests
  r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PolicyTests));(H/'evaluation/policy_tests.json').write_text(json.dumps(dict(tests_run=r.testsRun,failures=len(r.failures),errors=len(r.errors),passed=r.wasSuccessful()),indent=2)+'\n');assert r.wasSuccessful();return
 f=B/'chemical_correspondence_hardening/run_regressions.py';code=f.read_text();needle='\nH=Path(__file__).resolve().parent\n';assert code.count(needle)==1
 ctx={'__file__':str(f),'__name__':'retained_hardening_suites','NEW_OUT':H};exec(compile(code.replace(needle,'\nH=NEW_OUT\n'),str(f),'exec'),ctx);ctx['run'](name)
def real_world():
 from record_inputs import load
 from correspondence_assessment import assess as original
 from assessment import assess as hardened
 corpus=json.loads((B/'real_world_validation/reference_corpus/reference_cases.json').read_text())['cases'];out=[]
 for c in corpus:
  s,t=load(c);before=original(s,t,enabled=True);after=hardened(s,t,enabled=True)
  out.append(dict(case_id=c['case_id'],expected=c['expected_correspondence'],scored=c['accuracy_population_eligible'],original_chemical=before['represented_structure_comparison']['status'],hardened_chemical=after['represented_structure_comparison']['status'],hardened_dimensions=after['represented_structure_comparison']['dimension_comparisons']))
 scored=[r for r in out if r['scored']];result=dict(cases=out,scored=len(scored),original_agreement=sum(r['original_chemical']==r['expected'] for r in scored),hardened_agreement=sum(r['hardened_chemical']==r['expected'] for r in scored),frozen_labels_changed=False,expert_review='NOT_PERFORMED');(H/'evaluation/retained_real_world_results.json').write_text(json.dumps(result,indent=2)+'\n');assert result['original_agreement']==29 and result['hardened_agreement']==30
if __name__=='__main__':
 if len(sys.argv)>1:
  if sys.argv[1]=='real_world':real_world()
  else:run(sys.argv[1])
 else:
  codes={}
  for name in ('stereo','corrected_interface','diagnostic','correspondence','adapters','identity_reconciliation','nsc001','nsc002','charge','resolver','historical','baseline_controls','corrected_controls','retained_policy','real_world'):
   with (H/f'evaluation/{name}_regressions.log').open('w',encoding='utf8') as log:p=subprocess.run([sys.executable,str(H/'run_regressions.py'),name],cwd=H,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
   codes[name]=p.returncode;print(name,p.returncode,flush=True)
  (H/'evaluation/regression_exit_codes.json').write_text(json.dumps(codes,indent=2)+'\n');assert not any(codes.values())
