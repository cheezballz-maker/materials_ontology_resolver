"""Call the existing admission function; never authorize a persistent ID reuse."""
import bootstrap
from chemistry import describe
from policy import decision

def input_category(incoming,source):
 bound=set(incoming.concept.binding.get('evidence_ids',[]))
 direct=[c for c in source['claims'] if c.evidence_id in bound and c.claim_role=='STRUCTURAL_IDENTITY_ASSERTION' and c.source_provenance.get('interpretation_basis')=='SOURCE_TYPED_STRUCTURE' and c.source_provenance.get('origin')=='SOURCE_PROVIDED' and c.source_provenance.get('binding_policy')=='BINDING_IDENTITY_ASSERTION']
 explicit_route=incoming.concept.binding.get('kind') in ('EXPLICIT_STRUCTURAL_FIELD_REFERENT','EXPLICIT_SOURCE_ASSERTION')
 supplied=bool(direct) and explicit_route
 verified=supplied and source['binding_valid'] and source['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' and not source['source_conflicts']
 category='EXPLICIT_SOURCE_STRUCTURE' if supplied else 'NAME_DERIVED_OR_OTHER_QUALIFIED_EVIDENCE' if source['graph_view'] else 'BROAD_OR_UNQUALIFIED_SOURCE_CONCEPT'
 return dict(category=category,verified_explicit_structure=verified,bound_source_structure_evidence_ids=[c.evidence_id for c in direct],external_exemption='APPLICABLE_VERIFIED_EXPLICIT_STRUCTURE' if verified else 'NOT_APPLICABLE',independent_registry_ancestry_required_for_structural_lookup=False)

def assess_admission(incoming,source,official_validator=None):
 category=input_category(incoming,source);official=incoming.official_validation;graph=source['graph_view'];d=None
 if graph:
  d=describe(graph)
  if official is None and official_validator is not None:official=official_validator(d)
  if official is not None:
   # The existing policy trusts its official-validator input. Bind that input
   # to this exact source graph at the new API boundary, without changing it.
   official={**official,'agrees':bool(official.get('agrees') and official.get('inchi')==d['inchi'] and official.get('inchikey')==d['inchikey'])}
 assertion={**incoming.form_assertion,'explicit_structure':category['verified_explicit_structure']}
 complete=source['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' and source['binding_valid']
 result=decision(d,official,incoming.external_evidence,incoming.name,assertion,incoming.source_profile,source_complete=complete)
 return dict(input_classification=category,official_validation=official,external_evidence_origin=incoming.evidence_origin,existing_policy_result=result,admission_eligible=result['status']=='AUTO_ACCEPT',external_corroboration_exemption=category['external_exemption'],policy_function='policy.decision (unchanged)',known_dependence='Provider qualification rejects SOURCE_DEPENDENCE_KNOWN',unknown_dependence='Existing qualifying_lineage permits SOURCE_DEPENDENCE_UNKNOWN; not audited independence',registry_ancestry_is_not_external_corroboration=True,persistent_id_reuse_authorized=False,new_id_creation_authorized=False)
