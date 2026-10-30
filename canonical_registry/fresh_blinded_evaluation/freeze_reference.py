"""Validate and freeze the independent references before any predictions exist."""
import hashlib,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
from rdkit import Chem
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
assert not (H/'RUN_STARTED.json').exists() and not (H/'REFERENCE_FROZEN.json').exists()
implementation=read(H.parent/'FRESH_BLINDED_EVALUATION_FREEZE.json')
for name,digest in implementation['implementation_hashes'].items():
    assert sha(H.parent/name)==digest,'BLINDED_EVALUATION_INVALIDATED_BY_CODE_CHANGE: '+name
for name,item in implementation['external_hashes'].items():assert sha(item['path'])==item['sha256'],'CONTRACT_CHANGED: '+name
manifest=read(H/'SAMPLE_FROZEN.json');assert sha(H/'fresh_sample.json')==manifest['sample_sha256']
sample={r['cuma_index']:r for r in read(H/'fresh_sample.json')};combined=[]
for n in (1,2,3):
    packet=H/f'packet_{n}';rows=read(packet/'reference.json');source=read(packet/'records.json')
    assert (packet/'METHODOLOGY.md').exists() and len(rows)==len(source)
    assert {r['cuma_index'] for r in rows}=={r['cuma_index'] for r in source}
    for row in rows:
        s=sample[row['cuma_index']];assert row['preferred_name']==s['preferred_name']
        assert Counter(a.get('alias') for a in row.get('alias_judgments',[]))==Counter(s['aliases']),('ALIAS_COVERAGE',row['cuma_index'])
        assert row['reference_status'] in ('EXACT_REFERENCE_AVAILABLE','NOT_EXACT_REFERENCE','OUT_OF_SCOPE_REFERENCE','UNADJUDICABLE')
        if row['reference_status']=='EXACT_REFERENCE_AVAILABLE':
            m=Chem.MolFromSmiles(row.get('reference_smiles') or '');assert m is not None,row['cuma_index']
            assert Chem.MolToInchiKey(m)==row.get('reference_inchikey'),row['cuma_index']
            urls=[e.get('url','') for e in row.get('evidence',[]) if isinstance(e,dict)]
            assert len({urlparse(u).netloc for u in urls if urlparse(u).scheme=='https'})>=2,('INSUFFICIENT_SOURCE_DIVERSITY',row['cuma_index'])
        combined.append(row)
assert len(combined)==400 and len({r['cuma_index'] for r in combined})==400
combined.sort(key=lambda x:x['cuma_index']);dest=H/'reference_adjudication.json';dest.write_text(json.dumps(combined,indent=2,ensure_ascii=False),encoding='utf-8')
paths=['reference_adjudication.json']+[f'packet_{n}/{p}' for n in (1,2,3) for p in ('records.json','reference.json','METHODOLOGY.md')]
out=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),sample_sha256=sha(H/'fresh_sample.json'),files={p:sha(H/p) for p in paths},reference_labels_revised_after_prediction=False,acknowledgment='Reference sources may share ancestry; domain diversity does not establish independent chemical evidence.')
(H/'REFERENCE_FROZEN.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('Frozen references:',len(combined))
