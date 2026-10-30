import json
from pathlib import Path
H=Path(__file__).resolve().parent
strings={'type':'array','items':{'type':'string'}}
assertion={'type':'object','required':['state','rule_id'],'properties':{'state':{'enum':['EXACT','SET','UNSPECIFIED','UNKNOWN','NOT_APPLICABLE']},'structures':strings,'framework':{'type':['string','null']},'scope':{'enum':['DEFINED_VALUES','ALL_WITHIN_FRAMEWORK']},'rule_id':{'type':'string','minLength':1}},'additionalProperties':False}
fields={n:{'type':'string','minLength':1} for n in ('evidence_id','source_id','source_record_id','claim_id','claim_role','evidence_type','referent_id')}
fields.update(original_value={},source_provenance={'type':'object','required':['origin','role_established','interpretation_basis'],'properties':{'origin':{'enum':['SOURCE_PROVIDED','DERIVED_SOURCE','CANDIDATE_DERIVED','EXTERNAL_REFERENCE']},'role_established':{'type':'boolean'},'interpretation_basis':{'enum':['SOURCE_TYPED_STRUCTURE','RULE_ESTABLISHED','UNVERIFIED']}}},derivation_dependencies=strings,unresolved_dependencies=strings,dimension_assertions={'type':'object','additionalProperties':assertion})
schema={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'IdentityEvidence v1','type':'object','required':list(fields),'properties':fields,'additionalProperties':False,'description':'Interpretation basis is a provenance assertion from a trusted adapter, not a calculated confidence score. Schema validity is not scientific validation. Dependency and chemical-scope checks are enforced by runtime logic.'}
(H/'identity_evidence_schema.json').write_text(json.dumps(schema,indent=2)+'\n',encoding='utf8')
