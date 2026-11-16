"""Isolated correction: isotope signatures first, H-normalized framework second.

Original source graphs are never changed. Only the temporary isotope-free
framework view removes ordinary explicit H. The legacy function objects/modules
are untouched; copies reuse their unchanged set/specificity/reconciliation logic.
"""
from collections import Counter
from types import FunctionType
import bootstrap
from rdkit import Chem
from chemistry import parse,describe,hydrogen_comparison_graph
import dimension_claim_comparator as legacy
import source_claim_reconciler as core

def isotope_inventory(text):
 return Counter((a.GetAtomicNum(),a.GetIsotope()) for a in parse(text).GetAtoms() if a.GetIsotope())

def framework(text,dimension='isotope'):
 if dimension!='isotope':return legacy._frame(text,dimension)
 m=Chem.Mol(hydrogen_comparison_graph(parse(text)))
 for atom in m.GetAtoms():atom.SetIsotope(0)
 # Previously labelled H nodes are now ordinary H and can be represented by
 # H counts. Never perform this on the original isotope-bearing graph.
 m=Chem.RemoveHs(m)
 return Chem.MolToSmiles(m,canonical=True,isomericSmiles=True)

def exact_dimension(left,right,dimension):
 if dimension!='isotope':return legacy._exact(left,right,dimension)
 li,ri=isotope_inventory(left),isotope_inventory(right)
 if framework(left)!=framework(right):
  # Explicitly different nuclide inventories establish a represented isotope
  # distinction even with an independently different constitution. Positional
  # correspondence on unlike frameworks is otherwise unknown.
  return 'DIFFERENT' if li!=ri else 'UNKNOWN'
 result=legacy.structural_compare(describe(left),describe(right))['dimensions']['isotope_specification']
 return 'EQUIVALENT' if result=='NOT_APPLICABLE' else result

def _copy_function(fn,**overrides):
 return FunctionType(fn.__code__,{**fn.__globals__,**overrides},fn.__name__,fn.__defaults__,fn.__closure__)

compare_assertions=_copy_function(legacy.compare_assertions,_frame=framework,_exact=exact_dimension)
reconcile=_copy_function(core.reconcile,compare_assertions=compare_assertions)

def diagnostic(left,right):
 return dict(left=left,right=right,left_isotopes=[list(k)+[v] for k,v in sorted(isotope_inventory(left).items())],right_isotopes=[list(k)+[v] for k,v in sorted(isotope_inventory(right).items())],legacy_left_framework=legacy._frame(left,'isotope'),legacy_right_framework=legacy._frame(right,'isotope'),corrected_left_framework=framework(left),corrected_right_framework=framework(right),represented_isotope_result=exact_dimension(left,right,'isotope'),source_specificity='MUST_BE_ESTABLISHED_SEPARATELY')
