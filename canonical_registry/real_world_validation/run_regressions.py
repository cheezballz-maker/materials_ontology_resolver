"""Run actual retained suites with all outputs redirected to this experiment."""
import json,os,socket,subprocess,sys,unittest
from pathlib import Path
import bootstrap
from bootstrap import BASE as B
H=Path(__file__).resolve().parent
def deny(*a,**kw):raise AssertionError('LIVE_RESOLVER_PROVIDER_NETWORK_DISABLED')
def run_child(name):
 socket.create_connection=deny
 if name=='diagnostic':
  result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_assessment'))
  (H/'evaluation/diagnostic_tests.json').write_text(json.dumps(dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful()),indent=2)+'\n',encoding='utf8');assert result.wasSuccessful();return
 source=B/'source_candidate_correspondence/run_regressions.py';code=source.read_text(encoding='utf8');needle='\nH=Path(__file__).resolve().parent\n';assert code.count(needle)==1;code=code.replace(needle,'\nH=NEW_OUT\n')
 ctx={'__file__':str(source),'__name__':'redirected_retained_suites','NEW_OUT':H};exec(compile(code,str(source),'exec'),ctx)
 if name=='correspondence':ctx['new_tests']()
 else:ctx['legacy'](name)
def baseline_controls():
 source=B/'source_candidate_correspondence/run_benchmark.py';code=source.read_text(encoding='utf8');old="(H/f'evaluation/{kind}_results.json')";assert code.count(old)==1;code=code.replace(old,"(NEW_OUT/f'baseline_{kind}_results.json')")
 ctx={'__file__':str(source),'__name__':'retained_baseline_controls','NEW_OUT':H/'evaluation'};exec(compile(code,str(source),'exec'),ctx)
 for kind in ('development','heldout'):
  summary=ctx['run'](kind);assert summary['passed']==summary['cases']
if __name__=='__main__':
 if len(sys.argv)>1:
  if sys.argv[1]=='baseline_controls':baseline_controls()
  else:run_child(sys.argv[1])
 else:
  exits={}
  for name in ('diagnostic','correspondence','adapters','identity_reconciliation','nsc001','nsc002','charge','resolver','historical','baseline_controls'):
   with (H/f'evaluation/{name}_tests.log').open('w',encoding='utf8') as log:proc=subprocess.run([sys.executable,str(H/'run_regressions.py'),name],cwd=H,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
   exits[name]=proc.returncode;print(name,proc.returncode,flush=True)
  (H/'evaluation/regression_exit_codes.json').write_text(json.dumps(exits,indent=2)+'\n',encoding='utf8');assert not any(exits.values())
