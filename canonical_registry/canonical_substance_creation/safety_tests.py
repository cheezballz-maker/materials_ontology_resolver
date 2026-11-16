"""Additional contract regressions; no chemical expectations from predictions."""
import copy,json,sqlite3,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import bootstrap
from evaluate import SyntheticAdapter,LockedValidator,db_state
from unified_resolver import SubstanceResolver
from adapter_registry import envelope
from creation_authorization import create_creation_fixture,connect_creation
from fixture_registry import PRODUCTION
from matching_control_inputs import matching_input
from chemistry import describe

H=Path(__file__).resolve().parent;B=H.parent
class SafetyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.validator=LockedValidator()
 @classmethod
 def tearDownClass(cls):cls.validator.close()
 def setUp(self):
  self.p=create_creation_fixture(PRODUCTION);self.resolver=SubstanceResolver(official_validator=self.validator);self.resolver.adapters.register('synthetic',SyntheticAdapter());self.record={'record_id':'safety','graph':'CCO','name':'Explicit synthetic molecular referent'}
 def resolve(self,r=None,**kw):return self.resolver.resolve(r or self.record,'synthetic',self.p.association,persist_association=True,allow_creation=True,creation_authorization=self.p,**kw)
 def test_name_derived_policy_acceptance_still_cannot_create(self):
  c=next(c for c in json.loads((B/'canonical_registry_matching/controls/development_controls.json').read_text())['cases'] if c['id']=='D19')
  inp=matching_input(c);inp.form_assertion={'explicit_structure':True}
  class Adapter:
   def adapt(_,r):return envelope(r,copy.deepcopy(inp))
  self.resolver.adapters.register('qualified-name-control',Adapter())
  r=self.resolver.resolve({'source_revision':'v1'},'qualified-name-control',self.p.association,persist_association=True,allow_creation=True,creation_authorization=self.p)
  self.assertTrue(r['admission']['admission_eligible']);self.assertFalse(r['admission']['input_classification']['verified_explicit_structure']);self.assertEqual(r['resolution_status'],'CREATION_WITHHELD');self.assertEqual(len(db_state(self.p)['substance_identity']),112)
 def test_official_success_for_different_graph_is_rejected(self):
  parent=SyntheticAdapter();d=describe('CCC')
  class Adapter:
   def adapt(_,r):
    x=parent.adapt(r);x.incoming.official_validation={'status':'SUCCESS','agrees':True,'inchi':d['inchi'],'inchikey':d['inchikey']};return x
  self.resolver.adapters.register('bad-official',Adapter())
  r=self.resolver.resolve(self.record,'bad-official',self.p.association,persist_association=True,allow_creation=True,creation_authorization=self.p)
  self.assertEqual(r['resolution_status'],'CREATION_WITHHELD');self.assertFalse(r['admission']['official_validation']['agrees'])
 def test_canonical_update_delete_and_cuma_insert_are_denied(self):
  self.assertEqual(self.resolve()['resolution_status'],'NEW_SUBSTANCE_CREATED');before=db_state(self.p);db=connect_creation(self.p)
  try:
   for sql in ("UPDATE substance_identity SET preferred_name='forged'",'DELETE FROM substance_structure',"INSERT INTO substance_reconciliation VALUES(9999999,'SUB_00000113','EXACT','forged')","PRAGMA foreign_keys=OFF","UPDATE creation_authorization SET token_hash='forged'","DROP TRIGGER immutable_event_update","UPDATE concept_resolution_event SET outcome='forged'"):
    with self.assertRaises(sqlite3.DatabaseError):db.execute(sql)
    db.rollback()
  finally:db.close()
  self.assertEqual(before,db_state(self.p))
 def test_interrupt_rolls_back_all_tables(self):
  before=db_state(self.p)
  def interrupt(stage):
   if stage=='AFTER_REPRESENTATIONS':raise KeyboardInterrupt('TEST_INTERRUPT')
  with self.assertRaises(KeyboardInterrupt):self.resolve(failure_injector=interrupt)
  self.assertEqual(before,db_state(self.p))
 def test_creation_requires_atomic_association(self):
  before=db_state(self.p);r=self.resolver.resolve(self.record,'synthetic',self.p.association,allow_creation=True,creation_authorization=self.p)
  self.assertEqual(r['resolution_status'],'VALIDATION_FAILED');self.assertEqual(before,db_state(self.p))
 def test_capabilities_for_different_fixtures_cannot_be_combined(self):
  other=create_creation_fixture(PRODUCTION);r=self.resolver.resolve(self.record,'synthetic',other.association,persist_association=True,allow_creation=True,creation_authorization=self.p)
  self.assertEqual(r['resolution_status'],'PERSISTENCE_NOT_AUTHORIZED');self.assertEqual(len(db_state(other)['substance_identity']),112)
 def test_creation_key_cannot_authorize_association_operation(self):
  first=self.resolve(idempotency_key='shared-operation-key');self.assertEqual(first['resolution_status'],'NEW_SUBSTANCE_CREATED')
  other={**self.record,'record_id':'different-concept'}
  r=self.resolver.resolve(other,'synthetic',self.p.association,persist_association=True,idempotency_key='shared-operation-key')
  self.assertEqual(r['association']['outcome'],'IDEMPOTENCY_CONFLICT');self.assertFalse(r['association']['association_created']);self.assertIsNone(r['canonical_substance_id']);self.assertEqual(len(db_state(self.p)['concept_substance_association']),1)
 def test_concurrent_same_concept_same_creation_key(self):
  with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(lambda _:self.resolve(idempotency_key='same-concurrent-request'),range(2)))
  self.assertEqual(sorted(r['resolution_status'] for r in rows),['EXISTING_SUBSTANCE_REUSED','NEW_SUBSTANCE_CREATED']);self.assertEqual(len({r['canonical_substance_id'] for r in rows}),1);state=db_state(self.p);self.assertEqual(len(state['substance_identity']),113);self.assertEqual(len(state['concept_substance_association']),1)
 def test_orphan_registry_record_blocks_creation_without_repair(self):
  db=sqlite3.connect(self.p.path)
  try:db.execute("INSERT INTO substance_structure VALUES('MISSING_ID','SMILES','CCO')");db.commit()
  finally:db.close()
  r=self.resolve();self.assertEqual(r['resolution_status'],'CREATION_WITHHELD');self.assertIn('REGISTRY_INTEGRITY_FAILURE',r['creation']['reasons']);state=db_state(self.p);self.assertEqual(len(state['substance_identity']),112);self.assertIn(('MISSING_ID','SMILES','CCO'),state['substance_structure'])

def main():
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SafetyTests))
 (H/'evaluation/safety_tests.json').write_text(json.dumps({'tests_run':r.testsRun,'passed':r.wasSuccessful(),'failures':len(r.failures),'errors':len(r.errors)},indent=2)+'\n');assert r.wasSuccessful()
if __name__=='__main__':main()
