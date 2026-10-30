"""Bounded source nomenclature annotations. No provider or candidate inputs."""
import re
import xml.etree.ElementTree as ET
from rdkit import Chem
from chemistry import parse

BLOCK=re.compile(r'\((\d+[a-z]?[RSEZ](?:\s*,\s*\d+[a-z]?[RSEZ])*)\)')
TOKEN=re.compile(r'(\d+[a-z]?)([RSEZ])')

def descriptors(name):
    return [dict(locant=m.group(1),configuration=m.group(2),source_scope='LEADING_NAME_BLOCK' if not name[:block.start()].strip() else 'LOCAL_SCOPE_UNESTABLISHED')
            for block in BLOCK.finditer(name) for m in TOKEN.finditer(block.group(1))]

def source_annotations(name):
    # Record only literal tokens, never derive R/S from rotation or D/L.
    charges=[int(sign+num) for num,sign in re.findall(r'\((\d+)([+-])\)',name)]
    ratios=[[int(a),int(b)] for a,b in re.findall(r'\((\d+)\s*:\s*(\d+)\)',name)]
    counterions=[m.group(0).lower() for m in re.finditer(r'\b(?:di|tri|tetra)?(?:sodium|potassium|lithium|calcium|magnesium)\b',name,re.I)]
    return dict(descriptors=descriptors(name), relative_stereo=re.findall(r'\b(?:cis|trans|syn|anti)\b',name,re.I),
                configurational_series=re.findall(r'(?<![a-zA-Z])[DL](?=\s*(?:[-(]))',name),
                optical_rotation=re.findall(r'\([+-]\)',name),explicit_charges=charges,
                component_ratios=ratios,counterion_terms=counterions)

def map_descriptors(cml, smiles, entries):
    """Map locants via an isomorphism of the OPSIN CML graph and OPSIN SMILES.

    Ambiguous isomorphisms, duplicate locants, missing bonds, and unsupported
    chemistry abstain. Never choose a mapping by atom order or expected CIP.
    """
    def fail(reason): return dict(status='UNKNOWN',reason=reason,mappings=[])
    try:
        root=ET.fromstring(cml); ns={'c':'http://www.xml-cml.org/schema'}
        atoms=root.findall('.//c:atom',ns);bonds=root.findall('.//c:bond',ns)
        rw=Chem.RWMol();ids={};labels={}
        for atom in atoms:
            if atom.get('elementType')=='H':continue
            a=Chem.Atom(atom.get('elementType'));a.SetFormalCharge(int(atom.get('formalCharge','0')))
            if atom.get('isotopeNumber'):a.SetIsotope(int(atom.get('isotopeNumber')))
            idx=rw.AddAtom(a);ids[atom.get('id')]=idx
            for label in atom.findall('c:label',ns):
                if label.get('dictRef','').endswith(':locant'):labels.setdefault(label.get('value'),[]).append(idx)
        types={'S':Chem.BondType.SINGLE,'D':Chem.BondType.DOUBLE,'T':Chem.BondType.TRIPLE,'A':Chem.BondType.AROMATIC}
        for bond in bonds:
            a,b=bond.get('atomRefs2').split()
            if a in ids and b in ids:rw.AddBond(ids[a],ids[b],types[bond.get('order')])
        query=rw.GetMol();Chem.SanitizeMol(query)
        target=parse(smiles);Chem.AssignStereochemistry(target,cleanIt=True,force=True)
        if query.GetNumAtoms()!=target.GetNumAtoms() or query.GetNumBonds()!=target.GetNumBonds():return fail('GRAPH_SIZE_MISMATCH')
        matches=target.GetSubstructMatches(query,uniquify=False,useChirality=False,maxMatches=1001)
        if not matches or len(matches)>=1001:return fail('GRAPH_MAPPING_AMBIGUOUS')
        mapped=[]
        potential=list(Chem.FindPotentialStereo(target))
        stereo_atoms={x.centeredOn for x in potential if str(x.type)=='Atom_Tetrahedral'}
        stereo_bonds={x.centeredOn for x in potential if str(x.type)=='Bond_Double'}
        for entry in entries:
            found=labels.get(entry['locant'],[])
            if not found:return fail('LOCANT_SCOPE_UNRESOLVED')
            indices=[]
            for label_idx in found:
                targets={m[label_idx] for m in matches}
                if len(targets)!=1:return fail('GRAPH_MAPPING_AMBIGUOUS')
                indices.append(next(iter(targets)))
            code=entry['configuration']
            if len(indices)>1:
                # Topological uniqueness does not establish grammatical ownership.
                return fail('LOCANT_SCOPE_UNRESOLVED')
            else:atom_idx=indices[0];scope='GLOBALLY_UNIQUE_LOCANT'
            a=target.GetAtomWithIdx(atom_idx)
            if code in 'RS':
                if not a.HasProp('_CIPCode') or a.GetProp('_CIPCode')!=code:return fail('STEREO_NOT_VERIFIED')
                mapped.append(dict(**entry,descriptor=entry['locant']+code,element='atom',atom_index=atom_idx,scope=scope,verification='VERIFIED'))
            else:
                possible=[b for b in a.GetBonds() if b.GetIdx() in stereo_bonds]
                if len(possible)!=1:return fail('LOCANT_SCOPE_UNRESOLVED')
                double=[b for b in possible if str(b.GetStereo()) in ('STEREOE','STEREOZ')]
                if len(double)!=1 or str(double[0].GetStereo())[-1]!=code:return fail('STEREO_NOT_VERIFIED')
                mapped.append(dict(**entry,descriptor=entry['locant']+code,element='bond',bond_index=double[0].GetIdx(),scope=scope,verification='VERIFIED'))
        elements=[(x['element'],x.get('atom_index',x.get('bond_index'))) for x in mapped]
        if len(set(elements))!=len(elements):return fail('LOCANT_SCOPE_UNRESOLVED')
        return dict(status='MAPPED',source_smiles=Chem.MolToSmiles(target,canonical=True,isomericSmiles=True),mappings=mapped)
    except (ValueError,KeyError,TypeError,ET.ParseError,RuntimeError):return fail('CML_GRAPH_UNSUPPORTED')
