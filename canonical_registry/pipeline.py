import argparse
import ast
from collections import Counter,defaultdict
import json
from pathlib import Path
import sqlite3
import time
import openpyxl
from rdkit import rdBase
from chemistry import describe,exact_key,normalize_name,related,comparison_views
from providers import Bridge,PubChem,ROOT
from policy import scope,eligible,reconcile

def ingest(path):
    w=openpyxl.load_workbook(path,read_only=True,data_only=True)
    s=w.active; rows=iter(s.values)
    if next(rows)[:3]!=('No.','display_name_en','alias_list_en'): raise ValueError('Unexpected workbook columns')
    seen=set()
    for row in rows:
        if all(x is None for x in row): continue
        i,name,raw=row[:3]
        if not isinstance(i,int) or i in seen: raise ValueError('Invalid/duplicate CUMA index: '+str(i))
        seen.add(i); error=None
        try:
            aliases=ast.literal_eval(raw) if raw else []
            if not isinstance(aliases,list) or not all(isinstance(a,str) for a in aliases): raise ValueError('Alias list must contain strings')
        except Exception as e: aliases=[]; error=str(e)
        yield dict(cuma_index=i,name=name,aliases=aliases,input_error=error,raw_alias_cell=raw if error else None)
    w.close()

def local_claim(name,bridge,cache):
    if not isinstance(name,str) or not name.strip(): return dict(status='INVALID',query=name)
    if name in cache: return cache[name]
    q=normalize_name(name)
    if scope(q): out=dict(status='OUT_OF_SCOPE',query=name)
    elif len(q)>250: out=dict(status='UNRESOLVED',query=name,reason='Name length budget')
    else:
        out=bridge.opsin(q); out['original']=name
        if out['status']=='SUCCESS':
            try: out['structure']=describe(out['smiles'])
            except Exception as e: out['status']='INVALID'; out['diagnostic']=str(e)
    cache[name]=out
    return out

def analyze(args):
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(out/'candidates.sqlite')
    db.execute('CREATE TABLE IF NOT EXISTS candidate(cuma_index INTEGER PRIMARY KEY,name TEXT,aliases TEXT,status TEXT,diagnostic TEXT,evidence_json TEXT)')
    done={r[0] for r in db.execute('SELECT cuma_index FROM candidate')}
    bridge=Bridge(); cache={}; start=time.time()
    try:
        for n,row in enumerate(ingest(args.input),1):
            if row['cuma_index'] in done: continue
            claims=[local_claim(v,bridge,cache) for v in [row['name']]+row['aliases']]
            status='INVALID' if row['input_error'] or not isinstance(row['name'],str) or not row['name'].strip() else scope(row['name']) or 'UNRESOLVED'
            evidence={'claims':claims,'input_error':row['input_error']}
            if row['input_error']: evidence['raw_alias_cell']=row['raw_alias_cell']
            db.execute('INSERT INTO candidate VALUES(?,?,?,?,?,?)',(row['cuma_index'],row['name'],json.dumps(row['aliases'],ensure_ascii=False),status,'Local evidence collected',json.dumps(evidence,ensure_ascii=False)))
            if n%250==0:
                db.commit(); print(json.dumps({'processed':n,'unique_claims':len(cache),'seconds':round(time.time()-start)}),flush=True)
        db.commit()
    finally: bridge.close(); db.close()

def build(args):
    from providers import ChEBI,GSRS
    from comptox import CompTox
    from resolver import Resolver
    from registry_builder import populate
    out=Path(args.output);dest=out/'registry.sqlite';staging=out/'registry.building.sqlite'
    if dest.exists() or staging.exists():raise FileExistsError('Registry snapshot already exists; select a fresh output directory')
    db=sqlite3.connect(out/'candidates.sqlite');bridge=Bridge()
    pub=PubChem(out/'http_cache',args.budget,args.offline)
    chebi=ChEBI(out/'chebi_cache',getattr(args,'chebi_budget',500),args.offline)
    gsrs=GSRS(out/'gsrs_cache',getattr(args,'gsrs_budget',200),args.offline)
    comptox=CompTox(out/'comptox_cache',getattr(args,'comptox_budget',20),args.offline)
    engine=Resolver(bridge,pub,chebi,getattr(args,'evidence_file',None),gsrs=gsrs,comptox=comptox)
    accepted=[];stats=Counter();reasons=Counter();held=promoted=0
    rows=list(db.execute('SELECT * FROM candidate ORDER BY cuma_index'))
    try:
        for n,(i,name,aliases,old_status,diagnostic,raw) in enumerate(rows,1):
            old=json.loads(raw);alias_list=json.loads(aliases)
            for claim in old.get('claims',[]):
                if isinstance(claim.get('original'),str):engine.claim_cache[claim['original']]=claim
            if old.get('input_error'):
                result=dict(status='INVALID',reason_codes=['MALFORMED_SOURCE_ALIASES'],evidence=old)
            else:result=engine.evaluate(name,alias_list)
            ev=result['evidence'];status=result['status'];reason=';'.join(result['reason_codes'])
            if not ev.get('alias_decisions'):
                ev['alias_decisions']=[dict(alias=a,accepted=False,reason='SUBJECT_NOT_ADMITTED') for a in alias_list]
            good=[a['alias'] for a in ev['alias_decisions'] if a['accepted']]
            promoted+=len(good);held+=len(alias_list)-len(good)
            ev['decision']={k:v for k,v in result.items() if k!='evidence'}
            if status=='AUTO_ACCEPT':
                accepted.append(dict(i=i,name=name,d=result['structure'],aliases=good,external={'rows':result['validated_rows']}));status='EXACT'
            stats[status]+=1;reasons[reason]+=1
            db.execute('UPDATE candidate SET status=?,diagnostic=?,evidence_json=? WHERE cuma_index=?',(status,reason,json.dumps(ev,ensure_ascii=False),i))
            db.commit()
            if n%10==0:print(json.dumps({'processed':n,'total':len(rows),'statuses':dict(stats),'pubchem_requests':pub.calls,'chebi_requests':chebi.calls}),flush=True)
        reg=sqlite3.connect(staging);reg.executescript((ROOT/'schema.sql').read_text())
        result=populate(reg,accepted,list(db.execute('SELECT cuma_index,status,diagnostic FROM candidate')),getattr(args,'base_registry',ROOT/'output/registry.sqlite'))
        for i,reason in result['blocked'].items():
            db.execute('UPDATE candidate SET status=?,diagnostic=? WHERE cuma_index=?',('UNRESOLVED',reason,i));stats['EXACT']-=1;stats['UNRESOLVED']+=1
        reg.commit();db.commit()
        summary=dict(total_cuma_records=len(rows),statuses=dict(stats),canonical_substances=result['canonical_substances'],new_substances=result['new_substances'],reused_substances=result['reused_substances'],multi_cuma_exact_clusters=result['multi_cuma_exact_clusters'],alias_claims_accepted=promoted,alias_claims_held=held,stored_aliases=reg.execute('SELECT count(*) FROM substance_alias').fetchone()[0],principal_failure_reasons=dict(reasons),pubchem_requests=pub.calls,chebi_requests=chebi.calls,rdkit_version=rdBase.rdkitVersion)
        summary['gsrs_requests']=gsrs.calls
        summary['comptox_requests']=comptox.calls
        (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        reg.close();staging.rename(dest);print(json.dumps(summary,indent=2))
    finally:bridge.close();db.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('stage',choices=['analyze','build']); p.add_argument('--input',default=str(ROOT.parent.parent/'cuma/CUMA v1 (ENG Only).xlsx')); p.add_argument('--output',default=str(ROOT/'output')); p.add_argument('--budget',type=int,default=120); p.add_argument('--chebi-budget',type=int,default=500); p.add_argument('--gsrs-budget',type=int,default=200); p.add_argument('--base-registry',default=str(ROOT/'output/registry.sqlite')); p.add_argument('--evidence-file'); p.add_argument('--offline',action='store_true'); args=p.parse_args()
    (analyze if args.stage=='analyze' else build)(args)
