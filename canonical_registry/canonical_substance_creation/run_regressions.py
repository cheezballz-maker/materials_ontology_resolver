"""Retained suites with all output paths redirected, never overwrite freezes."""
import json,shutil
from pathlib import Path
import bootstrap
H=Path(__file__).resolve().parent;B=H.parent

def redirected(file,out):
 out.mkdir(parents=True,exist_ok=True);(out/'evaluation').mkdir(exist_ok=True)
 needle='H=Path(__file__).resolve().parent;B=H.parent'
 code=file.read_text();assert needle in code
 # Replace the top-level assignment only; nested redirection code is literal.
 code=code.replace(needle,'H=NEW_OUT;B=BASE',1)
 ctx={'__file__':str(file),'__name__':'retained_creation_regressions','NEW_OUT':out,'BASE':B};exec(compile(code,str(file),'exec'),ctx);ctx['main']()

def main():
 root=H/'evaluation/regressions';redirected(B/'unified_substance_resolution/run_regressions.py',root)
 old=root/'unified';(old/'examples').mkdir(parents=True,exist_ok=True);shutil.copytree(B/'unified_substance_resolution/controls',old/'controls',dirs_exist_ok=True)
 redirected(B/'unified_substance_resolution/evaluate_pipeline.py',old)
 reg=json.loads((root/'evaluation/regression_results.json').read_text());unified=json.loads((old/'evaluation/end_to_end_results.json').read_text())
 # Retained real-world comparison assertions (30/30 hardened) are separate
 # from synthetic matching controls and cannot establish population accuracy.
 f=B/'canonical_registry_matching/run_regressions.py';code=f.read_text().replace('H=Path(__file__).resolve().parent;B=H.parent','H=NEW_OUT;B=BASE',1)
 ctx={'__file__':str(f),'__name__':'retained_real_world','NEW_OUT':root,'BASE':B};exec(compile(code,str(f),'exec'),ctx);ctx['real_world']()
 result={'retained':reg,'unified_passed':unified['passed'],'unified_total':unified['total'],'real_world':json.loads((root/'evaluation/retained_real_world_results.json').read_text()),'passed':reg['retained_unit_passed'] and reg['retained_association_passed']==25 and unified['passed']==unified['total']==19}
 (H/'evaluation/regression_results.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']
if __name__=='__main__':main()
