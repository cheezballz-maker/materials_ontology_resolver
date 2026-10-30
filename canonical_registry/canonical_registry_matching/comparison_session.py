"""Memoize unchanged deterministic comparators inside this matching session.

Only dependency bindings on copied functions change. Cached results are copied
on access. No chemistry rule, production function or module global is patched.
"""
import copy
from functools import lru_cache
from types import SimpleNamespace
import bootstrap
import assessment as hardened
import stereo_comparison as stereo
import isotope_comparator as isotope
import dimension_claim_comparator as dimension
import charge_comparison_attribution as charge
import chemistry
from evidence_adapters import candidate_assertions as original_assertions

@lru_cache(maxsize=4096)
def _descriptor(text):return chemistry.describe(text)
def descriptor(text):return copy.deepcopy(_descriptor(text))
@lru_cache(maxsize=65536)
def _structural_pair(left,right):return charge.compare(_descriptor(left),_descriptor(right))
def structural_pair(left,right):return copy.deepcopy(_structural_pair(left['smiles'],right['smiles']))
@lru_cache(maxsize=4096)
def _assertions(text):return original_assertions(text)
def assertions(text):return copy.deepcopy(_assertions(text))

clone=isotope._copy_function
_exact=clone(dimension._exact,describe=descriptor,structural_compare=structural_pair)
_isotope_exact=clone(isotope.exact_dimension,legacy=SimpleNamespace(_exact=_exact,structural_compare=structural_pair,_frame=dimension._frame),describe=descriptor)
_nonstereo=clone(isotope.compare_assertions,_exact=_isotope_exact)
_compare_assertions=clone(stereo.compare_assertions,previous=SimpleNamespace(compare_assertions=_nonstereo))
reconcile=clone(isotope.core.reconcile,compare_assertions=_compare_assertions)
qualify_source=clone(hardened.qualify_source,reconcile=reconcile,describe=descriptor,candidate_assertions=assertions)
qualify_candidate=clone(hardened.qualify_candidate,reconcile=reconcile,describe=descriptor,candidate_assertions=assertions)
compare=clone(hardened.compare,reconcile=reconcile)

def statistics():return dict(descriptors=_descriptor.cache_info()._asdict(),structural_pairs=_structural_pair.cache_info()._asdict(),assertions=_assertions.cache_info()._asdict())
