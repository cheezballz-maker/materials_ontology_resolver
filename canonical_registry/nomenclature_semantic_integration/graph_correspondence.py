"""Bounded all-isomorphism CML correspondence; never decide source semantics."""
import xml.etree.ElementTree as ET
from rdkit import Chem

def correspond(cml,candidate_smiles,max_mappings=1000):
 def fail(reason):return {'status':'UNKNOWN','reason':reason,'mappings':[]}
 try:
  if not isinstance(max_mappings,int) or max_mappings<1:return fail('INVALID_MAPPING_LIMIT')
  root=ET.fromstring(cml);ns={'c':'http://www.xml-cml.org/schema'}
  atoms=root.findall('.//c:atom',ns);bonds=root.findall('.//c:bond',ns)
  rw=Chem.RWMol();ids={};isotopic_h=False
  for element in atoms:
   atom=Chem.Atom(element.get('elementType'));atom.SetFormalCharge(int(element.get('formalCharge','0')))
   if element.get('isotopeNumber'):atom.SetIsotope(int(element.get('isotopeNumber')))
   if atom.GetSymbol()=='H' and atom.GetIsotope():isotopic_h=True
   atom.SetProp('_source_cml_id',element.get('id'));ids[element.get('id')]=rw.AddAtom(atom)
  if isotopic_h:return fail('ISOTOPIC_H_UNSUPPORTED')
  types={'S':Chem.BondType.SINGLE,'D':Chem.BondType.DOUBLE,'T':Chem.BondType.TRIPLE,'A':Chem.BondType.AROMATIC,'1':Chem.BondType.SINGLE,'2':Chem.BondType.DOUBLE,'3':Chem.BondType.TRIPLE}
  for bond in bonds:
   a,b=bond.get('atomRefs2').split();rw.AddBond(ids[a],ids[b],types[bond.get('order')])
  source=rw.GetMol();Chem.SanitizeMol(source);source=Chem.RemoveHs(source)
  params=Chem.SmilesParserParams();params.parseName=False;params.allowCXSMILES=False
  candidate=Chem.MolFromSmiles(candidate_smiles,params)
  if candidate is None:return fail('INVALID_CANDIDATE')
  if any(a.GetNumRadicalElectrons() for a in source.GetAtoms()) or any(a.GetNumRadicalElectrons() for a in candidate.GetAtoms()):return fail('ELECTRONIC_STATE_UNSUPPORTED')
  # This prototype deliberately rejects all specified or potential stereo rather
  # than interpreting CML parity using an unvalidated correspondence.
  if root.findall('.//c:atomParity',ns) or root.findall('.//c:bondStereo',ns) or Chem.FindPotentialStereo(source) or Chem.FindPotentialStereo(candidate):return fail('STEREO_MAPPING_UNSUPPORTED')
  if source.GetNumAtoms()!=candidate.GetNumAtoms() or source.GetNumBonds()!=candidate.GetNumBonds():return fail('GRAPH_SIZE_DIFFERENT')
  if len(Chem.GetMolFrags(source))!=len(Chem.GetMolFrags(candidate)):return fail('COMPONENT_COUNT_DIFFERENT')
  matches=candidate.GetSubstructMatches(source,uniquify=False,useChirality=True,maxMatches=max_mappings+1)
  if len(matches)>max_mappings:return fail('ISOMORPHISM_LIMIT_REACHED')
  if not matches:return fail('GRAPH_NOT_ISOMORPHIC')
  # Substructure matching can ignore hydrogen counts; enforce isotope, charge,
  # aromaticity and total H on every corresponding atom explicitly.
  valid=[]
  for match in matches:
   if all((a.GetAtomicNum(),a.GetIsotope(),a.GetFormalCharge(),a.GetIsAromatic(),a.GetTotalNumHs())==(candidate.GetAtomWithIdx(match[a.GetIdx()]).GetAtomicNum(),candidate.GetAtomWithIdx(match[a.GetIdx()]).GetIsotope(),candidate.GetAtomWithIdx(match[a.GetIdx()]).GetFormalCharge(),candidate.GetAtomWithIdx(match[a.GetIdx()]).GetIsAromatic(),candidate.GetAtomWithIdx(match[a.GetIdx()]).GetTotalNumHs()) for a in source.GetAtoms()):
    valid.append({a.GetProp('_source_cml_id'):match[a.GetIdx()] for a in source.GetAtoms()})
  if not valid:return fail('ATOM_STATE_DIFFERENT')
  return {'status':'MAPPED' if len(valid)==1 else 'AMBIGUOUS','reason':'ALL_ENUMERATED_ISOMORPHISMS','mappings':valid}
 except Exception:return fail('GRAPH_MAPPING_ERROR')

def positions_agree(mapping,cml_atom,predicate):
 """Only all mapped possibilities can support a common outcome."""
 matches=mapping.get('mappings',[])
 if mapping.get('status') not in ('MAPPED','AMBIGUOUS') or not matches:return 'UNKNOWN'
 try:outcomes={bool(predicate(m[cml_atom])) for m in matches}
 except (KeyError,TypeError,ValueError):return 'UNKNOWN'
 return ('ALL_TRUE' if outcomes=={True} else 'ALL_FALSE' if outcomes=={False} else 'UNKNOWN')
