"""Strict representation validation. Comparison parents never become identity keys."""
import re
import unicodedata
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors, inchi
from rdkit.Chem.MolStandardize import rdMolStandardize as ms

class ChemicalValidationError(ValueError):
    """A known failure at a particular chemical validation step."""

    def __init__(self, code, operation, message):
        super().__init__(message)
        self.code = code
        self.operation = operation


def hydrogen_comparison_graph(mol):
    """Expand only the isolated neutral protium H-count spelling of H2."""
    indices = [
        atom.GetIdx() for atom in mol.GetAtoms()
        if atom.GetAtomicNum() == 1 and atom.GetDegree() == 0
        and atom.GetTotalNumHs() == 1 and atom.GetIsotope() == 0
        and atom.GetFormalCharge() == 0 and atom.GetNumRadicalElectrons() == 0
    ]
    return Chem.AddHs(mol, onlyOnAtoms=indices) if indices else mol


def hydrogen_comparison_smiles(smiles):
    if '[HH]' not in smiles:
        return smiles
    return Chem.MolToSmiles(hydrogen_comparison_graph(parse(smiles)), isomericSmiles=True)


def normalize_name(value):
    return ' '.join(unicodedata.normalize('NFC', value).split())

def parse(value, kind='smiles'):
    if not isinstance(value,str) or not value or re.search(r'\s',value):
        raise ValueError('Empty structure or unconsumed whitespace/text')
    if kind == 'smiles':
        p=Chem.SmilesParserParams(); p.parseName=False; p.allowCXSMILES=False
        m=Chem.MolFromSmiles(value,p)
    elif kind == 'inchi':
        if not re.fullmatch(r'InChI=1S?/[A-Za-z0-9+\-(),.;?/*]+',value):
            raise ValueError('Invalid InChI lexical form')
        m=Chem.MolFromInchi(value,sanitize=True,removeHs=True)
        if m is not None:
            generated=Chem.MolToInchi(m,options='' if value.startswith('InChI=1S/') else '/FixedH')
            if generated != value:
                raise ValueError('InChI does not round trip exactly; review required')
    else:
        raise ValueError('Explicit input type must be smiles or inchi')
    if m is None or not m.GetNumAtoms(): raise ValueError('Structure parse failed')
    if any(a.GetAtomicNum()==0 or a.GetAtomMapNum() for a in m.GetAtoms()):
        raise ValueError('Query atoms/atom maps are not admitted')
    Chem.SanitizeMol(m)
    return m

def _inchi_projection(mol, operation, options=''):
    from rdkit.Chem import rdinchi
    try:
        value, code, message, _, _ = rdinchi.MolToInchi(mol, options)
    except (ValueError, RuntimeError) as exc:
        raise ChemicalValidationError('INCHI_GENERATION_FAILED', operation, 'InChI generation failed: ' + str(exc)) from exc
    if code > 1 or not value:
        raise ChemicalValidationError('INCHI_GENERATION_FAILED', operation, 'InChI generation failed: ' + (message or 'No InChI returned'))
    return value, message


def describe(value,kind='smiles'):
    m=parse(value,kind)
    std,message=_inchi_projection(m,'STANDARD_INCHI')
    fixed,_=_inchi_projection(m,'FIXED_H_INCHI','/FixedH')
    return dict(original_input=value,input_type=kind,smiles=Chem.MolToSmiles(m,canonical=True,isomericSmiles=True),
        canonical_smiles=Chem.MolToSmiles(m,canonical=True,isomericSmiles=False),
        inchi=std,inchikey=Chem.InchiToInchiKey(std),fixed_h_inchi=fixed,
        formula=rdMolDescriptors.CalcMolFormula(m),charge=Chem.GetFormalCharge(m),
        components=len(Chem.GetMolFrags(m)),atoms=m.GetNumHeavyAtoms(),
        isotopes=[(a.GetIdx(),a.GetIsotope()) for a in m.GetAtoms() if a.GetIsotope()],
        radicals=sum(a.GetNumRadicalElectrons() for a in m.GetAtoms()),
        stereo=[dict(type=str(s.type),specified=str(s.specified),centered_on=s.centeredOn) for s in Chem.FindPotentialStereo(m)],
        elements=sorted({a.GetSymbol() for a in m.GetAtoms()}),inchi_warning=message)

def exact_key(d):
    return (d['smiles'],d['inchikey'])

def comparison_views(d):
    m=parse(d['smiles']); out={}
    for label,fn in [('normalized',ms.Normalize),('tautomer',ms.TautomerParent),('charge',ms.ChargeParent),('fragment',ms.FragmentParent),('isotope',ms.IsotopeParent),('stereo',ms.StereoParent)]:
        try: out[label]=Chem.MolToSmiles(fn(Chem.Mol(m)),isomericSmiles=True)
        except Exception as e: out[label]={'error':str(e)}
    return out

def related(a,b):
    if exact_key(a)==exact_key(b): return 'EXACT'
    av,bv=comparison_views(a),comparison_views(b)
    # ChargeParent may also choose a fragment. Do not call a component loss a
    # protonation difference, and do not infer that disconnected components are salts.
    if a['components']!=b['components']:
        return 'SHARED_FRAGMENT_PARENT' if av['fragment']==bv['fragment'] else 'DIFFERENT_STRUCTURE'
    sa,sb=parse(a['smiles']),parse(b['smiles'])
    Chem.RemoveStereochemistry(sa); Chem.RemoveStereochemistry(sb)
    if Chem.MolToSmiles(sa)==Chem.MolToSmiles(sb): return 'SAME_CONNECTIVITY_DIFFERENT_STEREO'
    for key,label in [('isotope','ISOTOPE_RELATED'),('tautomer','TAUTOMER_RELATED'),('charge','CHARGE_PARENT_RELATED'),('fragment','SHARED_FRAGMENT_PARENT')]:
        if isinstance(av[key],str) and av[key]==bv[key]: return label
    return 'DIFFERENT_STRUCTURE'
