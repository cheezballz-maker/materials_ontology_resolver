"""Redirect existing validation outputs, preserving prior frozen artifacts."""
import json,os,socket,subprocess,sys,unittest
from pathlib import Path
import bootstrap
from bootstrap import BASE as B
H=Path(__file__).resolve().parent
def deny(*a,**kw):raise AssertionError('LIVE_NETWORK_DISABLED')
def new_tests():
 socket.create_connection=deny
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in ('test_correspondence','test_isotope_comparison'))
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 (H/'evaluation/correspondence_tests.json').write_text(json.dumps(dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful()),indent=2)+'\n',encoding='utf8');assert result.wasSuccessful()
def legacy(suite):
 source=B/'source_evidence_adapters/run_validations.py';code=source.read_text(encoding='utf8')
 old='H=Path(__file__).resolve().parent';assert code.count(old)==1;code=code.replace(old,'H=NEW_OUT')
 ctx={'__file__':str(source),'__name__':'redirected_validation','NEW_OUT':H/'evaluation'}
 # Existing runner expects H/evaluation, so H is this experiment root; it writes
 # only experiment-local outputs. Source import paths still point to old code.
 ctx['NEW_OUT']=H;exec(compile(code,str(source),'exec'),ctx)
 if suite=='historical':ctx['historical']()
 else:assert ctx['child'](suite)
if __name__=='__main__':
 if len(sys.argv)>1:
  socket.create_connection=deny
  if sys.argv[1]=='correspondence':new_tests()
  else:legacy(sys.argv[1])
 else:
  codes={}
  for suite in ('correspondence','adapters','identity_reconciliation','nsc001','nsc002','charge','resolver','historical'):
   with (H/f'evaluation/{suite}_tests.log').open('w',encoding='utf8') as log:proc=subprocess.run([sys.executable,str(H/'run_regressions.py'),suite],cwd=H,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
   codes[suite]=proc.returncode;print(suite,proc.returncode,flush=True)
  (H/'evaluation/regression_exit_codes.json').write_text(json.dumps(codes,indent=2)+'\n',encoding='utf8');assert not any(codes.values())
