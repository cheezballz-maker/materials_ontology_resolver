"""Evaluation-only scorer. No resolver or provider imports; never changes labels."""
import hashlib,json,math,sqlite3
from collections import Counter,defaultdict
from datetime import datetime,timezone
from functools import lru_cache
from itertools import combinations
from pathlib import Path
from rdkit import Chem
H=Path(__file__).resolve().parent;B=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def divide(a,b):return a/b if b else None
def wilson(c,n):
    if not n:return None
    z=1.959963984540054;p=c/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [mid-half,mid+half]
@lru_cache(maxsize=2048)
def graphs(s):
    assert isinstance(s,str) and not any(c.isspace() for c in s)
    p=Chem.SmilesParserParams();p.parseName=False;p.allowCXSMILES=False
    m=Chem.MolFromSmiles(s,p);assert m is not None and all(a.GetAtomicNum() for a in m.GetAtoms())
    forms={Chem.MolToSmiles(m,canonical=True,isomericSmiles=True)}
    for r in Chem.ResonanceMolSupplier(m,0,65):
        Chem.SanitizeMol(r);forms.add(Chem.MolToSmiles(r,canonical=True,isomericSmiles=True))
    return frozenset(forms),Chem.MolToInchiKey(m)
def same(a,b):
    x,k=graphs(a);y,l=graphs(b);return bool(x&y) and k==l
def nonadmissible(r):
    return r['expected_status'] in ('CONFLICT','OUT_OF_SCOPE','INVALID') or (r['expected_status']=='UNRESOLVED' and r.get('abstention_basis')=='INHERENT_AMBIGUITY')
def causes(reason,reference,ev):
    causes=[];text=reason.upper();f=reference.get('form_categories',[])
    if any(s in text for s in ['EXTERNAL_EVIDENCE','NO_EXTERNAL','NO_INDEPENDENT_CANDIDATE']):causes.append('insufficient external evidence')
    if 'STEREO' in text:causes.append('stereo interpretation')
    if 'ISOTOPE' in text:causes.append('isotope placement')
    if 'HYDRATION' in text:causes.append('hydrate stoichiometry')
    if 'SOLVENT' in text or 'SOLVATE' in text:causes.append('solvate semantics')
    if 'COUNTERION' in text:causes.append('counterion stoichiometry')
    if 'TAUTOMER' in text:causes.append('tautomer conflict')
    if 'COMPONENT' in text:
        causes.append('hydrate stoichiometry' if 'hydrate' in f else 'solvate semantics' if 'solvate' in f else 'salt semantics' if 'salt' in f else 'multicomponent stoichiometry')
    if 'PROTONATION' in text or 'CHARGE_STATE' in text:causes.append('protonation ambiguity')
    if 'PROVIDER_' in text or 'IDENTITY_DIMENSION_CONFLICT' in text:causes.append('provider disagreement')
    if 'IDENTITY_DIMENSION_UNKNOWN' in text:causes.append('unresolved identity dimension')
    if any(s in text for s in ['COORDINATION','ELEMENT_UNSUPPORTED','ELECTRONIC','EXTENDED_INORGANIC','ENSEMBLE']):causes.append('unsupported chemistry')
    if 'EXCLUDED_MATERIAL' in text:causes.append('scope classification')
    primary=ev.get('claims',[{}])[0] if ev.get('claims') else {}
    if primary.get('status') in ('FAILURE','ERROR','INVALID','WARNING'):causes.append('local parser failure or warning')
    if 'NAME_PARSER' in text:causes.append('local parser failure or warning')
    return list(dict.fromkeys(causes)) or ['source-name or form interpretation; manual review required']

def metrics(rows,aliases):
    n=len(rows);ad=[r for r in rows if r['predicted_status']=='EXACT'];c=sum(r['exact_verdict']=='CORRECT' for r in ad);bad=sum(r['exact_verdict']=='INCORRECT' for r in ad);u=len(ad)-c-bad
    refs=sum(r['expected_status']=='EXACT' for r in rows)
    abst=[r for r in rows if r['predicted_status']!='EXACT'];ca=sum(r['abstention_verdict']=='CORRECT' for r in abst);wa=sum(r['abstention_verdict']=='EXCESSIVE' for r in abst)
    na=sum(r['reference_nonadmissible'] for r in rows)
    ac=sum(r['verdict']=='CORRECT' for r in aliases);ab=sum(r['verdict']=='INCORRECT' for r in aliases)
    ids={r['cuma_index'] for r in rows};pairs=[];unknown=0;group=defaultdict(list)
    for r in ad:group[r['substance_id']].append(r)
    for sid,g in group.items():
        for a,b in combinations(g,2):
            if a['expected_status']==b['expected_status']=='EXACT':pairs.append((a,b,not same(a['expected_smiles'],b['expected_smiles'])))
            else:unknown+=1
    return dict(records=n,expected_status=dict(Counter(r['expected_status'] for r in rows)),predicted_status=dict(Counter(r['predicted_status'] for r in rows)),automatic_exact=dict(admissions=len(ad),correct=c,false_positive=bad,unverified=u,precision=divide(c,c+bad),wilson95=wilson(c,c+bad),confirmed_fraction=divide(c,len(ad))),correct_exact_recall=dict(correct=c,reference_exact=refs,rate=divide(c,refs)),false_merges=dict(count=sum(x[2] for x in pairs),assessed_pairs=len(pairs),unassessed_pairs=unknown,rate=divide(sum(x[2] for x in pairs),len(pairs))),abstention=dict(nonexact=len(abst),rate=divide(len(abst),n),internal_unresolved=sum(r['predicted_status']=='UNRESOLVED' for r in rows),internal_unresolved_rate=divide(sum(r['predicted_status']=='UNRESOLVED' for r in rows),n),correct=ca,excessive=wa,unverified=len(abst)-ca-wa,correct_abstention_precision=divide(ca,ca+wa),reference_nonadmissible=na,correct_abstention_recall=divide(ca,na)),alias_promotion=dict(promoted=len(aliases),correct=ac,incorrect=ab,unverified=len(aliases)-ac-ab,precision=divide(ac,ac+ab),wilson95=wilson(ac,ac+ab)),status_agreement=dict(count=sum(r['predicted_status']==r['expected_status'] for r in rows),rate=divide(sum(r['predicted_status']==r['expected_status'] for r in rows),n)))

def main():
    frozen=read(H/'ADJUDICATION_FROZEN.json');protocol=read(H/'PROTOCOL_FROZEN.json')
    assert sha(H/'PROTOCOL.md')==protocol['protocol_sha256']==frozen['protocol_sha256']
    assert sha(H/'SAMPLE_FROZEN.json')==protocol['sample_sha256']
    for f,v in frozen['files'].items():assert sha(H/f)==v,f
    protected=read(H/'steward/protected_hashes.json')
    for f,v in protected.items():assert sha(f)==v,f
    refs={};originals={}
    for n in (1,2,3):
        refs.update({r['cuma_index']:r for r in read(H/f'packet_{n}/reference.json')})
        originals.update({r['cuma_index']:r for r in read(H/f'packet_{n}/records.json')})
    run=H/'predictions';cand=sqlite3.connect((run/'candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    reg=sqlite3.connect((run/'registry.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    selection=read(H/'steward/selection.json');rows=[];aliasrows=[]
    for i,name,aliases,cs,reason,raw in cand.execute('SELECT * FROM candidate ORDER BY cuma_index'):
        ref=refs[i];ev=json.loads(raw);sid,status,rr=reg.execute('SELECT substance_id,resolution_status,reason FROM substance_reconciliation WHERE cuma_index=?',(i,)).fetchone()
        assert status==cs and reason==rr
        structs=[r[0] for r in reg.execute("SELECT structure_value FROM substance_structure WHERE substance_id=? AND structure_type='SMILES'",(sid,))]
        assert status!='EXACT' or structs
        verdict=None;av=None;failure=None
        if status=='EXACT':
            verdict=('CORRECT' if all(same(s,ref['expected_smiles']) for s in structs) else 'INCORRECT') if ref['expected_status']=='EXACT' else 'INCORRECT' if nonadmissible(ref) else 'UNVERIFIED'
            if verdict=='INCORRECT':failure='UNSAFE_FALSE_ADMISSION' if ref['expected_status']!='EXACT' else 'INCORRECT_FORM_OR_IDENTITY'
            elif verdict=='UNVERIFIED':failure='UNVERIFIED_ADMISSION'
        else:
            av='EXCESSIVE' if ref['expected_status']=='EXACT' else 'CORRECT' if nonadmissible(ref) else 'UNVERIFIED'
            if av=='EXCESSIVE':failure='EXCESSIVE_CONSERVATIVE_ABSTENTION'
            elif status!=ref['expected_status']:failure='NON_ADMISSION_STATUS_DISAGREEMENT' if av=='CORRECT' else 'UNRESOLVED_REFERENCE_COMPARISON'
        cause=causes(reason,ref,ev)
        row=dict(cuma_index=i,preferred_name=name,expected_status=ref['expected_status'],predicted_status=status,expected_smiles=ref.get('expected_smiles'),expected_inchikey=ref.get('expected_inchikey'),predicted_smiles=structs,substance_id=sid,exact_verdict=verdict,abstention_verdict=av,reference_nonadmissible=nonadmissible(ref),reference_reason=ref['reason'],reference_abstention_basis=ref.get('abstention_basis'),reference_confidence=ref.get('confidence'),resolver_reason=reason,primary_stratum=selection['primary_strata'][str(i)],sampling_tags=selection['tags'][str(i)],reference_categories=ref.get('form_categories',[]),failure_type=failure,likely_causes=cause,evidence=ref['evidence'],dimensions=ref['dimensions'])
        rows.append(row)
        refalias={a['alias_position']:a for a in ref['alias_judgments']};positions=defaultdict(list)
        for j,a in enumerate(originals[i]['aliases']):positions[a].append(j)
        seen=Counter()
        for a in ev.get('alias_decisions',[]):
            j=positions[a['alias']][seen[a['alias']]];seen[a['alias']]+=1
            if not a.get('accepted'):continue
            assert reg.execute('SELECT 1 FROM substance_alias WHERE substance_id=? AND alias=?',(sid,a['alias'])).fetchone()
            ar=refalias[j];v='UNVERIFIED'
            if verdict=='CORRECT' and ar['judgment'] in ('SAME','DIFFERENT'):v='CORRECT' if ar['judgment']=='SAME' else 'INCORRECT'
            elif verdict=='INCORRECT' and ref['expected_status']=='EXACT' and ar['judgment']=='SAME':v='INCORRECT'
            aliasrows.append(dict(cuma_index=i,alias_position=j,alias=a['alias'],reference_judgment=ar['judgment'],verdict=v,reference_reason=ar['reason'],evidence_urls=ar.get('evidence_urls',[])))
    assert len(rows)==360
    total=metrics(rows,aliasrows);strata={};actualforms={}
    for tag in list(selection['available_at_selection']):
        subset=[r for r in rows if tag in r['sampling_tags']];ids={r['cuma_index'] for r in subset}
        strata[tag]=metrics(subset,[a for a in aliasrows if a['cuma_index'] in ids])
    for tag in ['straightforward','stereo','isotope','protonation_charge','salt','hydrate','solvate','tautomer','multicomponent','out_of_scope']:
        subset=[r for r in rows if tag in r['reference_categories']];ids={r['cuma_index'] for r in subset}
        actualforms[tag]=metrics(subset,[a for a in aliasrows if a['cuma_index'] in ids])
    merges=[];group=defaultdict(list)
    for r in rows:
        if r['predicted_status']=='EXACT':group[r['substance_id']].append(r)
    for sid,g in group.items():
        for a,b in combinations(g,2):
            if a['expected_status']==b['expected_status']=='EXACT' and not same(a['expected_smiles'],b['expected_smiles']):merges.append(dict(substance_id=sid,cuma_indices=[a['cuma_index'],b['cuma_index']],failure_type='INCORRECT_MERGING'))
    gaps={}
    for cause in sorted({c for r in rows if r['failure_type'] for c in r['likely_causes']}):
        found=[r for r in rows if r['failure_type'] and cause in r['likely_causes']];lost=[r for r in found if r['abstention_verdict']=='EXCESSIVE']
        gaps[cause]=dict(records=len(found),reference_exact_lost_records=len(lost),reference_exact_lost_graphs=len({min(graphs(r['expected_smiles'])[0]) for r in lost}),confirmed_false_admissions=sum(r['exact_verdict']=='INCORRECT' for r in found),indices=[r['cuma_index'] for r in found],lost_indices=[r['cuma_index'] for r in lost])
    integrity=dict(sqlite=reg.execute('PRAGMA integrity_check').fetchone()[0],foreign_key_violations=len(reg.execute('PRAGMA foreign_key_check').fetchall()))
    for table in ['substance_identity','substance_alias','substance_identifier','substance_structure','substance_reconciliation']:integrity[table]=reg.execute('SELECT count(*) FROM '+table).fetchone()[0]
    assert integrity['sqlite']=='ok' and not integrity['foreign_key_violations']
    cand.close();reg.close()
    outputs={'metrics.json':total,'by_sampling_tag.json':strata,'by_reference_form.json':actualforms,'comparison.json':rows,'alias_comparison.json':aliasrows,'false_merges.json':merges,'gap_counts.json':gaps,'integrity.json':integrity,'disagreements.json':[r for r in rows if r['failure_type']]}
    for f,v in outputs.items():save(H/f,v)
    save(H/'SCORING_MANIFEST.json',dict(scored_at_utc=datetime.now(timezone.utc).isoformat(),reference_freeze_sha256=sha(H/'ADJUDICATION_FROZEN.json'),scorer_sha256=sha(__file__),protected_files_unchanged=len(protected),prediction_hashes={f:sha(run/f) for f in ['registry.sqlite','candidates.sqlite']},result_hashes={f:sha(H/f) for f in outputs}))
    print(json.dumps(total,indent=2))
if __name__=='__main__':main()
