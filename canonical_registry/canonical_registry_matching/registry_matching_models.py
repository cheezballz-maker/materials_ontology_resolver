"""Read-only contracts. No persistence or ID-allocation operations."""
from dataclasses import dataclass,field,asdict
import bootstrap
from correspondence_models import IncomingConcept

@dataclass(frozen=True)
class RetrievalPolicy:
 exhaustive:bool=True
 max_candidates:int|None=None
 allow_exploratory_names:bool=True
 strategy:str="indexed"
 def validate(self):
  if self.strategy not in ('indexed','exhaustive'):raise ValueError('INVALID_RETRIEVAL_STRATEGY')
  if self.max_candidates is not None and self.max_candidates<1:raise ValueError('INVALID_CANDIDATE_LIMIT')
  return self
 def identity_policy(self):
  """Retrieval implementation is not a change to the persisted chemical request."""
  return dict(exhaustive=self.exhaustive,max_candidates=self.max_candidates,
              allow_exploratory_names=self.allow_exploratory_names)

@dataclass
class MatchingInput:
 concept:IncomingConcept
 name:str=''
 retrieval_hypothesis:str|None=None
 official_validation:dict|None=None
 external_evidence:dict=field(default_factory=lambda:{'status':'NOT_QUERIED','rows':[]})
 form_assertion:dict=field(default_factory=dict)
 source_profile:dict|None=None
 evidence_origin:str='CALLER_SUPPLIED_QUALIFIED_EVIDENCE'

@dataclass
class CandidateRetrievalResult:
 candidate_ids:list
 routes:dict
 indexed_candidate_ids:list
 registry_total:int
 snapshot_sha256:str
 search_complete:bool
 exhaustive_requested:bool
 truncated:bool
 records_without_valid_single_graph:list
 excluded_candidate_ids:list=field(default_factory=list)
 completeness_basis:str='EXHAUSTIVE_COMPARISON'
 qualification_note:str='All routes generate candidates only; no route establishes equivalence.'
 def to_dict(self):return asdict(self)

MATCH_STATUSES=('UNIQUE_CANONICAL_MATCH','MULTIPLE_CANONICAL_MATCHES','MATCH_UNRESOLVED','NO_MATCH_IN_SEARCHED_REGISTRY','SOURCE_CONFLICT')
