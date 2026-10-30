"""Package reproduced diagnostic classes; this artifact is not wired to admission."""
import hashlib,json,zipfile
from pathlib import Path
H=Path(__file__).resolve().parent;m=json.loads((H/'reproduction_manifest.json').read_text())
src=Path(m['temp_build'])/'diagnostic-classes';out=H/'opsin-2.9.0-trace.jar'
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for p in sorted(src.rglob('*.class')):
  name=p.relative_to(src).as_posix();info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
  z.writestr(info,p.read_bytes())
print(hashlib.sha256(out.read_bytes()).hexdigest())
