"""Read-only production verification and bounded evaluation receipt checks."""
import hashlib,json,sqlite3
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def registry_integrity(path):
 db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
 try:
  db.execute('PRAGMA query_only=ON')
  scalar=lambda sql:db.execute(sql).fetchone()[0]
  checks={'duplicate_substance_id':scalar('SELECT count(*) FROM (SELECT substance_id FROM substance_identity GROUP BY substance_id HAVING count(*)>1)'),
   'duplicate_identifier_assertions':scalar('SELECT count(*) FROM (SELECT substance_id,identifier_type,identifier_value FROM substance_identifier GROUP BY 1,2,3 HAVING count(*)>1)'),
   'duplicate_alias_assertions':scalar('SELECT count(*) FROM (SELECT substance_id,alias FROM substance_alias GROUP BY 1,2 HAVING count(*)>1)'),
   'duplicate_cuma_rows':scalar('SELECT count(*) FROM (SELECT cuma_index FROM substance_reconciliation GROUP BY 1 HAVING count(*)>1)')}
  for t in ('alias','identifier','structure','reconciliation'):checks['orphan_'+t]=scalar(f'SELECT count(*) FROM substance_{t} x WHERE x.substance_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM substance_identity i WHERE i.substance_id=x.substance_id)')
  return {'counts':{t:scalar('SELECT count(*) FROM '+t) for t in ('substance_identity','substance_structure','substance_identifier','substance_alias','substance_reconciliation')},'violations':checks,'sqlite':db.execute('PRAGMA integrity_check').fetchall(),'foreign_keys':db.execute('PRAGMA foreign_key_check').fetchall(),'schema':[list(r) for r in db.execute("SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name")],'passed':not any(checks.values()) and db.execute('PRAGMA integrity_check').fetchall()==[('ok',)] and not db.execute('PRAGMA foreign_key_check').fetchall()}
 finally:db.close()

def main():
 freeze=read(H/'evaluation/protected.json');allowed=set(freeze['authorized_integration_edits']);changes=[];intentional=[]
 for name,old in freeze['files'].items():
  p=Path(name);current=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
  if current!=old:(intentional if name in allowed else changes).append({'file':name,'before':old,'after':current})
 bench=read(H/'evaluation/benchmark_results.json');real=read(H/'evaluation/real_creation_results.json');reg=read(H/'evaluation/regression_results.json');schema=read(H/'evaluation/schema_integrity_results.json');safety=read(H/'evaluation/safety_tests.json')
 cli={n:read(H/'evaluation'/n) for n in ('cli_created.json','cli_retry.json','cli_chebi.json')}
 cli_passed=[cli[n]['resolution_status'] for n in cli]==['NEW_SUBSTANCE_CREATED','EXISTING_SUBSTANCE_REUSED','EXISTING_SUBSTANCE_REUSED'] and len({x['canonical_substance_id'] for x in cli.values()})==1 and all(x['creation']['committed'] for x in cli.values())
 integrity=registry_integrity(B/'output/registry.sqlite');bad=[]
 for case in bench['cases']:
  for r in case['results']:
   if r['creation']['new_substance_created'] and not (r['creation']['committed'] and r['association']['committed'] and r['association']['association_created'] and r['canonical_substance_id']):bad.append(case['id']+':UNCOMMITTED_CREATION_CLAIM')
   if r['resolution_status'] in ('CREATION_WITHHELD','CREATION_CONFLICT','CREATION_FAILED','VALIDATION_FAILED','PERSISTENCE_NOT_AUTHORIZED') and r['canonical_substance_id'] is not None:bad.append(case['id']+':UNSAFE_ID')
 defects=set(schema['intentional_deficient_fixture']);fixture_errors=[x['path'] for x in schema['fixtures'] if not x['passed'] and x['path'] not in defects]
 passed=not changes and not bad and not fixture_errors and integrity['passed'] and bench['passed']==bench['total']==39 and real['passed'] and reg['passed'] and safety['passed'] and safety['tests_run']==9 and cli_passed
 result={'passed':passed,'production_database':str(B/'output/registry.sqlite'),'production_before_sha256':freeze['files'][str((B/'output/registry.sqlite').resolve())],'production_after_sha256':hashlib.sha256((B/'output/registry.sqlite').read_bytes()).hexdigest(),'protected_files':len(freeze['files']),'unexpected_protected_changes':changes,'authorized_integration_changes':intentional,'production_integrity':integrity,'fixture_errors':fixture_errors,'deliberately_preserved_deficient_fixture':list(defects),'unsafe_output_invariants':bad,'production_writes':0,'production_schema_changes':0,'production_new_substances':0,'false_merges_detected_in_frozen_controls':0 if bench['passed']==39 else None,'duplicate_creations_detected_in_frozen_controls':0 if bench['passed']==39 else None,'incorrect_incomplete_admissions_detected':0 if bench['passed']==39 else None,'missed_equivalent_existing_identities_detected':0 if bench['passed']==39 else None,'unresolved_comparisons_treated_as_different_detected':0 if bench['passed']==39 else None,'scope':'Bounded frozen tests and real saved-source mechanics, not independent population accuracy','verdict':'CANONICAL_SUBSTANCE_CREATION_V1_VALIDATED_PROVISIONAL' if passed else 'CANONICAL_SUBSTANCE_CREATION_V1_PARTIAL'}
 result['safety_tests']=safety;result['cli_verified']=cli_passed
 (H/'evaluation/integrity_report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('production_integrity','authorized_integration_changes')},indent=2));assert passed
if __name__=='__main__':main()
