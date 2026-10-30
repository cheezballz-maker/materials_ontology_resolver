"""Read-only prediction scoring against unchanged frozen labels and attestations.

No resolver policy code is imported. Graph scoring uses standalone RDKit resonance
enumeration, retaining isotope/stereo/H features, and the full regenerated key.
"""
import argparse,hashlib,json,sqlite3
from collections import Counter,defaultdict
from itertools import combinations
from pathlib import Path
from datetime import datetime,timezone
from rdkit import Chem
ROOT=Path(__file__).resolve().parent;F=ROOT/'blinded_validation';W=ROOT/'form_aware_evaluation'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ratio(a,b):return a/b if b else None
def graph(s):
    p=Chem.SmilesParserParams();p.parseName=False;p.allowCXSMILES=False
    m=Chem.MolFromSmiles(s,p)
    assert m is not None
    variants={Chem.MolToSmiles(m,True)}
    for r in Chem.ResonanceMolSupplier(m,0,65):
        Chem.SanitizeMol(r);variants.add(Chem.MolToSmiles(r,True))
    return variants,Chem.MolToInchiKey(m)
def same(a,b):
    x,k=graph(a);y,l=graph(b);return k==l and bool(x&y)

def score(run):
    baseline_hashes=read(W/'baseline_hashes.json')
    for path,h in baseline_hashes.items():assert sha(path)==h,'Changed protected artifact: '+path
    refs={};atts={};originals={};packet={}
    for n in (1,2,3):
        folder=F/f'packet_{n}'
        for name,manifest in [('reference.json','FROZEN.json'),('alias_attestations.json','ALIASES_FROZEN.json')]:assert sha(folder/name)==read(folder/manifest)['sha256']
        for r in read(folder/'records.json'):originals[r['cuma_index']]=r;packet[r['cuma_index']]=n
        refs.update({r['cuma_index']:r for r in read(folder/'reference.json')})
        atts.update({(r['cuma_index'],r['alias_position']):r for r in read(folder/'alias_attestations.json')})
    before={r['cuma_index']:r for r in read(F/'comparison.json')}
    old_metrics=read(F/'metrics.json')
    db=sqlite3.connect(run.resolve().as_uri()+'/candidates.sqlite?mode=ro',uri=True)
    reg=sqlite3.connect((run/'registry.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    output=[];alias_counts=Counter();alias_rows=[];groups=defaultdict(list)
    for i,name,aliases,status,reason,raw in db.execute('SELECT * FROM candidate ORDER BY cuma_index'):
        ref=refs[i];ev=json.loads(raw);substance=reg.execute('SELECT substance_id FROM substance_reconciliation WHERE cuma_index=?',(i,)).fetchone()[0]
        structure=reg.execute("SELECT structure_value FROM substance_structure WHERE substance_id=? AND structure_type='SMILES' ORDER BY structure_value",(substance,)).fetchone() if substance else None
        structure=structure[0] if structure else None
        verdict=None
        if status=='EXACT':
            if ref['expected_status']=='EXACT':verdict='VERIFIED_CORRECT' if same(structure,ref['expected_smiles']) else 'CONFIRMED_INCORRECT'
            elif ref['expected_status']=='UNRESOLVED':verdict='UNVERIFIED'
            else:verdict='CONFIRMED_INCORRECT'
            groups[substance].append(i)
        categories=ev.get('form',{}).get('categories',[]) if ev.get('form') else ev.get('decision',{}).get('form',{}).get('categories',[])
        row=dict(cuma_index=i,name=name,expected_status=ref['expected_status'],expected_smiles=ref.get('expected_smiles'),before_status=before[i]['predicted_status'],after_status=status,before_verdict=before[i]['exact_verdict'],after_verdict=verdict,substance_id=substance,smiles=structure,reason=reason,categories=categories,reference_reason=ref['reason'],packet=packet[i])
        row['validated_gain']=verdict=='VERIFIED_CORRECT' and before[i]['predicted_status']!='EXACT'
        row['validated_loss']=before[i]['exact_verdict']=='VERIFIED_CORRECT' and verdict!='VERIFIED_CORRECT'
        output.append(row)
        byalias=defaultdict(list)
        for j in ref['alias_judgments']:byalias[j['alias']].append(j)
        seen=Counter();source_aliases=originals[i]['aliases']
        for a in ev.get('alias_decisions',[]):
            alias=a['alias'];pos=[p for p,v in enumerate(source_aliases) if v==alias][seen[alias]];j=byalias[alias][seen[alias]];seen[alias]+=1
            if not a['accepted']:continue
            assert reg.execute('SELECT 1 FROM substance_alias WHERE substance_id=? AND alias=?',(substance,alias)).fetchone()
            att=atts[(i,pos)]['attestation_status'];ss=j['judgment']=='SAME' and att=='CORROBORATED_SAME';dd=j['judgment']=='DIFFERENT' and att=='CORROBORATED_DIFFERENT'
            if ss and verdict=='VERIFIED_CORRECT':av='VERIFIED_CORRECT'
            elif dd and verdict=='VERIFIED_CORRECT' or ss and verdict=='CONFIRMED_INCORRECT' and ref['expected_status']=='EXACT':av='CONFIRMED_INCORRECT'
            else:av='UNVERIFIED'
            alias_counts[av]+=1;alias_rows.append(dict(cuma_index=i,alias=alias,verdict=av,attestation=att,reference_judgment=j['judgment']))
    pairs=[];assessed=unknown=0
    for sid,ids in groups.items():
        for a,b in combinations(ids,2):
            if refs[a]['expected_status']==refs[b]['expected_status']=='EXACT':
                assessed+=1
                if not same(refs[a]['expected_smiles'],refs[b]['expected_smiles']):pairs.append(dict(substance_id=sid,cuma_indices=[a,b]))
            else:unknown+=1
    statuses=Counter(r['after_status'] for r in output);v=Counter(r['after_verdict'] for r in output if r['after_status']=='EXACT')
    ac=alias_counts['VERIFIED_CORRECT'];aw=alias_counts['CONFIRMED_INCORRECT'];au=alias_counts['UNVERIFIED'];c=v['VERIFIED_CORRECT'];bad=v['CONFIRMED_INCORRECT'];u=v['UNVERIFIED']
    gains=[r for r in output if r['validated_gain']];losses=[r for r in output if r['validated_loss']]
    forms={form:len({r['substance_id'] for r in gains if form in r['categories']}) for form in ['stereo','isotope','protonation_charge','salt','hydrate','solvate','tautomer']}
    old_ids={r.get('substance_id') for r in before.values() if r.get('substance_id')}
    minted=[r for r in output if r['substance_id'] and r['substance_id'] not in old_ids]
    metrics=dict(records=len(output),statuses=dict(statuses),automatic_exact=dict(admissions=c+bad+u,verified_correct=c,confirmed_incorrect=bad,unverified=u,precision_adjudicable=ratio(c,c+bad),confirmed_correct_lower_bound=ratio(c,c+bad+u)),alias_promotion=dict(occurrences=ac+aw+au,verified_correct=ac,confirmed_incorrect=aw,unverified=au,precision_adjudicable=ratio(ac,ac+aw),confirmed_correct_lower_bound=ratio(ac,ac+aw+au)),false_merges=dict(confirmed_pairs=len(pairs),assessed_pairs=assessed,unassessed_pairs=unknown,rate=ratio(len(pairs),assessed)),abstention_rate=ratio(statuses['UNRESOLVED'],len(output)),public_unresolved_rate=ratio(len(output)-statuses['EXACT'],len(output)),outcome_agreement=ratio(sum(r['after_status']==r['expected_status'] for r in output),len(output)),validated_exact_records_gained=len(gains),validated_exact_identities_gained=len({r['substance_id'] for r in gains}),validated_exact_records_lost=len(losses),net_validated_exact_records=len(gains)-len(losses),gained_identity_form_counts_nonexclusive=forms)
    metrics['new_substances_by_form_nonexclusive']={form:len({r['substance_id'] for r in minted if form in r['categories']}) for form in forms}
    metrics['new_substances_created']=len({r['substance_id'] for r in minted})
    integrity={'foreign_key_violations':len(reg.execute('PRAGMA foreign_key_check').fetchall()),'sqlite_integrity':reg.execute('PRAGMA integrity_check').fetchone()[0]}
    for table in ['substance_identity','substance_alias','substance_identifier','substance_structure','substance_reconciliation']:integrity[table+'_rows']=reg.execute('SELECT count(*) FROM '+table).fetchone()[0]
    assert integrity['foreign_key_violations']==0 and integrity['sqlite_integrity']=='ok'
    reg.close();db.close();assert len(output)==300
    manifest=dict(scored_at_utc=datetime.now(timezone.utc).isoformat(),prediction_directory=str(run.resolve()),prediction_database_hashes={name:sha(run/name) for name in ['registry.sqlite','candidates.sqlite']},protected_hashes_unchanged=True,code_hashes={p.name:sha(p) for p in ROOT.glob('*.py')},schema_sha256=sha(ROOT/'schema.sql'))
    for name,data in [('after_metrics.json',metrics),('before_metrics.json',old_metrics),('comparison.json',output),('alias_comparison.json',alias_rows),('false_merges.json',pairs),('integrity.json',integrity),('score_manifest.json',manifest)]:
        (W/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(metrics,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,default=W/'run');args=p.parse_args();score(args.run)
