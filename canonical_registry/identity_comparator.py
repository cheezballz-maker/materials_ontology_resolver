"""Dimension-wise structural identity contract; no name/provider/registry policy."""
from chemistry import comparison_views, hydrogen_comparison_smiles
from form_characterizer import characterize,SOLVENTS

E='EQUIVALENT';D='DIFFERENT';U='UNKNOWN';N='NOT_APPLICABLE'

def compare(a,b):
    # Only the temporary comparison descriptors use explicit H2 bonds.
    left, right = hydrogen_comparison_smiles(a['smiles']), hydrogen_comparison_smiles(b['smiles'])
    a_view = {**a, 'smiles': left} if left != a['smiles'] else a
    b_view = {**b, 'smiles': right} if right != b['smiles'] else b
    x,y=characterize(a_view),characterize(b_view)
    same_graph=bool(set(x['resonance_forms']) & set(y['resonance_forms']))
    achiral_same=bool(set(x['resonance_without_stereo_isotope']) & set(y['resonance_without_stereo_isotope']))
    skeleton=x['connectivity']==y['connectivity']
    complete=x['resonance_complete'] and y['resonance_complete']
    dims={};codes=[];relations=[]
    dims['connectivity']=E if skeleton else D
    if x['advanced_stereo'] or y['advanced_stereo'] or any(z['stereo_state'] in ('PARTIAL','UNSPECIFIED') for z in (x,y)):
        dims['stereochemistry']=U;codes.append('STEREO_UNSPECIFIED')
    elif x['stereo_state']==y['stereo_state']=='NOT_APPLICABLE':dims['stereochemistry']=N
    elif same_graph:dims['stereochemistry']=E
    elif achiral_same and not x['isotopes'] and not y['isotopes']:dims['stereochemistry']=D;codes.append('STEREO_DIFFERENT');relations.append('STEREO_RELATED')
    else:dims['stereochemistry']=U
    dims['isotope_specification']=N if not x['isotopes'] and not y['isotopes'] else E if x['isotope_signature']==y['isotope_signature'] else D
    if dims['isotope_specification']==D:
        codes.append('ISOTOPE_DIFFERENT')
        if achiral_same:relations.append('ISOTOPOLOGUE_RELATED')
    charge_equal=x['charge']==y['charge'] and x['hydrogen_count']==y['hydrogen_count'] and bool(set(x['charge_views']) & set(y['charge_views']))
    dims['protonation_charge']=E if charge_equal else D
    if not charge_equal:codes.append('PROTONATION_DIFFERENT')
    dims['electronic_state']=E if x['radical_electrons']==y['radical_electrons'] else D
    if same_graph or achiral_same:dims['tautomeric_form']=E
    elif not skeleton:dims['tautomeric_form']=U
    elif complete:
        av,bv=comparison_views(a_view),comparison_views(b_view)
        if isinstance(av.get('tautomer'),str) and av['tautomer']==bv.get('tautomer'):
            dims['tautomeric_form']=D;codes.append('TAUTOMER_DIFFERENT');relations.append('TAUTOMER_RELATED')
        else:
            dims['tautomeric_form']=U
            if charge_equal and dims['isotope_specification']!=D and dims['stereochemistry']!=D:dims['connectivity']=D
    else:dims['tautomeric_form']=U
    if x['component_count']==y['component_count']==1:
        dims['components']=N;dims['component_stoichiometry']=N
    elif same_graph:dims['components']=E;dims['component_stoichiometry']=E
    else:
        xs,ys=x['component_stoichiometry'],y['component_stoichiometry']
        dims['components']=E if set(xs)==set(ys) else D
        dims['component_stoichiometry']=E if xs==ys else D if set(xs)==set(ys) else U
        codes.append('COMPONENTS_DIFFERENT' if set(xs)!=set(ys) else 'COMPONENT_STOICHIOMETRY_DIFFERENT')
        shared=set(xs)&set(ys)
        changed={s for s in set(xs)|set(ys) if xs.get(s)!=ys.get(s)}
        if shared and changed and changed<=set(SOLVENTS.values()):
            relations.append('HYDRATE_RELATED' if changed=={'O'} else 'SOLVATE_RELATED')
        elif shared and any(c['charge'] for c in x['component_identities']) and any(c['charge'] for c in y['component_identities']):
            relations.append('SALT_RELATED');codes.append('COUNTERION_DIFFERENT')
    exact=same_graph and all(v in (E,N) for v in dims.values())
    return dict(assessment='EXACT' if exact else 'DISTINCT' if D in dims.values() else 'UNRESOLVED',dimensions=dims,
                reason_codes=sorted(set(codes)),relations=sorted(set(relations)),representation_equivalent=same_graph,
                standard_inchikey_equal=a['inchikey']==b['inchikey'])
