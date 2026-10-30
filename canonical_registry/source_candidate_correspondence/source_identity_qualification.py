"""Source-supported constraints and source/source consistency, before candidates."""
import copy
import bootstrap
from identity_evidence_models import DIMENSIONS
from evidence_adapters import candidate_assertions
from chemistry import describe,parse
from molecular_capability import inspect
from isotope_comparator import reconcile
from assertion_dependencies import comparison_view

NAME_ROLES={'CHEMICAL_NAME_ASSERTION','PARTIAL_IDENTITY_ASSERTION','UNVERIFIED_ALIAS'}
def qualify(incoming):
 pkg=incoming.evidence_package;byid={c.evidence_id:c for c in pkg.claims}
 if len(byid)!=len(pkg.claims):raise ValueError('DUPLICATE_EVIDENCE_ID')
 explicit_ids=set(incoming.binding.get('evidence_ids',[]))
 reasons=[]
 if not incoming.source_concept_id:reasons.append('SOURCE_CONCEPT_ID_MISSING')
 if incoming.binding.get('status')!='ESTABLISHED':reasons.append('INCOMING_REFERENT_LINK_UNESTABLISHED')
 if not incoming.binding.get('document'):reasons.append('SOURCE_BINDING_DOCUMENT_MISSING')
 if incoming.binding.get('kind') not in ('EXPLICIT_SOURCE_ASSERTION','EXPLICIT_STRUCTURAL_FIELD_REFERENT','QUALIFIED_NAME_IDENTITY','INDEPENDENTLY_VALIDATED_IDENTIFIER_MAPPING'):reasons.append('SOURCE_BINDING_ROUTE_NOT_QUALIFIED')
 if not explicit_ids or not explicit_ids<=set(byid):reasons.append('BINDING_SOURCE_CLAIM_REFERENCE_INVALID')
 selected=set(explicit_ids)&set(byid)
 for c in pkg.claims:
  p=c.source_provenance
  if p.get('binding_policy')=='BINDING_IDENTITY_ASSERTION' or c.claim_role=='UNKNOWN_ROLE':selected.add(c.evidence_id)
  if any('IDENTIFIER_GRAPH_INCONSISTENCY' in x for x in c.unresolved_dependencies):selected.add(c.evidence_id)
 pending=list(selected)
 while pending:
  for dep in byid[pending.pop()].derivation_dependencies:
   if dep in byid and dep not in selected:selected.add(dep);pending.append(dep)
 claims=[copy.deepcopy(c) for c in pkg.claims if c.evidence_id in selected]
 for c in claims:
  c.validate();c.dimension_assertions,deps=comparison_view(c.dimension_assertions)
  if deps:c.source_provenance['comparison_view_dependencies']={'component_identity_requires':deps,'original_source_evidence_unchanged':True}
 # An explicit link cannot make an unverified association/namespace into a
 # chemical assertion, nor make a candidate-derived observation into source data.
 if explicit_ids and not any(c.evidence_id in explicit_ids and c.source_provenance.get('origin')!='CANDIDATE_DERIVED' and c.source_provenance.get('interpretation_basis') in ('SOURCE_TYPED_STRUCTURE','RULE_ESTABLISHED') and bool(c.dimension_assertions) for c in claims):reasons.append('NO_QUALIFIED_BINDING_IDENTITY_ASSERTION')
 graphs=[]
 for c in claims:
  if c.source_provenance.get('origin')=='CANDIDATE_DERIVED':continue
  for a in c.dimension_assertions.values():
   if a.get('state')=='EXACT' and a.get('structures'):
    try:graphs.append(describe(a['structures'][0])['smiles'])
    except Exception:pass
 graph=graphs[0] if graphs else None
 assertions=candidate_assertions(graph) if graph else {}
 source_rec=reconcile(claims,assertions,DIMENSIONS,pkg.referent_id)
 # This is source-constraint consistency/sufficiency only. No self comparison
 # here is counted as a source-to-candidate match.
 source_conflicts=[];dependent_conflicts=[]
 for p in source_rec['pairwise_source_comparisons']:
  if p['relationship']!='EXACT_INCOMPATIBLE':continue
  lr=set(source_rec['dependency_roots'].get(p['left'],[]));rr=set(source_rec['dependency_roots'].get(p['right'],[]))
  (source_conflicts if lr and rr and lr.isdisjoint(rr) else dependent_conflicts).append(p)
 if dependent_conflicts:reasons.append('DEPENDENT_SOURCE_INTERNAL_INCONSISTENCY')
 if incoming.identity_scope not in ('DISCRETE_MOLECULAR','DEFINED_MULTICOMPONENT_COMPOSITION'):reasons.append('SOURCE_MOLECULAR_IDENTITY_SCOPE_UNESTABLISHED')
 features,capability=(inspect(describe(graph)) if graph else (None,[]));reasons.extend(capability)
 if features:
  if features['advanced_stereo']:reasons.append('ADVANCED_STEREOCHEMISTRY_UNSUPPORTED')
  if features['stereo_state'] in ('PARTIAL','UNSPECIFIED'):reasons.append('SOURCE_STEREOCHEMISTRY_UNSPECIFIED')
  if features['component_count']>1 and incoming.identity_scope!='DEFINED_MULTICOMPONENT_COMPOSITION':reasons.append('COMPONENT_ENTITY_SCOPE_UNESTABLISHED')
 else:reasons.append('SOURCE_COMPLETE_GRAPH_NOT_ESTABLISHED')
 # Source constraints may be partial; their exact graph view must not fill in
 # absent source assertions. The core's per-dimension support defines coverage.
 if not source_rec['complete_for_requested_dimensions']:reasons.append('SOURCE_IDENTITY_DIMENSIONS_INCOMPLETE')
 state='CONTRADICTORY_SOURCE_IDENTITY' if source_conflicts else 'SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' if not reasons else 'INCOMPLETELY_SPECIFIED_SOURCE_IDENTITY'
 excluded=[]
 for c in pkg.claims:
  if c.evidence_id not in selected:excluded.append(dict(evidence_id=c.evidence_id,role=c.claim_role,reason='OUTSIDE_EXPLICIT_INCOMING_REFERENT_BINDING',unresolved_dependencies=c.unresolved_dependencies,source_provenance=c.source_provenance))
 binding_valid=not any(r in reasons for r in ('SOURCE_CONCEPT_ID_MISSING','INCOMING_REFERENT_LINK_UNESTABLISHED','SOURCE_BINDING_DOCUMENT_MISSING','SOURCE_BINDING_ROUTE_NOT_QUALIFIED','BINDING_SOURCE_CLAIM_REFERENCE_INVALID','NO_QUALIFIED_BINDING_IDENTITY_ASSERTION'))
 lineage=set(incoming.provenance.get('lineage_roots',[]))|set(source_rec['unique_source_lineages'])
 for c in claims:
  if c.source_provenance.get('origin')!='CANDIDATE_DERIVED':lineage.update([c.evidence_id,f'{c.source_id}:{c.source_provenance.get("source_record_type","UNKNOWN")}:{c.source_record_id}',*c.source_provenance.get('lineage_roots',[])])
 return dict(source_concept_id=incoming.source_concept_id,state=state,claims=claims,source_reconciliation=source_rec,source_conflicts=source_conflicts,dependent_internal_conflicts=dependent_conflicts,obligations=sorted(set(reasons)),graph_view=graph,identity_scope=incoming.identity_scope,source_lineage_roots=sorted(lineage),source_identity_references=[incoming.source_concept_id,pkg.referent_id,pkg.source_record_id,*byid],excluded_claims=excluded,full_evidence_package=pkg.to_dict(),binding=incoming.binding,binding_valid=binding_valid)
