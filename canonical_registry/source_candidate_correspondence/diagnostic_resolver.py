"""Default-off end-to-end source evidence + independently supplied candidates."""
import bootstrap
from correspondence_models import EvidencePolicy
from source_identity_qualification import qualify as qualify_source
from candidate_identity_adapter import qualify as qualify_candidate
from identity_correspondence_comparator import compare

def resolve_correspondence(incoming_concept,candidate_set,evidence_policy=None):
 policy=(evidence_policy or EvidencePolicy()).validate()
 if not policy.enabled:return dict(diagnostic_enabled=False,production_behavior='UNCHANGED',canonical_admission='NOT_PERFORMED')
 candidates=list(candidate_set);ids=[c.candidate_substance_id for c in candidates]
 if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_CANDIDATE_ID')
 source=qualify_source(incoming_concept);limited=len(candidates)>policy.max_candidates
 results=[compare(source,qualify_candidate(c,source)) for c in candidates[:policy.max_candidates]]
 supported=[r['candidate_substance_id'] for r in results if r['correspondence_status']=='CORRESPONDENCE_SUPPORTED']
 unresolved=[r['candidate_substance_id'] for r in results if r['correspondence_status']=='CORRESPONDENCE_UNRESOLVED']
 source_bound=source['binding_valid']
 if source_bound and source['source_conflicts']:summary='SOURCE_IDENTITY_CONFLICT'
 elif len(supported)>1:summary='MULTIPLE_SUPPORTED_CANDIDATES'
 elif len(supported)==1 and not unresolved and not limited:summary='UNIQUE_SUPPORTED_CANDIDATE'
 elif supported:summary='CANDIDATE_SET_AMBIGUOUS'
 elif not candidates:summary='NO_SUPPORTED_CANDIDATE_IN_SET'
 elif not limited and all(r['correspondence_status']=='CORRESPONDENCE_DIFFERENT' for r in results):summary='NO_SUPPORTED_CANDIDATE_IN_SET'
 elif unresolved or source['state']!='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' or limited:summary='SOURCE_IDENTITY_UNRESOLVED'
 else:summary='NO_SUPPORTED_CANDIDATE_IN_SET'
 # A supported plus unresolved alternative does not establish uniqueness.
 no_match_basis='NO_CANDIDATES_SUPPLIED' if not candidates else 'ALL_SUPPLIED_CANDIDATES_DEMONSTRABLY_DIFFERENT' if results and all(r['correspondence_status']=='CORRESPONDENCE_DIFFERENT' for r in results) and not limited else 'UNRESOLVED_CANDIDATES_OR_SOURCE' if not supported else 'SUPPORTED_WITHIN_SUPPLIED_SET_ONLY'
 source_output={k:([c.to_dict() for c in v] if k=='claims' else v) for k,v in source.items()}
 duplicate_groups=[]
 if len(supported)>1:
  from chemistry import describe
  from charge_comparison_attribution import compare as graph_compare
  from isotope_comparator import exact_dimension
  qualified={r['candidate_substance_id']:r['candidate_evidence'] for r in results}
  for i,a in enumerate(supported):
   for b in supported[i+1:]:
    x,y=qualified[a]['descriptor'],qualified[b]['descriptor'];cmp=graph_compare(x,y)
    if cmp['assessment']=='EXACT' and exact_dimension(x['smiles'],y['smiles'],'isotope')=='EQUIVALENT':duplicate_groups.append({'left':a,'right':b,'relation':'EQUIVALENT_CANDIDATE_RECORDS','merge_performed':False})
 return dict(diagnostic_enabled=True,source_concept_id=incoming_concept.source_concept_id,source_identity=source_output,candidate_ids=ids,candidate_results=results,candidate_set_summary=summary,unique_supported_candidate_id=supported[0] if summary=='UNIQUE_SUPPORTED_CANDIDATE' else None,supported_candidate_ids=supported,unresolved_candidate_ids=unresolved,source_conflicts=source['source_conflicts'],unresolved_obligations=source['obligations'],duplicate_candidate_diagnostics=duplicate_groups,no_supported_basis=no_match_basis,candidate_search=dict(contract=policy.search_exhaustiveness,supplied=len(candidates),evaluated=len(results),budget_exhausted=limited,global_no_match_established=False),provenance=dict(policy_version=policy.version,incoming_provenance=incoming_concept.provenance),final_diagnostic_decision=summary,canonical_admission='NOT_PERFORMED',provider_queries=0,persistent_alias_promotion='NOT_PERFORMED')
