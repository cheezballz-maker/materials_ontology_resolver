"""Conservative, source-independent checks on candidate specificity.

The source name, a source-supplied structure and individual aliases are claims.
A provider structure can reveal a dimension needing examination, but cannot
establish that the source specified that dimension.
"""
import re
import unicodedata
from rdkit import Chem
from chemistry import normalize_name,parse
from form_characterizer import characterize,interpret,verified_source_stereo
from identity_comparator import compare

RELATIVE=re.compile(r'(?<![a-z])(?:cis|trans|syn|anti)(?![a-z])',re.I)
ENSEMBLE=re.compile(r'\b(?:racemic|racemate|rac\.?|dl|d\s*/\s*l|mixture)\b',re.I)
ABSOLUTE=re.compile(r'(?<![A-Za-z])(?:\d+[a-z]?)?([RS])(?=\s*[,\)\]])')
GEOMETRIC=re.compile(r'(?<![A-Za-z])(?:\d+[a-z]?)?([EZ])(?=\s*[,\)\]])')
DL=re.compile(r'(?<![a-zA-Z])(?:D|L)[-\s]')
DIMENSIONS=('constitution','stereochemistry','isotope','protonation_charge','electronic_state','tautomer','components','component_stoichiometry','hydration_solvation','molecular_form_scope')

def aggregate_dimensions(states):
    """Conjunction of applicable identity states; unknown cannot certify exactness."""
    values=[v.get('compatibility') for v in states.values()]
    if any(v in ('DIFFERENT','CONFLICTING') for v in values) or any(v.get('source') in ('DIFFERENT','CONFLICTING') and v.get('compatibility')!='NOT_APPLICABLE' for v in states.values()):return 'CONFLICT'
    if any(v not in ('SUPPORTED','EQUIVALENT','NOT_APPLICABLE') for v in values):return 'UNRESOLVED'
    if any(v.get('source') in ('UNKNOWN','UNSPECIFIED','PARTIALLY_SPECIFIED','NOT_ASSESSED') and v.get('compatibility')!='NOT_APPLICABLE' for v in states.values()):return 'UNRESOLVED'
    return 'SUPPORTED'


def _lexical_variant(a,b):
    # Textual identity only: case and punctuation can carry chemical meaning.
    return bool(a and b and normalize_name(a)==normalize_name(b))


def _mirror_distinct(smiles):
    """Relative stereo does not select an enantiomer when its mirror differs."""
    m=parse(smiles);mirror=Chem.Mol(m);changed=False
    for atom in mirror.GetAtoms():
        if atom.GetChiralTag() in (Chem.ChiralType.CHI_TETRAHEDRAL_CCW,Chem.ChiralType.CHI_TETRAHEDRAL_CW):
            atom.InvertChirality();changed=True
    if not changed:return False
    return Chem.MolToSmiles(m,canonical=True,isomericSmiles=True)!=Chem.MolToSmiles(mirror,canonical=True,isomericSmiles=True)


def source_claim(name,claim,kind='preferred'):
    n=unicodedata.normalize('NFC',name or '')
    absolute=ABSOLUTE.findall(n)
    relative=bool(RELATIVE.search(n));ensemble=bool(ENSEMBLE.search(n))
    features=dict(relative_stereo=relative,absolute_stereo_descriptors=len(absolute),
        absolute_configurations=absolute,geometric_configurations=GEOMETRIC.findall(n),dl_descriptor=bool(DL.search(n)),ensemble=ensemble)
    d=claim.get('structure') if claim.get('status')=='SUCCESS' else None
    return dict(text=name,claim_type=kind,parsed_interpretation=dict(status=claim.get('status'),smiles=d.get('smiles') if d else None),source_features=features)


def assess(name,primary,alias_claims,candidate,assertion=None,alias_support=None,source_profile=None):
    """Return source states and candidate compatibility; never issue an ID.

    Assertions only treat an actual source-supplied typed structure as a full
    structural claim. A selected provider record is never such a claim.
    """
    assertion=assertion or {};typed=assertion.get('explicit_structure') is True
    p=source_claim(name,primary);features=p['source_features'];f=characterize(candidate)
    stereo_verified=verified_source_stereo(candidate,source_profile)
    claims=[p];conflicts=[];specific_differences=[];specific_unknowns=[]
    for alias,c in alias_claims:
        item=source_claim(alias,c,'alias');d=c.get('structure') if c.get('status')=='SUCCESS' else None
        if d:
            comp=compare(candidate,d);item['candidate_comparison']=comp['assessment']
            if comp['assessment'] in ('DISTINCT','UNRESOLVED'):
                source_d=primary.get('structure') if primary.get('status')=='SUCCESS' else None
                src=compare(source_d,d) if source_d else None
                af=item['source_features'];alias_form=interpret(d,alias)
                broad=bool(af['ensemble'] or alias_form['specification']!='SPECIFIED' or (af['relative_stereo'] and not (af['absolute_stereo_descriptors'] or af['dl_descriptor']) and _mirror_distinct(d['smiles'])))
                conflicts.append(dict(alias=alias,reason_codes=comp['reason_codes'],constitution_different=bool(src and src['dimensions']['connectivity']=='DIFFERENT'),dimensions=comp['dimensions'],alias_specific=not broad))
                if not broad:
                    if comp['assessment']=='DISTINCT':specific_differences.append(comp)
                    else:specific_unknowns.append(comp)
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
    if parsed and any(x.get('constitution_different') and x.get('alias_specific') for x in conflicts):
        setdim('constitution','CONFLICTING','CONFLICTING','SOURCE_CONSTITUTION_CONFLICT')
    tetra=sum(s['type']=='Atom_Tetrahedral' and s['state']=='Specified' for s in f['stereo_elements'])
    double=sum(s['type']=='Bond_Double' and s['state']=='Specified' for s in f['stereo_elements'])
    if features['ensemble']:setdim('stereochemistry','ENSEMBLE','CONFLICTING','SOURCE_STEREO_ENSEMBLE')
    elif typed:setdim('stereochemistry','SPECIFIED','SUPPORTED')
    elif stereo_verified:setdim('stereochemistry','SPECIFIED','SUPPORTED')
    elif tetra:
        a=features['absolute_stereo_descriptors'];rel=features['relative_stereo'];dl=features['dl_descriptor']
        if rel and not a and not dl and _mirror_distinct(candidate['smiles']):
            setdim('stereochemistry','PARTIALLY_SPECIFIED','OVER_SPECIFIED','SOURCE_STEREO_RELATIVE_ONLY')
        elif not (a or dl or rel):setdim('stereochemistry','UNSPECIFIED','OVER_SPECIFIED','SOURCE_STEREO_UNSPECIFIED')
        elif a and a<tetra:
            setdim('stereochemistry','PARTIALLY_SPECIFIED','UNKNOWN','SOURCE_STEREO_PARTIALLY_SPECIFIED')
        elif dl and not a:
            setdim('stereochemistry','PARTIALLY_SPECIFIED','UNKNOWN','SOURCE_STEREO_PARTIALLY_SPECIFIED')
        else:setdim('stereochemistry','SPECIFIED','SUPPORTED')
    elif double:
        # The existing form characterizer checks E/Z and cis/trans source tokens.
        geometric=features['relative_stereo'] or features['geometric_configurations']
        setdim('stereochemistry','SPECIFIED' if geometric else 'UNSPECIFIED',
            'SUPPORTED' if geometric else 'UNKNOWN',None if geometric else 'SOURCE_STEREO_UNSPECIFIED')
    else:setdim('stereochemistry','NOT_APPLICABLE','NOT_APPLICABLE')
    if not stereo_verified and features['absolute_stereo_descriptors']==1 and tetra==1 and states['stereochemistry']['compatibility']=='SUPPORTED':
        m=parse(candidate['smiles']);Chem.AssignStereochemistry(m,force=True,cleanIt=True)
        cip=[atom.GetProp('_CIPCode') for atom in m.GetAtoms() if atom.HasProp('_CIPCode')]
        if len(cip)!=1:setdim('stereochemistry','SPECIFIED','UNKNOWN','SOURCE_STEREO_CONFIGURATION_UNKNOWN')
        elif cip[0].upper()!=features['absolute_configurations'][0]:setdim('stereochemistry','CONFLICTING','CONFLICTING','SOURCE_STEREO_CONFIGURATION_CONFLICT')
    if not stereo_verified and len(features['geometric_configurations'])==1 and double==1 and states['stereochemistry']['compatibility']=='SUPPORTED':
        m=parse(candidate['smiles']);Chem.AssignStereochemistry(m,force=True,cleanIt=True)
        geometries=[str(b.GetStereo())[-1] for b in m.GetBonds() if str(b.GetStereo()) in ('STEREOE','STEREOZ')]
        if len(geometries)!=1:setdim('stereochemistry','SPECIFIED','UNKNOWN','SOURCE_STEREO_CONFIGURATION_UNKNOWN')
        elif geometries[0]!=features['geometric_configurations'][0]:setdim('stereochemistry','CONFLICTING','CONFLICTING','SOURCE_STEREO_CONFIGURATION_CONFLICT')
    setdim('molecular_form_scope','SPECIFIED' if typed or parsed else 'UNSPECIFIED','SUPPORTED' if typed or parsed else 'UNKNOWN',None if typed or parsed else 'SOURCE_FORM_SCOPE_UNKNOWN')
    # Reuse existing deterministic checks for isotope, charge, stoichiometry,
    # solvation and tautomer; do not manufacture source evidence for them.
    existing=interpret(candidate,name,assertion,source_profile)
    code_map={'isotope':('ISOTOPE_POSITION_UNKNOWN',),'protonation_charge':('PROTONATION','CHARGE'),'electronic_state':('ELECTRONIC_STATE',),
              'components':('MULTICOMPONENT','COUNTERION','COMPONENTS'),
              'component_stoichiometry':('STOICHIOMETRY',),
              'hydration_solvation':('HYDRATION','SOLVENT','SOLVATE'), 'tautomer':('TAUTOMER',)}
    for dim,parts in code_map.items():
        failures=[x for x in existing['reason_codes'] if any(t in x for t in parts)]
        relevant=(dim=='isotope' and bool(f['isotopes'])) or (dim=='protonation_charge' and bool(f['charge_distribution'])) or (dim=='electronic_state' and bool(f['radical_electrons'])) or (dim in ('components','component_stoichiometry') and f['component_count']>1) or (dim=='hydration_solvation' and bool(f['solvent_components'].get('water'))) or (dim=='tautomer' and f['tautomer_sensitive'])
        if failures:setdim(dim,'UNSPECIFIED','UNKNOWN',failures[0])
        elif relevant and dim=='tautomer' and not typed:setdim(dim,'UNSPECIFIED','UNKNOWN','SOURCE_TAUTOMER_SPECIFICITY_UNKNOWN')
        elif relevant and dim=='protonation_charge' and not typed:setdim(dim,'UNSPECIFIED','UNKNOWN','SOURCE_PROTONATION_SPECIFICITY_UNKNOWN')
        elif relevant and (typed or parsed or matched_alias):setdim(dim,'SPECIFIED','SUPPORTED')
        elif relevant:setdim(dim,'UNSPECIFIED','UNKNOWN','SOURCE_FORM_OVERSPECIFIED_BY_CANDIDATE')
        else:setdim(dim,'NOT_APPLICABLE','NOT_APPLICABLE')
    mapping={'connectivity':('constitution','SOURCE_CONSTITUTION_CONFLICT'),'stereochemistry':('stereochemistry','STEREO_DIFFERENT'),'isotope_specification':('isotope','ISOTOPE_DIFFERENT'),'protonation_charge':('protonation_charge','PROTONATION_DIFFERENT'),'electronic_state':('electronic_state','ELECTRONIC_STATE_DIFFERENT'),'tautomeric_form':('tautomer','TAUTOMER_DIFFERENT'),'components':('components','COMPONENTS_DIFFERENT'),'component_stoichiometry':('component_stoichiometry','COMPONENT_STOICHIOMETRY_DIFFERENT')}
    for comparison in specific_unknowns:
        for key,(dim,code) in mapping.items():
            if comparison['dimensions'].get(key)=='UNKNOWN':setdim(dim,'UNSPECIFIED','UNKNOWN','SOURCE_ALIAS_COMPARISON_UNKNOWN')
    for comparison in specific_differences:
        for key,(dim,code) in mapping.items():
            # If constitution differs, secondary charge and tautomer signatures
            # are not independent form evidence for the source conflict.
            if key!='connectivity' and comparison['dimensions']['connectivity']=='DIFFERENT':continue
            if comparison['dimensions'].get(key)=='DIFFERENT':setdim(dim,'CONFLICTING','DIFFERENT',code)
    status=aggregate_dimensions(states)
    if status=='SUPPORTED' and reasons:status='UNRESOLVED'
    return dict(claims=claims,dimensions=states,source_stereo_used=stereo_verified and not features['ensemble'] and not typed,source_claim_conflicts=conflicts,source_alias_link='EXACT_LEXICAL_VARIANT' if matched_alias else 'NOT_ESTABLISHED',reason_codes=reasons,status=status)
