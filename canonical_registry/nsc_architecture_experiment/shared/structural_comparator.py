"""Bounded diagnostic comparator, strict about candidate-specific dimensions."""
from rdkit import Chem

def parse(text):
    p=Chem.SmilesParserParams();p.parseName=False;p.allowCXSMILES=False
    m=Chem.MolFromSmiles(text,p) if isinstance(text,str) else None
    if m is None:raise ValueError('INVALID_CANDIDATE')
    if len(Chem.GetMolFrags(m))!=1:raise ValueError('MULTICOMPONENT_UNSUPPORTED')
    if any(a.GetIsotope() for a in m.GetAtoms()):raise ValueError('ISOTOPE_UNSUPPORTED')
    if any(a.GetFormalCharge() for a in m.GetAtoms()):raise ValueError('CHARGE_UNSUPPORTED')
    if any(a.GetNumRadicalElectrons() for a in m.GetAtoms()) or Chem.FindPotentialStereo(m):raise ValueError('STEREO_OR_RADICAL_UNSUPPORTED')
    return m

def mappings(source,candidate,cap=1000):
    if source.GetNumAtoms()!=candidate.GetNumAtoms() or source.GetNumBonds()!=candidate.GetNumBonds():return []
    found=candidate.GetSubstructMatches(source,uniquify=False,useChirality=True,maxMatches=cap+1)
    if len(found)>cap:raise ValueError('MAPPING_LIMIT')
    state=lambda x:(x.GetAtomicNum(),x.GetIsotope(),x.GetFormalCharge(),x.GetIsAromatic(),x.GetTotalNumHs())
    return [m for m in found if all(state(a)==state(candidate.GetAtomWithIdx(m[a.GetIdx()])) for a in source.GetAtoms())]

def mapping_outcome(values):
    v=set(values)
    return 'SUPPORTED' if v=={True} else 'DIFFERENT' if v=={False} else 'UNKNOWN'

def _split(mol,bond):
    a,b=bond.GetBeginAtomIdx(),bond.GetEndAtomIdx()
    if mol.GetAtomWithIdx(a).IsInRing()==mol.GetAtomWithIdx(b).IsInRing():return None
    parent,side=(a,b) if mol.GetAtomWithIdx(a).IsInRing() else (b,a)
    rw=Chem.RWMol(Chem.AddHs(mol));rw.RemoveBond(parent,side)
    for i in (parent,side):
        h=rw.AddAtom(Chem.Atom('H'));rw.AddBond(i,h,Chem.BondType.SINGLE)
    result=rw.GetMol();Chem.SanitizeMol(result);result=Chem.RemoveHs(result)
    for i,a in enumerate(result.GetAtoms()):a.SetIntProp('_original',i)
    fragments=Chem.GetMolFrags(result,asMols=True,sanitizeFrags=True)
    if len(fragments)!=2:return None
    def get(idx):return next(f for f in fragments if any(a.GetIntProp('_original')==idx for a in f.GetAtoms()))
    p,s=get(parent),get(side)
    target=next(a.GetIdx() for a in p.GetAtoms() if a.GetIntProp('_original')==parent)
    return p,s,target

def _parts(m):
    out=[]
    for bond in m.GetBonds():
        if bond.GetBondType()!=Chem.BondType.SINGLE or bond.IsInRing():continue
        part=_split(m,bond)
        if part:out.append(part)
    return out

def compare_candidate(expected,candidate_text,context=None):
    try:
        context=context or {}
        if context.get('correspondence') in ('UNAVAILABLE','SIMULATED_UNRESOLVED_SYMMETRY'):return 'UNKNOWN','CORRESPONDENCE_UNAVAILABLE',{}
        candidate=parse(candidate_text)
        exact=mappings(expected,candidate)
        if exact:return 'SUPPORTED','EXACT_GRAPH_CORRESPONDENCE',{'mapping_count':len(exact)}
        source_parts=_parts(expected);candidate_parts=_parts(candidate)
        if len(source_parts)!=1:return 'UNKNOWN','SOURCE_ATTACHMENT_PARTITION_NOT_UNIQUE',{}
        p,s,site=source_parts[0];poss=[]
        for cp,cs,csite in candidate_parts:
            pm=mappings(p,cp);sm=mappings(s,cs)
            if pm and sm:poss += [m[site]==csite for m in pm]
        if poss:
            result=mapping_outcome(poss)
            return result,('ATTACHMENT_POSITION_DIFFERENT' if result=='DIFFERENT' else 'MAPPING_AMBIGUOUS' if result=='UNKNOWN' else 'ATTACHMENT_POSITION_MATCHES'),{'mapping_count':len(poss)}
        # Prove different alkyl only for a unique ring-to-sidechain partition,
        # with an exact capped parent and a fully saturated linear carbon chain.
        if len(candidate_parts)==1:
            cp,cs,_=candidate_parts[0]
            if mappings(p,cp) and all(a.GetSymbol()=='C' and a.GetFormalCharge()==0 for a in cs.GetAtoms()) and all(b.GetBondType()==Chem.BondType.SINGLE for b in cs.GetBonds()):
                return 'DIFFERENT','SUBSTITUENT_STRUCTURE_DIFFERENT',{'parent_mapped':True}
            if mappings(s,cs) and cp.GetRingInfo().NumRings()==1 and p.GetRingInfo().NumRings()==1:
                return 'DIFFERENT','PARENT_CONNECTIVITY_DIFFERENT',{'substituent_mapped':True,'single_ring_partition':True}
        return 'UNKNOWN','NO_PROVEN_OPERATION_CONTRADICTION',{}
    except Exception as e:return 'UNKNOWN',str(e),{}
