"""Upstream independence is distinct from chemical field agreement."""
def assess(source,candidate):
 p=candidate['provenance'];shared=candidate['shared_lineage_roots'];known='CANDIDATE_DERIVED_FROM_INCOMING_SOURCE' in candidate['obligations']
 audit=p.get('independence_audit',{})
 if shared or known:status='KNOWN_DEPENDENT';reason='SHARED_SOURCE_RECORD_OR_EVIDENCE_ROOT_OR_EXPLICIT_DERIVATION'
 elif candidate['independent'] and p.get('independence_status')=='ESTABLISHED_BY_AUDITED_PROVENANCE' and audit.get('original_source_attribution') and audit.get('mapping_route') and audit.get('documented_derivation_review'):
  status='INDEPENDENTLY_ESTABLISHED';reason='AUDITED_ORIGINAL_SOURCE_AND_DERIVATION_PROVENANCE'
 else:status='INDEPENDENCE_UNESTABLISHED';reason='SEPARATELY_SUPPLIED_FIELDS_DO_NOT_PROVE_INDEPENDENT_UPSTREAM_ORIGIN'
 dependent_fields=[dict(evidence_id=c.evidence_id,dependencies=c.derivation_dependencies,field=c.source_provenance.get('source_field')) for c in source['claims'] if c.derivation_dependencies]
 return dict(status=status,reason=reason,shared_lineage_roots=shared,source_lineage_roots=source['source_lineage_roots'],candidate_lineage_roots=p.get('lineage_roots',[]),candidate_provenance=p,within_record_derived_fields=dependent_fields,documentary_grounding_is_not_independence=True,download_is_not_corroboration=True,independent_corroboration='NOT_ESTABLISHED',qualifying_provider_record='NOT_PROVIDED_TO_EXISTING_GATE')
