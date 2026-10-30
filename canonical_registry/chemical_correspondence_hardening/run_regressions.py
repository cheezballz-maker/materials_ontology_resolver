"""Run retained suites offline, redirecting all artifacts to this experiment."""
import os,json,socket,subprocess,sys,unittest
from pathlib import Path
import bootstrap
from bootstrap import BASE as B
H=Path(__file__).resolve().parent
def deny(*args,**kwargs):raise AssertionError('PRODUCTION_PROVIDER_NETWORK_DISABLED')
def run(name):
 socket.create_connection=deny
 if name=='corrected_controls':
  from assessment import resolve_correspondence
  f=B/'source_candidate_correspondence/run_benchmark.py';code=f.read_text();old="(H/f'evaluation/{kind}_results.json')";assert code.count(old)==1
  ctx={'__file__':str(f),'__name__':'corrected_control_replay','NEW_OUT':H/'evaluation'}
  exec(compile(code.replace(old,"(NEW_OUT/f'corrected_{kind}_results.json')"),str(f),'exec'),ctx);ctx['resolve_correspondence']=resolve_correspondence
  for kind in ('development','heldout'):
   s=ctx['run'](kind);assert s['passed']==s['cases']
  return
 if name in ('stereo','corrected_interface'):
  if name=='stereo':suite=unittest.defaultTestLoader.loadTestsFromName('stereo_regression_tests')
  else:
   f=B/'real_world_validation/test_assessment.py';code=f.read_text().replace('from correspondence_assessment import assess','from assessment import assess')
   ctx={'__file__':str(f),'__name__':'corrected_interface_tests'};exec(compile(code,str(f),'exec'),ctx)
   suite=unittest.defaultTestLoader.loadTestsFromTestCase(ctx['AssessmentTests'])
  r=unittest.TextTestRunner(verbosity=2).run(suite)
  (H/f'evaluation/{name}_tests.json').write_text(json.dumps(dict(tests_run=r.testsRun,failures=len(r.failures),errors=len(r.errors),passed=r.wasSuccessful()),indent=2)+'\n')
  assert r.wasSuccessful();return
 f=B/'real_world_validation/run_regressions.py';code=f.read_text();needle='\nH=Path(__file__).resolve().parent\n';assert code.count(needle)==1
 ctx={'__file__':str(f),'__name__':'redirected_frozen_regressions','NEW_OUT':H};exec(compile(code.replace(needle,'\nH=NEW_OUT\n'),str(f),'exec'),ctx)
 if name=='baseline_controls':ctx['baseline_controls']()
 else:ctx['run_child'](name)
if __name__=='__main__':
 if len(sys.argv)>1:run(sys.argv[1])
 else:
  codes={}
  for name in ('stereo','corrected_interface','diagnostic','correspondence','adapters','identity_reconciliation','nsc001','nsc002','charge','resolver','historical','baseline_controls','corrected_controls'):
   with (H/f'evaluation/{name}_tests.log').open('w',encoding='utf8') as log:
    p=subprocess.run([sys.executable,str(H/'run_regressions.py'),name],cwd=H,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
   codes[name]=p.returncode;print(name,p.returncode,flush=True)
  (H/'evaluation/regression_exit_codes.json').write_text(json.dumps(codes,indent=2)+'\n');assert not any(codes.values())
