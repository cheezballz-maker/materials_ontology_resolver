"""Conservative, source-independent checks on candidate specificity.

The source name, a source-supplied structure and individual aliases are claims.
A provider structure can reveal a dimension needing examination, but cannot
establish that the source specified that dimension.
"""
import re
import unicodedata
from rdkit import Chem
from chemistry import normalize_name,parse
from form_characterizer import characterize,interpret
from identity_comparator import compare

RELATIVE=re.compile(r'(?<![a-z])(?:cis|trans|syn|anti)(?![a-z])',re.I)
ENSEMBLE=re.compile(r'\b(?:racemic|racemate|rac\.?|dl|d\s*/\s*l|mixture)\b',re.I)
ABSOLUTE=re.compile(r'(?<![A-Za-z])(?:\d+[a-z]?)?([RS])(?=\s*[,\)\]])',re.I)
DL=re.compile(r'(?<![a-z])(?:D|L)[-\s]',re.I)
SUGAR=re.compile(r'(?<![a-z])(?:[dl]-)?(?:gluc|galact|mann|fruct|rib|xyl|arab|idos|fucos)[a-z]*',re.I)
RING=re.compile(r'(?:pyranos|furanos)',re.I)
ANOMER=re.compile(r'(?<![a-z])(?:alpha|beta|α|β)[-\s]?',re.I)
OPEN_CHAIN=re.compile(r'\b(?:open[- ]chain|acyclic|aldehydo|keto[- ])',re.I)
OXYANION=re.compile(r'(?<![a-z])(?:sulfate|sulphate|sulfite|sulphite)(?![a-z])',re.I)
DIMENSIONS=('constitution','stereochemistry','isotope','protonation_charge','tautomer','components','component_stoichiometry','hydration_solvation','molecular_form_scope')


def _lexical_variant(a,b):
    # A narrow punctuation/whitespace variant, not a synonym or parent rule.
    # In particular, retain locant punctuation: 1-23 and 12-3 are different.
    def key(s):return normalize_name(re.sub(r'(?<=[a-z])-(?=[a-z])',' ',normalize_name(s).casefold()))
    return bool(a and b and key(a)==key(b))


def _mirror_distinct(smiles):
    """Relative stereo does not select an enantiomer when its mirror differs."""
    m=parse(smiles);mirror=Chem.Mol(m);changed=False
    for atom in mirror.GetAtoms():
        if atom.GetChiralTag() in (Chem.ChiralType.CHI_TETRAHEDRAL_CCW,Chem.ChiralType.CHI_TETRAHEDRAL_CW):
            atom.InvertChirality();changed=True
    if not changed:return False
    return Chem.MolToSmiles(m,canonical=True,isomericSmiles=True)!=Chem.MolToSmiles(mirror,canonical=True,isomericSmiles=True)


def _oxygen_sulfur_counts(smiles):
    m=parse(smiles)
    return {sum(n.GetAtomicNum()==8 for n in a.GetNeighbors()) for a in m.GetAtoms() if a.GetAtomicNum()==16}


def _sugar_like_ring(smiles):
    m=parse(smiles)
    for ring in m.GetRingInfo().AtomRings():
        atoms=[m.GetAtomWithIdx(i) for i in ring];ids=set(ring)
        if len(ring) not in (5,6) or sum(a.GetAtomicNum()==8 for a in atoms)!=1 or sum(a.GetAtomicNum()==6 for a in atoms)<3:continue
        decorated=sum(any(n.GetAtomicNum()==8 and n.GetIdx() not in ids for n in a.GetNeighbors()) for a in atoms if a.GetAtomicNum()==6)
        if decorated>=2:return True
    return False


def source_claim(name,claim,kind='preferred'):
    n=unicodedata.normalize('NFC',name or '')
    absolute=ABSOLUTE.findall(n)
    match=SUGAR.search(n);sugar=bool(match);alditol=bool(match and match.group().lower().endswith('itol'))
    relative=bool(RELATIVE.search(n));ensemble=bool(ENSEMBLE.search(n))
    features=dict(relative_stereo=relative,absolute_stereo_descriptors=len(absolute),
        absolute_configurations=[x.upper() for x in absolute],dl_descriptor=bool(DL.search(n)),ensemble=ensemble,sugar=sugar,alditol=alditol,
        ring_form=bool(RING.search(n)),anomer=bool(ANOMER.search(n)),open_chain=bool(OPEN_CHAIN.search(n)),
        oxyanion=[m.group().lower().replace('ph','f') for m in OXYANION.finditer(n)])
    d=claim.get('structure') if claim.get('status')=='SUCCESS' else None
    return dict(text=name,claim_type=kind,parsed_interpretation=dict(status=claim.get('status'),smiles=d.get('smiles') if d else None),source_features=features)


def assess(name,primary,alias_claims,candidate,assertion=None,alias_support=None):
    """Return source states and candidate compatibility; never issue an ID.

    Assertions only treat an actual source-supplied typed structure as a full
    structural claim. A selected provider record is never such a claim.
    """
    assertion=assertion or {};typed=assertion.get('explicit_structure') is True
    p=source_claim(name,primary);features=p['source_features'];f=characterize(candidate)
    claims=[p];conflicts=[]
    for alias,c in alias_claims:
        item=source_claim(alias,c,'alias');d=c.get('structure') if c.get('status')=='SUCCESS' else None
        if d:
            comp=compare(candidate,d);item['candidate_comparison']=comp['assessment']
            if comp['assessment']=='DISTINCT':conflicts.append(dict(alias=alias,reason_codes=comp['reason_codes']))
        claims.append(item)
    # The existing exact-form policy still enforces the chemical dimensions.
    # Here SUPPORTED means that no added source-specificity problem was detected,
    # not independent chemical proof or a replacement for that policy.
    states={k:dict(source='SPECIFIED' if typed else 'NOT_ASSESSED',compatibility='SUPPORTED' if typed else 'NOT_ASSESSED') for k in DIMENSIONS}
    reasons=[]
    def setdim(k,source,compatibility,reason=None):
        states[k]=dict(source=source,compatibility=compatibility)
        if reason and reason not in reasons:reasons.append(reason)
    parsed=primary.get('status')=='SUCCESS' and bool(primary.get('structure'))
    matched_alias=bool(alias_support and _lexical_variant(name,alias_support.get('alias','')))
    if typed or parsed or matched_alias:setdim('constitution','SPECIFIED','SUPPORTED')
    else:setdim('constitution','UNSPECIFIED','UNKNOWN','SOURCE_PREFERRED_INTERPRETATION_UNKNOWN')
    oxy=features['oxyanion']
    if oxy:
        counts=_oxygen_sulfur_counts(candidate['smiles']);expected={4 if x=='sulfate' else 3 for x in oxy}
        if not expected.issubset(counts):setdim('constitution','CONFLICTING','CONFLICTING','SOURCE_CONSTITUTION_CONFLICT')
    tetra=sum(s['type']=='Atom_Tetrahedral' and s['state']=='Specified' for s in f['stereo_elements'])
    double=sum(s['type']=='Bond_Double' and s['state']=='Specified' for s in f['stereo_elements'])
    if features['ensemble']:setdim('stereochemistry','ENSEMBLE','CONFLICTING','SOURCE_STEREO_ENSEMBLE')
    elif typed:setdim('stereochemistry','SPECIFIED','SUPPORTED')
    elif tetra:
        a=features['absolute_stereo_descriptors'];rel=features['relative_stereo'];dl=features['dl_descriptor']
        if rel and not a and not dl and _mirror_distinct(candidate['smiles']):
            setdim('stereochemistry','PARTIALLY_SPECIFIED','OVER_SPECIFIED','SOURCE_STEREO_RELATIVE_ONLY')
        elif not (a or dl or rel):setdim('stereochemistry','UNSPECIFIED','OVER_SPECIFIED','SOURCE_STEREO_UNSPECIFIED')
        elif a and a<tetra:
            setdim('stereochemistry','PARTIALLY_SPECIFIED','UNKNOWN','SOURCE_STEREO_PARTIALLY_SPECIFIED')
        elif dl and not a and tetra>1 and not (features['alditol'] and parsed):
            setdim('stereochemistry','PARTIALLY_SPECIFIED','UNKNOWN','SOURCE_STEREO_PARTIALLY_SPECIFIED')
        else:setdim('stereochemistry','SPECIFIED','SUPPORTED')
    elif double:
        # The existing form characterizer checks E/Z and cis/trans source tokens.
        setdim('stereochemistry','SPECIFIED' if (features['relative_stereo'] or features['absolute_stereo_descriptors'] or re.search(r'\([EZez]\)',name)) else 'UNSPECIFIED',
            'SUPPORTED' if (features['relative_stereo'] or features['absolute_stereo_descriptors'] or re.search(r'\([EZez]\)',name)) else 'UNKNOWN',
            None if (features['relative_stereo'] or features['absolute_stereo_descriptors'] or re.search(r'\([EZez]\)',name)) else 'SOURCE_STEREO_UNSPECIFIED')
    else:setdim('stereochemistry','NOT_APPLICABLE','NOT_APPLICABLE')
    if features['absolute_stereo_descriptors']==1 and tetra==1 and states['stereochemistry']['compatibility']=='SUPPORTED':
        m=parse(candidate['smiles']);Chem.AssignStereochemistry(m,force=True,cleanIt=True)
        cip=[atom.GetProp('_CIPCode') for atom in m.GetAtoms() if atom.HasProp('_CIPCode')]
        if len(cip)!=1:setdim('stereochemistry','SPECIFIED','UNKNOWN','SOURCE_STEREO_CONFIGURATION_UNKNOWN')
        elif cip[0].upper()!=features['absolute_configurations'][0]:setdim('stereochemistry','CONFLICTING','CONFLICTING','SOURCE_STEREO_CONFIGURATION_CONFLICT')
    if features['sugar'] and not features['alditol'] and not typed:
        ring_candidate=_sugar_like_ring(candidate['smiles'])
        if features['open_chain']:setdim('molecular_form_scope','SPECIFIED','SUPPORTED')
        elif not features['ring_form']:setdim('molecular_form_scope','UNSPECIFIED','OVER_SPECIFIED','SOURCE_SUGAR_FORM_UNSPECIFIED')
        elif not features['anomer']:setdim('molecular_form_scope','PARTIALLY_SPECIFIED','OVER_SPECIFIED','SOURCE_ANOMER_UNSPECIFIED')
        else:setdim('molecular_form_scope','SPECIFIED','SUPPORTED')
        if features['ring_form'] and not ring_candidate:setdim('molecular_form_scope','CONFLICTING','CONFLICTING','SOURCE_SUGAR_FORM_CONFLICT')
        elif features['open_chain'] and ring_candidate:setdim('molecular_form_scope','CONFLICTING','CONFLICTING','SOURCE_SUGAR_FORM_CONFLICT')
    else:setdim('molecular_form_scope','SPECIFIED' if typed else 'NOT_APPLICABLE','SUPPORTED' if typed else 'NOT_APPLICABLE')
    # Reuse existing deterministic checks for isotope, charge, stoichiometry,
    # solvation and tautomer; do not manufacture source evidence for them.
    existing=interpret(candidate,name,assertion)
    code_map={'isotope':('ISOTOPE_POSITION_UNKNOWN',),'protonation_charge':('PROTONATION','CHARGE'),
              'components':('MULTICOMPONENT','COUNTERION','COMPONENTS'),
              'component_stoichiometry':('STOICHIOMETRY',),
              'hydration_solvation':('HYDRATION','SOLVENT','SOLVATE'), 'tautomer':('TAUTOMER',)}
    for dim,parts in code_map.items():
        failures=[x for x in existing['reason_codes'] if any(t in x for t in parts)]
        relevant=(dim=='isotope' and bool(f['isotopes'])) or (dim=='protonation_charge' and bool(f['charge_distribution'])) or (dim in ('components','component_stoichiometry') and f['component_count']>1) or (dim=='hydration_solvation' and bool(f['solvent_components'])) or (dim=='tautomer' and f['tautomer_sensitive'])
        if failures:setdim(dim,'UNSPECIFIED','UNKNOWN',failures[0])
        elif relevant and (typed or parsed or matched_alias):setdim(dim,'SPECIFIED','SUPPORTED')
        elif relevant:setdim(dim,'UNSPECIFIED','UNKNOWN','SOURCE_FORM_OVERSPECIFIED_BY_CANDIDATE')
        else:setdim(dim,'NOT_APPLICABLE','NOT_APPLICABLE')
    return dict(claims=claims,dimensions=states,source_claim_conflicts=conflicts,source_alias_link='EXACT_LEXICAL_VARIANT' if matched_alias else 'NOT_ESTABLISHED',reason_codes=reasons,
                status='CONFLICT' if any(v['compatibility']=='CONFLICTING' for v in states.values()) else 'UNRESOLVED' if reasons else 'SUPPORTED')
