"""Memoize unchanged deterministic comparators inside this matching session.

Only dependency bindings on copied functions change. Cached results are copied
on access. No chemistry rule, production function or module global is patched.
"""
import copy
from contextlib import contextmanager
from contextvars import ContextVar
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
from molecular_capability import inspect as original_inspect
import json

@lru_cache(maxsize=4096)
def _descriptor(text):return chemistry.describe(text)
def descriptor(text):return copy.deepcopy(_descriptor(text))
@lru_cache(maxsize=65536)
def _structural_pair(left,right):return charge.compare(_descriptor(left),_descriptor(right))
def structural_pair(left,right):return copy.deepcopy(_structural_pair(left['smiles'],right['smiles']))
@lru_cache(maxsize=4096)
def _assertions(text):return original_assertions(text)
def assertions(text):return copy.deepcopy(_assertions(text))

@lru_cache(maxsize=4096)
def _capability(serialized_descriptor):return original_inspect(json.loads(serialized_descriptor))

def capability(descriptor):
 try:key=json.dumps(descriptor,sort_keys=True,ensure_ascii=False)
 except (TypeError,ValueError):return original_inspect(descriptor)
 return copy.deepcopy(_capability(key))

@lru_cache(maxsize=16384)
def _stereo_pair(left,right,mapping_limit):return stereo.compare(left,right,mapping_limit=mapping_limit)

def stereo_pair(left,right,*,mapping_limit=stereo.LIMIT):return copy.deepcopy(_stereo_pair(left,right,mapping_limit))

_original_dimension_frame=dimension._frame
@lru_cache(maxsize=8192)
def dimension_frame(text,dimension):return _original_dimension_frame(text,dimension)

@lru_cache(maxsize=8192)
def isotope_frame(text,dimension='isotope'):return isotope.framework(text,dimension)

@lru_cache(maxsize=8192)
def _isotope_inventory(text):return isotope.isotope_inventory(text)

def isotope_inventory(text):return copy.deepcopy(_isotope_inventory(text))

clone=isotope._copy_function
_exact=clone(dimension._exact,describe=descriptor,structural_compare=structural_pair,_frame=dimension_frame)
_isotope_exact=clone(isotope.exact_dimension,legacy=SimpleNamespace(_exact=_exact,structural_compare=structural_pair,_frame=dimension_frame),describe=descriptor,framework=isotope_frame,isotope_inventory=isotope_inventory)
_nonstereo=clone(isotope.compare_assertions,_exact=_isotope_exact,_frame=isotope_frame)
_compare_assertions=clone(stereo.compare_assertions,previous=SimpleNamespace(compare_assertions=_nonstereo),compare=stereo_pair)
_validated_claims=ContextVar("validated_match_claims",default=None)

@contextmanager
def validate_source_claims_once(claims):
 # Qualified source claims are private copies that comparison only reads.
 for claim in claims:claim.validate()
 token=_validated_claims.set({id(claim):claim for claim in claims})
 try:yield
 finally:_validated_claims.reset(token)

def _validate_claim(claim):
 validated=_validated_claims.get()
 if validated is None or validated.get(id(claim)) is not claim:claim.validate()

reconcile=clone(isotope.core.reconcile,compare_assertions=_compare_assertions,_validate_claim=_validate_claim)
_qualify_source_uncached=clone(hardened.qualify_source,reconcile=reconcile,describe=descriptor,candidate_assertions=assertions)
qualify_candidate=clone(hardened.qualify_candidate,reconcile=reconcile,describe=descriptor,candidate_assertions=assertions,inspect=capability)
compare=clone(hardened.compare,reconcile=reconcile)

def statistics():return dict(descriptors=_descriptor.cache_info()._asdict(),structural_pairs=_structural_pair.cache_info()._asdict(),assertions=_assertions.cache_info()._asdict(),capability=_capability.cache_info()._asdict(),stereo_pairs=_stereo_pair.cache_info()._asdict(),dimension_frames=dimension_frame.cache_info()._asdict(),isotope_frames=isotope_frame.cache_info()._asdict(),isotope_inventories=_isotope_inventory.cache_info()._asdict())

# Source chemical qualification is deterministic for the entire input object.
# Authorization and admission are deliberately NOT cached here.
import json,hashlib
from dataclasses import asdict
_SOURCE_QUALIFICATIONS={}
def qualify_source(incoming):
 try:key=hashlib.sha256(json.dumps(asdict(incoming),sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 except (TypeError,ValueError):return _qualify_source_uncached(incoming)
 if key not in _SOURCE_QUALIFICATIONS:
  _SOURCE_QUALIFICATIONS[key]=copy.deepcopy(_qualify_source_uncached(incoming))
  if len(_SOURCE_QUALIFICATIONS)>32:_SOURCE_QUALIFICATIONS.pop(next(iter(_SOURCE_QUALIFICATIONS)))
 return copy.deepcopy(_SOURCE_QUALIFICATIONS[key])
