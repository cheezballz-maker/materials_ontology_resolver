"""Execute retained suites with redirected outputs and isolated fixture data."""
import json,shutil
from pathlib import Path
import bootstrap
H=Path(__file__).resolve().parent;B=H.parent
def main():
 f=B/'controlled_identity_reuse/regressions.py';code=f.read_text().replace('H=Path(__file__).resolve().parent;B=H.parent','H=NEW_OUT;B=BASE',1)
 ctx={'__file__':str(f),'__name__':'retained_unit_suites','NEW_OUT':H,'BASE':B};exec(compile(code,str(f),'exec'),ctx);ctx['main']()
 root=H/'evaluation/retained_association';(root/'evaluation').mkdir(parents=True,exist_ok=True);(root/'fixtures').mkdir(exist_ok=True)
 shutil.copytree(B/'controlled_identity_reuse/controls',root/'controls',dirs_exist_ok=True)
 f=B/'controlled_identity_reuse/evaluate.py';code=f.read_text().replace('H=Path(__file__).resolve().parent;B=H.parent','H=NEW_OUT;B=BASE',1)
 ctx={'__file__':str(f),'__name__':'retained_association_workflows','NEW_OUT':root,'BASE':B};exec(compile(code,str(f),'exec'),ctx);ctx['main']()
 suites={n:json.loads((H/f'evaluation/{n}_tests.json').read_text()) for n in ('diagnostic','correspondence','adapters','identity_reconciliation','nsc001','nsc002','charge','resolver','stereo','corrected_interface','policy','matching')}
 bench=json.loads((root/'evaluation/benchmark_results.json').read_text())
 result=dict(suites=suites,retained_unit_integration=sum(s['tests_run'] for s in suites.values()),retained_unit_passed=all(s['passed'] for s in suites.values()),retained_association_controls=bench['total'],retained_association_passed=bench['passed'],historical_results=json.loads((H/'evaluation/historical_safety_results.json').read_text()))
 (H/'evaluation/regression_results.json').write_text(json.dumps(result,indent=2)+'\n');assert result['retained_unit_passed'] and bench['passed']==25
if __name__=='__main__':main()
