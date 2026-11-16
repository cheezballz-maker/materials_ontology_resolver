"""Small orchestration layer; chemical rules and persistence are reused."""
import copy,sqlite3
from dataclasses import asdict
from pathlib import Path
import bootstrap
from adapter_registry import AdapterRegistry,InputValidationError,UnsupportedSourceError
from fixture_registry import FixturePermit
from transactional_association import AssociationService,now
from registry_identity_adapter import RegistrySnapshot
from registry_matcher import RegistryMatcher
from registry_matching_models import RetrievalPolicy
from source_concept_models import digest

STATUS={'UNIQUE_CANONICAL_MATCH':'EXACT_MATCH','MULTIPLE_CANONICAL_MATCHES':'MULTIPLE_MATCHES','MATCH_UNRESOLVED':'UNRESOLVED','SOURCE_CONFLICT':'SOURCE_CONFLICT','NO_MATCH_IN_SEARCHED_REGISTRY':'NO_MATCH_IN_REGISTRY'}
def failure(result,error,status,category,stage):
 result.update(resolution_status=status,canonical_substance_id=None,error={'category':category,'stage':stage,'type':type(error).__name__,'message':str(error)})
 return result
class SubstanceResolver:
 def __init__(self,*,official_validator=None,adapters=None):
  self.official_validator=official_validator;self.adapters=adapters or AdapterRegistry()
 def resolve(self,source_record,source_adapter,registry,*,persist_association=False,idempotency_key=None,retrieval_policy=None,diagnostic_verbosity='full',failure_injector=None,allow_creation=False,creation_authorization=None):
  result=dict(resolution_status=None,chemical_resolution_status=None,canonical_substance_id=None,association={'requested':persist_association,'status':'NOT_ATTEMPTED' if persist_association else 'NOT_REQUESTED','committed':False,'association_created':False},reason_codes=[],unresolved_obligations=[],provenance={'orchestrator_version':'1.0','production_writes':0,'new_substances_created':0},capabilities={'sources':['pubchem','chebi','qualified'],'chemistry':'EXISTING_VALIDATED_MOLECULAR_AND_FIXED_COMPOSITION_SCOPE','persistence':'VERIFIED_EXPLICIT_STRUCTURES_IN_MARKED_FIXTURES_ONLY','new_identity_creation':False})
  result['creation']={'requested':allow_creation,'status':'NOT_ATTEMPTED' if allow_creation else 'NOT_REQUESTED','committed':False,'new_substance_created':False}
  stage='SOURCE_ADAPTER'
  try:
   adapter=self.adapters.get(source_adapter) if isinstance(source_adapter,str) else source_adapter
   if adapter is None:raise UnsupportedSourceError('SOURCE_ADAPTER_REQUIRED')
   normalized=adapter.adapt(copy.deepcopy(source_record));incoming=normalized.incoming
   invalid=[d for c in incoming.concept.evidence_package.claims for d in c.unresolved_dependencies if d.startswith('STRUCTURE_INVALID_OR_UNSUPPORTED:')]
   if invalid:
    issues=[o for o in incoming.concept.evidence_package.observations if o['kind']=='STRUCTURE_VALIDATION_FAILURE']
    r=failure(result,InputValidationError(';'.join(invalid)),'VALIDATION_FAILED','INPUT_VALIDATION',stage)
    if issues:
     r['reason_codes']=sorted({issue['code'] for issue in issues})
     r['error']['chemical_validation']=issues
    return r
   result['source_concept']={**asdict(normalized.concept),'concept_id':normalized.concept.concept_id}
   eh=digest(asdict(incoming));result['provenance']['evaluated_at']=now();result['source_revision']={'source_revision':normalized.revision.source_revision,'source_record_id':normalized.concept.source_record_id,'evidence_hash':eh,'source_payload_hash':digest(normalized.revision.payload),'source_timestamp':normalized.revision.source_timestamp,'recorded_at':None,'stored':False}
   policy=retrieval_policy or RetrievalPolicy();policy.validate();stage='MATCHING'
   if allow_creation:
    if not persist_association:raise InputValidationError('CREATION_REQUIRES_ATOMIC_ASSOCIATION')
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'canonical_substance_creation'))
    from creation_authorization import CreationPermit
    from creation_transaction import CreationService
    if not isinstance(creation_authorization,CreationPermit) or not isinstance(registry,FixturePermit) or creation_authorization.association!=registry:raise PermissionError('SEPARATE_MATCHING_FIXTURE_CREATION_CAPABILITY_REQUIRED')
    stage='CREATION_TRANSACTION'
    token=idempotency_key or digest([normalized.concept.concept_id,normalized.revision.source_revision,digest(normalized.revision.payload),eh,'RESOLVE_OR_CREATE_V1'])
    creation=CreationService(creation_authorization,self.official_validator).execute(normalized,token,retrieval_policy=policy,failure_injector=failure_injector)
    match=creation['matching'];result['creation']={k:v for k,v in creation.items() if k not in ('matching','association')};result['creation']['requested']=True;result['creation']['status']=creation['outcome']
    result['association']={**creation['association'],'requested':True,'status':creation['association']['outcome'].removeprefix('ASSOCIATION_')}
    result['provenance']['new_substances_created']=int(creation['new_substance_created']);result['capabilities']['new_identity_creation']=True
   elif persist_association:
    if not isinstance(registry,FixturePermit):raise PermissionError('MARKED_FIXTURE_CAPABILITY_REQUIRED')
    service=AssociationService(registry,self.official_validator)
    proposal=service.prepare(normalized.concept,normalized.revision,incoming,policy);match=proposal.result
   else:
    # A caller may reuse an immutable read-only snapshot across a bounded
    # workload. The matcher still checks its digest before and after use.
    snapshot=registry if isinstance(registry,RegistrySnapshot) else RegistrySnapshot(registry.path if isinstance(registry,FixturePermit) else Path(registry))
    match=RegistryMatcher(snapshot,official_validator=self.official_validator).match(incoming,policy)
   chem=STATUS[match['status']];result.update(resolution_status=chem,chemical_resolution_status=chem,canonical_substance_id=match['unique_matched_substance_id'])
   source=match['source_identity'];result['identity_evidence']=source['evidence_package']
   result['reconciliation']={k:source[k] for k in ('state','binding_valid','binding','obligations','conflicts','excluded_claims')}
   result['candidate_retrieval']=match['retrieval'];result['chemical_comparison']=match['candidate_results'];result['registry_match']={'status':match['status'],'matched_substance_id':match['unique_matched_substance_id'],'uniqueness':match['uniqueness']};result['admission']=match['admission']
   result['unresolved_obligations']=source['obligations'];result['reason_codes']=list(match['admission']['existing_policy_result']['reason_codes'])
   if persist_association and not allow_creation:
    stage='ASSOCIATION_TRANSACTION'
    token=idempotency_key or digest([normalized.concept.concept_id,normalized.revision.source_revision,digest(normalized.revision.payload),eh,'UNIFIED_ASSOCIATION_V1'])
    assoc=service.associate(normalized.concept,normalized.revision,incoming,proposal,token,retrieval_policy=policy,fail_after_insert=bool(failure_injector and failure_injector()))
    assoc['requested']=True;assoc['status']=assoc['outcome'].removeprefix('ASSOCIATION_');result['association']=assoc;result['source_revision']['revision_id']=assoc['revision_id']
    stage='COMMITTED_REVISION_METADATA'
    db=sqlite3.connect(registry.path.resolve().as_uri()+'?mode=ro',uri=True)
    try:result['source_revision'].update(recorded_at=db.execute('SELECT recorded_at FROM source_concept_revision WHERE revision_id=?',(assoc['revision_id'],)).fetchone()[0],stored=True)
    finally:db.close()
    if assoc['association_created'] and assoc['exact_current']:result['resolution_status']='ASSOCIATED'
    elif assoc['outcome'] in ('ASSOCIATION_CONFLICT','ASSOCIATION_REVIEW_REQUIRED','IDEMPOTENCY_CONFLICT','STALE_PROPOSAL') or assoc['outcome']=='ASSOCIATION_UNCHANGED' and not assoc['exact_current']:
     result['resolution_status']='REVIEW_REQUIRED';result['canonical_substance_id']=None
    result['reason_codes']+=assoc['reasons']
   if allow_creation:
    result['resolution_status']=creation['outcome'];result['canonical_substance_id']=creation['substance_id'];result['source_revision']['revision_id']=creation['association']['revision_id']
    result['reason_codes']+=creation['reasons']
    stage='COMMITTED_REVISION_METADATA'
    db=sqlite3.connect(registry.path.resolve().as_uri()+'?mode=ro',uri=True)
    try:result['source_revision'].update(recorded_at=db.execute('SELECT recorded_at FROM source_concept_revision WHERE revision_id=?',(creation['association']['revision_id'],)).fetchone()[0],stored=True)
    finally:db.close()
   if diagnostic_verbosity=='summary':
    result['identity_evidence']={'source_name':source['evidence_package']['source_name'],'source_record_id':source['evidence_package']['source_record_id'],'claim_count':len(source['evidence_package']['claims']),'evidence_hash':eh}
    result['chemical_comparison']=[{k:c[k] for k in ('candidate_substance_id','chemical_status','source_identity_status','dimension_comparisons')} for c in match['candidate_results']]
   return result
  except UnsupportedSourceError as e:return failure(result,e,'UNSUPPORTED_SOURCE','UNSUPPORTED_INPUT',stage)
  except InputValidationError as e:
   status={'CONFLICT':'SOURCE_CONFLICT','UNRESOLVED':'UNRESOLVED','UNSUPPORTED':'UNSUPPORTED_CHEMISTRY','OUT_OF_SCOPE':'OUT_OF_SCOPE','NONCANONICAL_BROAD_TERM':'NONCANONICAL_BROAD_TERM'}.get(getattr(e,'status',None),'VALIDATION_FAILED')
   result['reason_codes']=list(getattr(e,'reasons',[]))
   return failure(result,e,status,'INPUT_VALIDATION',stage)
  except PermissionError as e:return failure(result,e,'PERSISTENCE_NOT_AUTHORIZED','AUTHORIZATION',stage)
  except Exception as e:
   if stage=='CREATION_TRANSACTION' and getattr(e,'matching',None):
    m=e.matching;result['chemical_resolution_status']=STATUS[m['status']];result['candidate_retrieval']=m['retrieval'];result['chemical_comparison']=m['candidate_results'];result['admission']=m['admission'];result['registry_match']={'status':m['status'],'matched_substance_id':m['unique_matched_substance_id'],'uniqueness':m['uniqueness']};result['creation']['eligibility']=e.eligibility;result['creation']['failed_phase']=e.phase
    source=m['source_identity'];result['identity_evidence']=source['evidence_package'];result['reconciliation']={k:source[k] for k in ('state','binding_valid','binding','obligations','conflicts','excluded_claims')}
   # Software/IO/transaction failures have their own outcome, never chemical U.
   result.update(resolution_status='PROCESSING_FAILED',canonical_substance_id=None,error={'category':'PROCESSING_FAILURE','stage':stage,'type':type(e).__name__,'message':str(e)})
   # If a later presentation/read step fails after commit, preserve the actual
   # committed outcome. A transaction exception never returned that receipt.
   if stage in ('ASSOCIATION_TRANSACTION','CREATION_TRANSACTION') and not result['association']['committed']:result['association']['status']='FAILED'
   if stage=='CREATION_TRANSACTION' and not result['creation']['committed']:
    result['resolution_status']='CREATION_FAILED';result['creation']['status']='CREATION_FAILED'
   return result
