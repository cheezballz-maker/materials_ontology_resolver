"""Sealed proposals, live revalidation under BEGIN IMMEDIATE, append-only audit."""
import copy,hmac,hashlib,json,uuid
from dataclasses import asdict,dataclass
from datetime import datetime,timezone
import bootstrap
from source_concept_models import canonical,digest
from fixture_registry import connect,registry_digest
from registry_identity_adapter import RegistrySnapshot
from registry_matcher import RegistryMatcher
from registry_matching_models import RetrievalPolicy
from audit_payload import encode as encode_audit
H=__import__('pathlib').Path(__file__).resolve().parent
def now():return datetime.now(timezone.utc).isoformat()
def version():return digest({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('canonical_registry_matching','chemical_correspondence_hardening','controlled_identity_reuse') for p in (H.parent/folder).glob('*.py')}|{n:hashlib.sha256((H.parent/n).read_bytes()).hexdigest() for n in ('policy.py','evidence_model.py','provider_capabilities.py','internal_structure_policy.py')})
@dataclass(frozen=True)
class Proposal:
 request_digest:str
 registry_digest:str
 matcher_version:str
 result:dict
 signature:str
class AssociationService:
 def __init__(self,permit,official_validator=None):self.permit=permit;self.official_validator=official_validator
 def _referent(self,concept,incoming):
  declared=incoming.concept.provenance.get('referent_key','primary-record-referent')
  if declared!=concept.referent_key:raise ValueError('INDIVIDUAL_REFERENT_BINDING_MISMATCH')
 def _signature(self,request,registry,ver,result):return hmac.new(self.permit.token.encode(),canonical([request,registry,ver,result]).encode(),hashlib.sha256).hexdigest()
 def prepare(self,concept,revision,incoming,retrieval_policy=None):
  concept.validate();self._referent(concept,incoming);db=connect(self.permit)
  try:rd=registry_digest(db)
  finally:db.close()
  request=digest([asdict(concept),asdict(revision),asdict(incoming),'ASSOCIATE_EXISTING',(retrieval_policy or RetrievalPolicy()).identity_policy()]);ver=version()
  r=RegistryMatcher(RegistrySnapshot(self.permit.path),official_validator=self.official_validator).match(copy.deepcopy(incoming),retrieval_policy)
  return Proposal(request,rd,ver,r,self._signature(request,rd,ver,r))
 def associate(self,concept,revision,incoming,proposal,idempotency_key,*,retrieval_policy=None,fail_after_insert=False):
  db=connect(self.permit)
  try:
   db.execute('BEGIN IMMEDIATE')
   result=self._associate_locked(db,concept,revision,incoming,proposal,idempotency_key,retrieval_policy=retrieval_policy)
   if fail_after_insert:raise RuntimeError('INJECTED_TRANSACTION_FAILURE')
   db.commit();return result
  except BaseException:db.rollback();raise
  finally:db.close()
 def _associate_locked(self,db,concept,revision,incoming,proposal,idempotency_key,*,retrieval_policy=None,live_snapshot=None,
                       locked_match=None):
  """Internal composition point; caller owns authorized connection and commit.

  No chemical/admission/revision decision is skipped. A receipt is private until
  the owning service commits. Ordinary callers use associate().
  """
  if not db.in_transaction:raise ValueError('LOCKED_ASSOCIATION_TRANSACTION_REQUIRED')
  self._referent(concept,incoming)
  if not idempotency_key:raise ValueError('IDEMPOTENCY_KEY_REQUIRED')
  expected=digest([asdict(concept),asdict(revision),asdict(incoming),'ASSOCIATE_EXISTING',(retrieval_policy or RetrievalPolicy()).identity_policy()])
  idempotency_digest=digest([expected,proposal.registry_digest,proposal.matcher_version,proposal.result.get('unique_matched_substance_id'),'ASSOCIATE_EXISTING'])
  if proposal.request_digest!=expected or not hmac.compare_digest(proposal.signature,self._signature(proposal.request_digest,proposal.registry_digest,proposal.matcher_version,proposal.result)):raise ValueError('UNQUALIFIED_OR_CHANGED_PROPOSAL')
  pkg=incoming.concept.evidence_package
  if (pkg.source_name,pkg.source_record_type,pkg.source_record_id)!=(concept.source_system,concept.source_record_type,concept.source_record_id):raise ValueError('SOURCE_REFERENT_KEY_MISMATCH')
  # Reuse an inventory only from this reserved transaction and before any
  # intervening write. Matching and admission still run against the live state.
  # The creation service can hand off its match before any intervening SQL
  # writes. Reuse only the same request and locked transaction state.
  same_state=live_snapshot is not None and live_snapshot.same_locked_state(db)
  current=live_snapshot.sha256 if same_state else registry_digest(db)
  if not same_state:
   live_snapshot=RegistrySnapshot.from_connection(db)
  if (same_state and locked_match is proposal.result and current==proposal.registry_digest
      and proposal.matcher_version==version() and live_snapshot.sqlite_integrity==[('ok',)]
      and not live_snapshot.foreign_key_errors):
   r=locked_match
  else:
   r=RegistryMatcher(live_snapshot,official_validator=self.official_validator).match(copy.deepcopy(incoming),retrieval_policy)
  prior_request=db.execute('SELECT request_digest,result_json FROM association_request WHERE idempotency_key=?',(idempotency_key,)).fetchone()
  # Creation-enabled fixtures share the external idempotency-key namespace.
  # Original association-only fixtures do not have this additional table.
  creation_request=db.execute('SELECT request_digest,result_json FROM creation_request WHERE idempotency_key=?',(idempotency_key,)).fetchone() if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='creation_request'").fetchone() else None
  cid=concept.concept_id;eh=digest(asdict(incoming));ph=digest(revision.payload);rid='REV_'+digest([cid,revision.source_revision,ph,eh]);ts=now()
  db.execute('INSERT OR IGNORE INTO source_concept VALUES(?,?,?,?,?,?,?)',(cid,concept.source_system,concept.source_record_type,concept.source_record_id,concept.referent_key,concept.concept_type,ts))
  stored=db.execute('SELECT concept_type FROM source_concept WHERE concept_id=?',(cid,)).fetchone()
  if stored[0]!=concept.concept_type:raise ValueError('SOURCE_CONCEPT_TYPE_CHANGED')
  db.execute('INSERT OR IGNORE INTO source_concept_revision VALUES(?,?,?,?,?,?,?,?)',(rid,cid,revision.source_revision,ph,eh,revision.source_timestamp,ts,canonical({'revision':asdict(revision),'incoming':asdict(incoming)})))
  active=db.execute("SELECT association_id,substance_id,association_status FROM concept_substance_association WHERE concept_id=? AND association_status IN ('ACTIVE','REVIEW_REQUIRED')",(cid,)).fetchone()
  head=db.execute('SELECT revision_id,state FROM source_concept_head WHERE concept_id=?',(cid,)).fetchone()
  target=r['unique_matched_substance_id'];reasons=[];operation='ASSOCIATE_EXISTING'
  eligible=(live_snapshot.sqlite_integrity==[('ok',)] and not live_snapshot.foreign_key_errors
            and r['status']=='UNIQUE_CANONICAL_MATCH' and r['admission']['admission_eligible']
            and (r['admission']['input_classification']['verified_explicit_structure']
                 or r['admission']['input_classification'].get('trusted_internal_structure',False)
                 or r['admission']['input_classification'].get('validated_chemical_interpretation',False))
            and r['retrieval']['search_complete'])
  stale=current!=proposal.registry_digest or version()!=proposal.matcher_version
  if creation_request:outcome='IDEMPOTENCY_CONFLICT';reasons.append('IDEMPOTENCY_KEY_BELONGS_TO_CREATION_OPERATION')
  elif prior_request and prior_request[0]!=idempotency_digest:outcome='IDEMPOTENCY_CONFLICT'
  elif stale:outcome='STALE_PROPOSAL'
  elif prior_request:outcome='ASSOCIATION_UNCHANGED';reasons.append('REPLAY_PRESERVES_CURRENT_HEAD_AND_REVIEW_STATE')
  elif head and head[0]!=rid and db.execute('SELECT 1 FROM concept_resolution_event WHERE source_revision_id=?',(rid,)).fetchone():outcome='ASSOCIATION_REVIEW_REQUIRED';reasons.append('OLDER_REVISION_REPLAY_NO_HEAD_CHANGE')
  elif db.execute('SELECT 1 FROM source_concept_revision WHERE concept_id=? AND source_revision=? AND revision_id!=? AND source_payload_hash!=?',(cid,revision.source_revision,rid,ph)).fetchone():outcome='ASSOCIATION_CONFLICT';reasons.append('SOURCE_VERSION_LABEL_REUSED_WITH_CHANGED_PAYLOAD')
  elif active and (not eligible or active[1]!=target or active[2]=='REVIEW_REQUIRED'):
   outcome='ASSOCIATION_CONFLICT' if eligible and active[1]!=target else 'ASSOCIATION_REVIEW_REQUIRED';reasons.append('NO_AUTOMATIC_REASSIGNMENT_OR_REACTIVATION')
  elif not eligible:outcome='ASSOCIATION_REJECTED';reasons.append('QUALIFIED_UNIQUE_ADMITTED_STRUCTURE_REQUIRED')
  elif active:outcome='ASSOCIATION_UNCHANGED'
  else:outcome='ASSOCIATION_CREATED'
  decision=encode_audit(db,{'idempotency_key':idempotency_key,'idempotency_request_digest':idempotency_digest,'previous_request':json.loads(prior_request[1]) if prior_request else None,'creation_operation_request':json.loads(creation_request[1]) if creation_request else None,'proposal':asdict(proposal),'live_matching':r})
  audit_version=version();policy_version=hashlib.sha256((H.parent/'policy.py').read_bytes()).hexdigest()
  def event(kind):
   eid=uuid.uuid4().hex;db.execute('INSERT INTO concept_resolution_event VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(eid,cid,rid,target,r['status'],r['admission']['existing_policy_result']['status'],operation,kind,eh,audit_version,policy_version,current,active[0] if active else None,ts,canonical(reasons),decision));return eid
  event('MATCH_EVALUATED');eid=event(outcome);aid=active[0] if active else None
  if outcome=='ASSOCIATION_CREATED':
   aid=uuid.uuid4().hex;db.execute('INSERT INTO concept_substance_association VALUES(?,?,?,?,?,?,?,?,?,?)',(aid,cid,target,'EXACT','ACTIVE',rid,rid,eid,ts,ts))
  elif active and (outcome in ('IDEMPOTENCY_CONFLICT','STALE_PROPOSAL') or outcome in ('ASSOCIATION_CONFLICT','ASSOCIATION_REVIEW_REQUIRED') and not prior_request):
   db.execute("UPDATE concept_substance_association SET association_status='REVIEW_REQUIRED',updated_at=? WHERE association_id=?",(ts,aid))
  elif active and outcome=='ASSOCIATION_UNCHANGED' and not prior_request:
   db.execute('UPDATE concept_substance_association SET validated_revision_id=?,resolution_event_id=?,updated_at=? WHERE association_id=?',(rid,eid,ts,aid))
  if not prior_request and not stale and 'OLDER_REVISION_REPLAY_NO_HEAD_CHANGE' not in reasons:
   state='VALIDATED' if outcome in ('ASSOCIATION_CREATED','ASSOCIATION_UNCHANGED') else 'REVIEW_REQUIRED' if active else 'UNRESOLVED'
   db.execute('INSERT INTO source_concept_head VALUES(?,?,?) ON CONFLICT(concept_id) DO UPDATE SET revision_id=excluded.revision_id,state=excluded.state',(cid,rid,state))
  result=dict(outcome=outcome,concept_id=cid,revision_id=rid,association_id=aid,substance_id=active[1] if active else target if outcome=='ASSOCIATION_CREATED' else None,candidate_substance_id=target,committed=True,association_created=outcome=='ASSOCIATION_CREATED',exact_current=outcome in ('ASSOCIATION_CREATED','ASSOCIATION_UNCHANGED') and bool(db.execute('SELECT 1 FROM current_exact_association WHERE concept_id=?',(cid,)).fetchone()),matching_status=r['status'],admission_status=r['admission']['existing_policy_result']['status'],event_id=eid,reasons=reasons)
  if not prior_request:db.execute('INSERT INTO association_request VALUES(?,?,?,?,?,?)',(idempotency_key,idempotency_digest,cid,rid,eid,canonical(result)))
  return result
