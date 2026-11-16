"""Frozen end-to-end controls and genuine saved-source demonstrations."""
import copy,json,hashlib,sqlite3,socket
from pathlib import Path
from dataclasses import asdict
import bootstrap
from providers import Bridge
from unified_resolver import SubstanceResolver
from adapter_registry import envelope
from fixture_registry import create_fixture,PRODUCTION
from matching_control_inputs import matching_input
from registry_matching_models import RetrievalPolicy
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf8'))
def write(n,obj):(H/'evaluation'/n).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
SEEDS={c['id']:c for k in ('development','heldout') for c in read(B/f'canonical_registry_matching/controls/{k}_controls.json')['cases']}
class SyntheticAdapter:
 def adapt(self,record):
  c=copy.deepcopy(SEEDS[record['case']])
  if 'override_graph' in record:c['source_graph']=record['override_graph']
  inp=matching_input(c);inp.evidence_origin='EXPLICITLY_SYNTHETIC_END_TO_END_CONTROL'
  return envelope(record,inp)
def metrics(rows):
 from collections import Counter
 r=[row['result'] for row in rows]
 return dict(source_records=len(r),qualified_identity_evidence=sum(x.get('reconciliation',{}).get('state')=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' for x in r),chemical_resolution_counts=dict(Counter(x['chemical_resolution_status'] for x in r)),resolution_status_counts=dict(Counter(x['resolution_status'] for x in r)),admission_eligible_matches=sum(x['chemical_resolution_status']=='EXACT_MATCH' and x.get('admission',{}).get('admission_eligible',False) for x in r),associations_created=sum(x['association']['association_created'] for x in r),unchanged=sum(x['association']['status']=='UNCHANGED' for x in r),revision_reviews=sum(x['resolution_status']=='REVIEW_REQUIRED' for x in r),processing_failures=sum(x['resolution_status']=='PROCESSING_FAILED' for x in r),production_writes=0,new_substances=0)
def main():
 socket.create_connection=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('NO_LIVE_PROVIDER_REQUESTS'))
 for n,d in read(H/'controls/freeze.json').items():assert hashlib.sha256((H/'controls'/n).read_bytes()).hexdigest()==d
 bridge=Bridge();resolver=SubstanceResolver(official_validator=bridge.official);resolver.adapters.register('synthetic',SyntheticAdapter());rows=[];shared=None
 try:
  controls=[c for k in ('development','heldout') for c in read(H/f'controls/{k}.json')['cases']]
  for c in controls:
   key=c['id'];record={'case':c['matching_seed'],'source_revision':'v1'};source='synthetic';policy=RetrievalPolicy();failure=None
   if key in ('D01','D02','D03','H02'):
    if shared is None:shared=create_fixture(B/'canonical_registry_matching/fixtures/D01.sqlite')
    registry=shared
   else:registry=create_fixture(B/f"canonical_registry_matching/fixtures/{c['matching_seed']}.sqlite")
   if key=='D03':record['referent_key']='second-referent'
   if key=='D11':policy=RetrievalPolicy(exhaustive=False)
   if key=='H02':record.update(override_graph='COC',source_revision='v2')
   if key=='H03':source='not_configured'
   if key=='H04':failure=lambda:True
   if key=='H05':record['override_graph']='CCO arbitrary text'
   result=resolver.resolve(record,source,registry,persist_association=c['persist'],retrieval_policy=policy,failure_injector=failure)
   ok=result['resolution_status']==c['expected']
   if result['resolution_status'] in ('UNRESOLVED','MULTIPLE_MATCHES','SOURCE_CONFLICT','REVIEW_REQUIRED','PROCESSING_FAILED'):ok=ok and result['canonical_substance_id'] is None
   if key=='D02':ok=ok and result['association']['status']=='UNCHANGED' and result['source_revision']['recorded_at']==rows[0]['result']['source_revision']['recorded_at']
   if key=='D05':ok=ok and not result['admission']['admission_eligible']
   if key=='H04':
    db=sqlite3.connect(registry.path.as_uri()+'?mode=ro',uri=True)
    try:ok=ok and db.execute('SELECT count(*) FROM concept_substance_association').fetchone()[0]==0 and db.execute('SELECT count(*) FROM concept_resolution_event').fetchone()[0]==0
    finally:db.close()
   rows.append(dict(id=key,expected=c['expected'],passed=ok,origin='SYNTHETIC',input=record,result=result));print(key,result['resolution_status'],ok,flush=True)
  write('end_to_end_results.json',dict(cases=rows,metrics=metrics(rows),passed=sum(x['passed'] for x in rows),total=len(rows)))
  write('error_handling_results.json',{'cases':[x for x in rows if x['id'] in ('H03','H04','H05','H06')]})
  write('association_results.json',{'cases':[x for x in rows if x['result']['association']['requested']]})
  # Actual source packets: no downstream matching/association decisions supplied.
  saved=read(B/'canonical_registry_matching/evaluation/saved_input_records.json')['records'];permit=create_fixture(PRODUCTION);real=[]
  for cid in ('1049','6323'):
   r=next(x for x in saved if x['record_id']==cid);record={'provider':'PubChem','record':r['original_record'],'provenance':r['provenance'],'source_revision':'local-cache-v1'}
   if cid=='1049':(H/'examples/pubchem_input.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
   for repetition in range(2):real.append(dict(source='PubChem',record_id=cid,origin='REAL_SAVED_SOURCE_KNOWN_SHARED_ANCESTRY',result=resolver.resolve(record,'pubchem',permit,persist_association=True)))
  prior=read(B/'real_world_validation/evaluation/pubchem_chebi_pair_results.json')['pairs']
  for pair in prior:
   for source,key,pk in [('pubchem','source_record','source_record_provenance'),('chebi','reference_identity','reference_provenance')]:
    rec=pair['source_inputs'][key];record={'record':rec['record'],'provenance':pair['source_inputs'][pk],'source_revision':'local-cache-v1'}
    if source=='chebi' and pair==prior[0]:(H/'examples/chebi_input.json').write_text(json.dumps({'source_type':'chebi',**record},indent=2)+'\n',encoding='utf8')
    real.append(dict(source=source,record_id=rec['record_id'],origin='REAL_SAVED_SOURCE_READ_ONLY',result=resolver.resolve(record,source,PRODUCTION)))
  write('real_source_results.json',dict(records=real,metrics=metrics(real),independent_chemical_accuracy_estimate=False))
  write('cross_source_results.json',dict(real_sources_evaluated=['PubChem','ChEBI'],real_many_to_one_positive=0,reason='Available ChEBI records have no exact target in the existing snapshot. No positive was manufactured.',synthetic_many_to_one=next(r for r in rows if r['id']=='D03')))
  broad=SyntheticAdapter().adapt({'case':'D27'}).incoming
  packet={'source_type':'qualified','concept':asdict(broad.concept),'name':broad.name,'source_revision':'example-v1'}
  (H/'examples/broad_concept_input.json').write_text(json.dumps(packet,indent=2)+'\n',encoding='utf8')
  assert all(x['passed'] for x in rows)
  assert [x['result']['resolution_status'] for x in real[:4]]==['ASSOCIATED','EXACT_MATCH','ASSOCIATED','EXACT_MATCH']
 finally:bridge.close()
if __name__=='__main__':main()
