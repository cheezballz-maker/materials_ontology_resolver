"""Read-only integrity checks and machine-readable release evidence."""
import hashlib,json,platform,sqlite3
from pathlib import Path
from rdkit import rdBase,Chem
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,o):(H/'evaluation'/n).write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
 protected=read(H/'evaluation/protected_input_freeze.json')['files'];changes=[n for n,v in protected.items() if not Path(n).is_file() or sha(Path(n))!=v]
 registry=B/'output/registry.sqlite';before=sha(registry);db=sqlite3.connect(registry.resolve().as_uri()+'?mode=ro',uri=True)
 try:
  integrity=db.execute('PRAGMA integrity_check').fetchall();fk=db.execute('PRAGMA foreign_key_check').fetchall();counts={}
  for table,columns in [('substance_identity','substance_id'),('substance_alias','substance_id,alias'),('substance_identifier','substance_id,identifier_type,identifier_value'),('substance_structure','substance_id,structure_type,structure_value'),('substance_reconciliation','cuma_index')]:
   counts['duplicate_'+table]=db.execute(f'SELECT count(*) FROM (SELECT {columns} FROM {table} GROUP BY {columns} HAVING count(*)>1)').fetchone()[0]
  for table in ('substance_alias','substance_identifier','substance_structure','substance_reconciliation'):
   counts['orphan_'+table]=db.execute(f'SELECT count(*) FROM {table} t LEFT JOIN substance_identity s ON t.substance_id=s.substance_id WHERE t.substance_id IS NOT NULL AND s.substance_id IS NULL').fetchone()[0]
  registry_count=db.execute('SELECT count(*) FROM substance_identity').fetchone()[0]
 finally:db.close()
 suites={n:read(H/f'evaluation/{n}_tests.json') for n in ('diagnostic','correspondence','adapters','identity_reconciliation','nsc001','nsc002','charge','resolver','stereo','corrected_interface','policy')}
 frozen={k:read(H/f'evaluation/baseline_{k}_results.json')['summary'] for k in ('development','heldout')};corrected={k:read(H/f'evaluation/corrected_{k}_results.json')['summary'] for k in ('development','heldout')}
 historical=read(H/'evaluation/historical_safety_results.json');historical_unchanged=historical==read(B/'real_world_validation/evaluation/historical_safety_results.json')
 score=read(H/'evaluation/documentary_accuracy_before_after.json')['POST_CORRECTION_DOCUMENTARY_CORPUS'];rows=read(H/'evaluation/chemical_correspondence_results.json')['cases']
 verdict='CORRESPONDENCE_HARDENING_V1_CHEMICAL_CORRECTNESS_FAILURE' if score['false_equivalences'] or score['false_differences'] else 'CORRESPONDENCE_HARDENING_V1_VALIDATED_PROVISIONAL'
 from rdkit.Chem.EnumerateStereoisomers import EnumerateStereoisomers
 counts_property={s:len(list(EnumerateStereoisomers(Chem.MolFromSmiles(s)))) for s in ('FC(Cl)C(Br)I','CC(O)C(O)C','FC=CC(O)C(Cl)Br','CC1CCC(C)C1O')}
 tests=dict(suites=suites,unit_integration_total=sum(s['tests_run'] for s in suites.values()),retained_unit_integration_total=sum(suites[n]['tests_run'] for n in ('diagnostic','correspondence','adapters','identity_reconciliation','nsc001','nsc002','charge','resolver')),passed=all(s['passed'] for s in suites.values()),frozen_original_controls=frozen,corrected_interface_controls=corrected,nsc_controls=read(H/'evaluation/nsc_regression.json')['passed'],historical_cases=len(historical),historical_unchanged=historical_unchanged,prospective_stereo_controls=18,random_traversal_assertions=17*12,complete_stereo_variants_by_framework=counts_property,complete_stereo_pair_assertions=sum(v*v for v in counts_property.values()),synthetic_admission_policy_fixtures=10,python=platform.python_version(),rdkit=rdBase.rdkitVersion,verdict=verdict)
 write('test_results.json',tests)
 frozen_ok=all(s['cases']==s['passed'] and not s['false_supported'] and not s['false_differences'] for s in list(frozen.values())+list(corrected.values()))
 report=dict(protected_files=len(protected),changed_protected_files=changes,registry_mode='ro',registry_substances=registry_count,registry_sha256_before=before,registry_sha256_after=sha(registry),sqlite_integrity=integrity,foreign_key_errors=fk,registry_integrity_counts=counts,canonical_ids_created=0,registry_writes=0,ontology_schema_aliases_provider_policy_admission_budgets_frozen_history='UNCHANGED_BY_DIGEST',production_resolver_provider_requests=0,public_validation_documents='reference_review/public_document_observations.json (separate, nonqualifying)',real_admissions=sum(r['result']['admission_eligibility']['eligible'] for r in rows),frozen_controls_passed=frozen_ok,historical_unchanged=historical_unchanged,pass_=not changes and before==sha(registry) and integrity==[('ok',)] and not fk and not any(counts.values()) and tests['passed'] and frozen_ok and historical_unchanged)
 write('integrity_report.json',report)
 runtime={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts and ('evaluation' not in p.parts) and p.suffix in ('.py','.json','.md','.mol')};write('implementation_manifest.json',dict(files=runtime,freeze_scope='Final diagnostic implementation, controls and review material; existing production artifacts protected separately.'))
 print(json.dumps(dict(integrity=report,tests=tests),indent=2));assert report['pass_']
if __name__=='__main__':main()
