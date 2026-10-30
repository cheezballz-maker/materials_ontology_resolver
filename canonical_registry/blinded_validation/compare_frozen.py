"""Read predictions only after ALL reference packets are frozen; never change inputs."""
import hashlib,json,random,sqlite3
from collections import Counter,defaultdict
from datetime import datetime,timezone
from itertools import combinations
from pathlib import Path
from rdkit import Chem,rdBase

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
STATUSES={'EXACT','UNRESOLVED','CONFLICT','OUT_OF_SCOPE','INVALID'}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def structure(s):
    if not isinstance(s,str) or not s or any(c.isspace() for c in s): raise ValueError('Invalid reference structure text')
    p=Chem.SmilesParserParams();p.parseName=False;p.allowCXSMILES=False
    m=Chem.MolFromSmiles(s,p)
    if m is None: raise ValueError('Invalid reference SMILES')
    return (Chem.MolToSmiles(m,canonical=True,isomericSmiles=True),Chem.MolToInchiKey(m))
def ratio(a,b): return a/b if b else None
def show(v): return 'N/A' if v is None else f'{v:.2%}'
def cell(v): return str(v).replace('|','/').replace('\n',' ')

def run():
    refs={};freezes=[];alias_attestations={};alias_freezes=[]
    # Nothing below this gate is allowed to inspect predictions.
    for n in (1,2,3):
        folder=ROOT/f'packet_{n}'
        f=read(folder/'FROZEN.json'); rows=read(folder/'reference.json'); source=read(folder/'records.json')
        assert sha(folder/'reference.json')==f['sha256'],f'Changed frozen packet {n}'
        assert f['record_count']==len(rows)==100
        assert {r['cuma_index'] for r in rows}=={r['cuma_index'] for r in source}
        originals={r['cuma_index']:r for r in source}
        af=read(folder/'ALIASES_FROZEN.json');attestations=read(folder/'alias_attestations.json')
        assert sha(folder/'alias_attestations.json')==af['sha256'],f'Changed alias supplement {n}'
        assert af['occurrence_count']==len(attestations)==sum(len(x['aliases']) for x in source)
        expected_positions={(x['cuma_index'],p) for x in source for p in range(len(x['aliases']))}
        actual_positions=set()
        for attestation in attestations:
            k=(attestation['cuma_index'],attestation['alias_position'])
            assert k not in actual_positions and k not in alias_attestations
            actual_positions.add(k)
            assert attestation['alias']==originals[k[0]]['aliases'][k[1]]
            assert attestation['attestation_status'] in {'CORROBORATED_SAME','CORROBORATED_DIFFERENT','INSUFFICIENT'}
            if attestation['attestation_status']!='INSUFFICIENT': assert attestation.get('evidence'),k
            alias_attestations[k]=attestation
        assert actual_positions==expected_positions
        for r in rows:
            i=r['cuma_index'];assert i not in refs
            assert r['expected_status'] in STATUSES
            assert r['preferred_name']==originals[i]['preferred_name']
            assert r.get('evidence') or r.get('reason'),i
            judgments=r.get('alias_judgments',[])
            assert Counter(x['alias'] for x in judgments)==Counter(originals[i]['aliases']),(i,'Incomplete alias judgments')
            assert all(x['judgment'] in {'SAME','DIFFERENT','UNRESOLVED'} for x in judgments)
            if r['expected_status']=='EXACT':
                key=structure(r['expected_smiles'])
                assert key[1]==r['expected_inchikey'],(i,'Reference structure/key mismatch')
                r['_reference_key']=key
            refs[i]=r
        freezes.append({'packet':n,**f})
        alias_freezes.append({'packet':n,**af})
    assert len(refs)==300
    reference_index=[]
    for i,ref in sorted(refs.items()):
        corroborated=[]
        for k,attestation in sorted(alias_attestations.items()):
            if k[0]==i and attestation['attestation_status']=='CORROBORATED_SAME' and ref['expected_status']=='EXACT' and any(j['alias']==attestation['alias'] and j['judgment']=='SAME' for j in ref['alias_judgments']):
                corroborated.append(attestation['alias'])
        reference_index.append({'cuma_index':i,'preferred_name':ref['preferred_name'],'expected_status':ref['expected_status'],'expected_smiles':ref.get('expected_smiles'),'expected_inchikey':ref.get('expected_inchikey'),'corroborated_same_aliases':corroborated,'reference_reason':ref.get('reason')})
    (ROOT/'reference_index.json').write_text(json.dumps(reference_index,ensure_ascii=False,indent=2),encoding='utf-8')
    sampling=read(ROOT/'steward/selection.json')['strata']
    prior=read(ROOT/'steward/source_hashes.json')
    for name,h in prior.items(): assert sha(BASE/'output'/name)==h,'Engine data changed before comparison: '+name
    opened=datetime.now(timezone.utc).isoformat()
    for freeze in freezes+alias_freezes:
        frozen_time=datetime.fromisoformat(freeze['frozen_at_utc'].replace('Z','+00:00'))
        assert frozen_time.tzinfo is not None and frozen_time<=datetime.fromisoformat(opened),'Invalid freeze chronology'
    c=sqlite3.connect((BASE/'output/candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    rdb=sqlite3.connect((BASE/'output/registry.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    records=[];alias_counts=Counter();alias_disagreements=[];held_supported_aliases=[];clusters=defaultdict(list)
    for i,ref in sorted(refs.items()):
        name,predicted,reason,raw=c.execute('SELECT name,status,diagnostic,evidence_json FROM candidate WHERE cuma_index=?',(i,)).fetchone()
        assert name==ref['preferred_name']
        sid=rdb.execute('SELECT substance_id FROM substance_reconciliation WHERE cuma_index=?',(i,)).fetchone()[0]
        ev=json.loads(raw);pred_smiles=None;verdict=None
        if predicted=='EXACT':
            pred_smiles=rdb.execute('SELECT structure_value FROM substance_structure WHERE substance_id=?',(sid,)).fetchone()[0]
            pred_key=structure(pred_smiles)
            if ref['expected_status']=='EXACT': verdict='VERIFIED_CORRECT' if pred_key==ref['_reference_key'] else 'CONFIRMED_INCORRECT'
            elif ref['expected_status']=='UNRESOLVED': verdict='UNVERIFIED'
            else: verdict='CONFIRMED_INCORRECT'
            clusters[sid].append(i)
        row={'cuma_index':i,'preferred_name':name,'stratum':sampling[str(i)],'expected_status':ref['expected_status'],'predicted_status':predicted,'expected_smiles':ref.get('expected_smiles'),'expected_inchikey':ref.get('expected_inchikey'),'predicted_smiles':pred_smiles,'substance_id':sid,'exact_verdict':verdict,'engine_reason':reason,'reference_reason':ref.get('reason'),'evidence':ref.get('evidence',[]),'source_dependence_notes':ref.get('source_dependence_notes'),'status_agrees':predicted==ref['expected_status']}
        row['independent_source_support']=ref.get('independent_source_support','unknown')
        row['reference_confidence']=ref.get('reference_confidence','unspecified')
        row['disagreement']=not row['status_agrees'] or verdict=='CONFIRMED_INCORRECT'
        if verdict=='UNVERIFIED': cause='Reference evidence insufficient to verify admission; not proof of a false identity.'
        elif verdict=='CONFIRMED_INCORRECT': cause='Automatic admission contradicts the frozen reference form, structure or scope.'
        elif predicted=='UNRESOLVED': cause='Engine abstention: '+reason
        elif predicted=='CONFLICT': cause='Engine evidence conflict: '+reason
        else: cause='Different source interpretation or scope judgment; see frozen evidence.'
        row['likely_cause']=cause
        records.append(row)
        byalias=defaultdict(list)
        for a in ref['alias_judgments']: byalias[a['alias']].append(a)
        positions=Counter()
        for a in ev.get('alias_decisions',[]):
            alias=a['alias'];j=byalias[alias][positions[alias]];positions[alias]+=1
            matching_attestations=[v for k,v in sorted(alias_attestations.items()) if k[0]==i and v['alias']==alias]
            attestation=matching_attestations[positions[alias]-1]
            assert attestation['alias']==alias
            supported_same=j['judgment']=='SAME' and attestation['attestation_status']=='CORROBORATED_SAME'
            supported_different=j['judgment']=='DIFFERENT' and attestation['attestation_status']=='CORROBORATED_DIFFERENT'
            if not a['accepted']:
                if verdict=='VERIFIED_CORRECT' and supported_same:
                    held_supported_aliases.append({'cuma_index':i,'preferred_name':name,'alias':alias,'reference_alias_judgment':j,'engine_substance_id':sid})
                continue
            assert sid and rdb.execute('SELECT 1 FROM substance_alias WHERE substance_id=? AND alias=?',(sid,alias)).fetchone(),(i,alias,'Promotion absent from registry')
            if supported_different and verdict=='VERIFIED_CORRECT': av='CONFIRMED_INCORRECT'
            elif supported_same and verdict=='CONFIRMED_INCORRECT' and ref['expected_status']=='EXACT': av='CONFIRMED_INCORRECT'
            elif supported_same and verdict=='VERIFIED_CORRECT': av='VERIFIED_CORRECT'
            else: av='UNVERIFIED'
            alias_counts[av]+=1
            if av!='VERIFIED_CORRECT': alias_disagreements.append({'cuma_index':i,'preferred_name':name,'alias':alias,'verdict':av,'reference_alias_judgment':j,'alias_attestation':attestation,'reference_status':ref['expected_status'],'engine_substance_id':sid})
    merges=[];assessed_pairs=0;unassessed_pairs=0;all_pairs=0
    for sid,ids in clusters.items():
        for a,b in combinations(ids,2):
            all_pairs+=1
            if refs[a]['expected_status']==refs[b]['expected_status']=='EXACT':
                assessed_pairs+=1
                if refs[a]['_reference_key']!=refs[b]['_reference_key']: merges.append({'substance_id':sid,'cuma_indices':[a,b],'reference_smiles':[refs[a]['expected_smiles'],refs[b]['expected_smiles']]})
            else: unassessed_pairs+=1
    expected=Counter(x['expected_status'] for x in records);predicted=Counter(x['predicted_status'] for x in records)
    admissions=Counter(x['exact_verdict'] for x in records if x['predicted_status']=='EXACT')
    correct=admissions['VERIFIED_CORRECT'];wrong=admissions['CONFIRMED_INCORRECT'];unknown=admissions['UNVERIFIED'];n=predicted['EXACT']
    ac=alias_counts['VERIFIED_CORRECT'];aw=alias_counts['CONFIRMED_INCORRECT'];au=alias_counts['UNVERIFIED'];an=ac+aw+au
    metrics={'sample_records':300,'expected_counts':{s:expected[s] for s in sorted(STATUSES)},'predicted_counts':{s:predicted[s] for s in sorted(STATUSES)},'automatic_exact':{'admissions':n,'verified_correct':correct,'confirmed_incorrect':wrong,'unverified':unknown,'precision_adjudicable':ratio(correct,correct+wrong),'confirmed_correct_lower_bound':ratio(correct,n),'precision_upper_bound':ratio(correct+unknown,n),'reference_verification_rate':ratio(correct+wrong,n)},'false_merges':{'confirmed_pairs':len(merges),'confirmed_clusters':len({x['substance_id'] for x in merges}),'adjudicable_coassigned_pairs':assessed_pairs,'unassessed_coassigned_pairs':unassessed_pairs,'all_coassigned_pairs':all_pairs,'rate_adjudicable_pairs':ratio(len(merges),assessed_pairs)},'alias_promotion':{'occurrences':an,'verified_correct':ac,'confirmed_incorrect':aw,'unverified':au,'precision_adjudicable':ratio(ac,ac+aw),'confirmed_correct_lower_bound':ratio(ac,an),'precision_upper_bound':ratio(ac+au,an)},'outcome_agreement':ratio(sum(x['status_agrees'] for x in records),300),'abstention_rate_unresolved':ratio(predicted['UNRESOLVED'],300),'non_admission_rate':1-ratio(n,300),'disagreement_records':sum(x['disagreement'] for x in records),'sampling_strata':dict(Counter(x['stratum'] for x in records))}
    metrics['reference_independent_source_support']=dict(Counter(str(x['independent_source_support']) for x in records))
    metrics['reference_confidence_counts']=dict(Counter(str(x['reference_confidence']) for x in records))
    metrics['verified_admissions_with_independent_source_support']=sum(x['exact_verdict']=='VERIFIED_CORRECT' and x['independent_source_support'] is True for x in records)
    metrics['alias_attestation_counts']=dict(Counter(x['attestation_status'] for x in alias_attestations.values()))
    rng=random.Random(20261028)
    good=[x for x in records if x['exact_verdict']=='VERIFIED_CORRECT'];rng.shuffle(good)
    abstention_groups=defaultdict(list)
    for x in records:
        if x['predicted_status']=='UNRESOLVED': abstention_groups[(x['stratum'],x['expected_status'])].append(x)
    for group in abstention_groups.values(): rng.shuffle(group)
    keys=list(abstention_groups);rng.shuffle(keys);abstentions=[]
    while len(abstentions)<20 and any(abstention_groups.values()):
        for k in keys:
            if abstention_groups[k]: abstentions.append(abstention_groups[k].pop())
            if len(abstentions)==20: break
    review={'exact_agreements':good[:20],'all_confirmed_false_positive_exact':[x for x in records if x['exact_verdict']=='CONFIRMED_INCORRECT'],'all_false_merges':merges,'representative_abstentions':abstentions,'unverified_exact_admissions':[x for x in records if x['exact_verdict']=='UNVERIFIED']}
    manifest={'predictions_opened_at_utc':opened,'reference_freezes':freezes,'alias_attestation_freezes':alias_freezes,'source_hashes_before':prior,'source_hashes_after':{name:sha(BASE/'output'/name) for name in prior},'rdkit_version':rdBase.rdkitVersion}
    manifest['validation_artifact_hashes']={name:sha(ROOT/name) for name in ('PROTOCOL.md','prepare_sample.py','compare_frozen.py','steward/selection.json','reference_index.json')}
    assert manifest['source_hashes_before']==manifest['source_hashes_after']
    for filename,data in [('comparison.json',records),('metrics.json',metrics),('spot_check_set.json',review),('alias_disagreements.json',alias_disagreements),('held_supported_aliases.json',held_supported_aliases),('comparison_manifest.json',manifest)]:
        (ROOT/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(metrics,indent=2))

if __name__=='__main__':run()
