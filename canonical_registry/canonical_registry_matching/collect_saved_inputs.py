"""Recover original saved PubChem payload rows, never copy registry graphs.

These are intentionally source-dependent consistency demonstrations. The CID
intersection selects records; original provider fields supply their structures.
"""
import hashlib,json,sqlite3
from pathlib import Path
import bootstrap
from registry_identity_adapter import RegistrySnapshot,digest
H=Path(__file__).resolve().parent;B=H.parent
def main():
 registry=RegistrySnapshot(B/'output/registry.sqlite');wanted={v for r in registry.entries.values() for t,v in r['identifiers'] if t=='PubChemCID'}
 ids=sorted({i for r in registry.entries.values() for i in r['candidate'].provenance['cuma_indices']})
 path=B/'output/candidates.sqlite';sha=digest(path);db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True);out={};available={}
 try:
  for index in ids:
   row=db.execute('SELECT evidence_json FROM candidate WHERE cuma_index=?',(index,)).fetchone()
   if not row:continue
   ev=json.loads(row[0]);providers=[('external',ev['external'])] if ev.get('external') else []
   providers += [('providers['+str(i)+']',p) for i,p in enumerate(ev.get('providers',[])) if p.get('provider')=='PubChem']
   for pointer,p in providers:
    if p.get('provider','PubChem')!='PubChem':continue
    for i,r in enumerate(p.get('rows',[])):
     cid=str(r.get('CID',''))
     if cid not in wanted or not r.get('SMILES',r.get('IsomericSMILES')):continue
     origin=dict(payload_path=str(path.resolve()),payload_sha256=sha,sqlite_query='SELECT evidence_json FROM candidate WHERE cuma_index=?',sqlite_parameter=index,record_pointer='$.'+pointer+'.rows['+str(i)+']',url=p.get('url') or 'Saved original PubChem response embedded in candidate evidence',retrieved_at=p.get('retrieved_at'),lineage_roots=['PubChem:COMPOUND:'+cid],role='SAVED_PROVIDER_RECORD_SAME_UPSTREAM_AS_REGISTRY_NOT_INDEPENDENT_VALIDATION',original_row_sha256=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest())
     available.setdefault(cid,[]).append(origin)
     if cid not in out:out[cid]=dict(record_id=cid,original_record=r,provenance=origin)
 finally:db.close()
 assert sha==digest(path);registry.assert_unchanged()
 for cid in out:out[cid]['all_saved_occurrences']=available[cid]
 result=dict(records=[out[cid] for cid in sorted(out,key=int)],requested_registry_pubchem_records=len(wanted),original_saved_records_found=len(out),missing_record_ids=sorted(wanted-set(out)),selection='Intersection on stored PubChem CID; first deterministic saved provider response per CID, without inspecting matching results. No registry structure copied.',evidence_independence='KNOWN_DEPENDENT_IF_REGISTRY_SHARES_THIS_PUBCHEM_CID',provider_requests=0)
 (H/'evaluation/saved_input_records.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8');print(result['original_saved_records_found'],'original provider records;',len(wanted-set(out)),'missing')
if __name__=='__main__':main()
