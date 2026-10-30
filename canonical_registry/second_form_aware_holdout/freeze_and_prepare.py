"""Independent structural/coverage QA; prediction inputs contain no references."""
import hashlib,json,re,sqlite3
from datetime import datetime,timezone
from pathlib import Path
from rdkit import Chem,rdBase

H=Path(__file__).resolve().parent; B=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def protect():
    s=read(H/'SAMPLE_FROZEN.json')
    assert sha(s['source_path'])==s['source_sha256'],'Source changed'
    assert sha(H/'prepare_sample.py')==s['sampling_script_sha256']
    for key,file in [('selection_sha256','selection.json'),('eligible_sha256','eligible_population.json'),('exclusions_sha256','exclusions.json')]:
        assert sha(H/'steward'/file)==s[key],file
    assert sha(H/'steward/protected_hashes.json')==s['protected_hashes_sha256']
    for p,v in read(H/'steward/protected_hashes.json').items():assert sha(p)==v,p
    for p,v in s['packets'].items():assert sha(H/p)==v,p
    assert sha(H/'supplemental/records.json')==s['supplemental_sha256']
    return s

def validate():
    sample=protect(); rows=[];refs=[];files={};counts={};aliascounts={}
    for folder in ['packet_1','packet_2','packet_3','supplemental']:
        d=H/folder;original=read(d/'records.json');reference=read(d/'reference.json');f=read(d/'FROZEN.json')
        assert f['predictions_seen'] is False,folder
        assert sha(d/'reference.json')==f['sha256'],folder
        by={r['cuma_index']:r for r in reference};assert len(by)==len(reference)==len(original)
        assert set(by)=={r['cuma_index'] for r in original}
        counts[folder]=len(original);aliascounts[folder]=0
        for o in original:
            i=o['cuma_index'];r=by[i];assert r['preferred_name']==o['preferred_name'],i
            assert r['expected_status'] in ['EXACT','UNRESOLVED','CONFLICT','OUT_OF_SCOPE','INVALID'],i
            assert r.get('reason') and isinstance(r.get('dimensions'),dict) and isinstance(r.get('form_categories'),list),i
            if r['expected_status']=='UNRESOLVED':assert r.get('abstention_basis') in ['INHERENT_AMBIGUITY','INSUFFICIENT_EVIDENCE'],i
            assert isinstance(r.get('evidence'),list),i
            if r['expected_status']=='EXACT':
                s=r['expected_smiles'];assert isinstance(s,str) and s and not any(c.isspace() for c in s),i
                p=Chem.SmilesParserParams();p.parseName=False;p.allowCXSMILES=False
                mol=Chem.MolFromSmiles(s,p);assert mol is not None and all(a.GetAtomicNum()>0 for a in mol.GetAtoms()),i
                assert Chem.MolToInchi(mol)==r['expected_inchi'],(i,'InChI disagreement')
                assert Chem.MolToInchiKey(mol)==r['expected_inchikey'],(i,'key disagreement')
                assert re.fullmatch('[A-Z]{14}-[A-Z]{10}-[A-Z]',r['expected_inchikey']),i
                for k in ['constitution','stereo','isotope','protonation_charge','components','component_stoichiometry','hydration_solvation','tautomer']:
                    assert k in r['dimensions'],(i,'missing dimension',k)
                assert r['evidence'] and all(e.get('url') and e.get('lineage') and e.get('independence') for e in r['evidence']), (i,'missing provenance')
            assert len(r['alias_judgments'])==len(o['aliases']),i
            for j,(a,s) in enumerate(zip(r['alias_judgments'],o['aliases'])):
                assert a['alias_position']==j and a['alias']==s,(i,j)
                assert a['judgment'] in ['SAME','DIFFERENT','UNRESOLVED'],(i,j)
                assert a.get('reason'),(i,j)
                if a['judgment'] in ('SAME','DIFFERENT'):assert a.get('evidence_urls'),(i,j,'unattested alias judgment')
            aliascounts[folder]+=len(o['aliases'])
        for name in ['records.json','reference.json','FROZEN.json','methodology.json','Molecular_Substance_Identity_Framework_v1.md']:
            files[f'{folder}/{name}']=sha(d/name)
        if folder!='supplemental':rows+=original;refs+=reference
    assert len(rows)==400 and {r['cuma_index'] for r in rows}==set(sample['indices'])
    assert not set(sample['indices']) & {9152,46724,52217}
    return rows,dict(files=files,record_counts=counts,alias_claim_counts=aliascounts,qa='PASS',rdkit_version=rdBase.rdkitVersion)

if __name__=='__main__':
    rows,qa=validate()
    dest=H/'predictions';assert not dest.exists(),'Never replace or rerun predictions'
    dest.mkdir();db=sqlite3.connect(dest/'candidates.sqlite')
    db.execute('CREATE TABLE candidate(cuma_index INTEGER PRIMARY KEY,name TEXT,aliases TEXT,status TEXT,diagnostic TEXT,evidence_json TEXT)')
    errors=read(H/'steward/selection.json')['input_errors']
    for r in rows:
        db.execute('INSERT INTO candidate VALUES(?,?,?,?,?,?)',(r['cuma_index'],r['preferred_name'],json.dumps(r['aliases'],ensure_ascii=False),'UNRESOLVED','Frozen original input, not a prediction',json.dumps({'claims':[],'input_error':errors.get(str(r['cuma_index']))})))
    db.commit();db.close()
    save(H/'ADJUDICATION_FROZEN.json',dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),**qa,predictions_seen=False,protocol_sha256=sha(H/'PROTOCOL.md'),sample_sha256=sha(H/'SAMPLE_FROZEN.json'),pubchem_budget=2400,chebi_budget=4000,gsrs_budget=800))
    print('PASS: 400 holdout references and 3 supplemental references frozen; original prediction inputs prepared.')
