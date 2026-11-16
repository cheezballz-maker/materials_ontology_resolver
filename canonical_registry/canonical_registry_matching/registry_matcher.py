"""Source qualification → retrieval → hardened comparison → proposal only."""
import bootstrap
from time import perf_counter
from comparison_session import qualify_source,qualify_candidate,compare,descriptor,structural_pair,validate_source_claims_once
from correspondence_assessment import _hard_chemical_blockers
from evidence_independence_assessment import assess as assess_independence
from registry_candidate_retriever import RegistryRetriever
from registry_matching_models import RetrievalPolicy
from diagnostic_match_policy import assess_admission

ANCESTRY_ONLY={'CANDIDATE_INDEPENDENCE_UNESTABLISHED','CANDIDATE_DERIVED_FROM_INCOMING_SOURCE'}

def _composition_difference(source,candidate,candidate_obligations):
 if (not source['binding_valid'] or source['state']!='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY'
     or source['source_conflicts'] or candidate_obligations or not source['graph_view'] or not candidate['descriptor']
     or source['identity_scope']!=candidate['identity_scope'] or source['identity_scope']!='DISCRETE_MOLECULAR'):
  return None
 left,right=descriptor(source['graph_view']),candidate['descriptor']
 if (left['components']!=1 or right['components']!=1 or left['charge']!=right['charge']
     or left['radicals'] or right['radicals'] or left['formula']==right['formula']):
  return None
 full=structural_pair(left,right)
 basis=full.get('charge_comparison_basis',{})
 if (full['assessment']=='DISTINCT' and basis.get('delta_total_H')
     and basis.get('delta_net_charge')==0 and not basis.get('protonation_attribution_supported')):
  return {'reason':'COMPLETE_MOLECULAR_COMPOSITION_DIFFERS','source_formula':left['formula'],
          'candidate_formula':right['formula'],'full_graph_assessment':full['assessment'],'charge_basis':basis}
 return None

def _compare_registry_candidate_uncached(source,entry,*,retain_full=False):
 candidate=qualify_candidate(entry['candidate'],source)
 candidate['obligations']+=entry['issues']
 raw=compare(source,candidate);dims=raw['dimension_comparisons'];hard=_hard_chemical_blockers(source['obligations']+candidate['obligations'])
 candidate_obligations=[r for r in candidate['obligations'] if r not in ANCESTRY_ONLY]
 distinction=None
 if hard or entry['issues'] or candidate['identity_evidence_conflicted']:chem='CHEMICALLY_UNRESOLVED'
 elif any(v=='EXACT_INCOMPATIBLE' for v in dims.values()):chem='CHEMICALLY_DIFFERENT'
 elif raw['reconciliation']['complete_for_requested_dimensions'] and not candidate_obligations:chem='CHEMICALLY_EQUIVALENT'
 elif (distinction:=_composition_difference(source,candidate,candidate_obligations)):chem='CHEMICALLY_DIFFERENT'
 else:chem='CHEMICALLY_UNRESOLVED'
 if source['source_conflicts'] and source['binding_valid']:identity='SOURCE_CONFLICT'
 elif source['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' and source['binding_valid'] and chem=='CHEMICALLY_EQUIVALENT':identity='SOURCE_IDENTITY_SUPPORTED'
 else:identity='SOURCE_IDENTITY_UNRESOLVED'
 independence=assess_independence(source,candidate)
 result=dict(candidate_substance_id=candidate['candidate_substance_id'],preferred_name=candidate['preferred_name'],chemical_status=chem,source_identity_status=identity,dimension_comparisons=dims,comparison_scope='QUALIFIED_SOURCE_ASSERTIONS_VS_ACCEPTED_REGISTRY_GRAPH_AND_FIXED_COMPOSITION',source_obligations=source['obligations'],candidate_obligations=candidate['obligations'],reconciliation_obligations=raw['reconciliation']['remaining_obligations'],independence_status=independence['status'],shared_lineage_roots=candidate['shared_lineage_roots'],independent_external_corroboration=False,registry_issues=entry['issues'])
 if distinction:result['full_graph_distinction']=distinction
 if retain_full:result.update(full_comparison=raw,independence=independence)
 return result

# Exact-input memoization only. Fresh snapshots, search completeness, admission
# and transaction-time matching still run. Snapshot labels are provenance, not
# chemical inputs; all current candidate facts/identifiers/issues stay in key.
import copy,json,hashlib
from dataclasses import asdict,is_dataclass
from collections import OrderedDict
_PAIR_CACHE=OrderedDict()
def _fingerprint(value):
 def encode(x):
  if is_dataclass(x):return asdict(x)
  raise TypeError('UNSUPPORTED_MEMOIZATION_INPUT')
 try:return hashlib.sha256(json.dumps(value,sort_keys=True,default=encode,ensure_ascii=False).encode()).hexdigest()
 except (TypeError,ValueError):return None
def compare_registry_candidate(source,entry,*,retain_full=False):
 if retain_full:return _compare_registry_candidate_uncached(source,entry,retain_full=True)
 candidate=asdict(entry['candidate']);candidate['provenance'].pop('registry_snapshot_sha256',None)
 facts={**entry,'candidate':candidate}
 key=(source.get('_comparison_fingerprint') or _fingerprint(source),_fingerprint(facts))
 if None in key:return _compare_registry_candidate_uncached(source,entry)
 if key not in _PAIR_CACHE:
  result=_compare_registry_candidate_uncached(source,entry)
  _PAIR_CACHE[key]=copy.deepcopy(result)
  if len(_PAIR_CACHE)>8192:_PAIR_CACHE.popitem(last=False)
 return copy.deepcopy(_PAIR_CACHE[key])

class RegistryMatcher:
 def __init__(self,registry,*,official_validator=None):
  from derived_index import engine_version
  self.registry=registry
  self.retriever=getattr(registry,'_candidate_retriever',None)
  if self.retriever is None or self.retriever.engine_version!=engine_version():
   self.retriever=RegistryRetriever(registry)
   registry._candidate_retriever=self.retriever
  self.official_validator=official_validator
 def _match_identity(self,incoming,retrieval_policy,retain_full,timings=None):
  qualification_started=perf_counter()
  self.registry.assert_unchanged();policy=(retrieval_policy or RetrievalPolicy()).validate();source=qualify_source(incoming.concept);source['_comparison_fingerprint']=_fingerprint(source)
  if timings is not None:timings['source_qualification']=perf_counter()-qualification_started
  started=perf_counter()
  retrieval=self.retriever.retrieve(incoming,source,policy)
  retrieved=perf_counter()
  with validate_source_claims_once(source['claims']):
   comparisons=[compare_registry_candidate(source,self.registry.entries[sid],retain_full=retain_full) for sid in retrieval.candidate_ids]
  if timings is not None:
   timings.update(candidate_retrieval=retrieved-started,chemical_comparison=perf_counter()-retrieved)
  supported=[r['candidate_substance_id'] for r in comparisons if r['chemical_status']=='CHEMICALLY_EQUIVALENT' and r['source_identity_status']=='SOURCE_IDENTITY_SUPPORTED']
  unresolved=[r['candidate_substance_id'] for r in comparisons if r['chemical_status']=='CHEMICALLY_UNRESOLVED']
  enough=source['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' and source['binding_valid']
  if source['source_conflicts'] and source['binding_valid']:status='SOURCE_CONFLICT'
  elif not enough:status='MATCH_UNRESOLVED'
  elif len(supported)>1:status='MULTIPLE_CANONICAL_MATCHES'
  elif not retrieval.search_complete or unresolved:status='MATCH_UNRESOLVED'
  elif len(supported)==1:status='UNIQUE_CANONICAL_MATCH'
  elif all(r['chemical_status']=='CHEMICALLY_DIFFERENT' for r in comparisons):status='NO_MATCH_IN_SEARCHED_REGISTRY'
  else:status='MATCH_UNRESOLVED'
  unique=supported[0] if status=='UNIQUE_CANONICAL_MATCH' else None
  return source,dict(source_concept_id=incoming.concept.source_concept_id,status=status,unique_matched_substance_id=unique,supported_candidate_ids=supported,unresolved_possible_candidate_ids=unresolved,source_identity=dict(state=source['state'],binding_valid=source['binding_valid'],binding=source['binding'],obligations=source['obligations'],conflicts=source['source_conflicts'],evidence_package=source['full_evidence_package'],excluded_claims=source['excluded_claims']),retrieval=retrieval.to_dict(),candidate_results=comparisons,uniqueness=dict(all_registry_records_examined=retrieval.search_complete,compared=len(comparisons),excluded_by_necessary_condition=len(retrieval.excluded_candidate_ids),accounted_records=len(comparisons)+len(retrieval.excluded_candidate_ids),completeness_basis=retrieval.completeness_basis,snapshot_records=len(self.registry.entries),source_sufficient=enough,supported_count=len(supported),unresolved_count=len(unresolved),scope='ONLY_THIS_REGISTRY_SNAPSHOT_AND_IMPLEMENTED_GRAPH_COMPOSITION_SCOPE',global_nonexistence_established=False))

 def match_identity(self,incoming,retrieval_policy=None,*,timings=None):
  """Compare qualified evidence with the registry without assessing admission."""
  _,result=self._match_identity(incoming,retrieval_policy,False,timings)
  self.registry.assert_unchanged()
  return result

 def match(self,incoming,retrieval_policy=None,*,retain_full=False,timings=None):
  source,result=self._match_identity(incoming,retrieval_policy,retain_full,timings)
  admission_started=perf_counter()
  admission=assess_admission(incoming,source,self.official_validator)
  if timings is not None:timings['admission_and_official_validation']=perf_counter()-admission_started
  unique=result['unique_matched_substance_id']
  eligible=bool(unique and admission['admission_eligible'])
  proposal=dict(substance_id=unique,kind='READ_ONLY_MATCHING_PROPOSAL',admission_eligible=eligible,canonical_id_reuse_authorized=False,persisted=False) if unique else None
  self.registry.assert_unchanged()
  return dict(**result,admission=admission,matching_proposal=proposal,diagnostic_reuse_proposal=proposal if eligible else None,registry_mutations=0,new_ids_created=0,id_reuse_authorized=False,provider_requests=0)
