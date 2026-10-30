from dataclasses import dataclass,asdict
import hashlib,json
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
@dataclass(frozen=True)
class SourceConcept:
 source_system:str
 source_record_type:str
 source_record_id:str
 referent_key:str
 concept_type:str='CHEMICAL_REFERENT'
 def validate(self):
  if any(not isinstance(x,str) or not x.strip() for x in asdict(self).values()):raise ValueError('EMPTY_SOURCE_KEY')
 @property
 def concept_id(self):return 'SC_'+digest([self.source_system,self.source_record_type,self.source_record_id,self.referent_key])
@dataclass(frozen=True)
class SourceRevision:
 source_revision:str
 payload:dict
 source_timestamp:str|None=None
