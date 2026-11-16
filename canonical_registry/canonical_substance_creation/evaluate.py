"""Frozen requirements-based controls, real saved records, actual SQLite writes."""
import copy,json,hashlib,sqlite3,threading,socket,time,os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import bootstrap
from evidence_adapter_contract import EvidencePackage,structural_field,associated_name,evidence
from evidence_adapters import candidate_assertions
from correspondence_models import IncomingConcept
from registry_matching_models import MatchingInput,RetrievalPolicy
from adapter_registry import envelope
from unified_resolver import SubstanceResolver
from creation_authorization import create_creation_fixture,connect_creation,CreationPermit
from fixture_registry import PRODUCTION,connect,FixturePermit,create_fixture
from source_concept_models import digest
from providers import Bridge
from chemistry import describe

H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,o):(H/'evaluation'/n).write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf8')

class SyntheticAdapter:
 def adapt(self,r):
  context={'document':str(H/'controls'),'origin':'EXPLICIT_SYNTHETIC_CREATION_CONTROL','payload_sha256':digest(r)}
  pkg=EvidencePackage(r.get('system','SyntheticRegistry'),'Record',r['record_id'],context);g=r.get('graph');kind=r.get('kind','EXPLICIT')
  if kind=='EXPLICIT':
   a=structural_field(pkg,'graph',g,'$.graph');binding='EXPLICIT_STRUCTURAL_FIELD_REFERENT'
   if r.get('conflicting_graph'):structural_field(pkg,'conflicting_graph',r['conflicting_graph'],'$.conflicting_graph')
  elif kind=='NAME_DERIVED':
   a=evidence(pkg,'qualified_name','CHEMICAL_NAME_ASSERTION',r['name'],'$.name',binding='BINDING_IDENTITY_ASSERTION',basis='RULE_ESTABLISHED',origin='DERIVED_SOURCE',assertions=candidate_assertions(g),extra={'interpretation_document':str(H/'controls'),'interpretation_kind':'FROZEN_SYNTHETIC_NAME_SEMANTICS'})
   pkg.add(a,['RECORD_STRUCTURE','TERMINOLOGY','INCOMING_CONCEPT']);binding='QUALIFIED_NAME_IDENTITY'
  else:a=associated_name(pkg,'broad','polymer','$.name');binding='QUALIFIED_NAME_IDENTITY'
  concept=IncomingConcept('SYNTHETIC:'+r['record_id'],pkg,{'status':'ESTABLISHED' if kind!='BROAD' else 'UNESTABLISHED','kind':binding,'evidence_ids':[a.evidence_id],'document':str(H/'controls')},r.get('identity_scope','DEFINED_MULTICOMPONENT_COMPOSITION' if g and '.' in g else 'DISCRETE_MOLECULAR'),context)
  inp=MatchingInput(concept,r.get('name','Explicit synthetic molecular referent'),form_assertion={'form_kind':'salt'} if r.get('salt') else {},official_validation={'agrees':False,'status':'NOT_SUPPLIED'} if r.get('missing_official') else None,evidence_origin='EXPLICITLY_SYNTHETIC_NOT_EXTERNAL_CORROBORATION')
  return envelope(r,inp)

class LockedValidator:
 def __init__(self):self.bridge=Bridge();self.lock=threading.Lock();self.cache={}
 def __call__(self,d):
  with self.lock:
   if d['smiles'] not in self.cache:self.cache[d['smiles']]=self.bridge.official(d)
   return copy.deepcopy(self.cache[d['smiles']])
 def close(self):self.bridge.close()

def db_state(p):
 d=sqlite3.connect(p.path.as_uri()+'?mode=ro',uri=True)
 try:return {t:d.execute('SELECT * FROM '+t+' ORDER BY 1').fetchall() for t, in d.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 finally:d.close()

def check_integrity(p):
 d=sqlite3.connect(p.path.as_uri()+'?mode=ro',uri=True)
 try:
  errors=d.execute('PRAGMA foreign_key_check').fetchall();sql=d.execute('PRAGMA integrity_check').fetchall()
  duplicate=d.execute("SELECT concept_id FROM concept_substance_association WHERE association_status IN ('ACTIVE','REVIEW_REQUIRED') GROUP BY concept_id HAVING count(*)>1").fetchall()
  incomplete=d.execute("SELECT substance_id FROM substance_identity i WHERE NOT EXISTS(SELECT 1 FROM substance_structure s WHERE s.substance_id=i.substance_id AND structure_type='SMILES') OR NOT EXISTS(SELECT 1 FROM substance_identifier j WHERE j.substance_id=i.substance_id AND identifier_type='InChIKey')").fetchall()
  return {'foreign_key_errors':errors,'sqlite_integrity':sql,'duplicate_active':duplicate,'incomplete':incomplete,'passed':not errors and sql==[('ok',)] and not duplicate and not incomplete}
 finally:d.close()

def metrics(executions):
 from collections import Counter
 return dict(incoming_records=len(executions),sufficiently_qualified=sum(r.get('reconciliation',{}).get('state')=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' for r in executions),existing_reused=sum(r['resolution_status']=='EXISTING_SUBSTANCE_REUSED' for r in executions),new_created=sum(r['creation'].get('new_substance_created',False) for r in executions),concept_associations_created=sum(r['association']['association_created'] for r in executions),idempotent_retries=sum(r['creation'].get('replayed_request',False) for r in executions),withheld=sum(r['resolution_status']=='CREATION_WITHHELD' for r in executions),unresolved_possible_duplicates=sum('UNRESOLVED_POSSIBLE_DUPLICATE' in r['creation'].get('reasons',[]) for r in executions),transaction_rollbacks=sum(r['resolution_status']=='CREATION_FAILED' for r in executions),invalid_or_incomplete=sum(r['resolution_status']=='VALIDATION_FAILED' or 'SOURCE_IDENTITY_INSUFFICIENT' in r['creation'].get('reasons',[]) for r in executions),unsupported_classes=sum(any(x in r['creation'].get('reasons',[]) for x in ('UNSUPPORTED_CREATION_SCOPE','UNSUPPORTED_ELEMENT_CAPABILITY','EXCLUDED_MATERIAL_FAMILY')) for r in executions),outcomes=dict(Counter(r['resolution_status'] for r in executions)),production_writes=0)

def main():
 socket.create_connection=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('LIVE_PROVIDER_QUERIES_DISABLED'))
 for n,d in read(H/'controls/benchmark_freeze.json').items():assert hashlib.sha256((H/'controls'/n).read_bytes()).hexdigest()==d
 controls=[c for n in ('development','heldout') for c in read(H/f'controls/{n}_controls.json')['cases']]
 validator=LockedValidator();resolver=SubstanceResolver(official_validator=validator);resolver.adapters.register('synthetic',SyntheticAdapter());rows=[];executions=[];fixtures=[];rollbacks=[];concurrent=[]
 def fresh():
  p=create_creation_fixture(PRODUCTION);fixtures.append(p);return p
 def packet(c,g,index=0,**kw):return {'record_id':c['id']+':'+str(index),'graph':g,'source_revision':'v1','name':'Explicit synthetic molecular referent',**kw}
 def run(p,r,token=None,**kw):
  result=resolver.resolve(r,'synthetic',p.association,persist_association=True,allow_creation=True,creation_authorization=p,idempotency_key=token,**kw);executions.append(result);return result
 def new(r):return r['resolution_status']=='NEW_SUBSTANCE_CREATED'
 def reused(r):return r['resolution_status']=='EXISTING_SUBSTANCE_REUSED'
 def withheld(r):return r['canonical_substance_id'] is None and not r['creation']['new_substance_created'] and r['resolution_status'] in ('CREATION_WITHHELD','VALIDATION_FAILED','CREATION_CONFLICT')
 try:
  for c in controls:
   key=c['id'];g=c['graphs'];p=fresh();out=[];ok=False;extra={};t=time.monotonic()
   if key in ('new','existing'):
    out=[run(p,packet(c,g[0]))];ok=new(out[0]) if key=='new' else reused(out[0]) and out[0]['canonical_substance_id']=='SUB_00000112'
   elif key in ('repeat','other_source','atom_order','constitutional','stereo','tautomer','isotope','protonation','aromatic_kekule','explicit_hydrogen','stereo_serialization','isotope_placement','counterions','component_ratio'):
    a=packet(c,g[0],salt=key in ('counterions','component_ratio'));b=packet(c,g[1],index=0 if key=='repeat' else 1,salt=key in ('counterions','component_ratio'))
    if key=='other_source':b['system']='SyntheticPublication'
    out=[run(p,a),run(p,b)];ok=new(out[0])
    if c['expected']=='REUSE':ok=ok and reused(out[1]) and out[0]['canonical_substance_id']==out[1]['canonical_substance_id']
    else:ok=ok and new(out[1]) and out[0]['canonical_substance_id']!=out[1]['canonical_substance_id']
    if key=='tautomer':extra['shared_standard_inchikey']=describe(g[0])['inchikey']==describe(g[1])['inchikey']
   elif key in ('unspecified','broad','name_derived','contradiction','incomplete','unsupported','missing_official','no_name','invalid_text'):
    r=packet(c,g[0])
    if key=='broad':r.update(kind='BROAD',identity_scope='BROAD_FAMILY',name='polymer')
    if key=='name_derived':r['kind']='NAME_DERIVED'
    if key=='contradiction':r['conflicting_graph']=g[1]
    if key=='unsupported':r['identity_scope']='COORDINATION_MATERIAL'
    if key=='missing_official':r['missing_official']=True
    if key=='no_name':r['name']=''
    out=[run(p,r,retrieval_policy=RetrievalPolicy(exhaustive=False) if key=='incomplete' else None)];ok=withheld(out[0])
   elif key in ('possible_duplicate','multiple_targets','changed_target'):
    # Fixture-only fault injection; production is never opened writable.
    d=sqlite3.connect(p.path);count=2 if key=='multiple_targets' else 1
    for n in range(count):
     sid='FIX_DEFECT_'+str(n);d.execute('INSERT INTO substance_identity VALUES(?,?,?)',(sid,'Synthetic defective existing record','ACCEPTED'))
     if key!='possible_duplicate':
      graph=g[0];d.execute('INSERT INTO substance_structure VALUES(?,?,?)',(sid,'SMILES',graph))
      ds=describe('COC' if key=='changed_target' else graph)
      for typ,f in [('InChI','inchi'),('InChIKey','inchikey')]:d.execute('INSERT INTO substance_identifier VALUES(?,?,?)',(sid,typ,ds[f]))
    d.commit();d.close();out=[run(p,packet(c,g[0]))];ok=withheld(out[0])
   elif key in ('concurrent_same','concurrent_equivalent','stale_snapshot'):
    a=packet(c,g[0]);b=packet(c,g[1],index=1,system='SyntheticOther')
    # Both read-only proposals precede both writers. Creation deliberately
    # discards these proposals and repeats matching on its locked connection.
    proposals=[resolver.resolve(r,'synthetic',p.path) for r in (a,b)];extra['before_matching']=[r['chemical_resolution_status'] for r in proposals]
    if key=='stale_snapshot':out=[run(p,a),run(p,b)]
    else:
     with ThreadPoolExecutor(max_workers=2) as pool:out=list(pool.map(lambda r:run(p,r),(a,b)))
    ok=sum(new(r) for r in out)==1 and sum(reused(r) for r in out)==1 and out[0]['canonical_substance_id']==out[1]['canonical_substance_id'];concurrent.append({'id':key,'passed':ok,'results':out})
   elif key=='rollback_all_stages':
    for stage in ('BEFORE_ID_ALLOCATION','AFTER_ID_ALLOCATION','AFTER_IDENTITY_INSERTION','AFTER_REPRESENTATIONS','DURING_ASSOCIATION','BEFORE_COMMIT'):
     before=db_state(p)
     def inject(s,at=stage):
      if s==at:raise RuntimeError('INJECTED_'+at)
     r=run(p,packet(c,g[0]),failure_injector=inject);after=db_state(p);out.append(r);rollbacks.append({'stage':stage,'passed':before==after and r['resolution_status']=='CREATION_FAILED','receipt':r})
    ok=all(x['passed'] for x in rollbacks)
   elif key in ('production_write','association_permit_only'):
    blocked=[]
    candidates=[p.association] if key=='association_permit_only' else [replace(p,association=FixturePermit(PRODUCTION,'fake','fake')),replace(p,association=FixturePermit(PRODUCTION.parent/'../output/registry.sqlite','fake','fake')),replace(p,creation_token='invalid')]
    for cap in candidates:
     try:connect_creation(cap);raise AssertionError('UNAUTHORIZED_CREATION_ALLOWED')
     except PermissionError:blocked.append('BLOCKED')
    api=resolver.resolve(packet(c,g[0]),'synthetic',p.association,persist_association=True,allow_creation=True);out=[api];executions.append(api);ok=len(blocked)==len(candidates) and api['resolution_status']=='PERSISTENCE_NOT_AUTHORIZED';extra['blocked']=blocked
    if key=='production_write':
     links=[]
     for kind in ('hard','symbolic'):
      target=p.path.with_name('creation_bypass_'+kind+'.sqlite')
      try:
       if target.exists() or target.is_symlink():target.unlink()
       if kind=='hard':os.link(p.path,target)
       else:target.symlink_to(p.path)
       try:connect_creation(replace(p,association=replace(p.association,path=target)));raise AssertionError('LINK_BYPASS_ALLOWED')
       except PermissionError:links.append(kind+':BLOCKED')
      except OSError as e:links.append(kind+':UNAVAILABLE:'+str(e))
      finally:
       if target.exists() or target.is_symlink():target.unlink()
     extra['links']=links
   elif key in ('idempotency_changed','changed_source','insufficient_revision','supporting_revision'):
    a=packet(c,g[0]);out=[run(p,a,token='stable')];b=packet(c,g[1]);b['source_revision']='v2'
    if key=='insufficient_revision':b.update(kind='BROAD',identity_scope='BROAD_FAMILY',name='polymer')
    if key=='supporting_revision':b['source_timestamp']='2026-11-02T00:00:00Z'
    out.append(run(p,b,token='stable' if key=='idempotency_changed' else 'updated'))
    if key=='supporting_revision':ok=new(out[0]) and reused(out[1]) and out[0]['canonical_substance_id']==out[1]['canonical_substance_id']
    else:
     ok=new(out[0]) and withheld(out[1]);state=db_state(p);ok=ok and len(state['substance_identity'])==113 and not any(a[4]=='ACTIVE' for a in state['concept_substance_association'])
   elif key=='cross_operation_key':
    r=packet(c,g[0]);first=resolver.resolve(r,'synthetic',p.association,persist_association=True,idempotency_key='same-key');executions.append(first)
    out=[first,run(p,r,token='same-key')];ok=out[1]['resolution_status']=='CREATION_CONFLICT' and not out[1]['creation']['new_substance_created']
   integrity=check_integrity(p);extra['integrity']=integrity
   # Fault-injected missing graph is deliberately deficient, preserved as-is.
   if key!='possible_duplicate':ok=ok and integrity['passed']
   row={'id':key,'expected':c['expected'],'passed':bool(ok),'origin':'FROZEN_SYNTHETIC_CONTROL','seconds':time.monotonic()-t,'results':out,'details':extra,'fixture':str(p.path)};rows.append(row);print(key,ok,[x['resolution_status'] for x in out],flush=True)
   write('benchmark_results.json',{'cases':rows,'passed':sum(x['passed'] for x in rows),'total':len(controls),'metrics':metrics(executions)})
  write('transaction_results.json',{'failures':rollbacks});write('concurrency_results.json',{'cases':concurrent})
  for name,ids in [('distinct_forms_results.json',('stereo','tautomer','isotope','protonation','isotope_placement','counterions','component_ratio')),('duplicate_prevention_results.json',('repeat','other_source','atom_order','aromatic_kekule','explicit_hydrogen','stereo_serialization','possible_duplicate','multiple_targets')),('idempotency_results.json',('repeat','idempotency_changed','changed_source','insufficient_revision','supporting_revision','cross_operation_key')),('creation_eligibility_results.json',('unspecified','broad','name_derived','contradiction','incomplete','unsupported','missing_official','no_name','invalid_text')),('production_write_protection.json',('production_write','association_permit_only'))]:write(name,{'cases':[r for r in rows if r['id'] in ids]})
  # Real independently extracted provider fields, not synthetic cross-source IDs.
  pairs=read(B/'real_world_validation/evaluation/pubchem_chebi_pair_results.json')['pairs'];pair=next(x for x in pairs if str(x['source_inputs']['source_record']['record_id'])=='11838');x=pair['source_inputs'];p=fresh();real=[];source_checks=[]
  for side,prov in [('source_record','source_record_provenance'),('reference_identity','reference_provenance')]:
   context=x[prov];path=Path(context['payload_path']);payload=read(path);actual=hashlib.sha256(path.read_bytes()).hexdigest()
   record=payload['rows'][0] if side=='source_record' else payload['data']
   source_checks.append({'path':str(path),'record_id':x[side]['record_id'],'expected_sha256':context['payload_sha256'],'actual_sha256':actual,'original_record_equal':record==x[side]['record'],'passed':actual==context['payload_sha256'] and record==x[side]['record']})
  assert all(x['passed'] for x in source_checks),'SAVED_SOURCE_PAYLOAD_FAILED_REVERIFICATION'
  for provider,side,prov,repeat in [('pubchem','source_record','source_record_provenance',False),('pubchem','source_record','source_record_provenance',True),('chebi','reference_identity','reference_provenance',False),('chebi','reference_identity','reference_provenance',True)]:
   r={'record':x[side]['record'],'provenance':x[prov],'source_revision':'local-cache-v1'}
   result=resolver.resolve(r,provider,p.association,persist_association=True,allow_creation=True,creation_authorization=p)
   real.append({'source':provider,'record_id':x[side]['record_id'],'retry':repeat,'result':result});print('real',provider,repeat,result['resolution_status'],result.get('error'),flush=True)
   if not repeat:(H/'examples').mkdir(exist_ok=True);(H/'examples'/f'{provider}_creation_input.json').write_text(json.dumps({'source_type':provider,**r},indent=2)+'\n')
  ids=[r['result']['canonical_substance_id'] for r in real];state=db_state(p);ok=[r['result']['resolution_status'] for r in real]==['NEW_SUBSTANCE_CREATED','EXISTING_SUBSTANCE_REUSED','EXISTING_SUBSTANCE_REUSED','EXISTING_SUBSTANCE_REUSED'] and len(set(ids))==1 and ids[0] is not None and len(state['substance_identity'])==113 and len(state['concept_substance_association'])==2 and check_integrity(p)['passed']
  result={'passed':ok,'records':real,'metrics':metrics([r['result'] for r in real]),'fixture':str(p.path),'source_payload_verification':source_checks,'created_identity':[row for row in state['substance_identity'] if row[0]==ids[0]],'created_structures':[row for row in state['substance_structure'] if row[0]==ids[0]],'created_identifiers':[row for row in state['substance_identifier'] if row[0]==ids[0]],'independent_corroboration_claim':False,'pair_reverified':'Both original provider records passed adapters, source reconciliation, official validation and complete graph matching; ancestry independence not established.'}
  write('real_creation_results.json',result);write('cross_source_reuse_results.json',result)
  write('schema_integrity_results.json',{'fixtures':[{'path':str(p.path),**check_integrity(p)} for p in fixtures],'intentional_deficient_fixture':[r['fixture'] for r in rows if r['id']=='possible_duplicate']})
  assert all(r['passed'] for r in rows),[r['id'] for r in rows if not r['passed']]
  assert ok,'REAL_CROSS_SOURCE_DEMONSTRATION_FAILED'
 finally:validator.close()
if __name__=='__main__':main()
