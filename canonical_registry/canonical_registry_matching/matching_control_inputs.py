"""Matching-specific declared inputs and fixtures; no legacy module shadowing."""
import hashlib,json,sqlite3
from pathlib import Path
import bootstrap
from evidence_adapter_contract import EvidencePackage,structural_field,associated_name,evidence
from evidence_adapters import candidate_assertions
from correspondence_models import IncomingConcept
from registry_matching_models import MatchingInput
from chemistry import describe
from test_provider_qualification import row
H=Path(__file__).resolve().parent;B=H.parent

def fixture_registry(c):
 path=(H/'fixtures'/f"{c['id']}.sqlite").resolve()
 if path.parent!=(H/'fixtures').resolve():raise ValueError('INVALID_FIXTURE_PATH')
 if path.exists():path.unlink()
 db=sqlite3.connect(path)
 try:
  db.executescript((B/'schema.sql').read_text())
  for entry in c['entries']:
   sid=entry['id'];db.execute('INSERT INTO substance_identity VALUES(?,?,?)',(sid,entry.get('name',sid),'ACCEPTED'))
   for alias in entry.get('aliases',[]):db.execute('INSERT INTO substance_alias VALUES(?,?)',(sid,alias))
   if entry['graph'] is not None:
    db.execute('INSERT INTO substance_structure VALUES(?,?,?)',(sid,'SMILES',entry['graph']))
    try:
     d=describe(entry.get('bad_identifier_graph',entry['graph']))
     for kind,key in [('InChI','inchi'),('InChIKey','inchikey')]:db.execute('INSERT INTO substance_identifier VALUES(?,?,?)',(sid,kind,d[key]))
    except ValueError:pass
  db.commit()
 finally:db.close()
 return path

def matching_input(c):
 kind=c.get('category_override',c['source_category']);name=c.get('source_name','Explicit source molecular graph');graph=c['source_graph']
 file=H/'controls'/('development_controls.json' if c['id'].startswith('D') else 'heldout_controls.json')
 pkg=EvidencePackage('MatchingControl','ANNOTATED_SOURCE',c['id'],dict(path=str(file.resolve()),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),record_path="$.cases[id="+c['id']+"]",origin='SYNTHETIC_CONTROL_NOT_CUMA'))
 if kind=='EXPLICIT':
  anchor=structural_field(pkg,'source_graph',graph,'$.source_graph');binding='EXPLICIT_STRUCTURAL_FIELD_REFERENT'
  if c.get('conflicting_graph'):structural_field(pkg,'independent_conflicting_field',c['conflicting_graph'],'$.conflicting_graph')
 elif kind=='QUALIFIED_NAME':
  anchor=evidence(pkg,'qualified_name','CHEMICAL_NAME_ASSERTION',name,'$.source_name',binding='BINDING_IDENTITY_ASSERTION',basis='RULE_ESTABLISHED',origin='DERIVED_SOURCE',assertions=candidate_assertions(graph),extra={'interpretation_document':str(file.resolve()),'interpretation_kind':'ANNOTATED_QUALIFIED_NAME_SEMANTICS_CONTROL_NOT_RAW_OPSIN_SUCCESS'})
  pkg.add(anchor,['RECORD_STRUCTURE','TERMINOLOGY','INCOMING_CONCEPT']);binding='QUALIFIED_NAME_IDENTITY'
 else:
  anchor=associated_name(pkg,'unverified_name',name,'$.source_name');binding='QUALIFIED_NAME_IDENTITY'
 concept=IncomingConcept('CONTROL:'+c['id'],pkg,dict(status='UNESTABLISHED' if kind in ('BROAD','UNQUALIFIED_NAME') or c.get('unbound') else 'ESTABLISHED',kind=binding,evidence_ids=[anchor.evidence_id],document=str(file.resolve())), 'DEFINED_MULTICOMPONENT_COMPOSITION' if graph and '.' in graph else 'DISCRETE_MOLECULAR',dict(lineage_roots=['MatchingControl:'+c['id']],source_category=kind))
 external={'status':'NOT_QUERIED','rows':[]};tag=c.get('external_fixture')
 if tag:
  r=row('CC[C@H](C)O' if tag=='CONTRADICTORY' else graph,name=name,provider='UNSUPPORTED_CONTROL_PROVIDER' if tag=='UNSUPPORTED' else 'PubChem')
  if tag=='KNOWN_DEPENDENT':r['provenance']['source_dependence_classification']='SOURCE_DEPENDENCE_KNOWN'
  if tag=='QUALIFIED':r['provenance']['source_dependence_classification']='SOURCE_INDEPENDENT'
  r['fixture_origin']='SYNTHETIC_POLICY_INPUT_NOT_A_REAL_PROVIDER_RECORD';external={'status':'SUCCESS','rows':[r],'fixture_origin':'SYNTHETIC_POLICY_EVIDENCE'}
 return MatchingInput(concept,name,retrieval_hypothesis=graph if kind=='UNQUALIFIED_NAME' else None,official_validation={'status':'NOT_SUPPLIED','agrees':False} if c.get('missing_official') else None,external_evidence=external,evidence_origin='SYNTHETIC_POLICY_FIXTURE' if tag else 'INDEPENDENTLY_SPECIFIED_MATCHING_CONTROL')
