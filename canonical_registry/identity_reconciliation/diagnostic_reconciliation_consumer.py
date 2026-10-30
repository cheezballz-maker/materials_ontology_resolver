"""Conservative, default-off source-form diagnostic; no admission or registry API."""
import copy
from source_form import aggregate_dimensions
def consume(before,reconciliation,*,enabled=False,referent_id=None):
    out=copy.deepcopy(before);changed=False
    if enabled:
        from rdkit import Chem
        primary=(out.get('claims') or [{}])[0].get('parsed_interpretation',{}).get('smiles')
        bound=reconciliation.get('candidate_binding')
        left=Chem.MolFromSmiles(primary) if primary else None;right=Chem.MolFromSmiles(bound) if bound else None
        if referent_id!=reconciliation['referent_id'] or left is None or right is None or Chem.MolToSmiles(left)!=Chem.MolToSmiles(right):
            return {'source_form':out,'changed':False,'local_eligible':False,'canonical_admission':'NOT_PERFORMED','evidence_rejection':'RECORD_OR_CANDIDATE_BINDING_UNVERIFIED'}
    if enabled and reconciliation['result']=='RECONCILIATION_CONFLICT':
        out['status']='CONFLICT';changed=before['status']!='CONFLICT'
        out['reason_codes']=list(dict.fromkeys(out['reason_codes']+['RECONCILED_EXACT_SOURCE_CONFLICT']))
    if enabled and reconciliation['result']=='RECONCILIATION_UNRESOLVED' and out['status']!='CONFLICT':
        out['status']='UNRESOLVED';changed=before['status']!='UNRESOLVED'
        out['reason_codes']=list(dict.fromkeys(out['reason_codes']+['ACTIVE_IDENTITY_EVIDENCE_UNRESOLVED']))
    # V1 consumes proved dimension compatibility only; it never retracts a
    # pre-existing DIFFERENT/CONFLICTING source assertion or specific reason.
    if enabled and reconciliation['result']=='RECONCILED_COMPATIBLE':
        for dim in reconciliation['supported_dimensions']:
            if dim in out['dimensions'] and out['dimensions'][dim]['compatibility']=='UNKNOWN':
                out['dimensions'][dim]={'source':'SPECIFIED','compatibility':'SUPPORTED'};changed=True
        if aggregate_dimensions(out['dimensions'])=='SUPPORTED' and not out['reason_codes']:out['status']='SUPPORTED'
    return {'source_form':out,'changed':changed,'local_eligible':out['status']=='SUPPORTED' and not out['reason_codes'],'canonical_admission':'NOT_PERFORMED'}
