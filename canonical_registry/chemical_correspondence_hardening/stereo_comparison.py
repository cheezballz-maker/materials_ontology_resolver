"""Bounded ordinary tetrahedral/E-Z constraints over every exact graph mapping.

The input graphs and original comparators are never changed. CIP is diagnostic
only: tetrahedral parity is transported using the ordered neighbour mapping.
Unsupported stereo and truncated symmetry enumeration always abstain.
"""
import bootstrap
from rdkit import Chem
from chemistry import hydrogen_comparison_graph, parse
import isotope_comparator as previous

LIMIT=4096
CW=Chem.ChiralType.CHI_TETRAHEDRAL_CW
CCW=Chem.ChiralType.CHI_TETRAHEDRAL_CCW

def _atom(a):
 return (a.GetAtomicNum(),a.GetIsotope(),a.GetFormalCharge(),a.GetNumRadicalElectrons(),a.GetTotalNumHs(),a.GetIsAromatic(),a.GetDegree())

def _bond(b):return (str(b.GetBondType()),b.GetIsAromatic())

def _supported(m, potential):
 if m.GetStereoGroups():return False
 if any(a.GetChiralTag() not in (Chem.ChiralType.CHI_UNSPECIFIED,CW,CCW) for a in m.GetAtoms()):return False
 ordinary=(Chem.BondStereo.STEREONONE,Chem.BondStereo.STEREOE,Chem.BondStereo.STEREOZ,Chem.BondStereo.STEREOCIS,Chem.BondStereo.STEREOTRANS)
 if any(b.GetStereo() not in ordinary for b in m.GetBonds()):return False
 return all(str(s.type) in ('Atom_Tetrahedral','Bond_Double') for s in potential)

def _exact_mapping(a, b, mapping):
 return (len(mapping) == a.GetNumAtoms() == b.GetNumAtoms()
         and a.GetNumBonds() == b.GetNumBonds()
         and all(_atom(atom) == _atom(b.GetAtomWithIdx(mapping[atom.GetIdx()])) for atom in a.GetAtoms())
         and all(_bond(bond) == _bond(b.GetBondBetweenAtoms(
             mapping[bond.GetBeginAtomIdx()], mapping[bond.GetEndAtomIdx()])) for bond in a.GetBonds()))

def _ordinary_unmarked_graph(mol, text):
 # Bound the shortcut to an unmarked, neutral, closed-shell organic graph.
 # The original input is checked because parsing can discard invalid markers.
 return (not any(mark in text for mark in ('@', '/', '\\'))
         and len(Chem.GetMolFrags(mol)) == 1
         and all(a.GetAtomicNum() in (1, 6, 7, 8, 9, 17, 35, 53)
                 and not a.GetFormalCharge() and not a.GetNumRadicalElectrons()
                 and a.GetChiralTag() == Chem.ChiralType.CHI_UNSPECIFIED for a in mol.GetAtoms())
         and all(b.GetStereo() == Chem.BondStereo.STEREONONE and b.GetBondDir() == Chem.BondDir.NONE
                 and b.GetBondType() in (Chem.BondType.SINGLE, Chem.BondType.DOUBLE,
                                        Chem.BondType.TRIPLE, Chem.BondType.AROMATIC)
                 for b in mol.GetBonds()))

def _parity(sequence):
 return sum(sequence[i]>sequence[j] for i in range(len(sequence)) for j in range(i+1,len(sequence)))%2

def _contradictions(a,b,mapping):
 differences=[];shared=0
 for atom in a.GetAtoms():
  other=b.GetAtomWithIdx(mapping[atom.GetIdx()])
  if atom.GetChiralTag() not in (CW,CCW) or other.GetChiralTag() not in (CW,CCW):continue
  # Both three-neighbour centres use implicit/explicit-count H as the final
  # virtual neighbour. Four-neighbour centres include all neighbours directly.
  left=[mapping[n.GetIdx()] for n in atom.GetNeighbors()]
  right=[n.GetIdx() for n in other.GetNeighbors()]
  permutation=[right.index(i) for i in left]
  shared+=1
  if ((atom.GetChiralTag()==CW)^bool(_parity(permutation))) != (other.GetChiralTag()==CW):differences.append({'type':'TETRAHEDRAL','left_atom':atom.GetIdx(),'right_atom':other.GetIdx()})
 for bond in a.GetBonds():
  other=b.GetBondBetweenAtoms(mapping[bond.GetBeginAtomIdx()],mapping[bond.GetEndAtomIdx()])
  def sign(x):
   if x.GetStereo() in (Chem.BondStereo.STEREOE,Chem.BondStereo.STEREOTRANS):return 0
   if x.GetStereo() in (Chem.BondStereo.STEREOZ,Chem.BondStereo.STEREOCIS):return 1
   return None
  x,y=sign(bond),sign(other)
  if x is None or y is None:continue
  left=[mapping[i] for i in bond.GetStereoAtoms()];right=list(other.GetStereoAtoms())
  if mapping[bond.GetBeginAtomIdx()]!=other.GetBeginAtomIdx():right.reverse()
  shared+=1
  if (x ^ (left[0]!=right[0]) ^ (left[1]!=right[1]))!=y:differences.append({'type':'DOUBLE_BOND','left_bond':bond.GetIdx(),'right_bond':other.GetIdx()})
 return differences,shared

def compare(left,right,*,mapping_limit=LIMIT):
 try:a,b=(hydrogen_comparison_graph(parse(text)) for text in (left,right))
 except Exception as e:return dict(result='UNKNOWN',reason='STEREO_INPUT_INVALID',error=str(e))
 stereo=[list(Chem.FindPotentialStereo(m)) for m in (a,b)]
 if not _supported(a,stereo[0]) or not _supported(b,stereo[1]):return dict(result='UNKNOWN',reason='UNSUPPORTED_STEREO_CLASS')
 aa,bb=Chem.Mol(a),Chem.Mol(b);Chem.RemoveStereochemistry(aa);Chem.RemoveStereochemistry(bb)
 if Chem.MolToSmiles(aa)!=Chem.MolToSmiles(bb):return dict(result='UNKNOWN',reason='STEREO_FRAMEWORK_DIFFERENT')
 scope='ORDINARY_TETRAHEDRAL_AND_DOUBLE_BOND_STEREO'
 if not any(stereo) and _ordinary_unmarked_graph(a,left) and _ordinary_unmarked_graph(b,right):
  mapping=bb.GetSubstructMatch(aa,useChirality=False)
  if mapping and _exact_mapping(a,b,mapping):
   return dict(result='NOT_APPLICABLE',reason='STEREO_NOT_APPLICABLE',valid_mapping_count=1,
               mappings=[dict(mapping=list(mapping),contradictions=[],shared_specified_elements=0)],
               potential_elements=[0,0],incomplete=False,scope=scope,mapping_enumeration='SINGLE_EXACT_WITNESS')
 mappings=bb.GetSubstructMatches(aa,uniquify=False,useChirality=False,maxMatches=mapping_limit+1)
 if len(mappings)>mapping_limit:return dict(result='UNKNOWN',reason='SYMMETRY_ENUMERATION_LIMIT',mapping_limit=mapping_limit)
 valid=[]
 for mapping in mappings:
  if not _exact_mapping(a,b,mapping):continue
  diffs,shared=_contradictions(a,b,mapping);valid.append(dict(mapping=list(mapping),contradictions=diffs,shared_specified_elements=shared))
 if not valid:return dict(result='UNKNOWN',reason='NO_VALIDATED_GRAPH_MAPPING')
 partial=any(str(s.specified)!='Specified' for elements in stereo for s in elements)
 if all(v['contradictions'] for v in valid):result,reason='DIFFERENT','ESTABLISHED_STEREO_DIFFERENCE'
 elif partial:result,reason='UNKNOWN','STEREO_SPECIFICITY_UNKNOWN'
 elif not any(stereo):result,reason='NOT_APPLICABLE','STEREO_NOT_APPLICABLE'
 else:result,reason='EQUIVALENT','ALL_RELEVANT_STEREO_SUPPORTED'
 return dict(result=result,reason=reason,valid_mapping_count=len(valid),mappings=valid,potential_elements=[len(s) for s in stereo],incomplete=partial,scope=scope)

def _values(assertion):
 if assertion.get('state')=='UNSPECIFIED':
  if assertion.get('scope')!='ALL_WITHIN_FRAMEWORK':return []
  return [assertion['framework']] if assertion.get('framework') else []
 return assertion.get('structures',[])

def compare_assertions(claim,candidate,dimension):
 if dimension!='stereochemistry':return previous.compare_assertions(claim,candidate,dimension)
 if not claim or not candidate or any(x.get('state')=='UNKNOWN' for x in (claim,candidate)):return 'UNKNOWN'
 av,bv=_values(claim),_values(candidate)
 if not av or not bv:return 'UNKNOWN'
 matrix=[[compare(a,b)['result'] for b in bv] for a in av]
 if any(x.get('state')=='NOT_APPLICABLE' for x in (claim,candidate)):
  # Preserve the existing achirality check: a malformed NOT_APPLICABLE claim
  # cannot borrow a specified graph's constraints to manufacture support.
  return 'NOT_APPLICABLE' if all(v=='NOT_APPLICABLE' for row in matrix for v in row) else 'UNKNOWN'
 if all(v=='DIFFERENT' for row in matrix for v in row):return 'EXACT_INCOMPATIBLE'
 # Even an explicitly broad assertion whose graph happens to be complete
 # cannot be upgraded by this adapter to exact source specificity.
 if any(x.get('state') in ('UNSPECIFIED','SET') for x in (claim,candidate)):return 'UNKNOWN'
 if all(v in ('EQUIVALENT','NOT_APPLICABLE') for row in matrix for v in row):
  return 'NOT_APPLICABLE' if all(v=='NOT_APPLICABLE' for row in matrix for v in row) else 'EXACT_COMPATIBLE'
 return 'UNKNOWN'

reconcile=previous._copy_function(previous.core.reconcile,compare_assertions=compare_assertions)
