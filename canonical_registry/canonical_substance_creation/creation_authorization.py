"""Separate creation capability issued only for a freshly copied fixture.

An association capability cannot upgrade an existing database. Neither boolean
options nor a writable path provide creation authority.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib,secrets,sqlite3
import bootstrap
from fixture_registry import FixturePermit,create_fixture,connect,CANONICAL

SCHEMA='''
CREATE TABLE creation_authorization(fixture_id TEXT PRIMARY KEY REFERENCES fixture_authorization,token_hash TEXT NOT NULL);
CREATE TABLE canonical_id_sequence(singleton INTEGER PRIMARY KEY CHECK(singleton=1),high_water INTEGER NOT NULL);
CREATE TABLE creation_request(idempotency_key TEXT PRIMARY KEY,request_digest TEXT NOT NULL,concept_id TEXT NOT NULL REFERENCES source_concept,revision_id TEXT NOT NULL REFERENCES source_concept_revision,event_id TEXT NOT NULL REFERENCES concept_resolution_event,result_json TEXT NOT NULL);
CREATE TABLE substance_creation_record(substance_id TEXT PRIMARY KEY REFERENCES substance_identity,concept_id TEXT NOT NULL REFERENCES source_concept,revision_id TEXT NOT NULL REFERENCES source_concept_revision,event_id TEXT NOT NULL UNIQUE REFERENCES concept_resolution_event,created_at TEXT NOT NULL,construction_json TEXT NOT NULL);
CREATE TRIGGER immutable_creation_update BEFORE UPDATE ON substance_creation_record BEGIN SELECT RAISE(ABORT,'IMMUTABLE_CREATION'); END;
CREATE TRIGGER immutable_creation_delete BEFORE DELETE ON substance_creation_record BEGIN SELECT RAISE(ABORT,'IMMUTABLE_CREATION'); END;
CREATE TRIGGER immutable_creation_request_update BEFORE UPDATE ON creation_request BEGIN SELECT RAISE(ABORT,'IMMUTABLE_CREATION_REQUEST'); END;
CREATE TRIGGER immutable_creation_request_delete BEFORE DELETE ON creation_request BEGIN SELECT RAISE(ABORT,'IMMUTABLE_CREATION_REQUEST'); END;
'''
@dataclass(frozen=True)
class CreationPermit:
 association:FixturePermit
 creation_token:str
 @property
 def path(self):return self.association.path

def create_creation_fixture(source, *, compact_audit=False):
 """Issue independent random capabilities for a new fixture; never migrate source."""
 permit=create_fixture(source);token=secrets.token_hex(32);db=connect(permit)
 try:
  db.executescript(SCHEMA)
  if compact_audit:
   from audit_payload import SCHEMA as AUDIT_SCHEMA
   db.executescript(AUDIT_SCHEMA)
  import re
  nums=[int(s[0][4:]) for s in db.execute('SELECT substance_id FROM substance_identity') if re.fullmatch(r'SUB_\d{8}',s[0])]
  db.execute('INSERT INTO canonical_id_sequence VALUES(1,?)',(max(nums,default=0),))
  db.execute('INSERT INTO creation_authorization VALUES(?,?)',(permit.fixture_id,hashlib.sha256(token.encode()).hexdigest()));db.commit()
 finally:db.close()
 return CreationPermit(permit,token)

def connect_creation(permit):
 if not isinstance(permit,CreationPermit):raise PermissionError('DISTINCT_CREATION_CAPABILITY_REQUIRED')
 db=connect(permit.association)
 try:
  row=db.execute('SELECT token_hash FROM creation_authorization WHERE fixture_id=?',(permit.association.fixture_id,)).fetchone()
  if not row or not secrets.compare_digest(row[0],hashlib.sha256(permit.creation_token.encode()).hexdigest()):raise PermissionError('CREATION_AUTHORIZATION_REQUIRED')
  def authorize(action,a,b,dbname,trigger):
   if action in (sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) and a in CANONICAL:return sqlite3.SQLITE_DENY
   if action==sqlite3.SQLITE_INSERT and a=='substance_reconciliation':return sqlite3.SQLITE_DENY
   if action in (sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH,sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_ALTER_TABLE,sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_DROP_TRIGGER,sqlite3.SQLITE_CREATE_TRIGGER):return sqlite3.SQLITE_DENY
   if action==sqlite3.SQLITE_PRAGMA and b is not None and a.lower() in ('foreign_keys','writable_schema','ignore_check_constraints'):return sqlite3.SQLITE_DENY
   if action in (sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_INSERT) and a in ('fixture_authorization','creation_authorization'):return sqlite3.SQLITE_DENY
   return sqlite3.SQLITE_OK
  db.set_authorizer(authorize);return db
 except BaseException:db.close();raise
