import hashlib,json
from charge_evidence_models import ChargeDimensionEvidence
from neutral_nitro_semantics import observe
from source_context_closure import assess
def build(name,aliases,candidate):
    context=assess(name,aliases,candidate);obs,sites=observe(candidate)
    complete=context['complete'] and obs.get('supported_candidate_envelope',False) and bool(sites)
    deps=list(context['unresolved'])
    if not obs.get('supported_candidate_envelope'):deps.append('CANDIDATE_OUTSIDE_CLOSED_ENVELOPE')
    if not sites:deps.append('NO_VALIDATED_NEUTRAL_NITRO_SITE')
    binding={'source_names':[name]+list(aliases),'candidate':obs.get('canonical_smiles')}
    evidence=ChargeDimensionEvidence(evidence_id=hashlib.sha256(json.dumps(binding,sort_keys=True).encode()).hexdigest(),source_claim_ids=[x['claim_id'] for x in context['claims']],nomenclature_rule_ids=['IUPAC-P13.1','IUPAC-P74.2.2.1.10'],semantic_owner='single_benzene_component',source_scope={'contract':'NSC-002','claims':context['claims'],'checks':context['checks'],'binding':binding},candidate_correspondence={'status':'SUPPORTED' if context['operation_result']=='SUPPORTED' else 'UNKNOWN'},structural_observations=obs,relevant_sites=sites,site_coverage={'complete':complete,'basis':'Full supported grammar and complete candidate graph, every supplied alias independently in scope and compatible.','all_other_sites_excluded':complete},unresolved_dependencies=deps,source_assertions=context['assertions'],dimension_result='SUPPORTED' if complete else 'UNKNOWN',operation_result=context['operation_result'],reason_codes=['COMPLETE_NEUTRAL_NITRO_SOURCE_CONTEXT' if complete else 'CHARGE_SOURCE_CONTEXT_INCOMPLETE'])
    return evidence.validate()
