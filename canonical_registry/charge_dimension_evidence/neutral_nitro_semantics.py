"""Candidate observations do not establish source charge specificity."""
from rdkit import Chem
from architecture_B.nsc002_interpreter.candidate_comparison import extract
def observe(smiles):
    params=Chem.SmilesParserParams();params.parseName=False;params.allowCXSMILES=False
    m=Chem.MolFromSmiles(smiles,params) if isinstance(smiles,str) else None
    if m is None:return {'valid':False,'reason':'INVALID_CANDIDATE'},[]
    sites=[]
    for match in m.GetSubstructMatches(Chem.MolFromSmarts('[#6]-[N+](=[O])-[O-]')):
        sites.append({'type':'N_ATTACHED_NEUTRAL_NITRO','atom_indices':list(match),'group_charge':sum(m.GetAtomWithIdx(i).GetFormalCharge() for i in match[1:]),'provenance':'STRUCTURALLY_DERIVED'})
    try:pattern=extract(smiles);envelope=True
    except Exception as e:pattern=None;envelope=False
    obs={'valid':True,'canonical_smiles':Chem.MolToSmiles(m),'formal_atomic_charges':[{'atom':a.GetIdx(),'charge':a.GetFormalCharge()} for a in m.GetAtoms() if a.GetFormalCharge()], 'net_component_charges':[Chem.GetFormalCharge(f) for f in Chem.GetMolFrags(m,asMols=True)],'hydrogen_distribution':[{'atom':a.GetIdx(),'hydrogens':a.GetTotalNumHs()} for a in m.GetAtoms()],'charge_bearing_groups':sites,'supported_candidate_envelope':envelope,'ring_pattern':pattern,'validated_resonance_relationships':'Only nitro oxygen-order/Kekule equivalence via complete supported structural comparison; no general proton movement.'}
    return obs,sites
