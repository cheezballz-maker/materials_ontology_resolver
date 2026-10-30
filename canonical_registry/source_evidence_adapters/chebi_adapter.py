"""Second-source field mapping using the same evidence and comparison contract."""
import re
import bootstrap
from evidence_adapter_contract import EvidencePackage,structural_field,record_identifier,associated_name,identifier_field
from semantic_bridges import interpret

def adapt(raw,context):
 r=raw['data'];accession=r['chebi_accession']
 pkg=EvidencePackage('ChEBI','CHEMICAL_ENTITY',accession,context)
 qualified=bool(re.fullmatch(r'https://www\.ebi\.ac\.uk/chebi/backend/api/public/compound/CHEBI:\d+/',context.get('url',''))) and bool(context.get('payload_sha256')) and bool(context.get('payload_path'))
 pkg.source_attributes={k:r.get(k) for k in ('stars','is_released','modified_on','created_by')};pkg.source_attributes.update(identity_scope='ChEBI represented entity graph; entity granularity may differ from canonical Substance',official_documentation='https://www.ebi.ac.uk/chebi/downloads')
 record_identifier(pkg,'accession',accession,'$.data.chebi_accession','ChEBIID')
 s=r.get('default_structure') or {};graph=None
 if s.get('smiles'):
  graph=structural_field(pkg,'default_structure',s['smiles'],'$.data.default_structure.smiles',qualified=qualified and not s.get('is_r_group'),representation='CHEBI_DEFAULT_STRUCTURE_VIEW')
 for field,kind in [('standard_inchi','InChI'),('standard_inchi_key','InChIKey')]:
  if s.get(field):identifier_field(pkg,field,s[field],'$.data.default_structure.'+field,kind,graph=graph.original_value if graph else None,dependency=graph)
 if r.get('name'):
  # Interpret only contracts already implemented. A curated preferred name is
  # still not automatically a demonstrated exact molecular alias.
  interpret(pkg,'preferred_name',r['name'],'$.data.name',candidate=graph.original_value if graph and graph.dimension_assertions else None)
 for kind,rows in (r.get('names') or {}).items():
  for j,name in enumerate(rows):
   associated_name(pkg,f'name:{kind}:{j}',name.get('name'),f'$.data.names.{kind}[{j}].name',extra={'contributor':name.get('source','UNAVAILABLE'),'curation_status':name.get('status','UNAVAILABLE'),'name_type':kind,'language':name.get('language_code')})
 for kind,rows in (r.get('database_accessions') or {}).items():
  for j,item in enumerate(rows):
   c=record_identifier(pkg,f'xref:{kind}:{j}',item.get('accession_number'),f'$.data.database_accessions.{kind}[{j}]',kind)
   c.source_provenance.update(contributor=item.get('source_name'),mapping_route='SOURCE_REPORTED_CROSS_REFERENCE_ONLY',correspondence_scope='EXACT_FORM_NOT_VALIDATED');c.unresolved_dependencies=['EXTERNAL_IDENTIFIER_FORM_CORRESPONDENCE_UNVALIDATED']
 return pkg
