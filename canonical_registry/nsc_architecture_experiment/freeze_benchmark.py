"""Prepare and freeze benchmark v2 before writing architecture implementations."""
import hashlib, json, shutil
from pathlib import Path
H=Path(__file__).resolve().parent; ROOT=H.parent
for d in ('NSC-001','shared','architecture_A/implementation','architecture_A/tests','architecture_B/implementation','architecture_B/tests','evaluation'):(H/d).mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
contract=read(ROOT/'nomenclature_support_contract.json');contract['version']='2.0';contract['status']='FROZEN_CHEMICAL_REVIEW_PENDING';contract['human_review']='CHEMICAL_REVIEW_PENDING';write(H/'NSC-001/contract_v2.json',contract)
shutil.copyfile(ROOT/'nomenclature_grammar.ebnf',H/'NSC-001/grammar_v2.ebnf')
shutil.copyfile(ROOT/'nomenclature_rule_catalog.json',H/'NSC-001/nomenclature_rule_catalog_v2.json')
schema={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'NSC-001 v2 interpretation','type':'object','required':['contract_id','contract_version','input_name','scope_status','source_claims','semantic_operations','structural_constraints','unresolved_dependencies'],
'properties':{'contract_id':{'const':'NSC-001'},'contract_version':{'const':'2.0'},'input_name':{'type':'string'},'scope_status':{'enum':['IN_CONTRACT','OUT_OF_CONTRACT','UNKNOWN']},
'source_claims':{'type':'array','items':{'$ref':'#/$defs/claim'}},'semantic_operations':{'type':'array','items':{'$ref':'#/$defs/operation'}},'structural_constraints':{'type':'array','items':{'$ref':'#/$defs/constraint'}},'unresolved_dependencies':{'type':'array','items':{'type':'string'}}},
'$defs':{'span':{'type':'object','required':['start','end'],'properties':{'start':{'type':'integer','minimum':0},'end':{'type':'integer','minimum':0}},'additionalProperties':False},
'claim':{'type':'object','required':['claim_id','source_span','source_text','claim_type','semantic_owner','rule_id'],'properties':{'claim_id':{'type':'string','minLength':1},'source_span':{'$ref':'#/$defs/span'},'source_text':{'type':'string','minLength':1},'claim_type':{'type':'string'},'semantic_owner':{'type':'string'},'rule_id':{'enum':['R1','R2','R3','R4','R5']}},'additionalProperties':False},
'operation':{'type':'object','required':['operation_id','operation_type','source_claim_ids','rule_ids','semantic_owner','parameters','dependencies'],'properties':{'operation_id':{'type':'string'},'operation_type':{'type':'string'},'source_claim_ids':{'type':'array','minItems':1,'items':{'type':'string'}},'rule_ids':{'type':'array','minItems':1,'items':{'type':'string'}},'semantic_owner':{'type':'string'},'parameters':{'type':'object'},'dependencies':{'type':'array','items':{'type':'string'}}},'additionalProperties':False},
'constraint':{'type':'object','required':['constraint_id','constraint_type','source_claim_ids','rule_ids','semantic_owner','structural_assertion','dependencies','applicability_conditions'],'properties':{'constraint_id':{'type':'string'},'constraint_type':{'type':'string'},'source_claim_ids':{'type':'array','minItems':1,'items':{'type':'string'}},'rule_ids':{'type':'array','minItems':1,'items':{'type':'string'}},'semantic_owner':{'type':'string'},'structural_assertion':{'type':'object'},'dependencies':{'type':'array','minItems':1,'items':{'type':'string'}},'applicability_conditions':{'type':'array','items':{'type':'string'}}},'additionalProperties':False}},'additionalProperties':False,
'description':'Half-open offsets in Unicode code points of original source. JSON Schema alone does not validate cross-references; semantic_interface.validate_interpretation enforces referential integrity, spans, unique IDs and rules.'}
write(H/'NSC-001/semantic_constraint_schema_v2.json',schema)
review={'version':'2.0','status':'CHEMICAL_REVIEW_PENDING','human_reviewer':None,'method':'IUPAC P-13.1, P-14.3.2, P-14.7, P-22 Table 2.2 and P-29.3.2.1; independently documented PubChem graphs used as corroboration; no new provider queries.',
'fixture_assessment':'All original expectations are provisional; no qualified human approval claimed. D09/D12/H04 are injected comparison-failure tests, not chemical ambiguity. D11 conflict is a separate record-level assertion.','changes_from_v1':['Strong typed source-claim and operation cross-references plus runtime cross-reference validation.','Moved simulated symmetry from a chemical claim to comparator-level context; no chemically false assertion.','Retained grammar and existing expected labels; added comparator symmetry fixtures.'],'limitations':['Public held-out data are not blinded.','Automated references and RDKit are not human chemical review.']}
write(H/'NSC-001/benchmark_review.json',review)
for old,new in [('independent_semantic_controls.json','development_controls.json'),('heldout_semantic_controls.json','heldout_controls.json')]:
    obj=read(ROOT/old)
    for x in obj['cases']:x['expectation_review']='PROVISIONAL_CHEMICAL_REVIEW_PENDING'
    write(H/'shared'/new,obj)
write(H/'shared/comparator_controls.json',{'status':'PROVISIONAL_CHEMICAL_REVIEW_PENDING','cases':[{'id':'SYM-1','source':'c1ccccc1','candidate':'C1=CC=CC=C1','expected':'SUPPORTED','meaning':'Same benzene graph; multiple automorphisms all satisfy graph identity.'},{'id':'SYM-2','source':'c1ccccc1','candidate':'c1ccccc1','expected':'UNKNOWN','meaning':'Two symmetry-equivalent source atoms mapped without distinguishing labels; site-specific mapping predicates differ.','predicate':'source_atom_0_maps_candidate_atom_0'},{'id':'SYM-3','source':'c1ccccc1','candidate':'c1ccncc1','expected':'DIFFERENT_GRAPH','meaning':'One ring carbon replaced by nitrogen; direct graph identity differs, no operation-specific conclusion.'}]})
paths=list((H/'NSC-001').glob('*'))+list((H/'shared').glob('*.json'))
digest={str(x.relative_to(H)).replace('\\','/'):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(paths)}
write(H/'NSC-001/benchmark_freeze.json',{'version':'2.0','scope':'Contract, schema, reviewed-provisional controls and comparator fixtures, frozen before architecture implementation.','sha256':digest})
production=['resolver.py','source_form.py','identity_comparator.py','providers.py','provider_capabilities.py','evidence_model.py','evidence_retrieval.py','comptox.py','schema.sql']
write(H/'evaluation/pre_implementation_hashes.json',{'files':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in production},'note':'This is a selective baseline, not a whole-workspace snapshot.'})
print('benchmark frozen; human review pending')
