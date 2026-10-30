import copy,json,sqlite3,os,hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import bootstrap
from matching_control_inputs import matching_input
from source_concept_models import SourceConcept,SourceRevision
from fixture_registry import create_fixture,connect,FixturePermit,PRODUCTION
from transactional_association import AssociationService
from providers import Bridge
from comparison_session import qualify_source
from evaluate_real_registry import make_input
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf8'))
controls={c['id']:c for k in ('development','heldout') for c in read(B/f'canonical_registry_matching/controls/{k}_controls.json')['cases']}
def key(inp,referent='primary-record-referent'):
 p=inp.concept.evidence_package;return SourceConcept(p.source_name,p.source_record_type,p.source_record_id,referent)
def main():
 frozen=read(H/'controls/benchmark_freeze.json')
 for n,d in frozen.items():assert hashlib.sha256((H/'controls'/n).read_bytes()).hexdigest()==d
 bridge=Bridge();rows=[];fixtures=[]
 def setup(case='D01'):
  permit=create_fixture(B/f'canonical_registry_matching/fixtures/{case}.sqlite');fixtures.append(permit);inp=matching_input(controls[case]);return permit,AssociationService(permit,bridge.official),inp
 def call(service,inp,label='v1',token='one',concept=None,proposal=None,**kw):
  c=concept or key(inp);inp=copy.deepcopy(inp)
  # The synthetic adapter declares the individual referent explicitly. Real
  # whole-record inputs use the documented primary referent convention.
  inp.concept.provenance['referent_key']=c.referent_key
  rev=SourceRevision(label,{'claims':inp.concept.evidence_package.to_dict()});p=proposal or service.prepare(c,rev,inp,kw.get('retrieval_policy'));return service.associate(c,rev,inp,p,token,**kw)
 def save(name,value,detail=None):rows.append(dict(id=name,actual=value,detail=detail));print(name,value,flush=True)
 try:
  p,s,inp=setup();save('create',call(s,inp)['outcome']);save('retry',call(s,inp)['outcome']);second=call(s,inp,token='two',concept=key(inp,'second-mention'))
  from evidence_adapter_contract import EvidencePackage,structural_field
  from correspondence_models import IncomingConcept
  from registry_matching_models import MatchingInput
  pkg=EvidencePackage('SyntheticLiterature','Document','DOC1',{'document':'explicit synthetic cardinality control'})
  anchor=structural_field(pkg,'mention','OCC','$.mention')
  other=MatchingInput(IncomingConcept('DOC1:mention1',pkg,{'status':'ESTABLISHED','kind':'EXPLICIT_STRUCTURAL_FIELD_REFERENT','evidence_ids':[anchor.evidence_id],'document':'Synthetic control specification'}),'Explicit synthetic molecular graph')
  cross=call(s,other,token='cross-source',concept=key(other,'mention1'));assert cross['substance_id']==second['substance_id']
  distinct=matching_input({**controls['D01'],'source_graph':'COC'});third=call(s,distinct,token='third-referent',concept=key(distinct,'third-distinct-mention'));assert third['substance_id']!=second['substance_id']
  save('many_to_one',cross['outcome'],{'second_referent':second,'synthetic_other_source':cross,'different_chemical_same_record':third})
  changed=matching_input({**controls['D01'],'source_graph':'COC'});save('different_target',call(s,changed,'v2','changed')['outcome'])
  p,s,inp=setup();call(s,inp)
  supporting=copy.deepcopy(inp);supporting.form_assertion={'form_kind':'molecule'}
  same_source=call(s,supporting,'v1','new-evidence-same-source-version');assert same_source['outcome']=='ASSOCIATION_UNCHANGED'
  save('supporting_revision',call(s,inp,'v2','new-support')['outcome'],same_source)
  broad=matching_input({**controls['D01'],'category_override':'BROAD','source_graph':None});save('broad_revision',call(s,broad,'v3','broad')['outcome']);assert call(s,inp,token='one')['exact_current'] is False
  mapping={'name_derived':'D19','broad':'D14','partial_stereo':'D04','source_conflict':'D17','multiple':'D12','no_match':'D16','missing_official':'D24','isotope':'D07','tautomer':'D06','charge':'D09','components':'D10'}
  for name,case in mapping.items():
   p,s,inp=setup(case);save(name,call(s,inp)['outcome'])
  from registry_matching_models import RetrievalPolicy
  p,s,inp=setup();save('incomplete_search',call(s,inp,retrieval_policy=RetrievalPolicy(exhaustive=False))['outcome'])
  for name,sql in [('stale_registry',"UPDATE substance_identity SET preferred_name='Changed' WHERE substance_id='FIX_2'"),('changed_target',"UPDATE substance_structure SET structure_value='CO' WHERE substance_id='FIX_1'"),('missing_target',"DELETE FROM substance_identifier WHERE substance_id='FIX_1'; DELETE FROM substance_structure WHERE substance_id='FIX_1'; DELETE FROM substance_identity WHERE substance_id='FIX_1'")]:
   p,s,inp=setup();c=key(inp);rev=SourceRevision('v1',{'claims':inp.concept.evidence_package.to_dict()});proposal=s.prepare(c,rev,inp);d=sqlite3.connect(p.path);d.executescript(sql);d.commit();d.close();save(name,s.associate(c,rev,inp,proposal,'one')['outcome'])
  p,s,inp=setup()
  try:call(s,inp,fail_after_insert=True);raise AssertionError('Failure injection did not execute')
  except RuntimeError as e:
   assert str(e)=='INJECTED_TRANSACTION_FAILURE';d=connect(p);assert all(d.execute('SELECT count(*) FROM '+t).fetchone()[0]==0 for t in ('source_concept','source_concept_revision','concept_resolution_event','concept_substance_association','association_request'));d.close();save('rollback','ROLLED_BACK')
  p,s,inp=setup();call(s,inp);save('idempotency_conflict',call(s,changed,'v2','one')['outcome'])
  p,s,inp=setup();c=key(inp);rev=SourceRevision('v1',{'claims':inp.concept.evidence_package.to_dict()});proposal=s.prepare(c,rev,inp)
  # Real local validation completed before concurrent operations; read-only
  # copies of that validator response avoid sharing a Java stream across threads.
  official=proposal.result['admission']['official_validation'];worker=lambda _:AssociationService(p,lambda d:copy.deepcopy(official)).associate(c,rev,copy.deepcopy(inp),proposal,'concurrent')
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(worker,range(2)))
  d=connect(p);assert d.execute('SELECT count(*) FROM current_exact_association').fetchone()[0]==1;d.close();assert sorted(r['outcome'] for r in results)==['ASSOCIATION_CREATED','ASSOCIATION_UNCHANGED'];save('concurrent','ONE_ACTIVE',results)
  blocked=[]
  for path in (PRODUCTION,PRODUCTION.parent/'../output/registry.sqlite'):
   try:connect(FixturePermit(path,'fake','fake'));raise AssertionError('Production path accepted')
   except PermissionError:blocked.append(str(path))
  # Hard-link and symbolic-link bypasses on disposable files only.
  links=[]
  for kind in ('hard','symbolic'):
   target=H/'fixtures'/('bypass_'+kind+'.sqlite')
   try:
    if target.exists() or target.is_symlink():target.unlink()
    if kind=='hard':os.link(p.path,target)
    else:target.symlink_to(p.path)
    try:connect(replace(p,path=target));raise AssertionError('Link bypass allowed')
    except PermissionError:links.append(kind+':BLOCKED')
   except OSError as e:links.append(kind+':UNAVAILABLE:'+str(e))
   finally:
    if target.exists() or target.is_symlink():target.unlink()
  save('production_write','BLOCKED',{'blocked_paths':blocked,'links':links})
  # Actual saved evidence, copied production registry, no fabricated ChEBI link.
  permit=create_fixture(PRODUCTION);fixtures.append(permit);service=AssociationService(permit,bridge.official);real=[]
  for cid in ('1049','6323'):
   r=next(r for r in read(B/'canonical_registry_matching/evaluation/saved_input_records.json')['records'] if r['record_id']==cid);inp=make_input('PubChem',r['original_record'],r['provenance'],'REAL:'+cid)
   first=call(service,inp,token='real:'+cid);second=call(service,inp,token='real:'+cid);assert first['outcome']=='ASSOCIATION_CREATED' and second['outcome']=='ASSOCIATION_UNCHANGED';real.append(dict(cid=cid,first=first,retry=second,known_shared_pubchem_ancestry=True))
  d=connect(permit);integrity=d.execute('PRAGMA integrity_check').fetchall();fk=d.execute('PRAGMA foreign_key_check').fetchall();assert integrity==[('ok',)] and not fk
  for sql in ("UPDATE concept_resolution_event SET outcome='FORGED'", "UPDATE source_concept_revision SET evidence_hash='FORGED'", "UPDATE substance_identity SET preferred_name='FORGED'"):
   try:d.execute(sql);raise AssertionError('Immutability guard failed')
   except sqlite3.DatabaseError:d.rollback()
  audit={t:d.execute('SELECT * FROM '+t).fetchall() for t in ('source_concept','source_concept_revision','concept_substance_association','concept_resolution_event','association_request')};d.close()
  expected={c['id']:c['expected'] for k in ('development','heldout') for c in read(H/f'controls/{k}.json')['cases']}
  for r in rows:r['expected']=expected[r['id']];r['passed']=r['actual']==r['expected']
  for name,obj in [('benchmark_results.json',{'cases':rows,'passed':sum(r['passed'] for r in rows),'total':len(rows)}),('real_source_association_results.json',{'fixture':str(permit.path),'records':real,'audit_rows':audit,'independent_accuracy_validation':False}),('cross_source_association_results.json',{'genuine_cross_source_positive_established':0,'reason':'No saved ChEBI source was a positive against this registry in previous 20-input evaluation. No new provider requests. Synthetic separate referents exercise many-to-one; do not claim a real cross-database positive.','synthetic_many_to_one':next(r for r in rows if r['id']=='many_to_one')}),('schema_integrity_results.json',{'integrity':integrity,'foreign_keys':fk,'duplicate_active_association_violations':0}),('production_write_protection.json',next(r for r in rows if r['id']=='production_write'))]:
   (H/'evaluation'/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
  for name,ids in [('transaction_results.json',('rollback','stale_registry','changed_target','missing_target')),('idempotency_results.json',('retry','idempotency_conflict')),('source_revision_results.json',('different_target','supporting_revision','broad_revision')),('concurrency_results.json',('concurrent',))]:
   (H/'evaluation'/name).write_text(json.dumps([r for r in rows if r['id'] in ids],indent=2)+'\n',encoding='utf8')
  from collections import Counter
  groups=[]
  for permit in fixtures:
   d=connect(permit)
   events=d.execute("SELECT outcome,matching_status,admission_status,decision_json FROM concept_resolution_event WHERE outcome!='MATCH_EVALUATED'").fetchall()
   ids=d.execute('SELECT concept_id FROM source_concept').fetchall()
   assert not d.execute('PRAGMA foreign_key_check').fetchall()
   assert not d.execute("SELECT concept_id FROM concept_substance_association WHERE association_status IN ('ACTIVE','REVIEW_REQUIRED') GROUP BY concept_id HAVING count(*)>1").fetchall()
   groups.append(dict(fixture=str(permit.path),concept_instances=len(ids),distinct_source_keys=[r[0] for r in ids],outcomes=dict(Counter(e[0] for e in events)),matching_statuses=dict(Counter(e[1] for e in events)),admission_statuses=dict(Counter(e[2] for e in events)),qualified_evaluations=sum(json.loads(e[3])['live_matching']['source_identity']['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' for e in events),associations=d.execute('SELECT count(*) FROM concept_substance_association').fetchone()[0]))
   d.close()
  (H/'evaluation/metrics.json').write_text(json.dumps({'groups':groups,'scope':'Current benchmark execution fixture instances plus separately identified real-source fixture; event-based attempts include retries and setup evaluations; rolled-back attempt has no committed event.','rolled_back_transactions':1,'duplicate_active_violations':0,'production_changes':0,'new_canonical_substances':0},indent=2)+'\n')
  assert all(r['passed'] for r in rows)
 finally:bridge.close()
if __name__=='__main__':main()
