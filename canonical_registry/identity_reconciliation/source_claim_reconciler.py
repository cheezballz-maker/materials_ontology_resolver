"""No voting, IDs, provider calls or alias writes; partial evidence combines by dimension."""
from dimension_claim_comparator import compare_assertions

def _validate_claim(claim):
    claim.validate()

def reconcile(claims,candidate_assertions,required_dimensions,referent_id):
    byid={c.evidence_id:c for c in claims};obligations=[];comparisons=[];roots={};support={d:[] for d in required_dimensions};incompatible=[];broad=[];usable=[];pairwise=[]
    if len(byid)!=len(claims):raise ValueError('DUPLICATE_EVIDENCE_ID')
    def lineage(cid,path=()):
        if cid in path:raise ValueError('DEPENDENCY_CYCLE')
        if cid not in byid:raise ValueError('DEPENDENCY_MISSING')
        c=byid[cid]
        if c.source_provenance.get('origin')=='CANDIDATE_DERIVED':raise ValueError('CANDIDATE_DERIVED_LINEAGE')
        if c.source_provenance.get('interpretation_basis') not in ('SOURCE_TYPED_STRUCTURE','RULE_ESTABLISHED'):raise ValueError('UNESTABLISHED_DEPENDENCY')
        if not c.derivation_dependencies:return {cid}
        return set().union(*(lineage(d,path+(cid,)) for d in c.derivation_dependencies))
    for c in claims:
        _validate_claim(c);p=c.source_provenance;role=c.claim_role;established=p.get('role_established') is True
        dims=set(c.dimension_assertions) or set(required_dimensions)
        if c.referent_id!=referent_id:raise ValueError('REFERENT_LINK_NOT_ESTABLISHED')
        if p.get('origin')=='CANDIDATE_DERIVED':
            comparisons.append({'evidence_id':c.evidence_id,'relationship':'CANDIDATE_OBSERVATION_ONLY','dimensions':{}});continue
        if role=='SEARCH_LABEL' and established:
            comparisons.append({'evidence_id':c.evidence_id,'relationship':'NON_BINDING_METADATA','dimensions':{}});continue
        trusted=p.get('interpretation_basis') in ('SOURCE_TYPED_STRUCTURE','RULE_ESTABLISHED') and established
        try:root=lineage(c.evidence_id) if trusted else set()
        except ValueError as e:root=set();trusted=False;obligations.append({'evidence_id':c.evidence_id,'reason':str(e)})
        roots[c.evidence_id]=sorted(root)
        if trusted and not c.unresolved_dependencies:usable.append(c)
        results={d:compare_assertions(c.dimension_assertions.get(d),candidate_assertions.get(d),d) if trusted else 'UNKNOWN' for d in sorted(dims)}
        if not trusted or c.unresolved_dependencies or not c.dimension_assertions:obligations.append({'evidence_id':c.evidence_id,'reason':'ACTIVE_IDENTITY_CLAIM_UNRESOLVED','dependencies':c.unresolved_dependencies})
        for d,r in results.items():
            if r=='EXACT_INCOMPATIBLE':incompatible.append({'evidence_id':c.evidence_id,'dimension':d})
            elif r=='BROADER_THAN_CANDIDATE':broad.append({'evidence_id':c.evidence_id,'dimension':d})
            elif r in ('UNKNOWN','NARROWER_THAN_CANDIDATE'):obligations.append({'evidence_id':c.evidence_id,'dimension':d,'reason':r})
            if d in support and r in ('EXACT_COMPATIBLE','NOT_APPLICABLE'):support[d].append(c.evidence_id)
        comparisons.append({'evidence_id':c.evidence_id,'dimensions':results,'source_provenance':p,'derivation_roots':sorted(root)})
    # Source/source contradictions must survive even when the proposed candidate
    # is broader than both exact source claims (e.g. R versus S vs unspecified).
    for index,left in enumerate(usable):
        for right in usable[index+1:]:
            for dim in set(left.dimension_assertions)&set(right.dimension_assertions):
                relation=compare_assertions(left.dimension_assertions[dim],right.dimension_assertions[dim],dim)
                pairwise.append({'left':left.evidence_id,'right':right.evidence_id,'dimension':dim,'relationship':relation})
                if relation=='EXACT_INCOMPATIBLE':incompatible.append({'evidence_id':left.evidence_id,'other_evidence_id':right.evidence_id,'dimension':dim,'basis':'ESTABLISHED_SOURCE_SOURCE_CONTRADICTION'})
    unsupported=[d for d,ids in support.items() if not ids]
    outcome='RECONCILIATION_CONFLICT' if incompatible else 'RECONCILIATION_UNRESOLVED' if obligations or unsupported else 'RECONCILED_COMPATIBLE'
    candidate_values=(candidate_assertions.get('constitution') or {}).get('structures',[])
    return {'result':outcome,'supported_dimensions':{d:ids for d,ids in support.items() if ids},'unresolved_dimensions':unsupported,'broad_claims':broad,'incompatible_claims':incompatible,'remaining_obligations':obligations,'claim_comparisons':comparisons,'pairwise_source_comparisons':pairwise,'dependency_roots':roots,'unique_source_lineages':sorted(set(v for root in roots.values() for v in root)),'required_dimensions':list(required_dimensions),'referent_id':referent_id,'candidate_binding':candidate_values[0] if len(candidate_values)==1 else None,'complete_for_requested_dimensions':outcome=='RECONCILED_COMPATIBLE','canonical_identity_admission':'NOT_PERFORMED','provider_corroboration':'SEPARATE_NOT_ASSESSED'}
