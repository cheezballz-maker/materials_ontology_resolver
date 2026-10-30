"""Verify archive manifest and extract only top-level research files."""
import hashlib,json,zipfile
from pathlib import Path
H=Path(__file__).resolve().parent
source=Path(r'C:\Users\IT PatsnapSG\Downloads\OPSIN_INDICATED_H_MAPPING_POC_BUNDLE.zip')
dest=H/'poc_bundle';dest.mkdir(exist_ok=True)
with zipfile.ZipFile(source) as z:
 manifest=json.loads(z.read('BUNDLE_MANIFEST.json'))
 failures=[n for n,v in manifest.items() if hashlib.sha256(z.read(n)).hexdigest()!=v]
 assert not failures,failures
 names=[x.filename for x in z.infolist() if '/' not in x.filename and not x.is_dir()]
 for n in names:
  assert Path(n).name==n
  (dest/n).write_bytes(z.read(n))
 print(json.dumps({'manifest_files_verified':len(manifest),'top_level_extracted':len(names),'archive_sha256':hashlib.sha256(source.read_bytes()).hexdigest()},indent=2))
