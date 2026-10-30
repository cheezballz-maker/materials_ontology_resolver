"""Compare a fully consumed benzene pattern over all 12 ring symmetries."""
from collections import Counter
from rdkit import Chem

HALOGENS={'F':'fluoro','Cl':'chloro','Br':'bromo','I':'iodo'}
def extract(text):
    params=Chem.SmilesParserParams();params.parseName=False;params.allowCXSMILES=False
    m=Chem.MolFromSmiles(text,params) if isinstance(text,str) else None
    if m is None:raise ValueError('INVALID_CANDIDATE')
    if len(Chem.GetMolFrags(m))!=1:raise ValueError('MULTICOMPONENT_UNSUPPORTED')
    if any(a.GetIsotope() or a.GetNumRadicalElectrons() for a in m.GetAtoms()) or Chem.FindPotentialStereo(m):raise ValueError('ISOTOPE_STEREO_OR_RADICAL_UNSUPPORTED')
    if Chem.GetFormalCharge(m)!=0:raise ValueError('NET_CHARGE_UNSUPPORTED')
    rings=m.GetRingInfo().AtomRings()
    if len(rings)!=1 or len(rings[0])!=6 or any(m.GetAtomWithIdx(i).GetSymbol()!='C' or not m.GetAtomWithIdx(i).GetIsAromatic() for i in rings[0]):raise ValueError('BENZENE_PARENT_UNSUPPORTED')
    ring=list(rings[0]);rset=set(ring);consumed=set(ring);pattern=[]
    for idx in ring:
        atom=m.GetAtomWithIdx(idx)
        if atom.GetFormalCharge()!=0:raise ValueError('RING_CHARGE_UNSUPPORTED')
        extra=[a for a in atom.GetNeighbors() if a.GetIdx() not in rset]
        if len(extra)>1:raise ValueError('MULTIPLE_GROUPS_AT_SITE')
        if not extra:pattern.append(None);continue
        sub=extra[0];bond=m.GetBondBetweenAtoms(idx,sub.GetIdx())
        if bond.GetBondType()!=Chem.BondType.SINGLE:raise ValueError('ATTACHMENT_BOND_UNSUPPORTED')
        if sub.GetSymbol() in HALOGENS and sub.GetFormalCharge()==0 and sub.GetDegree()==1:
            pattern.append(HALOGENS[sub.GetSymbol()]);consumed.add(sub.GetIdx());continue
        oxy=[a for a in sub.GetNeighbors() if a.GetIdx()!=idx]
        if sub.GetSymbol()!='N' or sub.GetFormalCharge()!=1 or len(oxy)!=2 or any(a.GetSymbol()!='O' or a.GetDegree()!=1 for a in oxy) or sorted(a.GetFormalCharge() for a in oxy)!=[-1,0] or sorted(float(m.GetBondBetweenAtoms(sub.GetIdx(),a.GetIdx()).GetBondTypeAsDouble()) for a in oxy)!=[1.0,2.0]:raise ValueError('SUBSTITUENT_UNSUPPORTED')
        pattern.append('nitro');consumed.add(sub.GetIdx());consumed.update(a.GetIdx() for a in oxy)
    if len(consumed)!=m.GetNumAtoms():raise ValueError('UNCONSUMED_STRUCTURE')
    return pattern

def compare(operations,candidate,context=None):
    try:
        if (context or {}).get('correspondence')=='UNAVAILABLE':return 'UNKNOWN','CORRESPONDENCE_UNAVAILABLE',{}
        expected=[None]*6
        for op in operations:
            for pos in op['parameters']['positions']:expected[pos-1]=op['parameters']['substituent']
        actual=extract(candidate)
        # All dihedral permutations: rotate in either direction, not arbitrary
        # substructure or locant-label matching.
        matches=[]
        for direction in (1,-1):
            for offset in range(6):matches.append(all(expected[i]==actual[(offset+direction*i)%6] for i in range(6)))
        if any(matches):return 'SUPPORTED','RING_PATTERN_CORRESPONDS',{'admissible_dihedral_matches':sum(matches),'mapped_ring_automorphisms_considered':12}
        reason='SUBSTITUENT_COMPOSITION_DIFFERENT' if Counter(expected)!=Counter(actual) else 'SUBSTITUENT_POSITION_DIFFERENT'
        return 'DIFFERENT',reason,{'mapped_ring_automorphisms_considered':12,'none_satisfy_all_source_claims':True}
    except Exception as e:return 'UNKNOWN',str(e),{}
