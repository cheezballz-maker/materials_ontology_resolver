"""Diagnostic wrapper preserving global distinctions and isolating reason attribution."""
import copy
from rdkit import Chem
from identity_comparator import compare as existing_compare
from form_characterizer import characterize
def compare(a,b):
    result=copy.deepcopy(existing_compare(a,b));x,y=characterize(a),characterize(b)
    if result['dimensions']['protonation_charge']=='DIFFERENT':
        same_framework=x['connectivity']==y['connectivity'] and not x['isotopes'] and not y['isotopes'] and x['component_count']==y['component_count']==1
        framework_mappings=[]
        if same_framework:
            left=Chem.MolFromSmiles(x['connectivity']);right=Chem.MolFromSmiles(y['connectivity'])
            framework_mappings=right.GetSubstructMatches(left,uniquify=False,maxMatches=1001) if left and right else []
            same_framework=bool(framework_mappings) and len(framework_mappings)<=1000
        delta_q=y['charge']-x['charge'];delta_h=y['hydrogen_count']-x['hydrogen_count']
        valid_proton_basis=same_framework and ((delta_q==delta_h and delta_q!=0) or (delta_q==delta_h==0))
        if not valid_proton_basis:
            result['dimensions']['protonation_charge']='UNKNOWN';result['reason_codes']=[c for c in result['reason_codes'] if c!='PROTONATION_DIFFERENT'];result['reason_codes'].append('PROTONATION_NOT_COMPARABLE')
        result['charge_comparison_basis']={'same_heavy_atom_framework':same_framework,'framework_mapping_count':len(framework_mappings),'delta_net_charge':delta_q,'delta_total_H':delta_h,'protonation_attribution_supported':valid_proton_basis,'source_specificity':'NOT_ASSESSED'}
    return result
