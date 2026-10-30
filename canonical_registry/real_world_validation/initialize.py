"""Protect existing implementation/data before diagnostic validation work."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
def main():
 for name in ('reference_corpus','validation_material','evaluation'):(H/name).mkdir(exist_ok=True)
 p=H/'evaluation/protected_input_freeze.json'
 if p.exists():raise SystemExit('Existing protected freeze retained; refusing overwrite')
 previous=json.loads((B/'source_candidate_correspondence/evaluation/protected_input_freeze.json').read_text())['files'];paths={Path(n) for n in previous}|set((B/'source_candidate_correspondence').rglob('*.py'))|set((B/'source_candidate_correspondence').rglob('*.json'))|{B/'SOURCE_TO_CANDIDATE_IDENTITY_CORRESPONDENCE_V1_REPORT.md'}
 p.write_text(json.dumps({'files':{str(x.resolve()):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(paths) if x.is_file()},'production_provider_calls_allowed':0},indent=2)+'\n',encoding='utf8');print('Protected existing resolver, registry, ontology and frozen inputs')
if __name__=='__main__':main()
