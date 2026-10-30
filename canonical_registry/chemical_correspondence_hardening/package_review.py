"""Reviewer navigation and derived molecular files; no new identity evidence."""
import hashlib,json
from pathlib import Path
import bootstrap
from chemistry import parse,describe
from rdkit import Chem
from rdkit.Chem import rdDepictor
H=Path(__file__).resolve().parent
def main():
 p=H/'reference_review/chemical_review_package.json';obj=json.loads(p.read_text(encoding='utf8'));dest=H/'reference_review/structures';dest.mkdir(exist_ok=True)
 lines=['# Independent chemical review queue','','Qualified expert review: **PENDING / NOT PERFORMED**. Review RW12, RW17, RW29 and RW30 first. `chemical_review_package.json` contains full original payloads, provenance, frozen expected labels, before/after outputs and obligations. Derived molecular files are visual aids, not independent structural evidence.','','| Case | Source → reference | Documentary expected | Corrected graph result | Proposed decision |','|---|---|---|---|---|']
 for row in obj['cases']:
  c=row['original_case'];files={}
  for side,key in [('source','source_structure'),('reference','reference_structure')]:
   text=c[key]
   if not text:files[side]={'status':'NO_EXPLICIT_MOLECULAR_GRAPH_IN_ORIGINAL_RECORD'};continue
   m=parse(text);rdDepictor.Compute2DCoords(m);f=dest/f"{c['case_id']}_{side}_derived.mol";block=Chem.MolToMolBlock(m)
   restored=Chem.MolFromMolBlock(block,sanitize=True,removeHs=True,strictParsing=True)
   assert restored is not None and Chem.MolToSmiles(restored,isomericSmiles=True)==Chem.MolToSmiles(m,isomericSmiles=True),(c['case_id'],side)
   f.write_text(block,encoding='utf8')
   files[side]=dict(path=str(f.resolve()),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),graph_roundtrip='PASS',origin='DERIVED_REVIEW_DISPLAY_FROM_PRESERVED_GRAPH_NOT_ORIGINAL_SOURCE_MOLFILE',independent_evidence=False,validated_descriptor=describe(text),original_graph=text)
  original=c['reference_identity']['record'].get('molfile')
  if original:files['reference_original_molfile']=original
  row['review_molecular_files']=files
  row['documentary_investigation']='stereochemistry_discrepancies.json' if c['case_id'] in ('RW12','RW17') else 'sodium_acetate_representation.json' if c['case_id']=='RW29' else None
  s=c['source_record'];r=c['reference_identity'];expect=c['expected_correspondence'] or 'UNSCORED_REFERENCE_PENDING'
  lines.append(f"| {c['case_id']} | {s['source_name']}:{s['record_id']} → {r['source_name']}:{r['record_id']} | {expect} | {row['corrected_output']['actual_correspondence']} | {row['suggested_reviewer_decision']} |")
 p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf8');(H/'reference_review/REVIEW_QUEUE.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
 manifest=H/'reference_review/review_manifest.json';data=json.loads(manifest.read_text());data['derived_display_files']={str(f.relative_to(H)):hashlib.sha256(f.read_bytes()).hexdigest() for f in dest.glob('*.mol')};data['all_derived_graph_roundtrips']='PASS';manifest.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
