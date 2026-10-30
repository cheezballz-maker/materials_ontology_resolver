"""Isolated default-off consumer; cannot allocate IDs or call providers."""
import copy
from source_form import aggregate_dimensions
def consume(source_form,reasons,evidence,*,enable_charge_dimension_evidence=False):
    result=copy.deepcopy(source_form);remaining=list(reasons);used=False
    if enable_charge_dimension_evidence:
        evidence.validate()
        names=[x.get('text') for x in result.get('claims',[])]
        binding=evidence.source_scope['binding']
        if names!=binding['source_names']:
            return {'source_form':result,'remaining_reasons':remaining,'consumed':False,'local_eligible':result['status']=='SUPPORTED' and not remaining,'final_canonical_admission':'NOT_PERFORMED','evidence_rejection':'SOURCE_BINDING_MISMATCH'}
        from rdkit import Chem
        source_smiles=result['claims'][0]['parsed_interpretation'].get('smiles')
        source_mol=Chem.MolFromSmiles(source_smiles) if source_smiles else None
        if source_mol is None or Chem.MolToSmiles(source_mol)!=binding['candidate']:
            return {'source_form':result,'remaining_reasons':remaining,'consumed':False,'local_eligible':False,'final_canonical_admission':'NOT_PERFORMED','evidence_rejection':'CANDIDATE_BINDING_MISMATCH'}
        dim=result['dimensions']['protonation_charge']
        if evidence.dimension_result=='SUPPORTED' and dim['compatibility']=='UNKNOWN' and dim['source']=='UNSPECIFIED' and 'SOURCE_PROTONATION_SPECIFICITY_UNKNOWN' in remaining:
            result['dimensions']['protonation_charge']={'source':'SPECIFIED','compatibility':'SUPPORTED'}
            remaining=[x for x in remaining if x!='SOURCE_PROTONATION_SPECIFICITY_UNKNOWN']
            result['reason_codes']=[x for x in result['reason_codes'] if x!='SOURCE_PROTONATION_SPECIFICITY_UNKNOWN'];used=True
            result['status']=aggregate_dimensions(result['dimensions'])
            if result['status']=='SUPPORTED' and remaining:result['status']='UNRESOLVED'
    return {'source_form':result,'remaining_reasons':remaining,'consumed':used,'local_eligible':result['status']=='SUPPORTED' and not remaining,'final_canonical_admission':'NOT_PERFORMED'}
