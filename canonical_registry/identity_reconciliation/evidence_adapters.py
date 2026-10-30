"""Adapters preserve upstream interpretation limits; no general name parser."""
from identity_evidence_models import IdentityEvidence,DIMENSIONS
from chemistry import describe
from form_characterizer import characterize

def assertion(smiles,dimension,state='EXACT',framework=None):
    return {'state':state,'structures':[smiles] if smiles else [],'framework':framework or smiles,'scope':'ALL_WITHIN_FRAMEWORK' if state=='UNSPECIFIED' else 'DEFINED_VALUES','rule_id':'EXPLICIT_GRAPH_OR_REVIEWED_RULE'}

def candidate_assertions(smiles):
    d=describe(smiles);f=characterize(d);out={k:assertion(smiles,k) for k in DIMENSIONS}
    if f['stereo_state'] in ('PARTIAL','UNSPECIFIED'):out['stereochemistry']=assertion(None,'stereochemistry','UNSPECIFIED',smiles)
    return out

def fixture_evidence(item,record):
    i=item['id'];a=assertion(item['smiles'],item['dimension'],item['state'],item['framework'])
    return IdentityEvidence(evidence_id=record+':'+i,source_id='independent_controls',source_record_id=record,claim_id=i,claim_role=item['role'],evidence_type='ANNOTATED_RULE_CLAIM',original_value=item['name'],source_provenance={'origin':item['origin'],'role_established':item['role_established'],'interpretation_basis':item['basis'],'review':'CHEMICAL_REVIEW_PENDING','rule_references':['https://iupac.qmul.ac.uk/BlueBook/P9.html#P-93.1','https://iupac.qmul.ac.uk/BlueBook/P7.html','https://iupac.qmul.ac.uk/BlueBook/P8.html'],'explicitly_provided':item['origin']=='SOURCE_PROVIDED'},referent_id=record,derivation_dependencies=[record+':'+x for x in item['dependencies']],dimension_assertions={item['dimension']:a})

def raw_claim(source,record,cid,role,value,*,role_established=False,origin='SOURCE_PROVIDED'):
    return IdentityEvidence(evidence_id=f'{source}:{record}:{cid}',source_id=source,source_record_id=str(record),claim_id=cid,claim_role=role,evidence_type='UNINTERPRETED_SOURCE_CLAIM',original_value=value,source_provenance={'origin':origin,'role_established':role_established,'interpretation_basis':'UNVERIFIED','explicitly_provided':origin=='SOURCE_PROVIDED'},referent_id=f'{source}:{record}',unresolved_dependencies=['SOURCE_SEMANTIC_MAPPING_UNESTABLISHED'])

def source_structure(source,record,cid,smiles):
    return IdentityEvidence(evidence_id=f'{source}:{record}:{cid}',source_id=source,source_record_id=str(record),claim_id=cid,claim_role='EXACT_STRUCTURE',evidence_type='EXPLICIT_MOLECULAR_STRUCTURE',original_value=smiles,source_provenance={'origin':'SOURCE_PROVIDED','role_established':True,'interpretation_basis':'SOURCE_TYPED_STRUCTURE','explicitly_provided':True},referent_id=f'{source}:{record}',dimension_assertions=candidate_assertions(smiles))

def architecture_b_claim(source,record,cid,name):
    """Optional NSC-001 source compilation; unsupported names stay unresolved."""
    from architecture_B.implementation.interpreter import interpret_name
    from architecture_B.implementation.semantic_operations import compose
    from rdkit import Chem
    obj=interpret_name(name)
    if obj.scope_status!='IN_CONTRACT':return raw_claim(source,record,cid,'IDENTITY_ASSERTION',name,role_established=True)
    op=obj.semantic_operations[0]['parameters'];smiles=Chem.MolToSmiles(compose(op['parent'],op['chain_length']))
    result=raw_claim(source,record,cid,'PARTIAL_IDENTITY',name,role_established=True)
    result.evidence_type='ARCHITECTURE_B_SEMANTIC_INTERPRETATION';result.source_provenance.update(interpretation_basis='RULE_ESTABLISHED',origin='DERIVED_SOURCE',source_spans=obj.source_claims,contract_id=obj.contract_id)
    result.dimension_assertions={'constitution':assertion(smiles,'constitution')};result.unresolved_dependencies=[]
    return result
