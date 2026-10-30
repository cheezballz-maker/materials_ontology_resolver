"""Frozen offline comparison. No provider imports/queries; caches read only."""
import collections,hashlib,json,socket
from pathlib import Path
import bootstrap
from bootstrap import BASE as B
from pubchem_adapter import compound
from chebi_adapter import adapt as chebi
from evidence_adapter_contract import DIMENSIONS
from evidence_adapters import source_structure,architecture_b_claim,raw_claim,candidate_assertions
from source_claim_reconciler import reconcile
from scoped_evaluator import evaluate
from chemistry import describe

H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x):(H/'evaluation'/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def deny_network(*a,**k):raise AssertionError('NO_NETWORK_DURING_EVALUATION')

def old_evidence(source,rid,graph,name):
 claims=[]
 if graph:claims.append(source_structure(source,rid,'provided_structure',graph))
 if name:claims.append(architecture_b_claim(source,rid,'provided_name',name))
 claims.append(raw_claim(source,rid,'provided_ID','SOURCE_IDENTIFIER',rid,role_established=True))
 return claims

def summary(rows):
 good=[r for r in rows if 'after' in r];claims=[c for r in good for c in r['package']['claims']]
 structures=[c for c in claims if c['claim_role']=='STRUCTURAL_IDENTITY_ASSERTION' and c['dimension_assertions']]
 counter=collections.Counter(d for c in structures for d,a in c['dimension_assertions'].items() if a['state']!='UNKNOWN')
 observations=[o for r in good for o in r['package']['observations']]
 return dict(records=len(rows),records_successfully_adapted=len(good),errors=len(rows)-len(good),explicit_structures_successfully_qualified=len(structures),identity_dimension_assertions=dict(counter),names_with_validated_semantic_interpretations=sum(c['claim_role']=='PARTIAL_IDENTITY_ASSERTION' and bool(c['dimension_assertions']) and c['source_provenance'].get('contract_id') in ('NSC-001','NSC-002') for c in claims),identifiers_with_validated_correspondences=sum(o['kind']=='STRUCTURAL_IDENTIFIER_CONSISTENCY' and o['matches'] for o in observations),identifier_correspondence_scope='Internal Standard InChI projection only, not independent exact-form or external registry validation',independent_external_identifier_mappings=0,claims_with_established_roles=sum(c['source_provenance']['role_established'] for c in claims),claims_with_unknown_roles=sum(not c['source_provenance']['role_established'] or c['claim_role']=='UNKNOWN_ROLE' for c in claims),claim_role_counts=dict(collections.Counter(c['claim_role'] for c in claims)),unverified_synonym_associations=sum(c['claim_role'] in ('REPORTED_NAME_ASSOCIATION','UNVERIFIED_ALIAS') for c in claims),independently_established_contradictions=sum(bool(r['after']['TERMINOLOGY']['reconciliation']['incompatible_claims']) for r in good),records_structurally_comparable=sum(bool(r['after']['RECORD_STRUCTURE']['reconciliation']['supported_dimensions']) for r in good),complete_represented_graph_scope=sum(r['after']['RECORD_STRUCTURE']['reconciliation']['complete_for_requested_dimensions'] for r in good),complete_terminology_scope=sum(r['after']['TERMINOLOGY']['reconciliation']['complete_for_requested_dimensions'] for r in good),complete_incoming_concept_matches=0,records_with_unresolved_terminology_obligations=sum(r['after']['TERMINOLOGY']['reconciliation']['result']=='RECONCILIATION_UNRESOLVED' for r in good),unknown_roles_not_suppressed=sum(c['claim_role']=='UNKNOWN_ROLE' for c in claims),production_eligibility_changes=0)

def main():
 socket.create_connection=deny_network
 for n,v in read(H/'evaluation/implementation_freeze.json')['files'].items():assert sha(H/n)==v
 selection=read(H/'evaluation/source_selection_freeze.json');all_rows={};inventory={}
 for source,files in selection['sources'].items():
  records={};versions=collections.defaultdict(set);statuses=collections.Counter();raw_rows=0
  for item in files:
   p=Path(item['path']);assert sha(p)==item['sha256'];raw=read(p);statuses[raw.get('status')]+=1
   if source=='PubChem':rows=raw.get('rows',raw.get('data',{}).get('PropertyTable',{}).get('Properties',[]))
   else:rows=[raw['data']]
   for index,row in enumerate(rows):
    raw_rows+=1;rid=row.get('CID') if source=='PubChem' else row.get('chebi_accession')
    if rid is None:continue
    h=hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest();key=(str(rid),h);versions[str(rid)].add(h)
    origin=dict(payload_path=str(p),payload_sha256=item['sha256'],url=item['url'],retrieved_at=raw.get('retrieved_at'),cached_row_path=f'$.rows[{index}]' if source=='PubChem' and 'rows' in raw else f'$.data.PropertyTable.Properties[{index}]' if source=='PubChem' else '$.data')
    if key not in records:records[key]=dict(row=row,origins=[])
    records[key]['origins'].append(origin)
  inventory[source]=dict(response_files=len(files),statuses=dict(statuses),raw_rows=raw_rows,unique_record_ids=len(versions),unique_record_versions=len(records),ids_with_multiple_payload_versions=sum(len(v)>1 for v in versions.values()),selection_before_outcomes=True)
  out=[]
  for (rid,version),item in sorted(records.items()):
   row=item['row'];ctx=item['origins'][0];graph=row.get('SMILES') if source=='PubChem' else (row.get('default_structure') or {}).get('smiles');name=row.get('IUPACName') if source=='PubChem' else row.get('name')
   try:
    pkg=compound(row,ctx) if source=='PubChem' else chebi({'data':row},ctx)
    # No fallback graph is claimed as source support. A harmless comparator
    # proposal is used only to expose unknown obligations when graph is absent.
    candidate=None;baseline_error=None
    if graph:
     try:candidate=describe(graph)['smiles']
     except Exception as exc:baseline_error='SOURCE_GRAPH_INVALID_OR_UNSUPPORTED:'+str(exc)
    old=old_evidence(source,rid,graph if candidate else None,name);before=reconcile(old,candidate_assertions(candidate) if candidate else {},DIMENSIONS,source+':'+rid)
    after={scope:evaluate(pkg,candidate,DIMENSIONS,scope,enabled=True) for scope in ('RECORD_STRUCTURE','TERMINOLOGY','INCOMING_CONCEPT')}
    out.append(dict(record_id=rid,record_version_hash=version,origins=item['origins'],original_record=row,package=pkg.to_dict(),before=before,after=after,baseline_graph_error=baseline_error,comparison_candidate=candidate,comparison_not_run_without_valid_candidate=not bool(candidate),default_off=evaluate(pkg,candidate,DIMENSIONS)))
   except Exception as exc:out.append(dict(record_id=rid,error=type(exc).__name__+': '+str(exc),original_record=row,origins=item['origins']))
  all_rows[source]=out
  write('pubchem_results.json' if source=='PubChem' else 'second_source_results.json',dict(source=source,inventory=inventory[source],summary=summary(out),records=out,interpretation='Within-source represented-graph self-consistency; no independent validation of names or incoming CUMA correspondence.'))
 delta={}
 for source,rows in all_rows.items():
  good=[r for r in rows if 'after' in r];s=summary(rows)
  delta[source]=dict(records_adapted_before=len(good),records_adapted_after=len(good),valid_structural_evidence_before=sum(bool(r['before']['supported_dimensions']) for r in good),valid_structural_evidence_after=s['explicit_structures_successfully_qualified'],supported_dimension_comparisons_before=sum(len(r['before']['supported_dimensions']) for r in good),supported_dimension_comparisons_after=sum(len(r['after']['RECORD_STRUCTURE']['reconciliation']['supported_dimensions']) for r in good),complete_all_claim_question_before=sum(r['before']['complete_for_requested_dimensions'] for r in good),complete_terminology_question_after=s['complete_terminology_scope'],complete_represented_graph_scope_after=s['complete_represented_graph_scope'],represented_graph_scope_before='NOT_SEPARATELY_DECLARED_BY_V1_ADAPTER',unresolved_records_before=sum(r['before']['result']=='RECONCILIATION_UNRESOLVED' for r in good),unresolved_terminology_records_after=s['records_with_unresolved_terminology_obligations'],obligation_entries_before=sum(len(r['before']['remaining_obligations']) for r in good),obligation_entries_after_terminology=sum(len(r['after']['TERMINOLOGY']['reconciliation']['remaining_obligations']) for r in good),qualified_field_roles_after=s['claims_with_established_roles'],qualified_field_roles_before='LEGACY_ROLE_LABELS_NOT_VALIDATED_AGAINST_FIELD_CATALOG',conflicts_before=sum(r['before']['result']=='RECONCILIATION_CONFLICT' for r in good),conflicts_after=sum(r['after']['TERMINOLOGY']['reconciliation']['result']=='RECONCILIATION_CONFLICT' for r in good),diagnostic_eligibility_changes=0,production_admission='UNCHANGED',scope_caution='New graph-scope completeness is not a gain in full terminology reconciliation or chemical truth accuracy.')
 write('reconciliation_before_after.json',dict(sources=delta,new_provider_calls=0,CUMA_transfer='NOT_RUN_OPTIONAL',previous_117_record_gate='Not installed or repeated. No CUMA status or eligibility changed.'))
 write('claim_role_results.json',dict(sources={s:summary(r) for s,r in all_rows.items()},raw_SID_execution='INCOMPLETE_NO_LOCAL_RAW_SID_PAYLOADS',synonym_endpoint_execution='NO_LOCAL_PUBCHEM_SYNONYM_PAYLOADS; annotated schema controls only',qualified_chemical_review='CHEMICAL_REVIEW_PENDING'))
 print(json.dumps({'inventory':inventory,'summaries':{s:summary(r) for s,r in all_rows.items()}},indent=2))
if __name__=='__main__':main()
