"""Provenance audit, separate from graph comparison and provider qualification."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
REQUIRED=('original_contributor','original_structure_assertion','revision_history','standardization_history','derivation_and_import_review','upstream_roots','audit_document')
def classify(left,right):
 roots=[set(p.get('upstream_roots',[])) for p in (left,right)]
 if roots[0]&roots[1] or left.get('known_derived_from_other') or right.get('known_derived_from_other'):
  return dict(status='KNOWN_DEPENDENT',shared_upstream_roots=sorted(roots[0]&roots[1]),missing=[])
 missing=[side+':'+k for side,p in [('left',left),('right',right)] for k in REQUIRED if not p.get(k)]
 if missing or not all(p.get('documented_no_shared_structural_origin') is True for p in (left,right)):
  return dict(status='INDEPENDENCE_UNESTABLISHED',missing=missing+([] if all(p.get('documented_no_shared_structural_origin') is True for p in (left,right)) else ['Documented review excluding shared structural origins']))
 return dict(status='INDEPENDENTLY_ESTABLISHED',missing=[],audit_documents=[left['audit_document'],right['audit_document']])

def main():
 saved=json.loads((H/'evaluation/pubchem_chebi_pair_results.json').read_text(encoding='utf8'));selected={'11838','24965990','30231','472335','79617'};audits=[]
 for p in saved['pairs']:
  if p['pubchem_cid'] not in selected:continue
  c=p['source_inputs'];r=c['reference_identity']['record'];s=c['source_record']['record'];structure=r['default_structure']
  # Record creators/citations are actual metadata. They do not assert who
  # supplied this specific graph or establish the graph's import history.
  left=dict(record='PubChem CID '+p['pubchem_cid'],current_structure=s.get('SMILES'),upstream_roots=[],retrieval_provenance=c['source_record_provenance'])
  right=dict(record=p['chebi_id'],record_creators=r.get('created_by'),current_structure=structure,record_modified_on=r.get('modified_on'),compound_origins=r.get('compound_origins'),citations_and_accessions=r.get('database_accessions'),name_source_attributions=r.get('names'),retrieval_provenance=c['reference_provenance'],upstream_roots=[])
  result=p['result'];audits.append(dict(pubchem_cid=p['pubchem_cid'],chebi_id=p['chebi_id'],name=r['ascii_name'],left_original_assertion_audit=left,right_original_assertion_audit=right,chemical_correspondence=result['represented_structure_comparison']['status'],source_identity_correspondence=result['source_identity_correspondence']['status'],independence=classify(left,right),qualifying_corroboration=result['corroboration_qualification'],admission=result['admission_eligibility'],precise_gap='PubChem property payload contains no original depositor SID/graph or CID standardization/revision chain. ChEBI record supplies current structure ID/creator/record modification, but no structure-level original contribution/import/revision chain linking the cited evidence to that graph. Name-source and accession citations cannot fill this gap. Cross-import/shared upstream structure cannot be ruled out.'))
 registry=json.loads((H/'evaluation/registry_candidate_results.json').read_text());dependent=[]
 for q in registry['queries']:
  for a in q['assessments']:dependent.append(dict(case_id=q['case_id'],candidate_id=a['candidate_id'],independence=a['evidence_independence'],chemistry=a['represented_structure_comparison']['status'],qualifying_corroboration=a['corroboration_qualification']))
 report=dict(proposed_positive_opportunities=len(audits),audited_for_available_provenance=len(audits),independently_established_positive_pairs=0,independence_unestablished=len(audits),candidates=audits,known_dependent_registry_cases=dependent,standard='Both original graph assertions, structural referents, contributor, version/transform/import chains and upstream origins must support a documented no-shared-structural-origin review. Different databases, keys, curator names, or copies alone are insufficient.',synthetic_audit_tests_are_real_pairs=False,new_provider_requests=0)
 for n in ('provenance_audit_results.json','corroboration_candidates.json'):(H/'evaluation'/n).write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
if __name__=='__main__':main()
