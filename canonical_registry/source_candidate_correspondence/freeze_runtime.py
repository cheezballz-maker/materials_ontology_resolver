import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
def main():
 p=H/'evaluation/implementation_freeze.json'
 if p.exists():raise SystemExit('Already frozen; refuse overwrite')
 files=['bootstrap.py','isotope_comparator.py','correspondence_models.py','source_identity_qualification.py','candidate_identity_adapter.py','identity_correspondence_comparator.py','diagnostic_resolver.py','control_inputs.py','molecular_capability.py']
 p.write_text(json.dumps({'version':'1.0','phase':'AFTER_INDEPENDENT_CONTROLS_BEFORE_REAL_SOURCE_EVALUATION','files':{n:hashlib.sha256((H/n).read_bytes()).hexdigest() for n in files},'public_heldout_development_fix':'All-candidates-different aggregation now remains a bounded no-supported-set outcome even with other source unknowns; expectations unchanged.','qualified_chemical_review':'CHEMICAL_REVIEW_PENDING'},indent=2)+'\n',encoding='utf8')
 # Source selection is all previous saved records, not chosen by correspondence.
 inputs=[B/'source_evidence_adapters/evaluation/pubchem_results.json',B/'source_evidence_adapters/evaluation/second_source_results.json',B/'output/registry.sqlite']
 (H/'evaluation/real_source_selection_freeze.json').write_text(json.dumps({'selection':'All 67 cached PubChem + all 90 cached ChEBI records from the preceding adapter run, including the 20 records with no qualified graph; candidate lookup is read-only against the existing 112-Substance registry.','files':{str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},'incoming_referent':'Explicit standardized/default structural record field, not associated preferred-name or original-material identity.','provider_requests_allowed':0},indent=2)+'\n',encoding='utf8')
 print('Runtime and real-source inputs frozen')
if __name__=='__main__':main()
