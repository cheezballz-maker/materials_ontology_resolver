"""Read-only registry/evidence verification for legacy and form-aware snapshots."""
import argparse,json,sqlite3
from pathlib import Path
from providers import ROOT
from chemistry import describe
from policy import decision,eligible,validate_external
from identity_comparator import compare

def run(out=ROOT/'output'):
    out=Path(out)
    r=sqlite3.connect((out/'registry.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    c=sqlite3.connect((out/'candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    counts={}
    try:
        assert r.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not r.execute('PRAGMA foreign_key_check').fetchall()
        assert len(r.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())==5
        assert r.execute('SELECT count(*) FROM substance_reconciliation').fetchone()[0]==c.execute('SELECT count(*) FROM candidate').fetchone()[0]
        graphs={};seen=[];checked=0
        for sid,value in r.execute("SELECT substance_id,structure_value FROM substance_structure WHERE structure_type='SMILES'"):
            d=describe(value);graphs.setdefault(sid,[]).append(d)
            assert sid.startswith('SUB_') and len(sid)==12
            ids=set(r.execute('SELECT identifier_type,identifier_value FROM substance_identifier WHERE substance_id=?',(sid,)))
            assert ('InChI',d['inchi']) in ids and ('InChIKey',d['inchikey']) in ids
            assert all(other==sid or compare(d,g)['assessment']!='EXACT' for other,g in seen)
            seen.append((sid,d))
        for i,sid in r.execute("SELECT cuma_index,substance_id FROM substance_reconciliation WHERE resolution_status='EXACT'"):
            name,status,raw=c.execute('SELECT name,status,evidence_json FROM candidate WHERE cuma_index=?',(i,)).fetchone();ev=json.loads(raw)
            d=ev.get('decision',{}).get('structure') or ev['claims'][0]['structure']
            assert status=='EXACT' and all(compare(d,g)['assessment']=='EXACT' for g in graphs[sid])
            if ev.get('retrieval',{}).get('version')==1:
                from evidence_retrieval import Acquisition
                acq=Acquisition(None,None);acq.results=ev['retrieval']['queries']
                acq.blocked_queries=ev['retrieval'].get('blocked_queries',[])
                external=acq.external(d)
                for item in ev.get('reviewed_evidence',[]):
                    for claim in item['claims']:
                        rd=describe(claim['smiles'])
                        external['rows'].append(dict(SMILES=rd['smiles'],InChI=rd['inchi'],InChIKey=rd['inchikey'],provider='Reviewed evidence',corroboration=False,url=claim['url'],source=claim['source']))
                assert external==ev['external'],i
                assertion=ev['decision'].get('form',{}).get('source_assertion')
                if ev['claims'][0]['status']!='SUCCESS':
                    support=ev.get('local_source_support')
                    if support:
                        original_aliases=json.loads(c.execute('SELECT aliases FROM candidate WHERE cuma_index=?',(i,)).fetchone()[0])
                        assert support['alias'] in original_aliases
                        assert support['claim']['original']==support['alias'] and support['claim']['status']=='SUCCESS'
                        assert compare(support['claim']['structure'],d)['assessment']=='EXACT' and eligible(d,support['alias'])
                        attestation=support['attestation'];v,error=validate_external(attestation)
                        assert not error and v and attestation['status']=='SUCCESS' and all(compare(x,d)['assessment']=='EXACT' for x,row in v)
                        assert attestation['retrieval_key']['value']==support['alias']
                    else:raise AssertionError('Incomplete source interpretation cannot be admitted')
            elif 'decision' in ev:
                providers=ev['providers'][:2]
                external={'rows':[row for p in providers for row in p.get('rows',[])], 'status':'INCOMPLETE' if any(p['status']=='INCOMPLETE' for p in providers) else 'SUCCESS'}
                assertion=ev['decision'].get('form',{}).get('source_assertion')
            else:external=ev['external'];assertion=None
            source_complete=bool((assertion or {}).get('explicit_structure') or ev.get('name_interpretation',{}).get('status')=='ESTABLISHED')
            assert decision(d,ev['official_inchi'],external,name,assertion,ev.get('source_name_profile'),source_complete)['status']=='AUTO_ACCEPT',(i,name)
            for a,claim in zip(ev['alias_decisions'],ev['claims'][1:]):
                if a['accepted']:
                    assert claim['status']=='SUCCESS' and compare(claim['structure'],d)['assessment']=='EXACT'
                    assert eligible(claim['structure'],a['alias'])
                    assert r.execute('SELECT 1 FROM substance_alias WHERE substance_id=? AND alias=?',(sid,a['alias'])).fetchone()
            checked+=1
        for sid,alias in r.execute('SELECT substance_id,alias FROM substance_alias'):
            supported=False
            for (i,) in r.execute('SELECT cuma_index FROM substance_reconciliation WHERE substance_id=?',(sid,)):
                name,raw=c.execute('SELECT name,evidence_json FROM candidate WHERE cuma_index=?',(i,)).fetchone()
                if alias==name or any(a['alias']==alias and a['accepted'] for a in json.loads(raw)['alias_decisions']):supported=True
            assert supported,(sid,alias)
        for table,cols in [('substance_identity','substance_id'),('substance_alias','substance_id,alias'),('substance_identifier','substance_id,identifier_type,identifier_value'),('substance_reconciliation','cuma_index')]:
            counts['duplicate_'+table]=r.execute('SELECT count(*) FROM (SELECT '+cols+',count(*) n FROM '+table+' GROUP BY '+cols+' HAVING count(*)>1)').fetchone()[0]
        for table in ['substance_alias','substance_identifier','substance_structure','substance_reconciliation']:
            counts['orphan_'+table]=r.execute('SELECT count(*) FROM '+table+' t LEFT JOIN substance_identity s ON t.substance_id=s.substance_id WHERE t.substance_id IS NOT NULL AND s.substance_id IS NULL').fetchone()[0]
        assert not any(counts.values())
        result=dict(result='PASS',sqlite_integrity='ok',foreign_keys='ok',persistent_tables=5,exact_reconciliations_revalidated=checked,canonical_graphs=len(graphs),alias_evidence='all stored aliases supported',counts=counts)
        (out/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
    finally:r.close();c.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'output');args=p.parse_args();run(args.output)
