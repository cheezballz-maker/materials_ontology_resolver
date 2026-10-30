"""Source-independent field contract; adapters, never the core, qualify field roles.

Scopes refer to different questions, not different chemistry. All claims remain in
the package. An association is not metadata, verified alias, or independent proof.
"""
from dataclasses import dataclass,field
import bootstrap
from identity_evidence_models import IdentityEvidence,DIMENSIONS
from evidence_adapters import assertion,candidate_assertions
from chemistry import describe

VERSION='1.0'
SCOPES=('RECORD_STRUCTURE','TERMINOLOGY','INCOMING_CONCEPT')
ALL=list(SCOPES)
@dataclass
class EvidencePackage:
 source_name:str
 source_record_type:str
 source_record_id:str
 payload_reference:dict
 claims:list=field(default_factory=list)
 claim_scopes:dict=field(default_factory=dict)
 observations:list=field(default_factory=list)
 source_attributes:dict=field(default_factory=dict)
 mapping_version:str=VERSION
 @property
 def referent_id(self):return f'{self.source_name}:{self.source_record_type}:{self.source_record_id}'
 def add(self,c,scopes):
  c.validate()
  if c.evidence_id in self.claim_scopes:raise ValueError('DUPLICATE_EVIDENCE_ID')
  self.claims.append(c);self.claim_scopes[c.evidence_id]=list(scopes);return c
 def to_dict(self):
  return dict(source_name=self.source_name,source_record_type=self.source_record_type,source_record_id=self.source_record_id,payload_reference=self.payload_reference,claims=[c.to_dict() for c in self.claims],claim_scopes=self.claim_scopes,observations=self.observations,source_attributes=self.source_attributes,mapping_version=self.mapping_version,alias_promotion='NOT_PERFORMED')

def evidence(pkg,key,role,value,path,*,binding='ACTIVE_UNRESOLVED_CLAIM',basis='UNVERIFIED',origin='SOURCE_PROVIDED',established=True,dependencies=(),unresolved=(),assertions=None,extra=None):
 p=dict(origin=origin,role_established=established,interpretation_basis=basis,source_name=pkg.source_name,source_record_type=pkg.source_record_type,source_record_id=pkg.source_record_id,source_field=path,payload_reference=pkg.payload_reference,mapping_version=VERSION,binding_policy=binding,independence='NOT_ESTABLISHED');p.update(extra or {})
 return IdentityEvidence(evidence_id=pkg.referent_id+':'+key,source_id=pkg.source_name,source_record_id=pkg.source_record_id,claim_id=key,claim_role=role,evidence_type=role,original_value=value,source_provenance=p,referent_id=pkg.referent_id,derivation_dependencies=list(dependencies),dimension_assertions=assertions or {},unresolved_dependencies=list(unresolved))

def structural_field(pkg,key,value,path,*,qualified=True,dependencies=(),representation='EXPLICIT_SOURCE_GRAPH',limited=False):
 c=evidence(pkg,key,'STRUCTURAL_IDENTITY_ASSERTION' if qualified else 'UNKNOWN_ROLE',value,path,binding='BINDING_IDENTITY_ASSERTION' if qualified else 'ACTIVE_UNRESOLVED_CLAIM',basis='SOURCE_TYPED_STRUCTURE' if qualified else 'UNVERIFIED',established=qualified,dependencies=dependencies,extra={'representation':representation,'assertion_scope':'REPRESENTED_GRAPH_ONLY','solid_phase':'NOT_ESTABLISHED','original_form_preservation':'NOT_ESTABLISHED'})
 if qualified:
  try:
   d=describe(value);c.dimension_assertions=candidate_assertions(value)
   if limited:
    c.dimension_assertions={k:v for k,v in c.dimension_assertions.items() if k in ('constitution','components','component_stoichiometry')}
   pkg.observations.append(dict(evidence_id=c.evidence_id,kind='VALIDATED_GRAPH_ATTRIBUTES',attributes=d,identity_scope='Explicit graph, not source name specificity, original SID form, or solid phase'))
  except Exception as exc:c.unresolved_dependencies=['STRUCTURE_INVALID_OR_UNSUPPORTED:'+str(exc)]
 else:c.unresolved_dependencies=['FIELD_PROVENANCE_UNESTABLISHED']
 return pkg.add(c,ALL)

def record_identifier(pkg,key,value,path,identifier_type):
 c=evidence(pkg,key,'REFERENCE_CROSS_LINK',value,path,binding='NONBINDING_ASSOCIATION',extra={'identifier_type':identifier_type,'correspondence_scope':'DATABASE_RECORD_ONLY'})
 return pkg.add(c,[])

def associated_name(pkg,key,value,path,*,generated=False,dependencies=(),role_known=True,extra=None):
 role='CHEMICAL_NAME_ASSERTION' if generated else 'REPORTED_NAME_ASSOCIATION' if role_known else 'UNKNOWN_ROLE'
 c=evidence(pkg,key,role,value,path,binding='NONBINDING_ASSOCIATION' if role_known and not generated else 'ACTIVE_UNRESOLVED_CLAIM',origin='DERIVED_SOURCE' if generated else 'SOURCE_PROVIDED',established=role_known,dependencies=dependencies,unresolved=['NAME_SEMANTICS_OR_EXACT_RECORD_CORRESPONDENCE_UNESTABLISHED'],extra=dict(generated=generated,verified_exact_alias=False,**(extra or {})))
 # Unknown roles remain active in every scope. Known associations are outside
 # represented-graph scope, but remain active within terminology/match scope.
 return pkg.add(c,['TERMINOLOGY','INCOMING_CONCEPT'] if role_known else ALL)

def identifier_field(pkg,key,value,path,kind,*,graph=None,dependency=None):
 deps=[dependency.evidence_id] if dependency else []
 c=evidence(pkg,key,'STRUCTURAL_IDENTIFIER',value,path,binding='QUALIFIED_PARTIAL_ASSERTION',origin='DERIVED_SOURCE' if dependency else 'SOURCE_PROVIDED',dependencies=deps,extra={'identifier_type':kind,'correspondence_scope':'UNVALIDATED'})
 scopes=['TERMINOLOGY','INCOMING_CONCEPT']
 try:
  if graph and dependency and dependency.dimension_assertions:
   d=describe(graph);actual=d['inchikey' if kind=='InChIKey' else 'inchi']
   agrees=value==actual
   c.source_provenance.update(interpretation_basis='RULE_ESTABLISHED' if agrees else 'UNVERIFIED',correspondence_scope='SAME_RECORD_STANDARD_INCHI_PROJECTION_ONLY',internal_consistency=agrees)
   c.unresolved_dependencies=[] if agrees else ['DERIVED_IDENTIFIER_GRAPH_INCONSISTENCY']
   scopes=[] if agrees else ALL
   pkg.observations.append(dict(kind='STRUCTURAL_IDENTIFIER_CONSISTENCY',evidence_id=c.evidence_id,matches=agrees,independent=False,canonical_form_correspondence=False,route='Local RDKit Standard InChI generation from explicit source graph',expected=actual))
  elif kind=='InChI':
   d=describe(value,'inchi');c.dimension_assertions={'constitution':assertion(d['smiles'],'constitution')};c.source_provenance.update(interpretation_basis='SOURCE_TYPED_STRUCTURE',correspondence_scope='ENCODED_CONSTITUTION_ONLY');scopes=ALL
  else:c.unresolved_dependencies=['IDENTIFIER_TO_STRUCTURE_CORRESPONDENCE_UNVALIDATED']
 except Exception as exc:c.unresolved_dependencies=['IDENTIFIER_VALIDATION_FAILED:'+str(exc)]
 return pkg.add(c,scopes)

def validated_mapping(pkg,key,value,path,smiles,document,*,independent=False):
 """Explicit typed correspondence input; does not discover or certify mappings.

 A caller must supply an auditable mapping document and original graph. This
 boundary is not exposed to raw synonym strings or automatically populated.
 """
 c=evidence(pkg,key,'STRUCTURAL_IDENTIFIER',value,path,binding='QUALIFIED_PARTIAL_ASSERTION',extra={'mapping_document':document,'independence':'ASSERTED_DISTINCT_SOURCE' if independent else 'NOT_ESTABLISHED'})
 if document and smiles:
  try:describe(smiles);c.dimension_assertions=candidate_assertions(smiles);c.source_provenance['interpretation_basis']='RULE_ESTABLISHED'
  except Exception as exc:c.unresolved_dependencies=['MAPPING_GRAPH_INVALID:'+str(exc)]
 else:c.unresolved_dependencies=['MAPPING_ROUTE_NOT_DOCUMENTED']
 return pkg.add(c,ALL)
