"""In-process capability for a fixed, hash-verified warehouse batch.

Not authentication against hostile Python code. Serialized claims or caller
booleans cannot mint this capability. Deep copies retain it; JSON does not.
"""
import hashlib,json
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
POLICY='TRUSTED_INTERNAL_STRUCTURE_ASSERTION';VERSION='1.0'
SYSTEM='PatSnapWarehouse';TABLE='pd_dw.dws_material_substance_entity_v2'
_SEAL=object()
class _Authority:
 def __init__(self,pkg):self.seal=_SEAL;self.fingerprint=digest(pkg.to_dict())
 def __deepcopy__(self,memo):return self
def _authorize(pkg):pkg._internal_authority=_Authority(pkg)
def authorized(pkg):
 a=getattr(pkg,'_internal_authority',None)
 return bool(isinstance(a,_Authority) and a.seal is _SEAL and (pkg.source_name,pkg.source_record_type)==(SYSTEM,TABLE) and a.fingerprint==digest(pkg.to_dict()))
