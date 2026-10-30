"""Actual suite counts, local-only historical replay, outputs confined here."""
import json,os,socket,subprocess,sys,unittest
from pathlib import Path
import bootstrap
from bootstrap import BASE as B
H=Path(__file__).resolve().parent
SUITES={
 'adapters':['test_adapters'],
 'identity_reconciliation':['test_reconciliation'],
 'nsc001':['architecture_B.tests.test_interpreter','shared.test_semantic_and_graph'],
 'nsc002':['architecture_B.nsc002_tests.test_nsc002'],
 'charge':['test_charge_evidence'],
}
def denied(*a,**kw):raise AssertionError('LIVE_NETWORK_DISABLED_FOR_VALIDATION')
def child(name):
 socket.create_connection=denied
 if name=='resolver':os.chdir(B)  # Retained registry tests load schema.sql relatively.
 loader=unittest.TestLoader()
 suite=loader.discover(str(B),pattern='test*.py',top_level_dir=str(B)) if name=='resolver' else unittest.TestSuite(loader.loadTestsFromName(n) for n in SUITES[name])
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 summary=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),passed=result.wasSuccessful())
 (H/f'evaluation/{name}_tests.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8');return result.wasSuccessful()
def historical():
 socket.create_connection=denied
 source=B/'charge_dimension_evidence/run_regressions.py';code=source.read_text(encoding='utf8')
 for old,new in [("(H/'evaluation/nsc_regression.json')","(NEW_OUT/'nsc_regression.json')"),("'OUT':H/'evaluation'","'OUT':NEW_OUT")]:
  assert code.count(old)==1;code=code.replace(old,new)
 exec(compile(code,str(source),'exec'),{'__file__':str(source),'__name__':'__main__','NEW_OUT':H/'evaluation'})
 prior=json.loads((B/'identity_reconciliation/evaluation/historical_safety_results.json').read_text());now=json.loads((H/'evaluation/historical_safety_results.json').read_text())
 assert prior==now,'HISTORICAL_SAFETY_RESULT_CHANGED'
if __name__=='__main__':
 if len(sys.argv)>1:
  if sys.argv[1]=='historical':historical()
  else:sys.exit(0 if child(sys.argv[1]) else 1)
 else:
  codes={}
  for name in list(SUITES)+['resolver','historical']:
   with (H/f'evaluation/{name}_tests.log').open('w',encoding='utf8') as log:
    proc=subprocess.run([sys.executable,str(H/'run_validations.py'),name],cwd=H,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
   codes[name]=proc.returncode;print(name,proc.returncode,flush=True)
  (H/'evaluation/validation_exit_codes.json').write_text(json.dumps(codes,indent=2)+'\n',encoding='utf8');assert not any(codes.values())
