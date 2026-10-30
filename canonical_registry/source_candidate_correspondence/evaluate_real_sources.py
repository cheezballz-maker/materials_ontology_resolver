"""Frozen saved-evidence transfer. Read-only canonical lookup; no provider calls."""
import collections,hashlib,json,socket,sqlite3
from pathlib import Path
import bootstrap
from bootstrap import BASE as B
from correspondence_models import IncomingConcept,EvidencePolicy,CanonicalCandidate
from evidence_adapter_contract import EvidencePackage
from identity_evidence_models import IdentityEvidence
from candidate_identity_adapter import registry_lookup
from diagnostic_resolver import resolve_correspondence
from chemistry import describe
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def denied(*a,**kw):raise AssertionError('NEW_PROVIDER_REQUEST_NOT_PERMITTED')
def package(item):
 keys=('source_name','source_record_type','source_record_id','payload_reference','claim_scopes','observations','source_attributes','mapping_version')
 return EvidencePackage(**{k:item[k] for k in keys},claims=[IdentityEvidence(**c) for c in item['claims']])
SQL='SELECT DISTINCT substance_id FROM substance_identifier WHERE identifier_type=? AND identifier_value=?'
def main():
 socket.create_connection=denied
 for n,v in read(H/'evaluation/implementation_freeze.json')['files'].items():assert sha(H/n)==v
 for n,v in read(H/'evaluation/real_source_selection_freeze.json')['files'].items():assert sha(Path(n))==v
 out=[];previous_sources={s:read(B/'source_evidence_adapters/evaluation'/f) for s,f in [('PubChem','pubchem_results.json'),('ChEBI','second_source_results.json')]}
 pool={s:collections.defaultdict(list) for s in previous_sources}
 for source,previous in previous_sources.items():
  for row in previous['records']:
   pkg=package(row['package'])
   for c in pkg.claims:
    if c.claim_role=='STRUCTURAL_IDENTITY_ASSERTION' and c.dimension_assertions:
     d=describe(c.original_value)
     candidate=CanonicalCandidate('CACHED_REFERENCE:'+source+':'+row['record_id'],source+' explicit represented reference record '+row['record_id'],c.original_value,dict(definition_kind='SEPARATELY_RETRIEVED_REFERENCE_RECORD',document=row['origins'][0]['payload_path'],payload_reference=row['origins'][0],lineage_roots=[pkg.referent_id],independence_status='UNESTABLISHED',derived_from_source_concepts=[],upstream_structure_dependence='NOT_DOCUMENTED_BY_CACHED_FIELDS',source_metadata=pkg.source_attributes),identity_scope='DISCRETE_MOLECULAR')
     pool[source][d['inchikey']].append(candidate);break
 for source,previous in previous_sources.items():
  for row in previous['records']:
   pkg=package(row['package']);graph_claims=[c for c in pkg.claims if c.claim_role in ('STRUCTURAL_IDENTITY_ASSERTION','UNKNOWN_ROLE') and c.claim_id in ('SMILES','default_structure')]
   doc='https://pubchem.ncbi.nlm.nih.gov/docs/compounds' if source=='PubChem' else 'https://www.ebi.ac.uk/chebi/downloads'
   incoming=IncomingConcept(source+':represented-record:'+row['record_id'],pkg,dict(status='ESTABLISHED' if graph_claims else 'UNESTABLISHED',kind='EXPLICIT_STRUCTURAL_FIELD_REFERENT',evidence_ids=[c.evidence_id for c in graph_claims],document=doc,scope_note='Incoming concept is the represented structural field itself, not every name or original depositor form.'),identity_scope='DISCRETE_MOLECULAR',provenance={'document':row['origins'][0]['payload_path'],'lineage_roots':[pkg.referent_id],'source_role':'DOCUMENTED_RECORD_STRUCTURE_REFERENT'})
   d=None
   for c in graph_claims:
    if c.dimension_assertions:
     try:d=describe(c.original_value);break
     except Exception:pass
   registry_candidates=registry_lookup(B/'output/registry.sqlite',d['inchikey']) if d else []
   peer='ChEBI' if source=='PubChem' else 'PubChem';cached_candidates=pool[peer].get(d['inchikey'],[]) if d else []
   proposals=registry_candidates+cached_candidates
   result=resolve_correspondence(incoming,proposals,EvidencePolicy(enabled=True))
   out.append(dict(source=source,record_id=row['record_id'],original_payload_origins=row['origins'],qualified_source_structure=bool(d),retrieval=dict(route='READ_ONLY_REGISTRY_AND_OPPOSITE_CACHED_SOURCE_FULL_STANDARD_INCHIKEY',registry_candidates=len(registry_candidates),cached_reference_candidates=len(cached_candidates),key=d['inchikey'] if d else None,SQL=SQL,parameters=['InChIKey',d['inchikey']] if d else None,proof_of_identity=False),result=result,original_name_concept_link='NOT_ESTABLISHED_BY_THIS_RECORD_STRUCTURE_EVALUATION'))
 db=sqlite3.connect((B/'output/registry.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
 try:registry_count=db.execute('SELECT COUNT(*) FROM substance_identity').fetchone()[0]
 finally:db.close()
 def summary(records):
  pairs=[p for r in records for p in r['result']['candidate_results']]
  unknowns=collections.Counter(d for p in pairs for d,v in p['dimension_comparisons'].items() if v=='UNKNOWN')
  return dict(incoming_concepts_evaluated=len(records),records_with_qualified_source_graph=sum(r['qualified_source_structure'] for r in records),concepts_with_sufficiently_qualified_source_identity=sum(r['result']['source_identity']['state']=='SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY' for r in records),incoming_structural_field_links_established=sum(r['result']['source_identity']['binding_valid'] for r in records),records_with_candidates=sum(bool(r['result']['candidate_ids']) for r in records),candidate_comparisons=len(pairs),registry_lookup_candidates=sum(r['retrieval']['registry_candidates'] for r in records),cached_reference_candidates=sum(r['retrieval']['cached_reference_candidates'] for r in records),supported_correspondences=sum(p['correspondence_status']=='CORRESPONDENCE_SUPPORTED' for p in pairs),demonstrated_differences=sum(p['correspondence_status']=='CORRESPONDENCE_DIFFERENT' for p in pairs),unresolved_comparisons=sum(p['correspondence_status']=='CORRESPONDENCE_UNRESOLVED' for p in pairs),source_conflict_concepts=sum(r['result']['candidate_set_summary']=='SOURCE_IDENTITY_CONFLICT' for r in records),multiple_match_cases=sum(r['result']['candidate_set_summary']=='MULTIPLE_SUPPORTED_CANDIDATES' for r in records),independence_unestablished_or_dependent=sum(not p['provenance']['candidate_independence_established'] for p in pairs),source_specificity_obligations=dict(collections.Counter(v for r in records for v in r['result']['source_identity']['obligations'])),dimension_level_unknowns=dict(unknowns),set_outcomes=dict(collections.Counter(r['result']['candidate_set_summary'] for r in records)),false_supported_matches='NOT_ESTIMABLE_WITHOUT_INDEPENDENT_REAL_REFERENCE_LABELS',false_differences='NOT_ESTIMABLE_WITHOUT_INDEPENDENT_REAL_REFERENCE_LABELS',independent_real_correspondence_coverage='0 independently established pairs; no structural self-comparison counted')
 payload=dict(method='All preceding saved PubChem/ChEBI records; intended incoming referent explicitly limited to represented record graph. Matching names/formulas/CIDs/xrefs do not establish identity. Full-key retrieval is followed by source qualification and independent candidate provenance checks.',source_summaries={s:summary([r for r in out if r['source']==s]) for s in ('PubChem','ChEBI')},combined_summary=summary(out),canonical_registry_records=registry_count,records=out,new_provider_calls=0,registry_writes=0)
 (H/'evaluation/pubchem_chebi_results.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
 print(json.dumps({'sources':payload['source_summaries'],'combined':payload['combined_summary']},indent=2))
if __name__=='__main__':main()
