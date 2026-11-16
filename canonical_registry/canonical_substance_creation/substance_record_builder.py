"""Preserve the graph; display names and source IDs never establish identity."""
import bootstrap
from chemistry import describe

def build(incoming,eligibility):
 name=incoming.name
 # This is the source's display label from the qualified record. It is not
 # promoted as an exact alias or treated as chemical evidence by this builder.
 if not isinstance(name,str) or not name.strip() or any(ord(c)<32 for c in name):raise ValueError('QUALIFIED_DISPLAY_NAME_REQUIRED')
 d=eligibility['descriptor'];pkg=incoming.concept.evidence_package
 return dict(preferred_name=name.strip(),identity_status='ACCEPTED',structures=[['SMILES',d['smiles']]],identifiers=[['InChI',d['inchi']],['InChIKey',d['inchikey']]],aliases=[],name_provenance={'source_system':pkg.source_name,'source_record_id':pkg.source_record_id,'basis':'SOURCE_RECORD_DISPLAY_LABEL_ONLY','original_value':name},identifier_policy='Only locally generated, officially confirmed structural identifiers. Source IDs remain SourceConcept identifiers; exact-form scope is not independently established for database IDs.',original_structure=eligibility['graph'],descriptor=d)

def insert(db,sid,record):
 db.execute('INSERT INTO substance_identity VALUES(?,?,?)',(sid,record['preferred_name'],record['identity_status']))

def insert_representations(db,sid,record):
 for t,v in record['structures']:db.execute('INSERT INTO substance_structure VALUES(?,?,?)',(sid,t,v))
 for t,v in record['identifiers']:db.execute('INSERT INTO substance_identifier VALUES(?,?,?)',(sid,t,v))
 for a in record['aliases']:db.execute('INSERT INTO substance_alias VALUES(?,?)',(sid,a))
