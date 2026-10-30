"""Load all identity records through SQLite mode=ro; retain deficient records."""
from collections import defaultdict
import hashlib,sqlite3
from pathlib import Path
import bootstrap
from chemistry import describe
from correspondence_models import CanonicalCandidate

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class RegistrySnapshot:
 def __init__(self,path):
  self.path=Path(path).resolve();self.sha256=digest(self.path)
  db=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)
  try:
   db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
   self.schema=[dict(type=t,name=n,sql=s) for t,n,s in db.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name')]
   identities=db.execute('SELECT substance_id,preferred_name,identity_status FROM substance_identity ORDER BY substance_id').fetchall()
   aliases=defaultdict(list);identifiers=defaultdict(list);structures=defaultdict(list);indices=defaultdict(list)
   for sid,a in db.execute('SELECT substance_id,alias FROM substance_alias'):aliases[sid].append(a)
   for sid,t,v in db.execute('SELECT substance_id,identifier_type,identifier_value FROM substance_identifier'):identifiers[sid].append([t,v])
   for sid,t,v in db.execute('SELECT substance_id,structure_type,structure_value FROM substance_structure'):structures[sid].append([t,v])
   for sid,i in db.execute("SELECT substance_id,cuma_index FROM substance_reconciliation WHERE resolution_status='EXACT'"):indices[sid].append(i)
   self.table_counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('substance_identity','substance_alias','substance_identifier','substance_structure','substance_reconciliation')}
   self.sqlite_integrity=db.execute('PRAGMA integrity_check').fetchall();self.foreign_key_errors=db.execute('PRAGMA foreign_key_check').fetchall()
  finally:db.close()
  self.assert_unchanged();self.entries={}
  for sid,name,status in identities:
   graphs=[v for t,v in structures[sid] if t=='SMILES'];graph=graphs[0] if len(graphs)==1 else None;d=None;issues=[]
   if len(graphs)!=1:issues.append('REGISTRY_REQUIRES_SINGLE_EXPLICIT_GRAPH')
   if status!='ACCEPTED':issues.append('REGISTRY_IDENTITY_NOT_ACCEPTED')
   if graph:
    try:d=describe(graph)
    except Exception as e:issues.append('REGISTRY_GRAPH_INVALID:'+str(e))
   provenance=dict(definition_kind='EXISTING_CANONICAL_REGISTRY',document=str(self.path),registry_snapshot_sha256=self.sha256,lineage_roots=[f'PubChem:COMPOUND:{v}' for t,v in identifiers[sid] if t=='PubChemCID'] or ['REGISTRY:'+sid],independence_status='UNESTABLISHED',identifiers=identifiers[sid],registry_issues=issues,identity_scope_basis='ACCEPTED_EXPLICIT_GRAPH_AND_FIXED_COMPONENT_COUNTS_ONLY_NOT_SOLID_PHASE',cuma_indices=sorted(indices[sid]))
   candidate=CanonicalCandidate(sid,name,graph,provenance,'DEFINED_MULTICOMPONENT_COMPOSITION' if d and d['components']>1 else 'DISCRETE_MOLECULAR')
   self.entries[sid]=dict(candidate=candidate,descriptor=d,aliases=sorted(aliases[sid]),identifiers=identifiers[sid],structures=structures[sid],issues=issues,status=status)
 def assert_unchanged(self):
  if digest(self.path)!=self.sha256:raise RuntimeError('REGISTRY_SNAPSHOT_CHANGED_DURING_READ_ONLY_MATCHING')
 def inventory(self):
  return dict(path=str(self.path),sha256=self.sha256,connection='mode=ro; query_only=ON; read transaction',tables=self.table_counts,schema=self.schema,sqlite_integrity=self.sqlite_integrity,foreign_key_errors=self.foreign_key_errors,entries=[dict(substance_id=sid,preferred_name=r['candidate'].preferred_name,identity_status=r['status'],aliases=r['aliases'],identifiers=r['identifiers'],structures=r['structures'],descriptor=r['descriptor'],issues=r['issues'],provenance=r['candidate'].provenance) for sid,r in self.entries.items()],stored_identity_dimensions=False,stored_structure_level_provenance=False,component_relationship_table=False)
