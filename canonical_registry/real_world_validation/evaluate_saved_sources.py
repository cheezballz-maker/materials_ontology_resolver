"""Reassess ten saved cross-source pairs and actual read-only registry candidates."""
import collections,hashlib,json,socket,sqlite3
from pathlib import Path
import bootstrap
from bootstrap import BASE as B
from record_inputs import load
from correspondence_assessment import assess
from candidate_identity_adapter import registry_lookup
from chemistry import describe,parse
from rdkit import Chem
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,o):(H/'evaluation'/n).write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def deny(*a,**kw):raise AssertionError('NEW_PROVIDER_QUERY_NOT_PERMITTED')
def actual_case(source,reference,key):
 s=source['package'];r=reference['package'];sg=next((c['original_value'] for c in s['claims'] if c['claim_role']=='STRUCTURAL_IDENTITY_ASSERTION' and c['dimension_assertions']),None);rg=next((c['original_value'] for c in r['claims'] if c['claim_role']=='STRUCTURAL_IDENTITY_ASSERTION' and c['dimension_assertions']),None)
 return dict(case_id=key,source_record=dict(source_name=s['source_name'],source_record_type=s['source_record_type'],record_id=s['source_record_id'],record=source['original_record'],structure=sg),reference_identity=dict(source_name=r['source_name'],source_record_type=r['source_record_type'],record_id=r['source_record_id'],record=reference['original_record'],structure=rg),source_record_provenance={**source['origins'][0],'lineage_roots':[s['source_name']+':'+s['source_record_type']+':'+s['source_record_id']]},reference_provenance={**reference['origins'][0],'lineage_roots':[r['source_name']+':'+r['source_record_type']+':'+r['source_record_id']]},source_identity_scope='DISCRETE_MOLECULAR',reference_identity_scope='DISCRETE_MOLECULAR',incoming_concept_mode='STRUCTURAL_FIELD_REFERENT')
def main():
 socket.create_connection=deny
 saved={s:{r['record_id']:r for r in read(B/'source_evidence_adapters/evaluation'/file)['records']} for s,file in [('PubChem','pubchem_results.json'),('ChEBI','second_source_results.json')]}
 old=read(B/'source_candidate_correspondence/evaluation/pubchem_chebi_results.json');pairs=[]
 # Prior results select the already requested ten pairs, never reference labels.
 for r in old['records']:
  if r['source']!='PubChem':continue
  for candidate in r['result']['candidate_ids']:
   prefix='CACHED_REFERENCE:ChEBI:'
   if not candidate.startswith(prefix):continue
   chebi_id=candidate[len(prefix):];c=actual_case(saved['PubChem'][r['record_id']],saved['ChEBI'][chebi_id],'PAIR:'+r['record_id']+':'+chebi_id);s,t=load(c);result=assess(s,t,enabled=True)
   row=dict(pubchem_cid=r['record_id'],chebi_id=chebi_id,source_inputs=c,result=result,ground_truth='NOT_ASSIGNED_FROM_PREVIOUS_RESOLVER_RESULT',accuracy_population_eligible=False)
   if r['record_id']=='636405':
    a,b=describe(c['source_record']['structure']),describe(c['reference_identity']['structure'])
    def groups(d):
     m=parse(d['smiles']);return dict(aromatic_NH=m.GetSubstructMatches(Chem.MolFromSmarts('[nH]')),aromatic_OH=m.GetSubstructMatches(Chem.MolFromSmarts('[c]-[O;H1]')))
    row['tautomer_diagnostic']=dict(source_smiles=a['smiles'],reference_smiles=b['smiles'],source_fixed_H_inchi=a['fixed_h_inchi'],reference_fixed_H_inchi=b['fixed_h_inchi'],standard_inchi_equal=a['inchi']==b['inchi'],full_inchikey_equal=a['inchikey']==b['inchikey'],source_graph_groups=groups(a),reference_graph_groups=groups(b),documentary_basis='PubChem names 6-methyl-4-oxo-1H-pyridine; ChEBI definition and curated IUPAC name specify 4-hydroxy-6-methylpyridine.',interpretation='Genuine represented N-H/carbonyl versus pyridine/O-H tautomer difference; Standard InChI mobile-H projection does not retain this distinction.',causal_attribution='Cannot establish whether original deposition, later standardization or curation caused the difference without original SID/structure history.',record_specific_exception=False)
   pairs.append(row)
 write('pubchem_chebi_pair_results.json',dict(distinct_pairs=len(pairs),chemical_counts=dict(collections.Counter(p['result']['represented_structure_comparison']['status'] for p in pairs)),source_correspondence_counts=dict(collections.Counter(p['result']['source_identity_correspondence']['status'] for p in pairs)),independence_counts=dict(collections.Counter(p['result']['evidence_independence']['status'] for p in pairs)),pairs=pairs,independent_corroborations=0,unsafe_admission_recommendations=sum(p['result']['admission_eligibility']['eligible'] for p in pairs)))
 corpus=read(H/'reference_corpus/reference_cases.json')['cases'];out=[]
 for c in corpus:
  source,_=load(c);graph=c['source_structure'];proposals=[];key=None
  if graph:
   try:key=describe(graph)['inchikey'];proposals=registry_lookup(B/'output/registry.sqlite',key)
   except Exception:pass
  results=[assess(source,p,enabled=True) for p in proposals]
  mapping={'CHEMICALLY_EQUIVALENT':'CANDIDATE_CHEMICALLY_EQUIVALENT','CHEMICALLY_DIFFERENT':'CANDIDATE_CHEMICALLY_DIFFERENT','CHEMICALLY_UNRESOLVED':'CANDIDATE_CORRESPONDENCE_UNRESOLVED'}
  out.append(dict(case_id=c['case_id'],source_id=source.evidence_package.referent_id,retrieval_status='CANDIDATE_RETRIEVED' if proposals else 'CANDIDATE_NOT_RETRIEVED',full_inchikey_lookup=key,candidate_ids=[p.candidate_substance_id for p in proposals],chemical_statuses=[mapping[r['represented_structure_comparison']['status']] for r in results],assessments=results,global_absence_established=False))
 db=sqlite3.connect((B/'output/registry.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
 try:registry_count=db.execute('SELECT COUNT(*) FROM substance_identity').fetchone()[0]
 finally:db.close()
 write('registry_candidate_results.json',dict(registry_path=str((B/'output/registry.sqlite').resolve()),connection='mode=ro',registry_substances=registry_count,cases_evaluated=len(out),case_queries=sum(r['full_inchikey_lookup'] is not None for r in out),unique_query_keys=len({r['full_inchikey_lookup'] for r in out if r['full_inchikey_lookup']}),unique_source_records=len({r['source_id'] for r in out}),cases_with_candidates=sum(bool(r['candidate_ids']) for r in out),distinct_retrieved_substances=len({i for r in out for i in r['candidate_ids']}),candidate_chemical_counts=dict(collections.Counter(v for r in out for v in r['chemical_statuses'])),queries=out,registry_writes=0))
 (H/'evaluation/registry_lookup.sql').write_text('SELECT DISTINCT substance_id\nFROM substance_identifier\nWHERE identifier_type = ? AND identifier_value = ?;\n-- Parameters: InChIKey, full source key. Narrow retrieval only; never global NO_MATCH.\n',encoding='utf8')
 print(json.dumps({'pairs':len(pairs),'pair_chemistry':dict(collections.Counter(p['result']['represented_structure_comparison']['status'] for p in pairs)),'registry_candidate_cases':sum(bool(r['candidate_ids']) for r in out)},indent=2))
if __name__=='__main__':main()
