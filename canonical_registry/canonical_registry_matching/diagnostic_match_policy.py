"""Call the existing admission function; never authorize a persistent ID reuse."""
import bootstrap
from chemistry import describe
from policy import decision

def input_category(incoming,source):
 from chemical_input_policy import qualified,VERSION as CHEMICAL_VERSION
 pkg=incoming.concept.evidence_package
 if qualified(pkg):
  valid=source['binding_valid'] and source['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' and not source['source_conflicts']
  return dict(category='VALIDATED_MOLECULAR_INTERPRETATION',policy_version=CHEMICAL_VERSION,verified_explicit_structure=False,validated_chemical_interpretation=valid,persistent_structure_eligible=valid,external_exemption='CHEMICALLY_QUALIFIED_INTERPRETATION' if valid else 'NOT_APPLICABLE',bound_source_structure_evidence_ids=list(incoming.concept.binding.get('evidence_ids',[])),independent_registry_ancestry_required_for_structural_lookup=False)
 from internal_structure_policy import authorized,POLICY,VERSION,SYSTEM,TABLE
 pkg=incoming.concept.evidence_package
 if (pkg.source_name,pkg.source_record_type)==(SYSTEM,TABLE):
  valid=authorized(pkg) and source['binding_valid'] and source['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' and not source['source_conflicts']
  return dict(category=POLICY if authorized(pkg) else 'UNAUTHORIZED_OR_UNVERIFIED_WAREHOUSE_ASSERTION',policy_version=VERSION,verified_explicit_structure=False,trusted_internal_structure=valid,persistent_structure_eligible=valid,upstream_provider_provenance='UNKNOWN_NOT_REQUIRED_BY_INTERNAL_POLICY',external_exemption='TRUSTED_INTERNAL_POLICY' if valid else 'NOT_APPLICABLE',bound_source_structure_evidence_ids=list(incoming.concept.binding.get('evidence_ids',[])),independent_registry_ancestry_required_for_structural_lookup=False)
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
  if category.get('validated_chemical_interpretation',False):
   official=None
  if official is None and official_validator is not None:official=official_validator(d)
  if official is not None:
   # The existing policy trusts its official-validator input. Bind that input
   # to this exact source graph at the new API boundary, without changing it.
   official={**official,'agrees':bool(official.get('agrees') and official.get('inchi')==d['inchi'] and official.get('inchikey')==d['inchikey'])}
 assertion={**incoming.form_assertion,'explicit_structure':category['verified_explicit_structure'] or category.get('trusted_internal_structure',False) or category.get('validated_chemical_interpretation',False)}
 complete=source['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' and source['binding_valid']
 result=decision(d,official,incoming.external_evidence,incoming.name,assertion,incoming.source_profile,source_complete=complete)
 from internal_structure_policy import authorized
 if authorized(incoming.concept.evidence_package):
  blockers=incoming.concept.evidence_package.source_attributes.get('internal_validation_blockers',[])
  if 'UNSUPPORTED_MATERIAL_SCOPE' in blockers:result.update(status='OUT_OF_SCOPE',reason_codes=blockers)
  elif blockers:result.update(status='CONFLICT' if any('CONTRADICTION' in b for b in blockers) else 'UNRESOLVED',reason_codes=blockers)
  elif source['source_conflicts']:result.update(status='CONFLICT',reason_codes=['TRUSTED_INTERNAL_STRUCTURAL_CONTRADICTION'])
  elif result['status']=='AUTO_ACCEPT':result['reason_codes']=['TRUSTED_INTERNAL_STRUCTURE_ASSERTION_VALIDATED']
 return dict(input_classification=category,official_validation=official,external_evidence_origin=incoming.evidence_origin,existing_policy_result=result,admission_eligible=result['status']=='AUTO_ACCEPT',external_corroboration_exemption=category['external_exemption'],policy_function='policy.decision (unchanged)',known_dependence='Provider qualification rejects SOURCE_DEPENDENCE_KNOWN',unknown_dependence='Existing qualifying_lineage permits SOURCE_DEPENDENCE_UNKNOWN; not audited independence',registry_ancestry_is_not_external_corroboration=True,persistent_id_reuse_authorized=False,new_id_creation_authorized=False)
