"""PubChem v1: offline documented field extraction, no identity acceptance."""
from urllib.parse import urlparse,unquote
import re
import bootstrap
from evidence_adapter_contract import EvidencePackage,structural_field,record_identifier,associated_name,identifier_field,evidence
from semantic_bridges import interpret

DOC='https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest'
def compound_context(url):
 u=urlparse(url);p=unquote(u.path)
 return u.scheme=='https' and u.hostname=='pubchem.ncbi.nlm.nih.gov' and bool(re.fullmatch(r'/rest/pug/compound/(cid|name|inchikey|inchi)/.+/property/[^/]+/JSON',p))

def compound(row,context):
 cid=row.get('CID')
 if not isinstance(cid,int) or isinstance(cid,bool) or cid<=0:raise ValueError('INVALID_OR_MISSING_CID')
 pkg=EvidencePackage('PubChem','COMPOUND',str(cid),context)
 qualified=compound_context(context.get('url','')) and bool(context.get('payload_sha256')) and bool(context.get('payload_path'))
 pkg.source_attributes=dict(depositor_metadata='UNAVAILABLE_IN_PROPERTY_PAYLOAD',SID='UNAVAILABLE',synonyms='UNAVAILABLE_IN_PROPERTY_PAYLOAD',standardization='PUBCHEM_STANDARDIZED_COMPOUND',original_SID_form_equivalence='UNESTABLISHED',official_documentation=DOC)
 record_identifier(pkg,'CID',cid,'$.rows[].CID','PubChemCID')
 graphs=[]
 for field in ('SMILES','IsomericSMILES','ConnectivitySMILES','CanonicalSMILES'):
  if field in row:
   graph=structural_field(pkg,field,row[field],'$.rows[].'+field,qualified=qualified,representation='PUBCHEM_STANDARDIZED_COMPOUND_DESCRIPTOR',limited=field in ('ConnectivitySMILES','CanonicalSMILES'))
   graphs.append(graph)
 main=next((c for c in graphs if c.dimension_assertions),None)
 # Multiple computed structure serializations are dependent views of the same
 # standardized Compound, not multiple independent source claims.
 if main:
  for c in graphs:
   if c is not main:c.derivation_dependencies=[main.evidence_id]
 for field in ('InChI','InChIKey'):
  if field in row:identifier_field(pkg,field,row[field],'$.rows[].'+field,field,graph=main.original_value if main else None,dependency=main)
 if row.get('IUPACName'):
  name=row['IUPACName'];deps=[main.evidence_id] if main else []
  before=len(pkg.claims);c=interpret(pkg,'IUPACName',name,'$.rows[].IUPACName',candidate=main.original_value if main else None,dependencies=deps)
  c.source_provenance.update(generated=True,field_definition='Computed systematic name for standardized Compound',derivation_mechanism='PubChem computed descriptor; per-record generator/version unavailable in property payload',official_documentation=DOC)
  if c.dimension_assertions:
   c.source_provenance['binding_policy']='QUALIFIED_PARTIAL_ASSERTION'
  else:
   c.claim_role='CHEMICAL_NAME_ASSERTION';c.source_provenance['origin']='DERIVED_SOURCE'
  if not qualified:
   for q in pkg.claims[before:]:q.source_provenance.update(interpretation_basis='UNVERIFIED',role_established=False);q.dimension_assertions={};q.unresolved_dependencies.append('FIELD_PROVENANCE_UNESTABLISHED')
 # A property endpoint does not document arbitrary extra keys as a synonym
 # response. Preserve them as unknown rather than inventing depositor origin.
 for field in ('Synonym','Synonyms','synonyms','CAS','SID'):
  if field in row:
   values=row[field] if isinstance(row[field],list) else [row[field]]
   for n,value in enumerate(values):associated_name(pkg,f'{field}:{n}',value,'$.rows[].'+field,role_known=False,extra={'depositor':'UNAVAILABLE','reason':'FIELD_NOT_DEFINED_BY_PROPERTY_ENDPOINT'})
 return pkg

def synonym_response(payload,context):
 """Actual /compound/.../synonyms response, without fictitious SID provenance."""
 if not re.fullmatch(r'https://pubchem\.ncbi\.nlm\.nih\.gov/rest/pug/compound/.+/synonyms/JSON',context.get('url','')):raise ValueError('SYNONYM_ENDPOINT_UNESTABLISHED')
 out=[]
 for row in payload.get('InformationList',{}).get('Information',[]):
  pkg=EvidencePackage('PubChem','COMPOUND',str(row['CID']),context);record_identifier(pkg,'CID',row['CID'],'$.InformationList.Information[].CID','PubChemCID')
  for j,value in enumerate(row.get('Synonym',[])):
   associated_name(pkg,f'synonym:{j}',value,'$.InformationList.Information[].Synonym[]',extra={'association_origin':'Filtered depositor synonym association; filtering is not correctness validation','depositor':'UNAVAILABLE_IN_THIS_RESPONSE','CAS_like':bool(re.fullmatch(r'\d{2,7}-\d{2}-\d',value))})
  out.append(pkg)
 return out

def substance(payload,context):
 """Bounded SID metadata adapter. Does not guess a deposited graph from a CID.

 PC_Substances graph reconstruction is intentionally unsupported until original
 atom/bond/stereo provenance is tested on actual local raw SID payloads.
 """
 if not re.fullmatch(r'https://pubchem\.ncbi\.nlm\.nih\.gov/rest/pug/substance/sid/\d+/JSON',context.get('url','')):raise ValueError('SID_ENDPOINT_UNESTABLISHED')
 out=[]
 for index,row in enumerate(payload.get('PC_Substances',[])):
  sid=row.get('sid',{}).get('id')
  if not isinstance(sid,int) or sid<=0:raise ValueError('INVALID_OR_MISSING_SID')
  pkg=EvidencePackage('PubChem','SUBSTANCE',str(sid),context);source=row.get('source',{}).get('db',{})
  pkg.source_attributes=dict(depositor=source.get('name','UNAVAILABLE'),depositor_record_id=source.get('source_id','UNAVAILABLE'),deposited_graph='UNAVAILABLE_OR_UNSUPPORTED_RAW_GRAPH_MAPPING',original_structure_not_reconstructed=True)
  record_identifier(pkg,'SID',sid,f'$.PC_Substances[{index}].sid.id','PubChemSID')
  for j,name in enumerate(row.get('synonyms',[])):associated_name(pkg,f'synonym:{j}',name,f'$.PC_Substances[{index}].synonyms[{j}]',extra={'depositor':source or 'UNAVAILABLE','association_origin':'Depositor supplied; unfiltered, not exact verified'})
  for j,c in enumerate(row.get('compound',[])):
   cid=c.get('id',{}).get('id',{}).get('cid')
   if cid:record_identifier(pkg,f'linkedCID:{j}',cid,f'$.PC_Substances[{index}].compound[{j}].id.id.cid','PubChemCID')
  pkg.add(evidence(pkg,'deposited_structure','UNKNOWN_ROLE',row.get('compound'),f'$.PC_Substances[{index}].compound',unresolved=['ORIGINAL_DEPOSITED_GRAPH_MAPPING_NOT_VALIDATED']),['RECORD_STRUCTURE','INCOMING_CONCEPT'])
  out.append(pkg)
 return out
