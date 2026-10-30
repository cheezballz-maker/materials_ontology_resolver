"""Freeze protected inputs and prospective chemical controls before execution."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
def main():
 for d in ('evaluation','reference_review','controls'): (H/d).mkdir(exist_ok=True)
 protected=H/'evaluation/protected_input_freeze.json'
 if protected.exists():raise RuntimeError('Do not replace pre-work snapshot')
 prior=json.loads((B/'real_world_validation/evaluation/protected_input_freeze.json').read_text())['files']
 paths={Path(p) for p in prior}|set((B/'real_world_validation').rglob('*.json'))|set((B/'real_world_validation').rglob('*.py'))|set((B/'real_world_validation/validation_material').glob('*'))|{B/'REAL_WORLD_CORRESPONDENCE_VALIDATION_V1_REPORT.md'}
 files={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file() and p.suffix!='.log'}
 protected.write_text(json.dumps({'files':files,'scope':'Prior protected resolver/registry/ontology plus original real-world implementation, corpus and results'},indent=2)+'\n',encoding='utf8')
 cases=[
 ('partial_contradiction','C1C([C@H](C2=CC=CC=C21)O)Br','C1[C@H]([C@@H](C2=CC=CC=C21)O)Br','DIFFERENT'),
 ('partial_compatible','C1C([C@H](C2=CC=CC=C21)O)Br','C1[C@@H]([C@H](C2=CC=CC=C21)O)Br','UNKNOWN'),
 ('complete_match','F[C@H](Cl)[C@H](Br)I','F[C@H](Cl)[C@H](Br)I','EQUIVALENT'),
 ('complete_one_difference','F[C@H](Cl)[C@H](Br)I','F[C@@H](Cl)[C@H](Br)I','DIFFERENT'),
 ('different_traversal','N[C@@H](C)C(=O)O','C[C@H](N)C(O)=O','EQUIVALENT'),
 ('symmetric_meso','C[C@H](O)[C@H](O)C','C[C@@H](O)[C@@H](O)C','EQUIVALENT'),
 ('symmetric_opposite','C[C@H](O)[C@@H](O)C','C[C@@H](O)[C@H](O)C','DIFFERENT'),
 ('unspecified','CC(O)CC','CC(O)CC','UNKNOWN'),
 ('nonstereogenic','CCO','OCC','NOT_APPLICABLE'),
 ('different_constitution','CCO','COC','UNKNOWN'),
 ('enhanced_relative','C[C@H](O)CC |&1:1|','C[C@H](O)CC |&1:1|','UNKNOWN'),
 ('double_complete','F/C=C/Cl','Cl/C=C/F','EQUIVALENT'),
 ('double_opposite','F/C=C/Cl','F/C=C\\Cl','DIFFERENT'),
 ('double_unspecified','FC=CCl','F/C=C/Cl','UNKNOWN'),
 ('two_partial_incompatible','F[C@H](Cl)C(Br)I','F[C@@H](Cl)C(Br)I','DIFFERENT'),
 ('two_partial_compatible','F[C@H](Cl)C(Br)I','F[C@H](Cl)C(Br)I','UNKNOWN'),
 ('isotope_environment_diff','[13CH3][C@H](O)CC','C[C@H](O)CC','UNKNOWN'),
 ('partial_bond_and_center','F/C=C/[C@H](O)C(Cl)Br','F/C=C/[C@@H](O)[C@H](Cl)Br','DIFFERENT')]
 f=H/'controls/stereo_controls.json';f.write_text(json.dumps({'grounding':'Prospective explicit graph constraints; not blind or expert-reviewed; frozen before comparator implementation','cases':[dict(id=k,left=a,right=b,expected=e) for k,a,b,e in cases]},indent=2)+'\n',encoding='utf8')
 (H/'controls/freeze.json').write_text(json.dumps({'stereo_controls.json':hashlib.sha256(f.read_bytes()).hexdigest()},indent=2)+'\n',encoding='utf8')
 print(len(files),'protected files;',len(cases),'prospective controls')
if __name__=='__main__':main()
