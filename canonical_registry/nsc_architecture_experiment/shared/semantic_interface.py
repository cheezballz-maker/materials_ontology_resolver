"""Shared diagnostic-only NSC data model and referential integrity checks."""
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class SemanticInterpretation:
    input_name:str
    scope_status:str
    source_claims:list[dict]=field(default_factory=list)
    semantic_operations:list[dict]=field(default_factory=list)
    structural_constraints:list[dict]=field(default_factory=list)
    unresolved_dependencies:list[str]=field(default_factory=list)
    contract_id:str='NSC-001'
    contract_version:str='2.0'
    def to_dict(self):return asdict(self)

@dataclass
class SemanticValidation:
    result:str
    operation_results:list[dict]=field(default_factory=list)
    dimension_results:list[dict]=field(default_factory=lambda:[{'dimension':'tautomer','result':'UNKNOWN'},{'dimension':'identity','result':'NOT_ESTABLISHED'}])
    evidence:dict=field(default_factory=dict)
    reason_codes:list[str]=field(default_factory=list)
    def to_dict(self):return asdict(self)

def validate_interpretation(obj:SemanticInterpretation)->None:
    from jsonschema import Draft202012Validator
    from pathlib import Path
    import json
    schema=json.loads((Path(__file__).resolve().parents[1]/'NSC-001/semantic_constraint_schema_v2.json').read_text(encoding='utf8'))
    Draft202012Validator(schema).validate(obj.to_dict())
    claims={c['claim_id'] for c in obj.source_claims};operations={o['operation_id'] for o in obj.semantic_operations};constraints={c['constraint_id'] for c in obj.structural_constraints}
    if len(claims)!=len(obj.source_claims) or len(operations)!=len(obj.semantic_operations) or len(constraints)!=len(obj.structural_constraints) or claims&operations or claims&constraints or operations&constraints:raise ValueError('DUPLICATE_ID')
    valid_rules={'R1','R2','R3','R4','R5'}
    for c in obj.source_claims:
        s=c['source_span'];start=s['start'];end=s['end']
        if not (0<=start<end<=len(obj.input_name)) or obj.input_name[start:end]!=c['source_text']:raise ValueError('BAD_SOURCE_SPAN')
    for o in obj.semantic_operations:
        if not set(o['source_claim_ids'])<=claims or not set(o['rule_ids'])<=valid_rules or not set(o['dependencies'])<=claims:raise ValueError('BAD_OPERATION_REFERENCE')
    for c in obj.structural_constraints:
        if not set(c['source_claim_ids'])<=claims or not set(c['rule_ids'])<=valid_rules or not set(c['dependencies'])<=operations:raise ValueError('BAD_CONSTRAINT_REFERENCE')

def make_claims(name,locant,alkyl,h,parent):
    """Offsets are provided by each interpreter, in original code points."""
    entries=[('c1','SUBSTITUTION_LOCANT','parent','R2',locant),('c2','ALKYL','substituent','R5',alkyl),('c3','INDICATED_H','parent','R3',h),('c4','PARENT','parent','R4',parent)]
    return [{'claim_id':i,'source_span':{'start':a,'end':b},'source_text':name[a:b],'claim_type':kind,'semantic_owner':owner,'rule_id':rule} for i,kind,owner,rule,(a,b) in entries]

def make_operation(parent,alkyl,length):
    return {'operation_id':'op1','operation_type':'SUBSTITUTE_PARENT_H','source_claim_ids':['c1','c2','c3','c4'],'rule_ids':['R1','R2','R3','R4','R5'],'semantic_owner':'parent','parameters':{'parent':parent,'parent_position':1,'substituent':alkyl,'chain_length':length},'dependencies':['c1','c2','c3','c4']}

def make_constraint(parent,alkyl,length):
    return {'constraint_id':'k1','constraint_type':'N1_ALKYL_ATTACHMENT','source_claim_ids':['c1','c2','c3','c4'],'rule_ids':['R1','R2','R3','R4','R5'],'semantic_owner':'parent','structural_assertion':{'parent':parent,'position':1,'substituent':alkyl,'chain_length':length},'dependencies':['op1'],'applicability_conditions':['single neutral molecular component','no unsupported stereochemistry or isotope labels']}
