"""Add alternate-form comparisons to the single candidate workspace, never the registry."""
import json
import sqlite3
from chemistry import describe,related,comparison_views
from providers import ROOT

def run():
    db=sqlite3.connect(ROOT/'output/candidates.sqlite')
    n=0
    for i,raw in db.execute("SELECT cuma_index,evidence_json FROM candidate WHERE status='CONFLICT'").fetchall():
        ev=json.loads(raw); local=ev['claims'][0].get('structure'); comparisons=[]
        for row in ev.get('external',{}).get('rows',[]):
            try:
                other=describe(row.get('SMILES') or row.get('IsomericSMILES') or '')
                comparisons.append(dict(provider='PubChem',cid=row.get('CID'),relation=related(local,other),local_views=comparison_views(local),provider_views=comparison_views(other)))
            except Exception as e: comparisons.append(dict(error=str(e)))
        ev['provider_comparisons']=comparisons
        db.execute('UPDATE candidate SET evidence_json=? WHERE cuma_index=?',(json.dumps(ev,ensure_ascii=False),i)); n+=1
    db.commit(); db.close(); print('Annotated',n,'conflicts in candidate evidence only')
    db=sqlite3.connect(ROOT/'output/candidates.sqlite')
    for i,raw in db.execute("SELECT cuma_index,evidence_json FROM candidate WHERE status='EXACT'").fetchall():
        ev=json.loads(raw); local=ev['claims'][0]['structure']
        for decision,claim in zip(ev['alias_decisions'],ev['claims'][1:]):
            if decision.get('relation') and claim.get('structure'):
                decision['relation']=related(local,claim['structure'])
        db.execute('UPDATE candidate SET evidence_json=? WHERE cuma_index=?',(json.dumps(ev,ensure_ascii=False),i))
    db.commit(); db.close()

if __name__=='__main__': run()
