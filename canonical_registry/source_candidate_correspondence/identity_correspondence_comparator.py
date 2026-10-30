"""Chemical correspondence; retrieval/labels never set the result."""
import bootstrap
from correspondence_models import IdentityCorrespondenceResult
from identity_evidence_models import DIMENSIONS
from isotope_comparator import reconcile

def compare(source,candidate):
 rec=reconcile(source['claims'],candidate['assertions'],DIMENSIONS,source['full_evidence_package']['source_name']+':'+source['full_evidence_package']['source_record_type']+':'+source['full_evidence_package']['source_record_id'])
 dimensions={}
 for d in DIMENSIONS:
  values=[c.get('dimensions',{}).get(d) for c in rec['claim_comparisons']]
  dimensions[d]='EXACT_INCOMPATIBLE' if 'EXACT_INCOMPATIBLE' in values else 'EXACT_COMPATIBLE' if d in rec['supported_dimensions'] else 'BROADER_THAN_CANDIDATE' if 'BROADER_THAN_CANDIDATE' in values else 'NARROWER_THAN_CANDIDATE' if 'NARROWER_THAN_CANDIDATE' in values else 'UNKNOWN'
 obligations=[{'reason':r} for r in source['obligations']+candidate['obligations']]+rec['remaining_obligations']
 relevant_difference=any(v=='EXACT_INCOMPATIBLE' for v in dimensions.values())
 bound=source['binding_valid']
 if bound and source['source_conflicts']:status='SOURCE_CONFLICT'
 elif not bound or not candidate['independent'] or candidate['identity_evidence_conflicted']:status='CORRESPONDENCE_UNRESOLVED'
 elif relevant_difference:status='CORRESPONDENCE_DIFFERENT'
 elif source['state']!='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' or candidate['obligations']:status='CORRESPONDENCE_UNRESOLVED'
 elif rec['complete_for_requested_dimensions']:status='CORRESPONDENCE_SUPPORTED'
 else:status='CORRESPONDENCE_UNRESOLVED'
 contradictions=source['source_conflicts']+rec['incompatible_claims']
 result=IdentityCorrespondenceResult(source['source_concept_id'],candidate['candidate_substance_id'],status,dimensions,[c.to_dict() for c in source['claims']],{k:v for k,v in candidate.items() if k!='assertions'},obligations,contradictions,dict(evidence_policy_version='1.0',candidate_independence_established=candidate['independent'],shared_lineage_roots=candidate['shared_lineage_roots'],source_binding=source['binding'],chemical_identity_scope=source['identity_scope'],canonical_admission='NOT_PERFORMED',production_exact='NOT_DECIDED',external_corroboration='SEPARATE_NOT_ASSESSED'))
 out=result.to_dict();out['reconciliation']=rec;return out
