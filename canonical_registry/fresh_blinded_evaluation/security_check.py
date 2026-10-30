"""Count secret occurrences without printing their value or surrounding text."""
import json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path.insert(0,str(B))
from comptox import configured_key
key=configured_key();matches=[];files=0
for p in H.rglob('*'):
    if p.is_file() and p.suffix in ('.json','.log','.txt','.md','.py'):
        files+=1
        if key and key.encode() in p.read_bytes():matches.append(str(p.relative_to(H)))
report=B/'FRESH_BLINDED_RESOLVER_EVALUATION_REPORT.md'
if report.exists() and key and key.encode() in report.read_bytes():matches.append(report.name)
result=dict(CTX_API_KEY_configured=bool(key),files_scanned=files,secret_occurrence_files=len(matches))
(H/'security_check.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if matches:sys.exit(1)
