from dataclasses import dataclass,field,asdict
from typing import Literal

@dataclass
class ChargeDimensionEvidence:
    evidence_id:str
    source_claim_ids:list[str]
    nomenclature_rule_ids:list[str]
    semantic_owner:str
    source_scope:dict
    candidate_correspondence:dict
    structural_observations:dict
    relevant_sites:list[dict]
    site_coverage:dict
    unresolved_dependencies:list[str]
    source_assertions:list[dict]
    dimension_result:Literal['SUPPORTED','DIFFERENT','UNKNOWN','NOT_APPLICABLE']='UNKNOWN'
    operation_result:str='UNKNOWN'
    reason_codes:list[str]=field(default_factory=list)
    version:str='1.0'
    def to_dict(self):return asdict(self)
    def validate(self):
        import json
        from pathlib import Path
        from jsonschema import Draft202012Validator
        Draft202012Validator(json.loads((Path(__file__).resolve().parent/'charge_evidence_schema.json').read_text(encoding='utf8'))).validate(self.to_dict())
        ids={x['claim_id'] for x in self.source_scope['claims']}
        if set(self.source_claim_ids)!=ids:raise ValueError('SOURCE_CLAIM_REFERENCE_INVALID')
        for claim in self.source_scope['claims']:
            name=claim['original'];span=claim['source_span']
            if name[span['start']:span['end']]!=claim['source_text']:raise ValueError('SOURCE_SPAN_INVALID')
        for assertion in self.source_assertions:
            if not set(assertion['source_claim_ids'])<=ids:raise ValueError('ASSERTION_REFERENCE_INVALID')
        if self.dimension_result=='SUPPORTED' and (not self.site_coverage.get('complete') or self.unresolved_dependencies or self.operation_result!='SUPPORTED' or not self.source_assertions or self.candidate_correspondence.get('status')!='SUPPORTED'):raise ValueError('INCOMPLETE_DIMENSION_PROOF')
        return self
