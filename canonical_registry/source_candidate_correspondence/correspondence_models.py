"""Diagnostic contracts; these classes have no persistence/admission methods."""
from dataclasses import dataclass,field,asdict
from typing import Literal
import bootstrap
from evidence_adapter_contract import EvidencePackage
from identity_evidence_models import DIMENSIONS

STATUSES=('CORRESPONDENCE_SUPPORTED','CORRESPONDENCE_DIFFERENT','CORRESPONDENCE_UNRESOLVED','SOURCE_CONFLICT')
@dataclass
class IncomingConcept:
 source_concept_id:str
 evidence_package:EvidencePackage
 binding:dict
 identity_scope:str='DISCRETE_MOLECULAR'
 provenance:dict=field(default_factory=dict)

@dataclass
class CanonicalCandidate:
 candidate_substance_id:str
 preferred_name:str
 structure:str|None
 provenance:dict
 identity_scope:str='DISCRETE_MOLECULAR'
 evidence:list=field(default_factory=list)

@dataclass
class EvidencePolicy:
 version:str='1.0'
 required_dimensions:tuple=DIMENSIONS
 enabled:bool=False
 max_candidates:int=256
 search_exhaustiveness:str='BOUNDED_SUPPLIED_SET'
 def validate(self):
  if tuple(self.required_dimensions)!=DIMENSIONS:raise ValueError('ALL_IDENTITY_DIMENSIONS_REQUIRED_FOR_CORRESPONDENCE')
  if self.max_candidates<1:raise ValueError('INVALID_CANDIDATE_LIMIT')
  return self

@dataclass
class IdentityCorrespondenceResult:
 source_concept_id:str
 candidate_substance_id:str
 correspondence_status:Literal['CORRESPONDENCE_SUPPORTED','CORRESPONDENCE_DIFFERENT','CORRESPONDENCE_UNRESOLVED','SOURCE_CONFLICT']
 dimension_comparisons:dict
 source_evidence:list
 candidate_evidence:dict
 unresolved_obligations:list
 contradictions:list
 provenance:dict
 def to_dict(self):return asdict(self)
