"""Additional synthetic cross-system control through the public entry point."""
import json
from dataclasses import asdict
from pathlib import Path
import bootstrap
from evidence_adapter_contract import EvidencePackage,structural_field
from correspondence_models import IncomingConcept
from fixture_registry import create_fixture
from providers import Bridge
from unified_resolver import SubstanceResolver
H=Path(__file__).resolve().parent;B=H.parent
def main():
 permit=create_fixture(B/'canonical_registry_matching/fixtures/D01.sqlite');bridge=Bridge();rows=[]
 try:
  resolver=SubstanceResolver(official_validator=bridge.official)
  for system,record_id,graph in [('SyntheticDatabase','REC1','CCO'),('SyntheticPublication','DOC1','OCC')]:
   package=EvidencePackage(system,'ExplicitRecord',record_id,{'document':'Synthetic cardinality control, not a real database or publication'})
   claim=structural_field(package,'molecular_graph',graph,'$.molecular_graph')
   concept=IncomingConcept(system+':'+record_id,package,{'status':'ESTABLISHED','kind':'EXPLICIT_STRUCTURAL_FIELD_REFERENT','evidence_ids':[claim.evidence_id],'document':'Explicit supplied synthetic graph control'})
   record={'concept':asdict(concept),'name':'Explicit source molecular graph','source_revision':'synthetic-v1'}
   result=resolver.resolve(record,'qualified',permit,persist_association=True)
   assert result['resolution_status']=='ASSOCIATED';rows.append(result)
  assert rows[0]['canonical_substance_id']==rows[1]['canonical_substance_id']=='FIX_1'
  assert rows[0]['source_concept']['concept_id']!=rows[1]['source_concept']['concept_id']
  (H/'evaluation/synthetic_cross_source_results.json').write_text(json.dumps({'evidence_origin':'EXPLICITLY_SYNTHETIC_NOT_REAL_CROSS_SOURCE_CORROBORATION','results':rows,'same_existing_substance':True},indent=2)+'\n',encoding='utf8')
 finally:bridge.close()
if __name__=='__main__':main()
