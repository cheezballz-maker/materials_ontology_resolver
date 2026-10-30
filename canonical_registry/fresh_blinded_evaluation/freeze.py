"""Freeze the pre-existing resolver before sampling, excluding all secrets."""
import hashlib,json,os,platform,sys
from datetime import datetime,timezone
from pathlib import Path
H=Path(__file__).resolve().parent; B=H.parent; sys.path.insert(0,str(B))
from providers import DEFAULT_JAR
from comptox import configured_key
from rdkit import rdBase
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
f=read(B/'provider_correspondence_remediation/frozen.json')
assert all(sha(B/name)==digest for name,digest in f['files'].items()),'Current resolver differs from frozen implementation'
old=read(B/'evidence_scope_remediation_result/IMPLEMENTATION_FROZEN.json')
paths={'opsin_jar':DEFAULT_JAR,'ontology':Path(old['ontology_path']),'framework':Path(old['framework_path']),'schema':B/'schema.sql','nonsecret_config':B/'.env.example','requirements':B/'requirements.txt'}
assert sha(paths['ontology'])==old['ontology_sha256']
assert sha(paths['schema'])==old['runtime_hashes']['schema.sql']
assert sha(DEFAULT_JAR)==read(B/'evidence_scope_remediation_result/classpath.json')['jar_sha256']
manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),source_freeze_sha256=sha(B/'provider_correspondence_remediation/frozen.json'),implementation_hashes=f['files'],external_hashes={k:{'path':str(p),'sha256':sha(p)} for k,p in paths.items()},runtime={'python':platform.python_version(),'rdkit':rdBase.rdkitVersion,'CTX_API_KEY_configured':bool(configured_key())},note='No secret values, authorization headers or credential-bearing URLs recorded.')
dest=B/'FRESH_BLINDED_EVALUATION_FREEZE.json';assert not dest.exists();dest.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Freeze written; existing implementation and contract hashes match.')
