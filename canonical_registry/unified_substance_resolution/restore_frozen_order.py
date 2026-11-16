"""Restore accidental replays only when reconstructed bytes match recorded SHA256.
No expected label, comparison value or source evidence is changed.
"""
import hashlib,itertools,json,time,copy
from pathlib import Path
B=Path(__file__).resolve().parent.parent;H=Path(__file__).resolve().parent
protected=json.loads((H/'evaluation/protected.json').read_text())['files']
def restore(kind):
 name=kind+'_heldout_results.json';p=B/'canonical_registry_matching/evaluation'/name;raw=p.read_bytes();obj=json.loads(raw);wanted=protected[str(p.resolve())]
 pair=obj['cases'][9]['result']['source_identity']['source_reconciliation']['pairwise_source_comparisons'];dims=[x['dimension'] for x in pair];assert len(dims)==9
 modified=copy.deepcopy(obj);modified['cases'][9]['result']['source_identity']['source_reconciliation']['pairwise_source_comparisons']='__ORDER_SLOT__'
 nl=b'\r\n' if b'\r\n' in raw else b'\n';template=(json.dumps(modified,indent=2,ensure_ascii=False)+'\n').encode().replace(b'\n',nl);token=b'"__ORDER_SLOT__"';prefix,suffix=template.split(token)
 # All other variable lists in this heldout case have singleton contradictions.
 baseindent=len(prefix.rsplit(b'\n',1)[1])-len(prefix.rsplit(b'\n',1)[1].lstrip())
 blocks=[((' '*(baseindent+2))+json.dumps(x,indent=2,ensure_ascii=False).replace('\n','\n'+' '*(baseindent+2))).encode().replace(b'\n',nl) for x in pair]
 start=b'['+nl;end=nl+b' '*baseindent+b']';join=b','+nl
 assert prefix+start+join.join(blocks)+end+suffix==raw
 initial=hashlib.sha256(prefix);t=time.monotonic()
 for perm in itertools.permutations(range(9)):
  middle=start+join.join(blocks[i] for i in perm)+end
  trial=initial.copy();trial.update(middle);trial.update(suffix)
  if trial.hexdigest()==wanted:
   restored=prefix+middle+suffix;assert hashlib.sha256(restored).hexdigest()==wanted
   p.write_bytes(restored);order=[dims[i] for i in perm];print(kind,'restored exact heldout bytes in',round(time.monotonic()-t,2),'seconds',flush=True)
   # Restore source-source array ordering in the development artifact using
   # this same original process's set iteration order.
   q=B/'canonical_registry_matching/evaluation'/(kind+'_development_results.json');data=json.loads(q.read_bytes());rank={d:i for i,d in enumerate(order)}
   def reorder(x):
    if isinstance(x,dict):
     for v in x.values():reorder(v)
    elif isinstance(x,list):
     for v in x:reorder(v)
     i=0
     while i<len(x):
      v=x[i]
      if not isinstance(v,dict) or 'dimension' not in v or not ('left' in v or v.get('basis')=='ESTABLISHED_SOURCE_SOURCE_CONTRADICTION'):i+=1;continue
      key=(v.get('left'),v.get('right'),v.get('evidence_id'),v.get('other_evidence_id'),v.get('basis'));j=i+1
      while j<len(x) and isinstance(x[j],dict) and 'dimension' in x[j] and (x[j].get('left'),x[j].get('right'),x[j].get('evidence_id'),x[j].get('other_evidence_id'),x[j].get('basis'))==key:j+=1
      x[i:j]=sorted(x[i:j],key=lambda v:rank[v['dimension']]);i=j
   reorder(data);encoded=(json.dumps(data,indent=2,ensure_ascii=False)+'\n').encode().replace(b'\n',nl)
   assert hashlib.sha256(encoded).hexdigest()==protected[str(q.resolve())], 'Development reconstruction did not match original SHA'
   q.write_bytes(encoded);return order
 raise RuntimeError('No dimension ordering matched recorded original SHA')
if __name__=='__main__':
 receipt={k:restore(k) for k in ('baseline','corrected')};(H/'evaluation/historical_restoration.json').write_text(json.dumps({'restored_original_sha256':True,'reason':'Accidental regression output redirection; changes were Python set iteration ordering only, no chemical outcome or evidence differences.','original_dimension_orders':receipt},indent=2)+'\n')
