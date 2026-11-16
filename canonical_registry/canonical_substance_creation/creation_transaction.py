"""Resolve-or-create against one BEGIN IMMEDIATE transaction, then associate.

Chemical comparison and admission are existing implementations. The association
service's locked operation retains its revision and no-reassignment rules.
"""
import copy,hashlib,json,uuid,time
from dataclasses import asdict
from pathlib import Path
import bootstrap
from source_concept_models import digest,canonical
from transactional_association import AssociationService,Proposal,version,now
from fixture_registry import registry_digest
from registry_identity_adapter import RegistrySnapshot
from registry_matcher import RegistryMatcher
from registry_matching_models import RetrievalPolicy
from creation_authorization import connect_creation
from creation_eligibility import assess
from substance_record_builder import build,insert,insert_representations
from canonical_id_allocator import allocate
from audit_payload import encode as encode_audit

H=Path(__file__).resolve().parent

class CreationTransactionFailure(RuntimeError):
 """Failed transaction diagnostics contain no uncommitted ID or receipt."""
 def __init__(self,error,matching,eligibility,phase):
  super().__init__(str(error));self.matching=matching;self.eligibility=eligibility;self.phase=phase

def implementation_version():
 return digest({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in H.glob('*.py')})

class CreationService:
 def __init__(self,permit,official_validator=None):self.permit=permit;self.official_validator=official_validator
 def execute(self,normalized,idempotency_key,*,retrieval_policy=None,failure_injector=None):
  return self._execute(normalized,idempotency_key,retrieval_policy=retrieval_policy,failure_injector=failure_injector)
 def _execute(self,normalized,idempotency_key,*,retrieval_policy=None,failure_injector=None,finalize=None):
  """Internal fixture composition point for transaction-bound workflow metadata."""
  if not idempotency_key:raise ValueError('IDEMPOTENCY_KEY_REQUIRED')
  c,rev,incoming=normalized.concept,normalized.revision,copy.deepcopy(normalized.incoming)
  c.validate();svc=AssociationService(self.permit.association,self.official_validator);svc._referent(c,incoming)
  pkg=incoming.concept.evidence_package
  if (pkg.source_name,pkg.source_record_type,pkg.source_record_id)!=(c.source_system,c.source_record_type,c.source_record_id):raise ValueError('SOURCE_REFERENT_KEY_MISMATCH')
  policy=(retrieval_policy or RetrievalPolicy()).validate();request=digest([asdict(c),asdict(rev),asdict(incoming),'RESOLVE_OR_CREATE_V1',policy.identity_policy()])
  start=time.monotonic();db=connect_creation(self.permit);r=None;eligibility=None;phase='LOCKED_MATCHING'
  def fail(stage):
   nonlocal phase
   phase=stage
   if failure_injector:failure_injector(stage)
  try:
   db.execute('BEGIN IMMEDIATE');snapshot=RegistrySnapshot.for_locked_writer(db);before=snapshot.sha256
   r=RegistryMatcher(snapshot,official_validator=self.official_validator).match(incoming,policy)
   eligibility=assess(incoming,r);record=None;new_id=None;reasons=list(eligibility['reasons'])
   if snapshot.foreign_key_errors or snapshot.sqlite_integrity!=[('ok',)]:
    eligibility['eligible']=False;eligibility['reasons'].append('REGISTRY_INTEGRITY_FAILURE');reasons.append('REGISTRY_INTEGRITY_FAILURE')
   cid=c.concept_id;eh=digest(asdict(incoming));ph=digest(rev.payload);rid='REV_'+digest([cid,rev.source_revision,ph,eh])
   active=db.execute("SELECT association_id,substance_id,association_status FROM concept_substance_association WHERE concept_id=? AND association_status IN ('ACTIVE','REVIEW_REQUIRED')",(cid,)).fetchone()
   head=db.execute('SELECT revision_id,state FROM source_concept_head WHERE concept_id=?',(cid,)).fetchone()
   prior=db.execute('SELECT request_digest,result_json FROM creation_request WHERE idempotency_key=?',(idempotency_key,)).fetchone()
   cross=db.execute('SELECT 1 FROM association_request WHERE idempotency_key=?',(idempotency_key,)).fetchone()
   conflict=bool(prior and prior[0]!=request or cross)
   revision_conflict=bool(db.execute('SELECT 1 FROM source_concept_revision WHERE concept_id=? AND source_revision=? AND revision_id!=? AND source_payload_hash!=?',(cid,rev.source_revision,rid,ph)).fetchone())
   older=bool(head and head[0]!=rid and db.execute('SELECT 1 FROM concept_resolution_event WHERE source_revision_id=?',(rid,)).fetchone())
   if conflict:reasons.append('IDEMPOTENCY_OPERATION_OR_EVIDENCE_CONFLICT')
   if revision_conflict:reasons.append('SOURCE_VERSION_LABEL_REUSED_WITH_CHANGED_PAYLOAD')
   if older:reasons.append('OLDER_REVISION_REPLAY_NO_HEAD_CHANGE')
   if active and (active[2]=='REVIEW_REQUIRED' or active[1]!=r['unique_matched_substance_id']):reasons.append('EXISTING_ASSOCIATION_REQUIRES_REVIEW_NO_REASSIGNMENT')
   # Never allocate before checking existing source-assignment history. A
   # changed referent must not leave an unassociated new identity behind.
   can_create=eligibility['eligible'] and not active and not conflict and not revision_conflict and not older and not prior
   if can_create:
    try:record=build(incoming,eligibility)
    except ValueError as e:reasons.append(str(e));can_create=False
   if can_create:
    fail('BEFORE_ID_ALLOCATION');new_id=allocate(db);fail('AFTER_ID_ALLOCATION')
    insert(db,new_id,record);fail('AFTER_IDENTITY_INSERTION')
    insert_representations(db,new_id,record);fail('AFTER_REPRESENTATIONS')
   # Build a fresh signed association proposal from the current transaction.
   # This includes the new graph, when created; no fabricated unique result.
   live_snapshot=RegistrySnapshot.for_locked_writer(db,after_canonical_insert=snapshot) if new_id else snapshot
   if new_id and (live_snapshot.sqlite_integrity!=[('ok',)] or live_snapshot.foreign_key_errors):
    raise RuntimeError('NEW_IDENTITY_REGISTRY_INTEGRITY_FAILURE')
   live=RegistryMatcher(live_snapshot,official_validator=self.official_validator).match(incoming,policy) if new_id else r
   if new_id and (live['status']!='UNIQUE_CANONICAL_MATCH' or live['unique_matched_substance_id']!=new_id):raise RuntimeError('NEW_IDENTITY_FAILED_LIVE_SELF_MATCH')
   assoc_request=digest([asdict(c),asdict(rev),asdict(incoming),'ASSOCIATE_EXISTING',policy.identity_policy()]);rd=live_snapshot.sha256;ver=version()
   proposal=Proposal(assoc_request,rd,ver,live,svc._signature(assoc_request,rd,ver,live))
   # A conflicting key must not cause a new association even if its new source
   # is otherwise eligible. Store the revision and an explicit rejection below.
   if conflict:
    ts=now();db.execute('INSERT OR IGNORE INTO source_concept VALUES(?,?,?,?,?,?,?)',(cid,c.source_system,c.source_record_type,c.source_record_id,c.referent_key,c.concept_type,ts))
    stored=db.execute('SELECT concept_type FROM source_concept WHERE concept_id=?',(cid,)).fetchone()
    if stored[0]!=c.concept_type:raise ValueError('SOURCE_CONCEPT_TYPE_CHANGED')
    db.execute('INSERT OR IGNORE INTO source_concept_revision VALUES(?,?,?,?,?,?,?,?)',(rid,cid,rev.source_revision,ph,eh,rev.source_timestamp,ts,canonical({'revision':asdict(rev),'incoming':asdict(incoming)})))
    if active:
     db.execute("UPDATE concept_substance_association SET association_status='REVIEW_REQUIRED',updated_at=? WHERE association_id=?",(ts,active[0]))
     db.execute("UPDATE source_concept_head SET state='REVIEW_REQUIRED' WHERE concept_id=?",(cid,))
    else:db.execute('INSERT OR IGNORE INTO source_concept_head VALUES(?,?,?)',(cid,rid,'UNRESOLVED'))
    assoc=dict(outcome='IDEMPOTENCY_CONFLICT',concept_id=cid,revision_id=rid,association_id=active[0] if active else None,substance_id=None,candidate_substance_id=live['unique_matched_substance_id'],committed=True,association_created=False,exact_current=False,reasons=['IDEMPOTENCY_OPERATION_OR_EVIDENCE_CONFLICT'])
   else:
    fail('DURING_ASSOCIATION')
    # Registry digest is part of the old association idempotency contract. The
    # outer creation key intentionally survives registry growth; inner keys are
    # distinct per fully revalidated state without changing that old contract.
    assoc=svc._associate_locked(db,c,rev,incoming,proposal,'creation-assoc:'+digest([idempotency_key,request,rd,ver]),retrieval_policy=policy,live_snapshot=live_snapshot,locked_match=live)
   if new_id and not (assoc['association_created'] and assoc['exact_current']):raise RuntimeError('NEW_IDENTITY_ASSOCIATION_NOT_COMMITTED')
   if conflict or assoc['outcome'] in ('ASSOCIATION_CONFLICT','IDEMPOTENCY_CONFLICT','ASSOCIATION_REVIEW_REQUIRED','STALE_PROPOSAL'):outcome='CREATION_CONFLICT'
   elif new_id:outcome='NEW_SUBSTANCE_CREATED'
   elif assoc['exact_current']:outcome='EXISTING_SUBSTANCE_REUSED'
   else:outcome='CREATION_WITHHELD'
   target=new_id or live['unique_matched_substance_id'];ts=now();eid=uuid.uuid4().hex
   audit_match=copy.deepcopy(r)
   audit_match['source_identity']['evidence_package']={'source_revision_id':rid,'evidence_hash':eh,'storage':'source_concept_revision.evidence_json'}
   after=registry_digest(db)
   decision=dict(idempotency_key=idempotency_key,request_digest=request,prior_request=json.loads(prior[1]) if prior else None,pre_creation_matching=audit_match,eligibility=eligibility,record_construction=record,association_receipt=assoc,registry_after=after,implementation_version=implementation_version(),official_validation=r['admission']['official_validation'])
   encoded=encode_audit(db,decision);canonical_write_check=db.total_changes
   db.execute('INSERT INTO concept_resolution_event VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(eid,cid,rid,target,r['status'],r['admission']['existing_policy_result']['status'],'RESOLVE_OR_CREATE_V1',outcome,eh,ver,hashlib.sha256((H.parent/'policy.py').read_bytes()).hexdigest(),before,active[0] if active else None,ts,canonical(sorted(set(reasons))),encoded))
   if new_id:db.execute('INSERT INTO substance_creation_record VALUES(?,?,?,?,?,?)',(new_id,cid,rid,eid,ts,canonical(record)))
   # Retain the late digest if triggers caused any additional writes.
   if db.total_changes-canonical_write_check!=1+int(bool(new_id)):
    after=registry_digest(db)
   if conflict:assoc['event_id']=eid
   result=dict(outcome=outcome,committed=True,new_substance_created=bool(new_id),substance_id=target if assoc['exact_current'] else None,event_id=eid,association=assoc,eligibility=eligibility,reasons=sorted(set(reasons)),matching=r,registry_before=before,registry_after=after,registry_records_before=len(snapshot.entries),registry_records_after=db.execute('SELECT count(*) FROM substance_identity').fetchone()[0],replayed_request=bool(prior and not conflict),transaction_seconds=time.monotonic()-start)
   if not prior and not cross:db.execute('INSERT INTO creation_request VALUES(?,?,?,?,?,?)',(idempotency_key,request,cid,rid,eid,canonical({k:v for k,v in result.items() if k!='matching'})))
   if finalize is not None:finalize(db,result)
   fail('BEFORE_COMMIT');db.commit();return result
  except BaseException as e:
   db.rollback()
   if isinstance(e,Exception):raise CreationTransactionFailure(e,r,eligibility,phase) from e
   raise
  finally:db.close()
