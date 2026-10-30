"""Compare established dimension assertions, never derive name specificity."""
from rdkit import Chem
from chemistry import describe
from form_characterizer import characterize
from charge_comparison_attribution import compare as structural_compare
KEYS={'constitution':'connectivity','stereochemistry':'stereochemistry','tautomer':'tautomeric_form','protonation_charge':'protonation_charge','isotope':'isotope_specification','components':'components','component_stoichiometry':'component_stoichiometry','hydration_solvation':'component_stoichiometry','electronic_state':'electronic_state'}

def _frame(smiles,dimension):
    m=Chem.MolFromSmiles(smiles)
    if m is None:raise ValueError('INVALID_FRAMEWORK')
    if dimension=='stereochemistry':Chem.RemoveStereochemistry(m)
    elif dimension=='isotope':
        for a in m.GetAtoms():a.SetIsotope(0)
    else:raise ValueError('OPEN_SCOPE_UNSUPPORTED_FOR_DIMENSION')
    return Chem.MolToSmiles(m,canonical=True,isomericSmiles=True)

def _exact(a,b,dimension):
    x,y=describe(a),describe(b);cmp=structural_compare(x,y)
    if dimension in ('stereochemistry','isotope') and _frame(a,dimension)!=_frame(b,dimension):return 'UNKNOWN'
    val=cmp['dimensions'][KEYS[dimension]]
    if dimension=='hydration_solvation' and val=='UNKNOWN' and cmp['dimensions']['components']=='DIFFERENT':
        # This adapter compares explicitly supplied full component graphs.
        # It does not infer solid-state hydration from a name or water subgraph.
        return 'DIFFERENT'
    if val=='NOT_APPLICABLE':
        # Single-component stoichiometry is still comparable when actual
        # source graphs are available; it does not mean arbitrary forms agree.
        if dimension in ('components','component_stoichiometry','hydration_solvation'):
            return 'EQUIVALENT' if Chem.MolToSmiles(Chem.MolFromSmiles(a))==Chem.MolToSmiles(Chem.MolFromSmiles(b)) else 'UNKNOWN'
        return 'EQUIVALENT'
    return val

def compare_assertions(claim,candidate,dimension):
    """Finite set inclusion or explicitly open scope on an identical framework."""
    try:
        if not claim or not candidate or claim['state']=='UNKNOWN' or candidate['state']=='UNKNOWN':return 'UNKNOWN'
        sa,sb=claim['state'],candidate['state']
        if sa=='NOT_APPLICABLE':
            if dimension!='stereochemistry':return 'UNKNOWN'
            if _frame(claim['structures'][0],dimension)!=_frame(candidate.get('framework') or candidate['structures'][0],dimension):return 'UNKNOWN'
            if Chem.FindPotentialStereo(Chem.MolFromSmiles(claim['structures'][0])):return 'UNKNOWN'
            return 'NOT_APPLICABLE'
        if sa=='UNSPECIFIED' or sb=='UNSPECIFIED':
            if not all(a.get('scope')=='ALL_WITHIN_FRAMEWORK' and a.get('framework') for a in (claim,candidate) if a['state']=='UNSPECIFIED'):return 'UNKNOWN'
            fa=claim.get('framework') or claim['structures'][0];fb=candidate.get('framework') or candidate['structures'][0]
            if _frame(fa,dimension)!=_frame(fb,dimension):return 'UNKNOWN'
            if sa==sb:return 'UNKNOWN'
            return 'BROADER_THAN_CANDIDATE' if sa=='UNSPECIFIED' else 'NARROWER_THAN_CANDIDATE'
        av,bv=claim['structures'],candidate['structures'];matrix=[[_exact(a,b,dimension) for b in bv] for a in av]
        if any(x=='UNKNOWN' for row in matrix for x in row):return 'UNKNOWN'
        equivalent=lambda x:x=='EQUIVALENT'
        a_in_b=all(any(equivalent(v) for v in row) for row in matrix)
        b_in_a=all(any(equivalent(matrix[i][j]) for i in range(len(av))) for j in range(len(bv)))
        if a_in_b and b_in_a:
            return 'EXACT_COMPATIBLE' if all(x=='EQUIVALENT' for row in matrix for x in row) else 'UNKNOWN'
        if b_in_a:return 'BROADER_THAN_CANDIDATE'
        if a_in_b:return 'NARROWER_THAN_CANDIDATE'
        if all(x=='DIFFERENT' for row in matrix for x in row):return 'EXACT_INCOMPATIBLE'
        return 'UNKNOWN'
    except Exception:return 'UNKNOWN'
