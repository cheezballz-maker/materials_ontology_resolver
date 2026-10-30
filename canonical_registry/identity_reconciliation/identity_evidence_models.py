"""Source-independent evidence. Trust labels describe provenance, not scores."""
from dataclasses import dataclass,field,asdict
DIMENSIONS=('constitution','stereochemistry','tautomer','protonation_charge','isotope','components','component_stoichiometry','hydration_solvation','electronic_state')
@dataclass
class IdentityEvidence:
    evidence_id:str
    source_id:str
    source_record_id:str
    claim_id:str
    claim_role:str
    evidence_type:str
    original_value:object
    source_provenance:dict
    referent_id:str
    derivation_dependencies:list[str]=field(default_factory=list)
    dimension_assertions:dict=field(default_factory=dict)
    unresolved_dependencies:list[str]=field(default_factory=list)
    def to_dict(self):return asdict(self)
    def validate(self):
        import json
        from pathlib import Path
        from jsonschema import Draft202012Validator
        Draft202012Validator(json.loads((Path(__file__).resolve().parent/'identity_evidence_schema.json').read_text(encoding='utf8'))).validate(self.to_dict())
        if not all(isinstance(x,str) and x for x in (self.evidence_id,self.source_id,self.source_record_id,self.claim_id,self.referent_id)):raise ValueError('MISSING_IDENTITY_PROVENANCE')
        if not set(self.dimension_assertions)<=set(DIMENSIONS):raise ValueError('UNKNOWN_DIMENSION')
        for d,a in self.dimension_assertions.items():
            if a['state'] not in ('EXACT','SET','UNSPECIFIED','UNKNOWN','NOT_APPLICABLE'):raise ValueError('BAD_SPECIFICITY_STATE')
            if a['state'] in ('EXACT','SET','NOT_APPLICABLE') and not a.get('structures'):raise ValueError('MISSING_ASSERTION_VALUE')
            if a['state']=='EXACT' and len(a['structures'])!=1:raise ValueError('EXACT_NOT_SINGLETON')
            if a['state']!='UNKNOWN' and not a.get('rule_id'):raise ValueError('MISSING_ASSERTION_BASIS')
        return self
