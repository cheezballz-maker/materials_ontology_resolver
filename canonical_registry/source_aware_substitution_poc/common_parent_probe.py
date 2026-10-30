"""Experimental graph observation only; never returns a semantic decision.

The two cut bonds must be supplied by independent, same-result OPSIN trace
events.  This does not certify the events' lineage or candidate provenance.
"""
import xml.etree.ElementTree as ET
from rdkit import Chem


def _parts(cml, parent_id, attachment_id):
    root = ET.fromstring(cml)
    ns = {'c': 'http://www.xml-cml.org/schema'}
    if root.findall('.//c:atomParity', ns) or root.findall('.//c:bondStereo', ns):
        raise ValueError('STEREO_UNSUPPORTED')
    rw = Chem.RWMol(); ids = {}
    for el in root.findall('.//c:atom', ns):
        atom = Chem.Atom(el.get('elementType'))
        atom.SetFormalCharge(int(el.get('formalCharge', '0')))
        atom.SetIsotope(int(el.get('isotopeNumber', '0')))
        if atom.GetSymbol() == 'H' and atom.GetIsotope():
            raise ValueError('ISOTOPIC_H_UNSUPPORTED')
        atom.SetProp('_cml_id', el.get('id'))
        ids[el.get('id')] = rw.AddAtom(atom)
    types = {'S': Chem.BondType.SINGLE, 'D': Chem.BondType.DOUBLE,
             'T': Chem.BondType.TRIPLE, 'A': Chem.BondType.AROMATIC}
    for el in root.findall('.//c:bond', ns):
        a, b = el.get('atomRefs2').split()
        rw.AddBond(ids[a], ids[b], types[el.get('order')])
    if len(Chem.GetMolFrags(rw)) != 1:
        raise ValueError('MULTICOMPONENT_UNSUPPORTED')
    a, b = ids[parent_id], ids[attachment_id]
    bond = rw.GetBondBetweenAtoms(a, b)
    if bond is None or bond.GetBondType() != Chem.BondType.SINGLE or bond.IsInRing():
        raise ValueError('ATTACHMENT_NOT_SINGLE_BRIDGE')
    rw.RemoveBond(a, b)
    # Restore the single valence at each endpoint with H. This is a comparison
    # construction only, not a claim about a historical intermediate.
    for idx in (a, b):
        h = rw.AddAtom(Chem.Atom('H')); rw.AddBond(idx, h, Chem.BondType.SINGLE)
    mol = rw.GetMol(); Chem.SanitizeMol(mol); mol = Chem.RemoveHs(mol)
    if Chem.FindPotentialStereo(mol) or any(x.GetNumRadicalElectrons() for x in mol.GetAtoms()):
        raise ValueError('STEREO_OR_RADICAL_UNSUPPORTED')
    frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
    if len(frags) != 2:
        raise ValueError('CUT_DID_NOT_YIELD_TWO_FRAGMENTS')
    def select(atomid):
        return next(f for f in frags if any(x.HasProp('_cml_id') and x.GetProp('_cml_id') == atomid for x in f.GetAtoms()))
    return select(parent_id), select(attachment_id)


def _matches(a, b, limit):
    if a.GetNumAtoms() != b.GetNumAtoms() or a.GetNumBonds() != b.GetNumBonds(): return None
    matches = b.GetSubstructMatches(a, uniquify=False, useChirality=True, maxMatches=limit+1)
    if len(matches) > limit: raise ValueError('MAPPING_LIMIT')
    def state(x): return (x.GetAtomicNum(), x.GetIsotope(), x.GetFormalCharge(), x.GetIsAromatic(), x.GetTotalNumHs())
    return [m for m in matches if all(state(x) == state(b.GetAtomWithIdx(m[x.GetIdx()])) for x in a.GetAtoms())]


def compare(source, candidate, limit=1000):
    """Return an observation, never OPERATION_SUPPORTED or DIFFERENT."""
    try:
        if not isinstance(limit, int) or limit < 1: raise ValueError('INVALID_LIMIT')
        for row in (source, candidate):
            if row['status'] != 'SUCCESS' or row['warnings'] or row['ambiguous'] or not row['single_selected_parse'] or len(row['events']) != 1:
                raise ValueError('UNRELIABLE_PARSE_OR_EVENT')
            event = row['events'][0]
            if event['clone_activity'] or not event['graph_bond_verified'] or not event['locant_span_verified'] or event['substituent_span_status'] != 'OBSERVED_CONTIGUOUS_PARSER_TOKENS':
                raise ValueError('UNRELIABLE_EVENT')
        ea, eb = source['events'][0], candidate['events'][0]
        pa, sa = _parts(source['cml'], ea['parent_atom'], ea['attachment_atom'])
        pb, sb = _parts(candidate['cml'], eb['parent_atom'], eb['attachment_atom'])
        pm = _matches(pa, pb, limit); sm = _matches(sa, sb, limit)
        if not pm or not sm: raise ValueError('NO_EXACT_CAPPED_FRAGMENT_CORRESPONDENCE')
        ia = next(x.GetIdx() for x in pa.GetAtoms() if x.GetProp('_cml_id') == ea['parent_atom'])
        ib = next(x.GetIdx() for x in pb.GetAtoms() if x.GetProp('_cml_id') == eb['parent_atom'])
        outcomes = sorted(set(m[ia] == ib for m in pm))
        return {'observation': 'ALL_TARGETS_AGREE' if outcomes == [True] else 'ALL_TARGETS_DIFFER' if outcomes == [False] else 'SYMMETRY_AMBIGUOUS',
                'parent_mappings': len(pm), 'substituent_mappings': len(sm),
                'operation': 'OPERATION_UNKNOWN', 'dimension': 'UNKNOWN',
                'reason': 'OPERATION_LINEAGE_AND_CANDIDATE_PROVENANCE_UNPROVEN'}
    except Exception as exc:
        return {'observation': 'UNKNOWN', 'operation': 'OPERATION_UNKNOWN', 'dimension': 'UNKNOWN', 'reason': str(exc)}
