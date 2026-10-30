"""Freeze runtime and dataset selection before transfer outcomes are inspected."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,x):(H/'evaluation'/name).write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def main():
 if (H/'evaluation/implementation_freeze.json').exists():raise SystemExit('Runtime already frozen')
 names=['bootstrap.py','evidence_adapter_contract.py','semantic_bridges.py','scoped_evaluator.py','pubchem_adapter.py','chebi_adapter.py','control_adapter.py','claim_role_policy.json','source_field_catalog.json']
 write('implementation_freeze.json',{'files':{n:sha(H/n) for n in names},'phase':'AFTER_CONTROLS_BEFORE_REAL_DATA_TRANSFER','known_public_holdout_failure':'H02: isotope explicit-H framework comparison conservatively UNKNOWN; benchmark unchanged'})
 sources={}
 for source,folder in [('PubChem','http_cache'),('ChEBI','chebi_cache')]:
  rows=[]
  for p in sorted((B/'fresh_blinded_evaluation/run'/folder).glob('*.json')):
   raw=json.loads(p.read_text(encoding='utf-8-sig'));url=raw.get('url','')
   if source=='PubChem':selected='pubchem.ncbi.nlm.nih.gov/rest/pug/compound/' in url
   else:selected=raw.get('status')=='SUCCESS' and isinstance(raw.get('data'),dict) and 'chebi_accession' in raw['data']
   if selected:rows.append({'path':str(p.resolve()),'sha256':sha(p),'url':url,'status':raw.get('status')})
  sources[source]=rows
 write('source_selection_freeze.json',{'selection':'All PubChem endpoint cache responses and all ChEBI full-entity responses in the same bounded fresh evaluation cache; no chemistry/outcome exclusions. Repeated identical CID/row or ChEBI accession/payload deduplicated as one record version; all retrieval origins retained.','sources':sources,'raw_SID_records':'UNAVAILABLE_IN_SELECTED_CACHE','new_resolver_provider_requests':0})
 print({k:len(v) for k,v in sources.items()})
if __name__=='__main__':main()
