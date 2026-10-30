"""Non-destructive molecular features and conservative source-form interpretation.

Features describe a graph; source intent is a separate, explicitly passed contract.
No source-specific IDs or registry writes are used here.
"""
from collections import Counter
from functools import lru_cache
import re
from rdkit import Chem
from chemistry import parse

SOLVENTS={'water':'O','DMSO':'CS(C)=O','methanol':'CO','ethanol':'CCO','acetonitrile':'CC#N'}
COUNTS={'mono':1,'di':2,'tri':3,'tetra':4,'penta':5,'hexa':6,'hepta':7,'octa':8,'nona':9,'deca':10}
STEREO_TOKEN=re.compile(r'(?<![A-Za-z])[DL]-|\((?:\d*[RSZE])(?:\s*,\s*\d*[RSZE])*\)|\b(?i:cis|trans)-')
ISOTOPE_TOKEN=re.compile(r'deuteri|triti|(?:^|[-\s])d\d+\b|\b(?:13|14)[ -]?c\b|\b(?:15)[ -]?n\b|\[\d+[A-Z]|\(\d+[A-Z]|-\d+[A-Z]',re.I)

def serial(m): return Chem.MolToSmiles(m,canonical=True,isomericSmiles=True)

def projection(m,*,isotopes=False,charges=False):
    """Hydrogen-free adjacency view, optionally retaining isotope-attached H nodes.

    Diagnostic signatures only; these unsanitized skeletons never become structures.
    """
    r=Chem.RWMol(m)
    Chem.RemoveStereochemistry(r)
    for a in list(r.GetAtoms())[::-1]:
        if a.GetAtomicNum()==1 and not (isotopes and a.GetIsotope()):r.RemoveAtom(a.GetIdx())
    for a in r.GetAtoms():
        if not isotopes:a.SetIsotope(0)
        if not charges:a.SetFormalCharge(0)
        a.SetNumExplicitHs(0);a.SetNoImplicit(True);a.SetNumRadicalElectrons(0);a.SetIsAromatic(False)
    for b in r.GetBonds():b.SetBondType(Chem.BondType.SINGLE);b.SetIsAromatic(False)
    return serial(r)

def without_stereo_isotope(m):
    c=Chem.Mol(m);Chem.RemoveStereochemistry(c)
    for a in c.GetAtoms():a.SetIsotope(0)
    return Chem.RemoveHs(c)

@lru_cache(maxsize=8192)
def _features(smiles):
    m=parse(smiles)
    # Canonical atom ordering makes recorded positions independent of input traversal.
    m=parse(serial(m))
    potential=list(Chem.FindPotentialStereo(m))
    stereo=[dict(type=str(s.type),state=str(s.specified),atom_or_bond=s.centeredOn,descriptor=str(s.descriptor)) for s in potential]
    assigned=sum(s['state']=='Specified' for s in stereo)
    stereo_state='NOT_APPLICABLE' if not stereo else 'SPECIFIED' if assigned==len(stereo) else 'PARTIAL' if assigned else 'UNSPECIFIED'
    fragments=Chem.GetMolFrags(m,asMols=True,sanitizeFrags=True)
    components=Counter(serial(f) for f in fragments)
    component_rows=[dict(smiles=s,count=n,charge=Chem.GetFormalCharge(parse(s))) for s,n in sorted(components.items())]
    # Enumerate only ordinary valid resonance contributors. Fixed atom H, isotope,
    # stereo and radical state are retained; this is not proton/tautomer movement.
    supplier=Chem.ResonanceMolSupplier(m,0,65)
    resonance=[]
    for r in supplier:
        Chem.SanitizeMol(r)
        resonance.append(r)
    if not resonance:resonance=[m]
    from rdkit.Chem.MolStandardize import rdMolStandardize as ms
    enumerator=ms.TautomerEnumerator();enumerator.SetMaxTautomers(64);enumerator.SetMaxTransforms(256)
    tautomers=enumerator.Enumerate(Chem.Mol(m))
    return dict(smiles=serial(m),connectivity=projection(m),tautomer_sensitive=len(tautomers)>1,tautomer_diagnostic_count=len(tautomers),
        component_count=len(fragments),component_identities=component_rows,
        component_stoichiometry=dict(sorted(components.items())),
        charge=Chem.GetFormalCharge(m),charge_distribution=[(a.GetIdx(),a.GetFormalCharge()) for a in m.GetAtoms() if a.GetFormalCharge()],
        radical_electrons=sum(a.GetNumRadicalElectrons() for a in m.GetAtoms()),
        stereo_elements=stereo,stereo_state=stereo_state,
        advanced_stereo=bool(m.GetStereoGroups()) or any(s['type'] not in ('Atom_Tetrahedral','Bond_Double') for s in stereo),
        isotopes=[dict(atom=a.GetIdx(),element=a.GetSymbol(),mass=a.GetIsotope()) for a in m.GetAtoms() if a.GetIsotope()],
        isotope_signature=projection(m,isotopes=True),
        hydrogen_count=sum(a.GetTotalNumHs() for a in m.GetAtoms())+sum(a.GetAtomicNum()==1 for a in m.GetAtoms()),
        hydrogen_placement=[(a.GetIdx(),a.GetTotalNumHs()) for a in m.GetAtoms()],
        bond_placement=[(b.GetBeginAtomIdx(),b.GetEndAtomIdx(),str(b.GetBondType())) for b in m.GetBonds()],
        resonance_forms=sorted({serial(r) for r in resonance}),
        resonance_without_stereo_isotope=sorted({serial(without_stereo_isotope(r)) for r in resonance}),
        charge_views=sorted({projection(r,charges=True) for r in resonance}),
        resonance_complete=len(resonance)<65,
        solvent_components={label:components[s] for label,s in SOLVENTS.items() if components[s]},
        elements=sorted({a.GetSymbol() for a in m.GetAtoms()}))

def characterize(d):
    # Return a fresh JSON-compatible copy: callers cannot mutate cached features.
    import copy
    out=copy.deepcopy(_features(d['smiles']))
    out.update(original_input=d.get('original_input',d['smiles']),parsed_structure=d['smiles'],
               standard_inchi=d['inchi'],standard_inchikey=d['inchikey'],fixed_h_inchi=d.get('fixed_h_inchi'))
    return out

def verified_source_stereo(d,profile):
    """Accept only complete verified mapping on the identical source graph."""
    mapping=(profile or {}).get('stereo_locant_mapping') or {}
    if mapping.get('status')!='MAPPED' or not mapping.get('source_smiles'):return False
    if serial(parse(d['smiles']))!=mapping['source_smiles']:return False
    f=characterize(d)
    if f['stereo_state']!='SPECIFIED' or f['advanced_stereo']:return False
    needed={(('atom' if x['type']=='Atom_Tetrahedral' else 'bond'),x['atom_or_bond']) for x in f['stereo_elements'] if x['state']=='Specified'}
    entries=mapping.get('mappings',[])
    covered={(x['element'],x.get('atom_index',x.get('bond_index'))) for x in entries if x.get('verification')=='VERIFIED'}
    return bool(needed) and needed==covered and len(entries)==len(covered)

def interpret(d,name,assertion=None,source_profile=None):
    """Check source semantics separately from graph features.

    assertion is source-independent metadata for an explicitly supplied, validated
    structural referent, not an automatically inferred claim from a provider hit.
    Fields: explicit_structure, form_kind, component_stoichiometry, solvent_counts.
    """
    f=characterize(d);a=assertion or {};n=name or '';reasons=[];categories=[]
    typed=a.get('explicit_structure') is True
    if re.search(r'\b(racemic|racemate|mixture|solution|blend|adduct|co-crystal|cocrystal|complex|atropisomer)\b',n,re.I):
        reasons.append('ENSEMBLE_OR_ASSOCIATION_UNSUPPORTED')
    if re.search(r'\b(?:atrop|axial|binol)|\([RS]_[ap]\)',n,re.I):reasons.append('STEREO_UNSUPPORTED')
    if d.get('inchi_warning') and any(word in d['inchi_warning'].lower() for word in ('unusual valence','undefined stereo','ambiguous','unrecognized')):
        reasons.append('INCHI_WARNING_REQUIRES_REVIEW')
    if f['advanced_stereo']:reasons.append('STEREO_UNSUPPORTED')
    verified=verified_source_stereo(d,source_profile)
    if not typed and STEREO_TOKEN.search(n) and f['stereo_state']=='NOT_APPLICABLE':reasons.append('STEREO_SOURCE_NOT_REPRESENTED')
    if f['stereo_state'] in ('UNSPECIFIED','PARTIAL'):reasons.append('STEREO_UNSPECIFIED')
    elif f['stereo_state']=='SPECIFIED':
        categories.append('stereo')
        if not typed and not verified and not STEREO_TOKEN.search(n):reasons.append('STEREO_SOURCE_INTENT_UNSPECIFIED')
    if f['isotopes']:
        categories.append('isotope')
        if not typed and not ISOTOPE_TOKEN.search(n):reasons.append('ISOTOPE_POSITION_UNKNOWN')
        if re.search(r'(monodeuterated|deuterated|labelled|labeled)\s',n,re.I) and not re.search(r'\d+[,-]|-d\d+|deuterium oxide',n,re.I):reasons.append('ISOTOPE_POSITION_UNKNOWN')
    if f['charge_distribution']:categories.append('protonation_charge')
    if f['tautomer_sensitive']:categories.append('tautomer')
    if f['radical_electrons']:reasons.append('ELECTRONIC_STATE_UNSUPPORTED')
    # This is a bounded implementation capability, not a chemical ontology.
    # Keep the previous tested envelope without admitting unvalidated elements.
    tested_elements={'C','H','N','O','F','Cl','Br','I','S','P','B','Si','Li','Na','K','Mg','Ca'}
    if not set(f['elements'])<=tested_elements:reasons.append('UNSUPPORTED_ELEMENT_CAPABILITY')
    if 'C' not in f['elements'] and set(f['elements']) & {'Si','B'}:reasons.append('UNSUPPORTED_DISCRETE_STRUCTURE_CAPABILITY')
    metal={'Li','Na','K','Mg','Ca'}
    for atom in parse(d['smiles']).GetAtoms():
        if atom.GetSymbol() in metal and (atom.GetDegree() or not atom.GetFormalCharge()):reasons.append('UNSUPPORTED_COORDINATION_CAPABILITY')
    hydrate=bool(re.search(r'hydrat',n,re.I))
    solvate=bool(re.search(r'solvat',n,re.I))
    supplied_solvents=dict(a.get('solvent_counts',{}))
    expected_solvents={'water':supplied_solvents['water']} if 'water' in supplied_solvents else {}
    if any(k!='water' for k in supplied_solvents):reasons.append('COMPONENT_STOICHIOMETRY_UNKNOWN')
    if hydrate:
        h=re.search(r'\b('+'|'.join(COUNTS)+r')hydrate\b',n,re.I)
        # A suffix alone does not prove a disconnected water-of-addition graph.
        water_semantics=a.get('form_kind')=='hydrate' or (typed and f['solvent_components'].get('water',0)>0)
        if h and water_semantics:expected_solvents['water']=COUNTS[h.group(1).lower()]
        elif h:reasons.append('HYDRATION_STOICHIOMETRY_UNKNOWN')
        elif not typed or 'water' not in expected_solvents:reasons.append('HYDRATION_STOICHIOMETRY_UNKNOWN')
        categories.append('hydrate')
    if solvate:
        categories.append('solvate')
        # The small solvent vocabulary is diagnostic; no name or label is a
        # complete, grounded source-component interpretation in this increment.
        expected_solvents={}
        reasons.append('COMPONENT_STOICHIOMETRY_UNKNOWN')
    for solvent,count in expected_solvents.items():
        if solvent not in SOLVENTS or not isinstance(count,int) or count<1:reasons.append('COMPONENT_STOICHIOMETRY_UNKNOWN')
        elif f['solvent_components'].get(solvent,0)!=count:reasons.append('SOLVENT_STOICHIOMETRY_CONFLICT')
    solvent_smiles={SOLVENTS[k] for k in expected_solvents if k in SOLVENTS}
    core=[x for x in f['component_identities'] if x['smiles'] not in solvent_smiles]
    ionic=len(core)>1 and any(x['charge']>0 for x in core) and any(x['charge']<0 for x in core)
    has_carbon=any('C' in {x.GetSymbol() for x in parse(c['smiles']).GetAtoms()} for c in core)
    if ionic and a.get('form_kind')=='salt':
        categories.append('salt')
        if sum(x['charge']*x['count'] for x in core)!=0:reasons.append('COUNTERION_RATIO_UNKNOWN')
        if any(not x['charge'] for x in core):reasons.append('MULTICOMPONENT_SEMANTICS_UNKNOWN')
    elif f['component_count']>1:
        if not (len(core)==1 and expected_solvents and (hydrate or solvate or a.get('form_kind') in ('hydrate','solvate'))):
            reasons.append('MULTICOMPONENT_SEMANTICS_UNKNOWN')
    if hydrate and not f['solvent_components'].get('water'):reasons.append('HYDRATION_STOICHIOMETRY_UNKNOWN')
    if a.get('component_stoichiometry') and a['component_stoichiometry']!=f['component_stoichiometry']:reasons.append('COMPONENT_STOICHIOMETRY_CONFLICT')
    if not core:reasons.append('MULTICOMPONENT_SEMANTICS_UNKNOWN')
    # Simple non-carbon molecules such as H2O/D2O are supported; extended ionic
    # inorganic compositions are outside this discrete molecular salt contract.
    if not has_carbon and any(x['charge'] for x in core) and len(core)>1:reasons.append('UNSUPPORTED_MULTICOMPONENT_CAPABILITY')
    return dict(features=f,categories=sorted(set(categories)),form_kind='salt' if 'salt' in categories else 'solvate' if solvate else 'hydrate' if hydrate else 'molecule',
                specification='UNSPECIFIED' if reasons else 'SPECIFIED',reason_codes=sorted(set(reasons)),source_assertion=a,source_stereo_used=verified)
