"""Load actual source records through existing adapters; no name lookup mapping."""
import bootstrap
from correspondence_models import IncomingConcept,CanonicalCandidate
from pubchem_adapter import compound
from chebi_adapter import adapt as chebi
def load(case):
 r=case['source_record'];p=case['source_record_provenance']
 pkg=compound(r['record'],p) if r['source_name']=='PubChem' else chebi({'data':r['record']},p)
 if case['incoming_concept_mode']=='ASSOCIATED_NAME_REFERENT':
  ids=[c.evidence_id for c in pkg.claims if c.claim_id=='IUPACName'];kind='QUALIFIED_NAME_IDENTITY'
 else:ids=[c.evidence_id for c in pkg.claims if c.claim_role in ('STRUCTURAL_IDENTITY_ASSERTION','UNKNOWN_ROLE') and c.claim_id in ('SMILES','default_structure')];kind='EXPLICIT_STRUCTURAL_FIELD_REFERENT'
 incoming=IncomingConcept(case['case_id']+':'+r['source_name']+':'+r['record_id'],pkg,dict(status='ESTABLISHED' if ids else 'UNESTABLISHED',kind=kind,evidence_ids=ids,document=p['url']),case['source_identity_scope'],p)
 ref=case['reference_identity'];rp=case['reference_provenance'];name=(ref['record'].get('title') or ref['record'].get('ascii_name') or ref['record'].get('IUPACName') or ref['record_id'])
 raw=ref['record'];data=(raw.get('default_structure') or {}) if ref['source_name']=='ChEBI' else raw
 identifiers=[]
 for typ,keys in [('InChI',('InChI','inchi','standard_inchi')),('InChIKey',('InChIKey','inchikey','standard_inchi_key'))]:
  value=next((data[k] for k in keys if data.get(k)),None)
  if value:identifiers.append([typ,value])
 candidate=CanonicalCandidate('VALIDATION_REF:'+ref['source_name']+':'+ref['record_id'],name,ref['structure'],{**rp,'document':rp.get('payload_path',rp.get('path')),'independence_status':'UNESTABLISHED','definition_kind':'SEPARATELY_SUPPLIED_PUBLIC_REFERENCE','derived_from_source_concepts':[],'identifiers':identifiers},case['reference_identity_scope'])
 return incoming,candidate
