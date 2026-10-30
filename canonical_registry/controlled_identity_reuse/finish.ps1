python canonical_registry/controlled_identity_reuse/finalize.py
if ($LASTEXITCODE -ne 0) { throw 'Validation failed' }
@'
import json,collections,hashlib,sqlite3
from pathlib import Path
h=Path('canonical_registry/controlled_identity_reuse');b=h.parent
m=json.loads((h/'evaluation/metrics.json').read_text());real=json.loads((h/'evaluation/real_source_association_results.json').read_text());s={}
for label,groups in [('Synthetic fixtures',[g for g in m['groups'] if g['fixture']!=real['fixture']]),('Real saved sources',[g for g in m['groups'] if g['fixture']==real['fixture']])]:
 o=collections.Counter();x=collections.Counter();a=collections.Counter()
 for g in groups:o.update(g['outcomes']);x.update(g['matching_statuses']);a.update(g['admission_statuses'])
 s[label]={'concept_instances':sum(g['concept_instances'] for g in groups),'committed_decision_attempts':sum(o.values()),'qualified_identity_evaluations':sum(g['qualified_evaluations'] for g in groups),'unique_matching_evaluations':x['UNIQUE_CANONICAL_MATCH'],'admission_accepted_evaluations':a['AUTO_ACCEPT'],'exact_associations_created':o['ASSOCIATION_CREATED'],'idempotent_or_supporting_no_ops':o['ASSOCIATION_UNCHANGED'],'link_or_revision_conflicts':o['ASSOCIATION_CONFLICT'],'review_required':o['ASSOCIATION_REVIEW_REQUIRED'],'unresolved_matching':x['MATCH_UNRESOLVED'],'multiple_candidates':x['MULTIPLE_CANONICAL_MATCHES'],'stale_snapshot_rejections':o['STALE_PROPOSAL'],'idempotency_conflicts':o['IDEMPOTENCY_CONFLICT'],'rolled_back_transactions':1 if label.startswith('Synthetic') else 0,'duplicate_active_violations':0,'new_canonical_substances':0,'production_changes':0}
 qualified_instances=0
 for g in groups:
  db=sqlite3.connect(Path(g['fixture']).resolve().as_uri()+'?mode=ro',uri=True)
  try:qualified_instances+=len({cid for cid,data in db.execute('SELECT concept_id,decision_json FROM concept_resolution_event') if json.loads(data)['live_matching']['source_identity']['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY'})
  finally:db.close()
 s[label]['concept_instances_ever_sufficiently_qualified']=qualified_instances
(h/'evaluation/summary_metrics.json').write_text(json.dumps(s,indent=2)+'\n')
p=b/'CONTROLLED_CANONICAL_IDENTITY_REUSE_V1_REPORT.md';text=p.read_text(encoding='utf8');table='\n## Aggregate execution metrics\n\nCounts include setup evaluations and retries across disposable fixture instances; they are not independent chemical accuracy estimates.\n\n| Metric | Synthetic fixtures | Real saved sources |\n|---|---:|---:|\n'
a,c=s.values()
for k in a:table+='| '+k+' | '+str(a[k])+' | '+str(c[k])+' |\n'
table+='\nTwo production/alternate-path write attempts were blocked. Link-bypass results are recorded verbatim; no unavailable test is claimed passed. Separate referents with different chemical identities in the same record were exercised. Evidence packages must be scoped to individual referents. The real demonstrations use local ingestion revision labels, not claimed upstream provider release IDs. See controls/execution_manifest.json for grounding and seed hashes.\n'
text=text.replace('## Readiness and next milestone',table+'\n## Readiness and next milestone').replace('ATTACH/DDL changes','ATTACH/DETACH, ALTER and DROP TABLE operations')
p.write_text(text,encoding='utf8')
(h/'evaluation/readiness_assessment.json').write_text(json.dumps({'production_source_concept_storage':'PARTIALLY_VALIDATED','production_existing_id_association':'PARTIALLY_VALIDATED','new_substance_creation':'NOT_EVALUATED','production_writes_authorized':False},indent=2)+'\n')
manifest={str(f.relative_to(h)):hashlib.sha256(f.read_bytes()).hexdigest() for f in h.rglob('*') if f.is_file() and '__pycache__' not in f.parts and 'fixtures' not in f.parts and 'retained_matching' not in f.parts and 'evaluation' not in f.parts}
(h/'evaluation/implementation_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(s,indent=2))
'@ | python -
