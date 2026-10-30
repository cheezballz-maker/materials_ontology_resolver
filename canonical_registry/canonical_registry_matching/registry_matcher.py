"""Source qualification → retrieval → hardened comparison → proposal only."""
import bootstrap
from comparison_session import qualify_source,qualify_candidate,compare
from correspondence_assessment import _hard_chemical_blockers
from evidence_independence_assessment import assess as assess_independence
from registry_candidate_retriever import RegistryRetriever
from registry_matching_models import RetrievalPolicy
from diagnostic_match_policy import assess_admission

ANCESTRY_ONLY={'CANDIDATE_INDEPENDENCE_UNESTABLISHED','CANDIDATE_DERIVED_FROM_INCOMING_SOURCE'}

def compare_registry_candidate(source,entry,*,retain_full=False):
 candidate=qualify_candidate(entry['candidate'],source)
 candidate['obligations']+=entry['issues']
 raw=compare(source,candidate);dims=raw['dimension_comparisons'];hard=_hard_chemical_blockers(source['obligations']+candidate['obligations'])
 candidate_obligations=[r for r in candidate['obligations'] if r not in ANCESTRY_ONLY]
 if hard or entry['issues'] or candidate['identity_evidence_conflicted']:chem='CHEMICALLY_UNRESOLVED'
 elif any(v=='EXACT_INCOMPATIBLE' for v in dims.values()):chem='CHEMICALLY_DIFFERENT'
 elif raw['reconciliation']['complete_for_requested_dimensions'] and not candidate_obligations:chem='CHEMICALLY_EQUIVALENT'
 else:chem='CHEMICALLY_UNRESOLVED'
 if source['source_conflicts'] and source['binding_valid']:identity='SOURCE_CONFLICT'
 elif source['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' and source['binding_valid'] and chem=='CHEMICALLY_EQUIVALENT':identity='SOURCE_IDENTITY_SUPPORTED'
 else:identity='SOURCE_IDENTITY_UNRESOLVED'
 independence=assess_independence(source,candidate)
 result=dict(candidate_substance_id=candidate['candidate_substance_id'],preferred_name=candidate['preferred_name'],chemical_status=chem,source_identity_status=identity,dimension_comparisons=dims,comparison_scope='QUALIFIED_SOURCE_ASSERTIONS_VS_ACCEPTED_REGISTRY_GRAPH_AND_FIXED_COMPOSITION',source_obligations=source['obligations'],candidate_obligations=candidate['obligations'],reconciliation_obligations=raw['reconciliation']['remaining_obligations'],independence_status=independence['status'],shared_lineage_roots=candidate['shared_lineage_roots'],independent_external_corroboration=False,registry_issues=entry['issues'])
 if retain_full:result.update(full_comparison=raw,independence=independence)
 return result

class RegistryMatcher:
 def __init__(self,registry,*,official_validator=None):
  self.registry=registry;self.retriever=RegistryRetriever(registry);self.official_validator=official_validator
 def match(self,incoming,retrieval_policy=None,*,retain_full=False):
  self.registry.assert_unchanged();policy=(retrieval_policy or RetrievalPolicy()).validate();source=qualify_source(incoming.concept)
  retrieval=self.retriever.retrieve(incoming,source,policy)
  comparisons=[compare_registry_candidate(source,self.registry.entries[sid],retain_full=retain_full) for sid in retrieval.candidate_ids]
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
  admission=assess_admission(incoming,source,self.official_validator)
  unique=supported[0] if status=='UNIQUE_CANONICAL_MATCH' else None
  eligible=bool(unique and admission['admission_eligible'])
  proposal=dict(substance_id=unique,kind='READ_ONLY_MATCHING_PROPOSAL',admission_eligible=eligible,canonical_id_reuse_authorized=False,persisted=False) if unique else None
  self.registry.assert_unchanged()
  return dict(source_concept_id=incoming.concept.source_concept_id,status=status,unique_matched_substance_id=unique,supported_candidate_ids=supported,unresolved_possible_candidate_ids=unresolved,source_identity=dict(state=source['state'],binding_valid=source['binding_valid'],binding=source['binding'],obligations=source['obligations'],conflicts=source['source_conflicts'],evidence_package=source['full_evidence_package'],excluded_claims=source['excluded_claims']),retrieval=retrieval.to_dict(),candidate_results=comparisons,uniqueness=dict(all_registry_records_examined=retrieval.search_complete,compared=len(comparisons),snapshot_records=len(self.registry.entries),source_sufficient=enough,supported_count=len(supported),unresolved_count=len(unresolved),scope='ONLY_THIS_REGISTRY_SNAPSHOT_AND_IMPLEMENTED_GRAPH_COMPOSITION_SCOPE',global_nonexistence_established=False),admission=admission,matching_proposal=proposal,diagnostic_reuse_proposal=proposal if eligible else None,registry_mutations=0,new_ids_created=0,id_reuse_authorized=False,provider_requests=0)
