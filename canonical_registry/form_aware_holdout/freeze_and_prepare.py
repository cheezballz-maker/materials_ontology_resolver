"""Gate prediction preparation on all independent reference freezes and QA."""
import hashlib,json,re,sqlite3
from datetime import datetime,timezone
from pathlib import Path
from rdkit import Chem
H=Path(__file__).resolve().parent;B=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def validate():
    sample=read(H/'SAMPLE_FROZEN.json');assert sha(sample['source_path'])==sample['source_sha256']
    for path,h in sample['packets'].items():assert sha(H/path)==h,path
    for path,h in read(H/'steward/protected_hashes.json').items():assert sha(path)==h,path
    allrefs=[];source=[];hashes={};issues=[]
    for n in (1,2,3):
        packet=H/f'packet_{n}';freeze=read(packet/'FROZEN.json');refs=read(packet/'reference.json');records=read(packet/'records.json')
        assert sha(packet/'Molecular_Substance_Identity_Framework_v1.md')==sha(Path(r'C:\Users\IT PatsnapSG\Downloads\Molecular_Substance_Identity_Framework_v1.md'))
        assert sha(packet/'reference.json')==freeze['sha256'];assert freeze.get('predictions_seen') is False
        assert len(refs)==len(records)==120
        by={r['cuma_index']:r for r in refs};assert len(by)==120 and set(by)=={r['cuma_index'] for r in records}
        for original in records:
            r=by[original['cuma_index']];i=r['cuma_index']
            assert r['preferred_name']==original['preferred_name'],i
            assert r['expected_status'] in ('EXACT','UNRESOLVED','CONFLICT','OUT_OF_SCOPE','INVALID'),i
            aliases=r['alias_judgments'];assert len(aliases)==len(original['aliases']),i
            for j,a in enumerate(aliases):
                assert a['alias_position']==j and a['alias']==original['aliases'][j],(i,j)
                assert a['judgment'] in ('SAME','DIFFERENT','UNKNOWN'),(i,j)
                if a['judgment']=='SAME':assert a.get('evidence_urls'),(i,j,'unattested alias')
            if r['expected_status']=='EXACT':
                s=r['expected_smiles'];assert not any(c.isspace() for c in s),i
                assert re.fullmatch(r'[A-Z]{14}-[A-Z]{10}-[A-Z]',r['expected_inchikey'] or ''),i
                p=Chem.SmilesParserParams();p.parseName=False;p.allowCXSMILES=False
                m=Chem.MolFromSmiles(s,p);assert m is not None and all(a.GetAtomicNum() for a in m.GetAtoms()),i
                assert Chem.MolToInchiKey(m)==r['expected_inchikey'],i
                assert len({e['url'] for e in r['evidence'] if e.get('url')})>=2,(i,'single source')
            assert r.get('reason') and isinstance(r.get('dimensions'),dict),i
        allrefs+=refs;source+=records
        for f in ('reference.json','FROZEN.json','methodology.json'):
            hashes[f'packet_{n}/{f}']=sha(packet/f)
    assert len(allrefs)==360 and {r['cuma_index'] for r in allrefs}==set(sample['indices'])
    return source,hashes

if __name__=='__main__':
    source,hashes=validate();out=H/'predictions';assert not out.exists(),'Never rerun/replace predictions'
    out.mkdir();db=sqlite3.connect(out/'candidates.sqlite')
    db.execute('CREATE TABLE candidate(cuma_index INTEGER PRIMARY KEY,name TEXT,aliases TEXT,status TEXT,diagnostic TEXT,evidence_json TEXT)')
    errors=read(H/'steward/selection.json')['input_errors']
    for r in source:
        error=errors.get(str(r['cuma_index']))
        db.execute('INSERT INTO candidate VALUES(?,?,?,?,?,?)',(r['cuma_index'],r['preferred_name'],json.dumps(r['aliases'],ensure_ascii=False),'UNRESOLVED','Frozen original input; not a prediction',json.dumps({'claims':[],'input_error':error})))
    db.commit();db.close()
    save(H/'ADJUDICATION_FROZEN.json',dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),records=360,files=hashes,qa='PASS',predictions_opened=False,protocol_sha256=sha(H/'PROTOCOL.md'),pubchem_budget=1800,chebi_budget=3000))
    print('360 references frozen and validated. Prepared original inputs; no predictions run yet.')
