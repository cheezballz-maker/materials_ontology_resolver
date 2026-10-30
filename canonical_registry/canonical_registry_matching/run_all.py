"""Reproduce offline matching evaluation without touching previous artifacts."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent
def main():
 files=json.loads((H/'evaluation/protected_input_freeze.json').read_text())['files']
 changed=[p for p,d in files.items() if not Path(p).is_file() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=d]
 if changed:raise RuntimeError('Protected baseline changed: '+str(changed))
 for script in ('collect_saved_inputs.py','evaluate_benchmark.py','matching_tests.py','run_regressions.py','evaluate_real_registry.py','provider_policy_audit.py','finalize.py','write_report.py'):
  print(script,flush=True)
  with (H/'evaluation'/(Path(script).stem+'_replay.log')).open('w',encoding='utf8') as log:subprocess.run([sys.executable,str(H/script)],cwd=H.parent.parent,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONIOENCODING':'utf-8'},check=True)
 print('Read-only matching validation completed; no persistent ID assignment authorized.')
if __name__=='__main__':main()
