"""Load all identity records through SQLite mode=ro; retain deficient records."""
from collections import defaultdict
import hashlib,sqlite3
from pathlib import Path
from time import perf_counter
import bootstrap
from comparison_session import descriptor as describe
from correspondence_models import CanonicalCandidate

def digest(path):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

class RegistrySnapshot:
 def __init__(self,path,*,use_derived_cache=True):
  self.path=Path(path).resolve();self.sha256=digest(self.path);self._transaction_db=None
  self.use_derived_cache=use_derived_cache
  db=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)
  try:
   db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
   rows=self._read_rows(db)
  finally:db.close()
  self.assert_unchanged();self._build_entries(*rows)
 @classmethod
 def from_connection(cls,db):
  """Borrow a caller-owned locked transaction; no second connection or commit.

  The logical digest covers the five canonical tables, including uncommitted
  inserts visible on this connection. Only persistence services use this path.
  """
  return cls._from_connection(db,owned_write_transaction=False)
 @classmethod
 def for_locked_writer(cls,db,*,after_canonical_insert=None):
  """Use only while the owning service holds its private BEGIN IMMEDIATE.

  The owner keeps this snapshot local and never uses it after commit or
  rollback. Other callers use from_connection and always reread the digest.
  """
  return cls._from_connection(db,owned_write_transaction=True,after_canonical_insert=after_canonical_insert)
 @classmethod
 def _from_connection(cls,db,owned_write_transaction,after_canonical_insert=None):
  if not db.in_transaction:raise ValueError('TRANSACTION_BOUND_SNAPSHOT_REQUIRED')
  obj=cls.__new__(cls);obj.path=Path(db.execute('PRAGMA database_list').fetchone()[2]).resolve();obj._transaction_db=db
  obj._owned_write_transaction=owned_write_transaction
  obj._loaded_at_changes=db.total_changes
  obj._schema_tokens=(db.execute('PRAGMA main.schema_version').fetchone()[0],
                      db.execute('PRAGMA temp.schema_version').fetchone()[0])
  obj._data_version=db.execute('PRAGMA main.data_version').fetchone()[0]
  if after_canonical_insert is not None and (
   not owned_write_transaction or after_canonical_insert._transaction_db is not db
   or not after_canonical_insert._owned_write_transaction
   or after_canonical_insert._data_version!=obj._data_version
   or after_canonical_insert._schema_tokens!=obj._schema_tokens
   or after_canonical_insert.sqlite_integrity!=[('ok',)] or after_canonical_insert.foreign_key_errors
  ):raise ValueError('VERIFIED_LOCKED_REGISTRY_SNAPSHOT_REQUIRED')
  obj.sha256=obj._logical_digest();obj._build_entries(*obj._read_rows(db,after_canonical_insert));obj.assert_unchanged()
  return obj
 def can_reuse_locked(self,db,digest):
  return self._same_transaction_state(db) and self.sha256==digest
 def same_locked_state(self,db):
  return self._owned_write_transaction and self._same_transaction_state(db)
 def _same_transaction_state(self,db):
  return (db.in_transaction and self._transaction_db is db
          and self._loaded_at_changes==db.total_changes and
          self._schema_tokens==(db.execute('PRAGMA main.schema_version').fetchone()[0],
                                db.execute('PRAGMA temp.schema_version').fetchone()[0]) and
          self._data_version==db.execute('PRAGMA main.data_version').fetchone()[0])
 def _logical_digest(self):
  tables=('substance_identity','substance_alias','substance_identifier','substance_structure','substance_reconciliation')
  return hashlib.sha256(repr([(t,self._transaction_db.execute('SELECT * FROM '+t+' ORDER BY 1,2').fetchall()) for t in tables]).encode()).hexdigest()
 def _read_rows(self,db,after_canonical_insert=None):
  started=perf_counter();self.timings={}
  self.schema=[dict(type=t,name=n,sql=s) for t,n,s in db.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name')]
  identities=db.execute('SELECT substance_id,preferred_name,identity_status FROM substance_identity ORDER BY substance_id').fetchall()
  aliases=defaultdict(list);identifiers=defaultdict(list);structures=defaultdict(list);indices=defaultdict(list)
  for sid,a in db.execute('SELECT substance_id,alias FROM substance_alias'):aliases[sid].append(a)
  for sid,t,v in db.execute('SELECT substance_id,identifier_type,identifier_value FROM substance_identifier'):identifiers[sid].append([t,v])
  for sid,t,v in db.execute('SELECT substance_id,structure_type,structure_value FROM substance_structure'):structures[sid].append([t,v])
  for sid,i in db.execute("SELECT substance_id,cuma_index FROM substance_reconciliation WHERE resolution_status='EXACT'"):indices[sid].append(i)
  self.table_counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('substance_identity','substance_alias','substance_identifier','substance_structure','substance_reconciliation')}
  self.timings['database_read']=perf_counter()-started;started=perf_counter()
  if after_canonical_insert is None:
   self.sqlite_integrity=db.execute('PRAGMA integrity_check').fetchall()
  else:
   # The creation service has checked the complete database under this lock.
   # Recheck the canonical tables touched by the insert, retaining FK checks.
   touched=('substance_identity','substance_structure','substance_identifier','substance_alias')
   issues=[row for t in touched for row in db.execute(f"PRAGMA integrity_check('{t}')") if row!=('ok',)]
   self.sqlite_integrity=issues or [('ok',)]
  self.foreign_key_errors=db.execute('PRAGMA foreign_key_check').fetchall()
  self.timings['sqlite_integrity']=perf_counter()-started
  return identities,aliases,identifiers,structures,indices
 def _build_entries(self,identities,aliases,identifiers,structures,indices):
  started=perf_counter();self.entries={}
  from derived_index import DerivedIndex
  try:cache=DerivedIndex() if getattr(self,'use_derived_cache',True) else None
  except Exception:cache=None
  for sid,name,status in identities:
   graphs=[v for t,v in structures[sid] if t=='SMILES'];graph=graphs[0] if len(graphs)==1 else None;d=None;issues=[]
   if len(graphs)!=1:issues.append('REGISTRY_REQUIRES_SINGLE_EXPLICIT_GRAPH')
   if status!='ACCEPTED':issues.append('REGISTRY_IDENTITY_NOT_ACCEPTED')
   if graph:
    try:
     derive=lambda:describe(graph)
     d=cache.get('descriptor',graph,derive) if cache else derive()
    except Exception as e:issues.append('REGISTRY_GRAPH_INVALID:'+str(e))
   provenance=dict(definition_kind='EXISTING_CANONICAL_REGISTRY',document=str(self.path),registry_snapshot_sha256=self.sha256,lineage_roots=[f'PubChem:COMPOUND:{v}' for t,v in identifiers[sid] if t=='PubChemCID'] or ['REGISTRY:'+sid],independence_status='UNESTABLISHED',identifiers=identifiers[sid],registry_issues=issues,identity_scope_basis='ACCEPTED_EXPLICIT_GRAPH_AND_FIXED_COMPONENT_COUNTS_ONLY_NOT_SOLID_PHASE',cuma_indices=sorted(indices[sid]))
   candidate=CanonicalCandidate(sid,name,graph,provenance,'DEFINED_MULTICOMPONENT_COMPOSITION' if d and d['components']>1 else 'DISCRETE_MOLECULAR')
   self.entries[sid]=dict(candidate=candidate,descriptor=d,aliases=sorted(aliases[sid]),identifiers=identifiers[sid],structures=structures[sid],issues=issues,status=status)
  self.timings['snapshot_materialization']=perf_counter()-started
  self.descriptor_cache={'hits':cache.hits,'misses':cache.misses} if cache else {'status':'UNAVAILABLE'}
  if cache:
   try:cache.close()
   except Exception:pass
 def assert_unchanged(self):
  if self._transaction_db is not None:
   if not self._transaction_db.in_transaction:
    raise RuntimeError('REGISTRY_SNAPSHOT_TRANSACTION_ENDED')
   tokens=(self._transaction_db.execute('PRAGMA main.schema_version').fetchone()[0],
           self._transaction_db.execute('PRAGMA temp.schema_version').fetchone()[0])
   # A live SQLite transaction preserves its read snapshot. On this connection,
   # DML advances total_changes and DDL advances a schema cookie. Checking both
   # avoids repeatedly serializing 53k reconciliation rows for every query.
   data_version=self._transaction_db.execute('PRAGMA main.data_version').fetchone()[0]
   if (self._transaction_db.total_changes==self._loaded_at_changes and tokens==self._schema_tokens
       and data_version==self._data_version):return
  current=self._logical_digest() if self._transaction_db is not None else digest(self.path)
  if current!=self.sha256:raise RuntimeError('REGISTRY_SNAPSHOT_CHANGED_DURING_READ_ONLY_MATCHING')
 def inventory(self):
  return dict(path=str(self.path),sha256=self.sha256,connection='mode=ro; query_only=ON; read transaction',tables=self.table_counts,schema=self.schema,sqlite_integrity=self.sqlite_integrity,foreign_key_errors=self.foreign_key_errors,entries=[dict(substance_id=sid,preferred_name=r['candidate'].preferred_name,identity_status=r['status'],aliases=r['aliases'],identifiers=r['identifiers'],structures=r['structures'],descriptor=r['descriptor'],issues=r['issues'],provenance=r['candidate'].provenance) for sid,r in self.entries.items()],stored_identity_dimensions=False,stored_structure_level_provenance=False,component_relationship_table=False)
