"""Write capabilities limited to marked, isolated, single-link fixture files."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,os,secrets,sqlite3,uuid
H=Path(__file__).resolve().parent;ROOT=H/'fixtures';PRODUCTION=H.parent/'output/registry.sqlite'
CANONICAL=('substance_identity','substance_alias','substance_identifier','substance_structure','substance_reconciliation')
@dataclass(frozen=True)
class FixturePermit:
 path:Path
 fixture_id:str
 token:str
def validate_path(path):
 p=Path(path).absolute()
 for part in [p,*p.parents]:
  if part.is_symlink() or getattr(part,'is_junction',lambda:False)():raise PermissionError('LINK_PATH_REJECTED')
 p=p.resolve()
 if p==PRODUCTION.resolve() or ROOT.resolve() not in p.parents:raise PermissionError('ONLY_ISOLATED_FIXTURES_WRITABLE')
 if p.exists() and (os.path.samefile(p,PRODUCTION) or p.stat().st_nlink!=1):raise PermissionError('SHARED_FILE_REJECTED')
 return p
def create_fixture(source):
 ROOT.mkdir(exist_ok=True);p=validate_path(ROOT/(uuid.uuid4().hex+'.sqlite'));fixture_id=uuid.uuid4().hex;token=secrets.token_hex(32)
 src=sqlite3.connect(Path(source).resolve().as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(p)
 try:
  src.backup(dst);dst.executescript((H/'schema/associations.sql').read_text());dst.execute('INSERT INTO fixture_authorization VALUES(?,?)',(fixture_id,hashlib.sha256(token.encode()).hexdigest()));dst.commit()
 finally:src.close();dst.close()
 return FixturePermit(p,fixture_id,token)
def connect(permit):
 p=validate_path(permit.path);before=p.stat();db=sqlite3.connect(p.as_uri()+'?mode=rw',uri=True,timeout=60)
 try:
  after=p.stat()
  if (before.st_dev,before.st_ino)!=(after.st_dev,after.st_ino):raise PermissionError('FILE_CHANGED_DURING_OPEN')
  row=db.execute('SELECT token_hash FROM fixture_authorization WHERE fixture_id=?',(permit.fixture_id,)).fetchone()
  if not row or row[0]!=hashlib.sha256(permit.token.encode()).hexdigest():raise PermissionError('FIXTURE_AUTHORIZATION_REQUIRED')
  db.execute('PRAGMA foreign_keys=ON')
  def authorize(action,arg1,arg2,dbname,trigger):
   if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) and arg1 in CANONICAL:return sqlite3.SQLITE_DENY
   if action in (sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH,sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_ALTER_TABLE):return sqlite3.SQLITE_DENY
   return sqlite3.SQLITE_OK
  db.set_authorizer(authorize);return db
 except Exception:db.close();raise
def registry_digest(db):
 return hashlib.sha256(repr([(t,db.execute('SELECT * FROM '+t+' ORDER BY 1,2').fetchall()) for t in CANONICAL]).encode()).hexdigest()
