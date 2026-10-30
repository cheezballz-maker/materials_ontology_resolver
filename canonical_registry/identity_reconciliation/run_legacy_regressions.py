from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
source=B/'charge_dimension_evidence/run_regressions.py';code=source.read_text(encoding='utf8')
old="(H/'evaluation/nsc_regression.json')";assert code.count(old)==1;code=code.replace(old,"(NEW_OUT/'nsc_regression.json')")
old="'OUT':H/'evaluation'";assert code.count(old)==1;code=code.replace(old,"'OUT':NEW_OUT")
exec(compile(code,str(source),'exec'),{'__file__':str(source),'__name__':'__main__','NEW_OUT':H/'evaluation'})
