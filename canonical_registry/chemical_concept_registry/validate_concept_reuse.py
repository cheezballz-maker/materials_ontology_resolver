"""Separate warehouse observations, derived serializations and synthetic controls."""
import json
import sqlite3
import uuid
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from rdkit import Chem, RDLogger
from constraints import compare_proposals, parse, molecular, ProposalError
from registry import FIXTURES, initialize, sha
from unified_chemical import UnifiedChemicalResolver
from validate_unified_v11 import H, P, PILOT, BASELINE, TrustedWarehouseAdapter, Bridge, read


def main():
    RDLogger.DisableLog('rdApp.*')
    packets = {p['source_record_id']:p for p in map(json.loads,(P/'sampled_records.jsonl').read_text(encoding='utf8').splitlines())}
    baseline=read(BASELINE)
    original = baseline['records']
    guards={**baseline['protected_hashes_after'],baseline['fixture_database']:sha(Path(baseline['fixture_database']))}
    assert guards=={p:sha(Path(p)) for p in guards}
    indexes = defaultdict(list)
    for sid, packet in packets.items():
        raw = packet['record']
        try:
            text=raw.get('isometric_smiles') or raw.get('jchem_smiles')
            mol=parse(text)
            if any(str(x.specified)!='Specified' for x in Chem.FindPotentialStereo(mol)):
                # Only a candidate screen. Same-constitution retrieval is not a reuse decision.
                indexes[Chem.MolToSmiles(mol,isomericSmiles=False)].append((sid,text))
        except (ValueError, RuntimeError):
            continue
    independent=[]
    fixture=initialize(FIXTURES/('reuse_validation_'+uuid.uuid4().hex+'.sqlite'))
    bridge=Bridge(timeout=5)
    adapter=TrustedWarehouseAdapter(batch_file=P/'sampled_records.json',expected_sha256=read(P/'sampling_manifest.json')['source_json_sha256'])
    router=UnifiedChemicalResolver(fixture,PILOT,name_adapter=bridge)
    def proposal(smiles):
        return {'kind':'molecular','smiles':smiles}
    def compact(r):
        return {k:r[k] for k in ('outcome','concept_id','diagnostics','interpretation','concept_comparisons','elapsed_seconds')}
    try:
        for group in indexes.values():
            for i,(a,x) in enumerate(group):
                for b,y in group[i+1:]:
                    rel=compare_proposals(proposal(x),proposal(y))
                    entry=dict(source_ids=[a,b],graphs=[x,y],comparison=rel,provenance_independence='UNVERIFIED')
                    if rel=='EQUIVALENT_CONCEPT':
                        first=router.resolve(packets[a],source_adapter=adapter,request_key='observed:'+a)
                        second=router.resolve(packets[b],source_adapter=adapter,request_key='observed:'+b)
                        entry['results']=[compact(first),compact(second)]
                        entry['same_id']=bool(first['concept_id'] and first['concept_id']==second['concept_id'])
                    independent.append(entry)
        alternatives=[]
        anchors=[r for r in original if r['outcome']=='CHEMICAL_CONCEPT_CREATED']
        for row in anchors[:6]:
            sid=row['source_id']
            a=router.resolve(packets[sid],source_adapter=adapter,request_key='anchor:'+sid)
            assert a['concept_id'], a['diagnostics']
            smiles=a['interpretation']['smiles']
            mol=parse(smiles)
            alt=next(t for i in range(mol.GetNumAtoms())
                     if (t:=Chem.MolToSmiles(mol,canonical=False,rootedAtAtom=i,isomericSmiles=True))!=smiles)
            b=router.resolve({'smiles':alt},request_key='derived:'+sid)
            rel=compare_proposals(proposal(smiles),proposal(alt))
            assert rel=='EQUIVALENT_CONCEPT' and b['outcome']=='CHEMICAL_CONCEPT_REUSED' and a['concept_id']==b['concept_id']
            alternatives.append(dict(source_id=sid,graph=smiles,alternative=alt,comparison=rel,results=[compact(a),compact(b)]))
    finally:
        bridge.close()
    synthetic=[]
    for label,a,b,expected in [
        ('opposite_known_stereo','C[C@H](O)C(O)CC','C[C@@H](O)C(O)CC','DISTINCT_CONCEPT'),
        ('open_vs_narrower','CC(O)C(O)CC','C[C@H](O)C(O)CC','BROADER_CONCEPT'),
        ('similar_named_constitutional_isomers','CCC(O)CCC','CC(O)CCCC','DISTINCT_CONCEPT'),
        ('unsupported_comparison','CC(O)F','CC(O)F.Cl','CONCEPT_COMPARISON_UNRESOLVED'),
    ]:
        rel=compare_proposals(proposal(a),proposal(b))
        assert rel==expected,(label,rel)
        synthetic.append(dict(case=label,left=a,right=b,comparison=rel))
    a=fixture.create_or_reuse(proposal('CCC(O)CCC'),'shared display label','label-a')
    b=fixture.create_or_reuse(proposal('CC(O)CCCC'),'shared display label','label-b')
    assert a['concept_id']!=b['concept_id']
    synthetic.append(dict(case='same_display_name_distinct_meanings',ids=[a['concept_id'],b['concept_id']]))
    with closing(sqlite3.connect(fixture.path.as_uri()+'?mode=ro',uri=True)) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    after={p:sha(Path(p)) for p in guards}
    assert after==guards
    output=dict(screened_records=len(packets),open_records=sum(map(len,indexes.values())),
                observed_candidate_pairs=independent,generated_alternatives=alternatives,
                synthetic_controls=synthetic,fixture_database=str(fixture.path),
                hashes_before=guards,hashes_after=after)
    (H/'concept_reuse_validation_v11.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print('Observed candidate pairs:',len(independent),'derived reuses:',len(alternatives),'synthetic:',len(synthetic))


if __name__=='__main__':
    main()
