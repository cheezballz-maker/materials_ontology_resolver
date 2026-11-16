"""Adapters return existing qualified evidence, never matching decisions."""
from dataclasses import dataclass
from typing import Protocol
import bootstrap
from evaluate_real_registry import make_input
from match_cli import decode
from source_concept_models import SourceConcept,SourceRevision

class InputValidationError(ValueError):pass
class UnsupportedSourceError(ValueError):pass
@dataclass
class AdaptedRecord:
 concept:SourceConcept
 revision:SourceRevision
 incoming:object
class SourceAdapter(Protocol):
 def adapt(self,record:dict)->AdaptedRecord:...

def envelope(record,incoming):
 p=incoming.concept.evidence_package;ref=record.get('referent_key','primary-record-referent')
 declared=incoming.concept.provenance.get('referent_key',ref)
 if declared!=ref:raise InputValidationError('INDIVIDUAL_REFERENT_BINDING_MISMATCH')
 incoming.concept.provenance={**incoming.concept.provenance,'referent_key':ref}
 concept=SourceConcept(p.source_name,p.source_record_type,p.source_record_id,ref,record.get('concept_type','CHEMICAL_REFERENT'));concept.validate()
 label=record.get('source_revision','local-v1')
 if not isinstance(label,str) or not label:raise InputValidationError('SOURCE_REVISION_REQUIRED')
 return AdaptedRecord(concept,SourceRevision(label,record.get('record',record.get('concept',record)),record.get('source_timestamp')),incoming)

class ProviderAdapter:
 def __init__(self,provider):self.provider=provider
 def adapt(self,record):
  try:
   raw=record['record'];context=record['provenance']
   sid=str(raw['CID'] if self.provider=='PubChem' else raw['chebi_accession'])
   inp=make_input(self.provider,raw,context,record.get('source_concept_id','UNIFIED:'+self.provider+':'+sid))
  except (KeyError,TypeError,ValueError) as e:raise InputValidationError(str(e)) from e
  if record.get('identity_scope'):inp.concept.identity_scope=record['identity_scope']
  for k in ('official_validation','external_evidence','source_profile','form_assertion'):
   if k in record:setattr(inp,k,record[k])
  return envelope(record,inp)

class QualifiedEvidenceAdapter:
 """Future-source boundary for already qualified, referent-scoped packages."""
 def adapt(self,record):
  try:return envelope(record,decode(record))
  except (KeyError,TypeError,ValueError) as e:raise InputValidationError(str(e)) from e

class AdapterRegistry:
 def __init__(self):self.adapters={'pubchem':ProviderAdapter('PubChem'),'chebi':ProviderAdapter('ChEBI'),'qualified':QualifiedEvidenceAdapter()}
 def register(self,name,adapter):
  if name.lower() in self.adapters:raise ValueError('ADAPTER_ALREADY_REGISTERED')
  self.adapters[name.lower()]=adapter
 def get(self,name):
  if not isinstance(name,str) or name.lower() not in self.adapters:raise UnsupportedSourceError('UNSUPPORTED_SOURCE_ADAPTER:'+str(name))
  return self.adapters[name.lower()]
