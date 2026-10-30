"""Actual read-only 112-record evaluation; no registry graph becomes an input."""
import collections,copy,hashlib,json,socket,time
from pathlib import Path
import bootstrap
from providers import Bridge
from pubchem_adapter import compound
from chebi_adapter import adapt as chebi
from correspondence_models import IncomingConcept
from registry_identity_adapter import RegistrySnapshot
from registry_matching_models import MatchingInput
from registry_matcher import RegistryMatcher
from comparison_session import statistics
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,o):(H/'evaluation'/n).write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def deny(*a,**kw):raise AssertionError('NEW_PRODUCTION_PROVIDER_REQUEST_NOT_ALLOWED')

def make_input(provider,record,provenance,case_id):
 p=compound(record,provenance) if provider=='PubChem' else chebi({'data':record},provenance)
 ids=[c.evidence_id for c in p.claims if c.claim_role in ('STRUCTURAL_IDENTITY_ASSERTION','UNKNOWN_ROLE') and c.claim_id in ('SMILES','default_structure')]
 name=record.get('IUPACName') or record.get('ascii_name') or record.get('name') or ''
 concept=IncomingConcept(case_id,p,dict(status='ESTABLISHED' if ids else 'UNESTABLISHED',kind='EXPLICIT_STRUCTURAL_FIELD_REFERENT',evidence_ids=ids,document=provenance.get('url') or provenance.get('payload_path')),'DISCRETE_MOLECULAR',provenance)
 return MatchingInput(concept,name,evidence_origin=provenance.get('role','SAVED_PROVIDER_RECORD_NO_NEW_QUERY'))

def summarize(rows):
 results=[r['result'] for r in rows];pairs=[c for r in results for c in r['candidate_results']]
 equivalent=[(r,c) for r in results for c in r['candidate_results'] if c['chemical_status']=='CHEMICALLY_EQUIVALENT']
 indexed_hits=sum(c['candidate_substance_id'] in r['retrieval']['indexed_candidate_ids'] for r,c in equivalent)
 all_hits=len(equivalent);routes=collections.Counter()
 for r in results:
  for sid,rs in r['retrieval']['routes'].items():
   for channel in {v['route'] for v in rs}:routes[channel]+=1
 return dict(incoming_concepts=len(rows),qualified_source_identities=sum(r['source_identity']['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' and r['source_identity']['binding_valid'] for r in results),candidate_pairs_compared=len(pairs),incoming_with_indexed_candidates=sum(bool(r['retrieval']['indexed_candidate_ids']) for r in results),candidate_retrieval_coverage=sum(bool(r['retrieval']['indexed_candidate_ids']) for r in results)/len(rows) if rows else None,verified_equivalent_candidates=len(equivalent),indexed_equivalent_retrieval_recall=indexed_hits/all_hits if all_hits else None,exhaustive_equivalent_retrieval_recall=1.0 if all_hits else None,missed_equivalent_candidates_indexed=all_hits-indexed_hits,missed_equivalent_candidates_exhaustive=0,chemical_status_counts=dict(collections.Counter(c['chemical_status'] for c in pairs)),match_status_counts=dict(collections.Counter(r['status'] for r in results)),complete_snapshot_searches=sum(r['retrieval']['search_complete'] for r in results),incomplete_searches=sum(not r['retrieval']['search_complete'] for r in results),unique_canonical_matches=sum(r['status']=='UNIQUE_CANONICAL_MATCH' for r in results),multiple_canonical_matches=sum(r['status']=='MULTIPLE_CANONICAL_MATCHES' for r in results),no_match_in_complete_search=sum(r['status']=='NO_MATCH_IN_SEARCHED_REGISTRY' for r in results),read_only_matching_proposals=sum(r['matching_proposal'] is not None for r in results),diagnostic_reuse_proposals=sum(r['diagnostic_reuse_proposal'] is not None for r in results),admission_eligible_proposals=sum(bool(r['matching_proposal'] and r['matching_proposal']['admission_eligible']) for r in results),canonical_id_reuse_authorized=0,provider_requests=0,retrieval_route_candidate_pair_counts=dict(routes),unsafe_unique_match_proposals='NOT_ESTIMABLE_WITHOUT_INDEPENDENT_REFERENCE_LABELS; mechanical invariants checked separately')

def main():
 socket.create_connection=deny;start=time.monotonic();snapshot=RegistrySnapshot(B/'output/registry.sqlite');write('registry_inventory.json',snapshot.inventory());bridge=Bridge();matcher=RegistryMatcher(snapshot,official_validator=bridge.official);inputs=[]
 saved=read(H/'evaluation/saved_input_records.json')
 for r in saved['records']:inputs.append(dict(group='SOURCE_DEPENDENT_REGISTRY_COVERAGE',source_record_id=r['record_id'],provider='PubChem',input=make_input('PubChem',r['original_record'],r['provenance'],'SAVED_PUBCHEM:'+r['record_id'])))
 # Separately supplied earlier PubChem and ChEBI records. No counterpart graph
 # is copied or made an incoming assertion by this loader.
 pairs=read(B/'real_world_validation/evaluation/pubchem_chebi_pair_results.json')['pairs']
 for p in pairs:
  for provider,side,provside in [('PubChem','source_record','source_record_provenance'),('ChEBI','reference_identity','reference_provenance')]:
   original=p['source_inputs'][side];provenance=copy.deepcopy(p['source_inputs'][provside]);provenance['role']='PREVIOUS_ACTUAL_SOURCE_RECORD_LOOKUP_DEMONSTRATION_NOT_INDEPENDENT_VALIDATION'
   inputs.append(dict(group='PREVIOUS_PUBCHEM_CHEBI_DEMONSTRATIONS',source_record_id=original['record_id'],provider=provider,input=make_input(provider,original['record'],provenance,'PAIR_INPUT:'+provider+':'+original['record_id'])))
 rows=[]
 try:
  for i,item in enumerate(inputs):
   result=matcher.match(item['input']);r={k:v for k,v in item.items() if k!='input'};r['result']=result;rows.append(r)
   if (i+1)%10==0 or i+1==len(inputs):print(i+1,'/',len(inputs),result['status'],'elapsed',round(time.monotonic()-start,1),flush=True)
 finally:bridge.close()
 summary=summarize(rows);groups={g:summarize([r for r in rows if r['group']==g]) for g in sorted({r['group'] for r in rows})}
 write('real_registry_results.json',dict(summary=summary,groups=groups,records=rows,ground_truth='Actual demonstrations and known-ancestry consistency checks, not independently labelled accuracy cases',registry_snapshot_sha256=snapshot.sha256,elapsed_seconds=time.monotonic()-start,cache_statistics=statistics()))
 write('unique_match_results.json',dict(records=[r for r in rows if r['result']['status']=='UNIQUE_CANONICAL_MATCH'],id_reuse_authorized=False))
 baseline=[];coverage=[]
 for row in rows:
  r=row['result'];eq=[c['candidate_substance_id'] for c in r['candidate_results'] if c['chemical_status']=='CHEMICALLY_EQUIVALENT'];key_hits=[sid for sid,rs in r['retrieval']['routes'].items() if any(x['route']=='FULL_INCHIKEY' for x in rs)]
  indexed=set(r['retrieval']['indexed_candidate_ids']);allids=set(r['retrieval']['candidate_ids'])
  coverage.append(dict(source_concept_id=r['source_concept_id'],indexed_candidate_ids=sorted(indexed),full_key_candidates=key_hits,additional_indexed_candidates_beyond_full_key=sorted(indexed-set(key_hits)),baseline_equivalent_ids=eq,missed_equivalents_indexed=sorted(set(eq)-indexed),missed_equivalents_key_only=sorted(set(eq)-set(key_hits)),missed_equivalents_all_routes=sorted(set(eq)-allids),insufficient_candidate_records=[c['candidate_substance_id'] for c in r['candidate_results'] if c['chemical_status']=='CHEMICALLY_UNRESOLVED'],all_snapshot_records_examined=r['retrieval']['search_complete']))
  baseline.append(dict(source_concept_id=r['source_concept_id'],all_snapshot_records_examined=r['retrieval']['search_complete'],candidate_results=r['candidate_results']))
 write('exhaustive_comparison_baseline.json',dict(snapshot_sha256=snapshot.sha256,registry_records=len(snapshot.entries),comparisons=baseline,reference_scope='Same hardened comparator exhaustively applied to every stored record; retrieval-validation reference, not independent chemical truth'))
 write('retrieval_coverage.json',dict(summary=summary,groups=groups,records=coverage,duplicate_candidate_evaluations=0,route_overlap='Multiple routes deduplicated by canonical Substance ID; equivalent distinct IDs are not deduplicated',search_completeness_scope='Only this 112-record snapshot, its available molecular graphs and implemented comparison scope; chemical unresolved results remain unresolved'))
 # These two actual inputs must succeed chemically even with shared ancestry.
 required={'1049':'SUB_00000112','6323':'SUB_00000006'}
 for cid,sid in required.items():
  r=next(x['result'] for x in rows if x['group']=='SOURCE_DEPENDENT_REGISTRY_COVERAGE' and x['source_record_id']==cid)
  assert r['status']=='UNIQUE_CANONICAL_MATCH' and r['unique_matched_substance_id']==sid
  hit=next(c for c in r['candidate_results'] if c['candidate_substance_id']==sid);assert hit['chemical_status']=='CHEMICALLY_EQUIVALENT' and hit['independence_status']=='KNOWN_DEPENDENT'
 snapshot.assert_unchanged();print(json.dumps({'summary':summary,'groups':groups},indent=2))
if __name__=='__main__':main()
