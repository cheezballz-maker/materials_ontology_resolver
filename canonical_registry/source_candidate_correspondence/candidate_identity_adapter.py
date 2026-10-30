"""Independently supplied candidate definitions and read-only registry lookup."""
import sqlite3
import bootstrap
from correspondence_models import CanonicalCandidate
from chemistry import describe,parse
from evidence_adapters import candidate_assertions
from molecular_capability import inspect
from identity_evidence_models import IdentityEvidence,DIMENSIONS
from evidence_adapters import source_structure
from isotope_comparator import reconcile
from assertion_dependencies import comparison_view

def qualify(candidate,source):
 p=candidate.provenance;obligations=[];assertions={};d=None
 try:
  d=describe(candidate.structure);assertions,_=comparison_view(candidate_assertions(candidate.structure));f,caps=inspect(d);obligations+=caps
  if f['stereo_state'] in ('PARTIAL','UNSPECIFIED') or f['advanced_stereo']:obligations.append('CANDIDATE_STEREOCHEMISTRY_UNRESOLVED')
  if f['component_count']>1 and candidate.identity_scope!='DEFINED_MULTICOMPONENT_COMPOSITION':obligations.append('CANDIDATE_COMPONENT_SCOPE_UNESTABLISHED')
 except Exception as exc:obligations.append('CANDIDATE_STRUCTURE_INVALID_OR_UNSUPPORTED:'+str(exc))
 if candidate.identity_scope not in ('DISCRETE_MOLECULAR','DEFINED_MULTICOMPONENT_COMPOSITION'):obligations.append('CANDIDATE_IDENTITY_SCOPE_UNESTABLISHED')
 roots=set(p.get('lineage_roots',[]));shared=roots&set(source['source_lineage_roots'])
 depends=bool(set(source['source_identity_references'])&set(p.get('derived_from_source_concepts',[]))) or p.get('definition_kind') in ('SOURCE_DERIVED','INCOMING_STRUCTURE_DERIVED')
 independent=p.get('independence_status') in ('ESTABLISHED_FOR_CONTROL_DEFINITION','ESTABLISHED_BY_AUDITED_PROVENANCE') and bool(p.get('document')) and bool(roots) and not shared and not depends
 if shared or depends:obligations.append('CANDIDATE_DERIVED_FROM_INCOMING_SOURCE')
 elif not independent:obligations.append('CANDIDATE_INDEPENDENCE_UNESTABLISHED')
 evidence_result=None
 if candidate.evidence and d:
  try:
   anchor=source_structure('CanonicalCandidate',candidate.candidate_substance_id,'canonical_graph',candidate.structure)
   claims=[x if isinstance(x,IdentityEvidence) else IdentityEvidence(**x) for x in candidate.evidence]
   evidence_result=reconcile([anchor]+claims,assertions,DIMENSIONS,anchor.referent_id)
   if evidence_result['result']!='RECONCILED_COMPATIBLE':obligations.append('CANDIDATE_EVIDENCE_NOT_RECONCILED')
  except Exception as exc:obligations.append('CANDIDATE_EVIDENCE_INVALID:'+str(exc))
 for kind,value in p.get('identifiers',[]):
  if d and kind in ('InChI','InChIKey') and d['inchi' if kind=='InChI' else 'inchikey']!=value:obligations.append('CANDIDATE_IDENTIFIER_STRUCTURE_INCONSISTENCY')
 conflicted=any(r.startswith(('CANDIDATE_EVIDENCE_','CANDIDATE_IDENTIFIER_STRUCTURE_INCONSISTENCY','CANDIDATE_STRUCTURE_INVALID')) for r in obligations)
 return dict(candidate_substance_id=candidate.candidate_substance_id,preferred_name=candidate.preferred_name,structure=candidate.structure,descriptor=d,assertions=assertions,provenance=p,identity_scope=candidate.identity_scope,independent=independent,shared_lineage_roots=sorted(shared),obligations=obligations,identity_evidence_conflicted=conflicted,evidence_reconciliation=evidence_result,additional_evidence=[x.to_dict() if isinstance(x,IdentityEvidence) else x for x in candidate.evidence])

def registry_lookup(path,inchikey):
 """A full Standard InChIKey is retrieval only; original graph comparison follows.

 Historical registry provenance is insufficient to certify external independence.
 Known PubChem record roots are retained to reject same-record self-confirmation.
 """
 db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
 try:
  ids=[r[0] for r in db.execute('SELECT DISTINCT substance_id FROM substance_identifier WHERE identifier_type=? AND identifier_value=?',('InChIKey',inchikey))]
  out=[]
  for sid in ids:
   name=db.execute('SELECT preferred_name FROM substance_identity WHERE substance_id=?',(sid,)).fetchone()[0]
   structures=db.execute('SELECT structure_value FROM substance_structure WHERE substance_id=? AND structure_type=?',(sid,'SMILES')).fetchall()
   identifiers=db.execute('SELECT identifier_type,identifier_value FROM substance_identifier WHERE substance_id=?',(sid,)).fetchall()
   roots=[f'PubChem:COMPOUND:{v}' for t,v in identifiers if t=='PubChemCID']
   if len(structures)==1:out.append(CanonicalCandidate(sid,name,structures[0][0],dict(definition_kind='EXISTING_CANONICAL_REGISTRY',document=str(path.resolve()),lineage_roots=roots or ['REGISTRY:'+sid],independence_status='UNESTABLISHED',derived_from_source_concepts=[],identifiers=identifiers),identity_scope='DISCRETE_MOLECULAR'))
  return out
 finally:db.close()
