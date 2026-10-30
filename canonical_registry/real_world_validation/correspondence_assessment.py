"""Thin three-decision view over frozen evidence qualification/comparison.

The old correspondence result is retained. Its independence gate is not changed;
the existing computed dimension result is exposed separately for chemistry.
"""
from dataclasses import dataclass,asdict
import bootstrap
from correspondence_models import IncomingConcept,CanonicalCandidate
from source_identity_qualification import qualify as qualify_source
from candidate_identity_adapter import qualify as qualify_candidate
from identity_correspondence_comparator import compare
from evidence_adapter_contract import EvidencePackage,structural_field
from chemistry import describe
from evidence_independence_assessment import assess as assess_independence
from policy import decision as existing_admission_decision

@dataclass
class RealWorldCorrespondenceAssessment:
 source_concept_id:str
 candidate_id:str
 represented_structure_comparison:dict
 source_identity_correspondence:dict
 evidence_independence:dict
 source_specificity:dict
 unresolved_obligations:list
 source_conflicts:list
 corroboration_qualification:dict
 admission_eligibility:dict
 provenance:dict
 def to_dict(self):return asdict(self)

def _hard_chemical_blockers(obligations):
 return [r for r in obligations if r.startswith(('UNSUPPORTED_','CANDIDATE_STRUCTURE_INVALID','CANDIDATE_EVIDENCE_','CANDIDATE_IDENTIFIER_STRUCTURE_INCONSISTENCY')) or r in ('STEREO_UNSUPPORTED','ADVANCED_STEREOCHEMISTRY_UNSUPPORTED','ELECTRONIC_STATE_UNSUPPORTED')]

def represented_graphs(incoming,candidate):
 fields=[c for c in incoming.evidence_package.claims if c.claim_role=='STRUCTURAL_IDENTITY_ASSERTION' and c.source_provenance.get('interpretation_basis')=='SOURCE_TYPED_STRUCTURE' and c.source_provenance.get('origin')!='CANDIDATE_DERIVED' and c.dimension_assertions]
 if len(fields)!=1:
  return dict(status='CHEMICALLY_UNRESOLVED',scope='REPRESENTED_GRAPH_ONLY',reason='ZERO_OR_MULTIPLE_QUALIFIED_SOURCE_STRUCTURAL_FIELDS',dimension_comparisons={},comparison=None,source_field_ids=[c.evidence_id for c in fields])
 c=fields[0]
 try:
  sd=describe(c.original_value);rd=describe(candidate.structure)
 except Exception as exc:return dict(status='CHEMICALLY_UNRESOLVED',scope='REPRESENTED_GRAPH_ONLY',reason='UNSUPPORTED_OR_INVALID_GRAPH:'+str(exc),dimension_comparisons={},comparison=None,source_field_ids=[c.evidence_id])
 # The graph-only question has composition scope, not material/phase scope.
 # This never changes the original incoming concept's source specificity.
 p=EvidencePackage(incoming.evidence_package.source_name,incoming.evidence_package.source_record_type,incoming.evidence_package.source_record_id,incoming.evidence_package.payload_reference)
 anchor=structural_field(p,'represented_graph',c.original_value,c.source_provenance.get('source_field'),representation=c.source_provenance.get('representation','EXPLICIT_SOURCE_GRAPH'))
 scope='DEFINED_MULTICOMPONENT_COMPOSITION' if sd['components']>1 else 'DISCRETE_MOLECULAR'
 view=IncomingConcept(incoming.source_concept_id+':represented-field',p,dict(status='ESTABLISHED',kind='EXPLICIT_STRUCTURAL_FIELD_REFERENT',evidence_ids=[anchor.evidence_id],document=incoming.binding.get('document') or 'Explicit provided source structural field'),scope,incoming.provenance)
 # A selected molecular file can be compared even when another derived field
 # in its record disagrees. Keep that inconsistency in the full source-identity
 # assessment; do not let it conceal what the supplied graph itself represents.
 ref=CanonicalCandidate(candidate.candidate_substance_id,candidate.preferred_name,candidate.structure,{**candidate.provenance,'identifiers':[]},'DEFINED_MULTICOMPONENT_COMPOSITION' if rd['components']>1 else 'DISCRETE_MOLECULAR',candidate.evidence)
 source=qualify_source(view);target=qualify_candidate(ref,source);raw=compare(source,target);rec=raw['reconciliation'];hard=_hard_chemical_blockers(source['obligations']+target['obligations'])
 if hard:status='CHEMICALLY_UNRESOLVED'
 elif any(v=='EXACT_INCOMPATIBLE' for v in raw['dimension_comparisons'].values()):status='CHEMICALLY_DIFFERENT'
 elif rec['complete_for_requested_dimensions'] and source['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' and not [x for x in target['obligations'] if x not in ('CANDIDATE_INDEPENDENCE_UNESTABLISHED','CANDIDATE_DERIVED_FROM_INCOMING_SOURCE')]:status='CHEMICALLY_EQUIVALENT'
 else:status='CHEMICALLY_UNRESOLVED'
 return dict(status=status,scope='REPRESENTED_MOLECULAR_GRAPH_AND_EXPLICIT_COMPOSITION_ONLY',reason='EXISTING_DIMENSION_RESULT_SEPARATED_FROM_INDEPENDENCE',dimension_comparisons=raw['dimension_comparisons'],comparison=raw,source_field_ids=[c.evidence_id],chemical_capability_blockers=hard,independent_corroboration='NOT_INFERRED',source_concept_specificity='ASSESSED_SEPARATELY')

def assess(incoming,candidate,*,enabled=False):
 if not enabled:return dict(diagnostic_enabled=False,production_behavior='UNCHANGED')
 source=qualify_source(incoming);target=qualify_candidate(candidate,source);old=compare(source,target);rep=represented_graphs(incoming,candidate);ind=assess_independence(source,target)
 rep['source_record_obligations']=source['obligations'];rep['candidate_record_obligations']=target['obligations'];rep['selected_reference_graph_scope_excludes_derived_identifier_assertions']=True
 hard=_hard_chemical_blockers(source['obligations']+target['obligations']);chem_obligations=[x for x in target['obligations'] if x not in ('CANDIDATE_INDEPENDENCE_UNESTABLISHED','CANDIDATE_DERIVED_FROM_INCOMING_SOURCE')]
 if source['source_conflicts'] and source['binding_valid']:identity='SOURCE_CONFLICT'
 elif not source['binding_valid'] or hard:identity='SOURCE_IDENTITY_UNRESOLVED'
 elif any(v=='EXACT_INCOMPATIBLE' for v in old['dimension_comparisons'].values()):identity='SOURCE_IDENTITY_DIFFERENT'
 elif source['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' and not chem_obligations and old['reconciliation']['complete_for_requested_dimensions']:
  identity='SOURCE_IDENTITY_CONSISTENCY_ONLY' if ind['status']=='KNOWN_DEPENDENT' else 'SOURCE_IDENTITY_CORRESPONDENCE_SUPPORTED'
 else:identity='SOURCE_IDENTITY_UNRESOLVED'
 admission=None
 if source['graph_view']:
  # Exercise the unchanged pure admission function with the evidence actually
  # available to this task. Do not invent official validation/provider records.
  try:admission=existing_admission_decision(describe(source['graph_view']),None,{'status':'NOT_QUERIED','rows':[]},'Explicit source structural referent',{'explicit_structure':True},source_complete=source['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY')
  except Exception as exc:admission={'status':'UNRESOLVED','reason_codes':['ADMISSION_ASSESSMENT_ERROR:'+str(exc)]}
 else:admission={'status':'UNRESOLVED','reason_codes':['NO_VALIDATED_SOURCE_GRAPH']}
 eligible=admission['status']=='AUTO_ACCEPT'
 # Even a hypothetical acceptance cannot write a record in this diagnostic.
 result=RealWorldCorrespondenceAssessment(incoming.source_concept_id,candidate.candidate_substance_id,rep,dict(status=identity,scope=incoming.identity_scope,binding_valid=source['binding_valid'],legacy_independence_gated_result=old['correspondence_status'],comparison=old,independently_corroborated_exact_identity=False),ind,dict(state=source['state'],obligations=source['obligations'],binding=source['binding'],full_evidence_package=source['full_evidence_package'],excluded_claims=source['excluded_claims']),[{'layer':'source','reason':r} for r in source['obligations']]+[{'layer':'candidate','reason':r} for r in target['obligations']],source['source_conflicts'],dict(independent_corroboration='NOT_ESTABLISHED',external_policy='UNCHANGED',public_validation_material_is_qualifying_provider=False),dict(eligible=eligible,recommendation='WITHHOLD' if not eligible else 'REVIEW_NO_MUTATION',existing_policy_result=admission,official_reference_InChI_validation='NOT_SUPPLIED',qualifying_external_provider_evidence='NOT_SUPPLIED',registry_mutation='NOT_PERFORMED'),dict(source=incoming.provenance,candidate=candidate.provenance,version='1.0',production_admission_modified=False))
 return dict(diagnostic_enabled=True,**result.to_dict())
