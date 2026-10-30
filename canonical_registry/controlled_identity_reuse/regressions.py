import json,os,shutil,subprocess,sys
from pathlib import Path
import bootstrap
H=Path(__file__).resolve().parent;B=H.parent
def main():
 # Redirect the retained 357-suite runner and all of its output roots.
 f=B/'canonical_registry_matching/run_regressions.py';code=f.read_text().replace('H=Path(__file__).resolve().parent;B=H.parent','H=NEW_OUT;B=BASE')
 ctx={'__file__':str(f),'__name__':'retained','NEW_OUT':H,'BASE':B};exec(compile(code,str(f),'exec'),ctx)
 for name in ('stereo','corrected_interface','diagnostic','correspondence','adapters','identity_reconciliation','nsc001','nsc002','charge','resolver','historical','baseline_controls','corrected_controls','retained_policy'):
  ctx['run'](name);print(name,flush=True)
 # Isolate the old matching tests, including their disposable SQLite files.
 root=H/'retained_matching';(root/'fixtures').mkdir(parents=True,exist_ok=True);(root/'evaluation').mkdir(exist_ok=True)
 shutil.copytree(B/'canonical_registry_matching/controls',root/'controls',dirs_exist_ok=True)
 shutil.copyfile(B/'canonical_registry_matching/evaluation/benchmark_results.json',root/'evaluation/benchmark_results.json')
 f=B/'canonical_registry_matching/matching_control_inputs.py';code=f.read_text().replace('H=Path(__file__).resolve().parent;B=H.parent','H=NEW_OUT;B=BASE');helper={'__file__':str(f),'__name__':'isolated_helpers','NEW_OUT':root,'BASE':B};exec(compile(code,str(f),'exec'),helper)
 f=B/'canonical_registry_matching/matching_tests.py';code=f.read_text().replace('from matching_control_inputs import matching_input,fixture_registry','').replace('H=Path(__file__).resolve().parent;B=H.parent','H=NEW_OUT;B=BASE')
 tests={'__file__':str(f),'__name__':'isolated_tests','NEW_OUT':root,'BASE':B,'matching_input':helper['matching_input'],'fixture_registry':helper['fixture_registry']};exec(compile(code,str(f),'exec'),tests);tests['main']()
 shutil.copyfile(root/'evaluation/matching_tests.json',H/'evaluation/matching_tests.json')
if __name__=='__main__':main()
