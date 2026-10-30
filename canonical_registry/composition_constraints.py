"""Source-only compositional constraints; never constructs a salt parent.

Typed component claims and form_kind are source-supplied assertions, not
provider data. A numerical hydrate suffix alone does not prove a disconnected
water-of-addition interpretation.
"""
import re
from collections import Counter
from rdkit import Chem
from chemistry import describe,normalize_name,parse
from identity_comparator import compare

COUNT_PREFIX={'di':2,'tri':3,'tetra':4}
WATER_PREFIX={'mono':1,'di':2,'tri':3,'tetra':4,'penta':5,'hexa':6,'hepta':7,'octa':8,'nona':9,'deca':10}
COUNT_RE=re.compile(r'(?<![A-Za-z])(?P<prefix>di|tri|tetra)(?P<kind>sodium|potassium|hydrochloride)(?![A-Za-z])',re.I)
HYDRATE_RE=re.compile(r'(?<![A-Za-z])(mono|di|tri|tetra|penta|hexa|hepta|octa|nona|deca)hydrate(?![A-Za-z])',re.I)
CHARGE_RE=re.compile(r'\b([a-z][a-z-]*)\((\d+)([+-])\)',re.I)

def field(status,value=None,**extra):return dict(status=status,value=value,**extra)

def extract(name,assertion=None,source_structure=None,source_structure_kind='SOURCE_TYPED_STRUCTURE'):
    """Extract only literal facts and independently supplied source assertions."""
    a=assertion or {};n=normalize_name(name or '');counts=[]
    for m in COUNT_RE.finditer(n):
        counts.append(dict(component=m.group('kind').lower(),count=COUNT_PREFIX[m.group('prefix').lower()],source_text=m.group()))
    by_kind={};conflicts=[]
    for c in counts:
        if c['component'] in by_kind and by_kind[c['component']]!=c['count']:conflicts.append(c['component'])
        by_kind[c['component']]=c['count']
    # Colon ratios are retained as uninterpreted source text until a grounded
    # source grammar and component ownership are available.
    parts=[]
    has_unowned_ratio=bool(re.search(r'\([1-9]\d*\s*[:/]\s*[1-9]\d*(?:\s*[:/]\s*[1-9]\d*)*\)',n))
    raw_claims=a.get('source_components',[]);typed=[];errors=[]
    charge_claims=[dict(component=x.group(1),charge=int(x.group(2))*(1 if x.group(3)=='+' else -1),source_text=x.group()) for x in CHARGE_RE.finditer(n)]
    hydrates=list(HYDRATE_RE.finditer(n));hvalues=[WATER_PREFIX[x.group(1).lower()] for x in hydrates]
    variable=bool(re.search(r'(?<![A-Za-z])(?:hydrate|hydrated|hemihydrate|x\s*H2O|variable\s+hydrate)(?![A-Za-z])',n,re.I))
    source_graph=source_structure if source_structure is not None else None
    source_graph_counts=None
    if source_graph:
        source_mol=parse(source_graph['smiles'])
        source_graph_counts=dict(Counter(Chem.MolToSmiles(f,canonical=True,isomericSmiles=True) for f in Chem.GetMolFrags(source_mol,asMols=True,sanitizeFrags=True)))
    water_meaning=a.get('form_kind')=='hydrate' or bool(source_structure_kind=='SOURCE_TYPED_STRUCTURE' and source_graph_counts and source_graph_counts.get('O'))
    if water_meaning and isinstance(a.get('solvent_counts'),dict) and 'water' in a['solvent_counts']:
        count=a['solvent_counts']['water']
        if isinstance(count,int) and not isinstance(count,bool) and count>0:hvalues.append(count)
        else:errors.append('SOURCE_COMPONENT_CLAIMS_INVALID')
    water_status='CONFLICTING' if len(set(hvalues))>1 else 'SPECIFIED' if hvalues and water_meaning else 'UNSPECIFIED' if hvalues or variable else 'NOT_APPLICABLE'
    # A name parser's proposed graph is candidate evidence, not an independent
    # source assertion of component structures, charges or stoichiometry.
    complete=bool(source_graph_counts and source_structure_kind=='SOURCE_TYPED_STRUCTURE')
    source_components=parts or [x['component'] for x in counts]
    components=field('SPECIFIED' if source_components or (source_graph_counts and source_structure_kind=='SOURCE_TYPED_STRUCTURE') else 'UNSPECIFIED' if hvalues or variable or (source_graph_counts and sum(source_graph_counts.values())>1) else 'NOT_APPLICABLE',source_components,complete=complete,source_graph_component_counts=source_graph_counts)
    return dict(components=components,
        component_counts=field('CONFLICTING' if conflicts else 'SPECIFIED' if counts else 'NOT_APPLICABLE',counts),
        component_ratios=field('UNSPECIFIED' if has_unowned_ratio else 'NOT_APPLICABLE',None,component_names=parts),
        formal_charges=field('SPECIFIED' if charge_claims or typed or (source_graph and source_structure_kind=='SOURCE_TYPED_STRUCTURE') else 'UNSPECIFIED' if counts else 'NOT_APPLICABLE',charge_claims,source_component_charges=[x['formal_charge'] for x in typed]),
        fixed_water_count=field(water_status,hvalues[0] if hvalues and len(set(hvalues))==1 else None,water_of_addition_established=water_meaning,source_equivalents=hvalues),
        typed_components=typed,uninterpreted_source_components=bool(raw_claims),source_name=n,source_graph=source_graph,source_graph_kind=source_structure_kind if source_graph else None,source_errors=errors)

def check(constraints,candidate):
    """Check source-established facts, never infer or rewrite structures."""
    reasons=[];checked=[];unknown=[]
    if constraints['source_errors'] or any(constraints[k]['status']=='CONFLICTING' for k in ('component_counts','fixed_water_count')):
        return dict(status='CONFLICT',reason_codes=['MULTICOMPONENT_SOURCE_INCOMPLETE'],checked=[])
    mol=parse(candidate['smiles']);frags=Chem.GetMolFrags(mol,asMols=True,sanitizeFrags=True)
    forms=Counter(Chem.MolToSmiles(f,canonical=True,isomericSmiles=True) for f in frags)
    source_graph=constraints.get('source_graph')
    if source_graph:
        comparison=compare(source_graph,candidate)
        checked.append(dict(kind='typed_source_graph',assessment=comparison['assessment']))
        if comparison['assessment']=='DISTINCT':reasons.append('IDENTITY_DIMENSION_CONFLICT')
        elif comparison['assessment']!='EXACT':unknown.append('MULTICOMPONENT_SOURCE_INCOMPLETE')
    def singleton_count(symbol,charges,hydrogens=None):
        return sum(1 for f in frags if f.GetNumAtoms()==1 and f.GetAtomWithIdx(0).GetSymbol()==symbol
            and f.GetAtomWithIdx(0).GetFormalCharge() in charges
            and (hydrogens is None or f.GetAtomWithIdx(0).GetTotalNumHs() in hydrogens))
    # Fractional hydration can make a candidate graph contain several formula
    # units. Without an established unit multiplier, absolute counts are not
    # comparable to per-formula-unit source coefficients.
    fractional=bool(re.search(r'(?<![A-Za-z])(?:hemihydrate|fractional\s+hydrate)(?![A-Za-z])',constraints.get('source_name',''),re.I))
    for c in ([] if fractional else constraints['component_counts']['value'] or []):
        kind=c['component']
        if kind=='sodium':observed=singleton_count('Na',{1})
        elif kind=='potassium':observed=singleton_count('K',{1})
        else:observed=singleton_count('Cl',{-1},{0})+singleton_count('Cl',{0},{1})
        checked.append(dict(kind=kind,expected=c['count'],observed=observed))
        if observed!=c['count']:reasons.append('COMPONENT_COUNT_MISMATCH')
    water=constraints['fixed_water_count']
    if water['status']=='SPECIFIED':
        observed=forms.get('O',0);checked.append(dict(kind='water',expected=water['value'],observed=observed))
        if observed!=water['value']:reasons.append('FIXED_HYDRATE_COUNT_MISMATCH')
    elif water['status']=='UNSPECIFIED':unknown.append('MULTICOMPONENT_SOURCE_INCOMPLETE')
    if constraints['component_ratios']['status']=='SPECIFIED':
        parts=constraints['typed_components']
        if len(parts)!=2:unknown.append('MULTICOMPONENT_SOURCE_INCOMPLETE')
        else:
            expected=Counter({p['smiles']:p['count'] for p in parts})
            observed=Counter({p['smiles']:forms.get(p['smiles'],0) for p in parts})
            checked.append(dict(kind='exact_components',expected=dict(expected),observed=dict(forms)))
            if expected!=observed:reasons.append('COMPONENT_RATIO_MISMATCH')
            if set(forms)!=set(expected):reasons.append('COMPONENT_COUNT_MISMATCH')
    if constraints['formal_charges']['value'] and not constraints['typed_components']:
        unknown.append('MULTICOMPONENT_SOURCE_INCOMPLETE')
    if constraints['component_ratios']['status']=='UNSPECIFIED':
        unknown.append('MULTICOMPONENT_SOURCE_INCOMPLETE')
    if constraints.get('uninterpreted_source_components'):
        unknown.append('MULTICOMPONENT_SOURCE_INCOMPLETE')
    if constraints.get('source_graph_kind')=='SOURCE_NAME_PARSE' and re.search(r'(?<![A-Za-z])(?:di|tri|tetra)?hydrochloride(?![A-Za-z])',constraints.get('source_name',''),re.I):
        unknown.append('MULTICOMPONENT_SOURCE_INCOMPLETE')
    if len(frags)>1 and not constraints['components']['complete']:
        unknown.append('MULTICOMPONENT_SOURCE_INCOMPLETE')
    return dict(status='CONFLICT' if reasons else 'UNRESOLVED' if unknown else 'SUPPORTED',reason_codes=sorted(set(reasons or unknown)),checked=checked)
