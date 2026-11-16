"""Creation adds scope/completeness requirements, never changes admission."""
import bootstrap
from comparison_session import qualify_source
from chemistry import describe

def assess(incoming,match):
 reasons=[];ad=match['admission'];source=match['source_identity']
 if not (ad['input_classification']['verified_explicit_structure'] or ad['input_classification'].get('trusted_internal_structure',False) or ad['input_classification'].get('validated_chemical_interpretation',False)):reasons.append('QUALIFIED_CHEMICAL_INTERPRETATION_REQUIRED')
 if not ad['admission_eligible']:reasons+=ad['existing_policy_result']['reason_codes']
 if source['state']!='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' or not source['binding_valid']:reasons.append('SOURCE_IDENTITY_INSUFFICIENT')
 if source['conflicts']:reasons.append('BLOCKING_SOURCE_CONTRADICTION')
 if incoming.concept.identity_scope not in ('DISCRETE_MOLECULAR','DEFINED_MULTICOMPONENT_COMPOSITION'):reasons.append('UNSUPPORTED_CREATION_SCOPE')
 if not match['retrieval']['search_complete']:reasons.append('INCOMPLETE_REGISTRY_SEARCH')
 if match['unresolved_possible_candidate_ids']:reasons.append('UNRESOLVED_POSSIBLE_DUPLICATE')
 if match['status']!='NO_MATCH_IN_SEARCHED_REGISTRY':reasons.append('COMPLETE_NO_MATCH_REQUIRED')
 graph=qualify_source(incoming.concept)['graph_view']
 return dict(eligible=not reasons,reasons=sorted(set(reasons)),scope='EXISTING_VALIDATED_MOLECULAR_AND_FIXED_COMPOSITION_CONTRACT',graph=graph,descriptor=describe(graph) if graph else None,global_uniqueness_claim=False)
