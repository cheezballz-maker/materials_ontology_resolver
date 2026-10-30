import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent
def main():
 p=H/'evaluation/implementation_freeze.json'
 if p.exists():raise SystemExit('Already frozen; refusing overwrite')
 names=['bootstrap.py','record_inputs.py','correspondence_assessment.py','evidence_independence_assessment.py']
 p.write_text(json.dumps({'version':'1.0','phase':'AFTER_DOCUMENTARY_DEVELOPMENT_REFERENCE_BEFORE_FROZEN_EVALUATION','files':{n:hashlib.sha256((H/n).read_bytes()).hexdigest() for n in names},'production_modules_changed':False},indent=2)+'\n',encoding='utf8');print('Thin diagnostic interface frozen')
if __name__=='__main__':main()
