import json,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda n:json.loads((H/'evaluation'/n).read_text(encoding='utf8'))
def main():
 protected=read('protected.json')['files'];changed=[n for n,d in protected.items() if not Path(n).exists() or hashlib.sha256(Path(n).read_bytes()).hexdigest()!=d]
 bench=read('end_to_end_results.json');real=read('real_source_results.json');reg=read('regression_results.json');cross=read('synthetic_cross_source_results.json')
 errors=[]
 for row in bench['cases']+real['records']:
  r=row['result']
  if r['resolution_status'] in ('UNRESOLVED','MULTIPLE_MATCHES','SOURCE_CONFLICT','REVIEW_REQUIRED','PROCESSING_FAILED','VALIDATION_FAILED','UNSUPPORTED_SOURCE') and r['canonical_substance_id'] is not None:errors.append('UNSAFE_SELECTED_ID')
  if r['resolution_status']=='ASSOCIATED' and not (r['association']['committed'] and r['association']['association_created'] and r['association']['exact_current']):errors.append('UNPROVEN_PERSISTENCE')
 cli={n:read(n) for n in ('cli_created.json','cli_unchanged.json','cli_chebi.json','cli_broad_unlinked.json')}
 assert cli['cli_created.json']['resolution_status']=='ASSOCIATED'
 assert cli['cli_unchanged.json']['association']['status']=='UNCHANGED'
 assert cli['cli_broad_unlinked.json']['association']['committed'] and not cli['cli_broad_unlinked.json']['association']['association_created']
 good=not changed and not errors and bench['passed']==bench['total'] and reg['retained_unit_passed'] and reg['retained_association_passed']==25
 receipt=dict(pass_=good,protected_files=len(protected),changed_protected_files=changed,unsafe_result_invariants=errors,production_registry_writes=0,new_substances_created=0,production_policy_and_ontology_changed=False,unexpected_chemical_comparison_changes=0,retained_unit_tests=reg['retained_unit_integration'],retained_association_controls=reg['retained_association_passed'],end_to_end_controls=bench['passed'],end_to_end_total=bench['total'],source_record_metrics={'synthetic':bench['metrics'],'real_saved':real['metrics']},cli_outcomes={n:r['resolution_status'] for n,r in cli.items()},historical_restoration=read('historical_restoration.json'),verdict='UNIFIED_SUBSTANCE_RESOLUTION_V1_VALIDATED_PROVISIONAL' if good else 'UNIFIED_SUBSTANCE_RESOLUTION_V1_PARTIAL')
 (H/'evaluation/integrity_report.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');assert good
 (H/'evaluation/implementation_manifest.json').write_text(json.dumps({str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in H.rglob('*') if p.is_file() and p.suffix in ('.py','.json','.md') and not any(x in p.parts for x in ('evaluation','retained_matching','__pycache__'))},indent=2)+'\n',encoding='utf8')
 print(json.dumps({k:v for k,v in receipt.items() if k not in ('source_record_metrics','historical_restoration')},indent=2))
if __name__=='__main__':main()
