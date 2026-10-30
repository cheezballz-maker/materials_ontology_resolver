"""Reproduce this isolated validation offline; no registry writes or providers."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent
def main():
 protected=json.loads((H/'evaluation/protected_input_freeze.json').read_text())['files']
 changed=[n for n,d in protected.items() if not Path(n).is_file() or hashlib.sha256(Path(n).read_bytes()).hexdigest()!=d]
 if changed:raise RuntimeError('Protected baseline changed: '+str(changed))
 for script in ('run_regressions.py','evaluate.py','investigate_references.py','evidence_independence_audit.py','admission_policy_checks.py','package_review.py','readiness_assessment.py','finalize.py','write_report.py'):
  print(script,flush=True)
  with (H/'evaluation'/f'{Path(script).stem}_replay.log').open('w',encoding='utf8') as log:
   subprocess.run([sys.executable,str(H/script)],cwd=H.parent.parent,env={**os.environ,'PYTHONIOENCODING':'utf-8'},stdout=log,stderr=subprocess.STDOUT,check=True)
 print('Isolated validation complete; production baseline unchanged.')
if __name__=='__main__':main()
