import copy,json,unittest
from pathlib import Path
import bootstrap
from evidence_adapter_contract import *
from pubchem_adapter import compound,substance,synonym_response
from scoped_evaluator import evaluate
from semantic_bridges import interpret
from control_adapter import adapt
from chemistry import describe

class AdapterTests(unittest.TestCase):
 def context(self,domain='compound'):
  return dict(url=f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/{domain}/cid/1/property/SMILES,InChI,InChIKey,IUPACName/JSON',payload_path='synthetic:explicit-test-fixture',payload_sha256='synthetic-hash')
 def row(self,s='CCO',name='ethanol'):
  d=describe(s);return dict(CID=1,SMILES=s,InChI=d['inchi'],InChIKey=d['inchikey'],IUPACName=name)
 def test_source_record_ids_not_molecular_ids(self):
  pkg=compound(self.row(),self.context());c=pkg.claims[0]
  self.assertEqual(c.claim_role,'REFERENCE_CROSS_LINK');self.assertFalse(c.dimension_assertions);self.assertEqual(c.source_provenance['correspondence_scope'],'DATABASE_RECORD_ONLY')
 def test_default_disabled(self):self.assertFalse(evaluate(compound(self.row(),self.context()),'CCO',DIMENSIONS)['diagnostic_enabled'])
 def test_three_scopes_are_separate(self):
  pkg=compound(self.row(),self.context())
  self.assertEqual(evaluate(pkg,'CCO',['constitution'],enabled=True)['reconciliation']['result'],'RECONCILED_COMPATIBLE')
  for scope in ('TERMINOLOGY','INCOMING_CONCEPT'):self.assertEqual(evaluate(pkg,'CCO',['constitution'],scope,enabled=True)['reconciliation']['result'],'RECONCILIATION_UNRESOLVED')
 def test_fields_share_graph_lineage(self):
  pkg=compound(self.row(),self.context());g=next(c for c in pkg.claims if c.claim_role=='STRUCTURAL_IDENTITY_ASSERTION')
  for c in pkg.claims:
   if c.claim_id in ('InChI','InChIKey','IUPACName'):self.assertEqual(c.derivation_dependencies,[g.evidence_id])
  self.assertEqual(len([o for o in pkg.observations if o['kind']=='STRUCTURAL_IDENTIFIER_CONSISTENCY' and o['matches']]),2)
 def test_bad_key_not_accepted(self):
  row=self.row();row['InChIKey']='LCGLNKUTAGEVQW-UHFFFAOYSA-N';pkg=compound(row,self.context())
  self.assertEqual(evaluate(pkg,'CCO',['constitution'],enabled=True)['reconciliation']['result'],'RECONCILIATION_UNRESOLVED')
 def test_endpoint_and_provenance_required(self):
  for context in ({},dict(self.context(),url='https://example.invalid/SMILES'),dict(self.context(),payload_sha256='')):
   pkg=compound(self.row(),context);self.assertEqual(evaluate(pkg,'CCO',['constitution'],enabled=True)['reconciliation']['result'],'RECONCILIATION_UNRESOLVED')
 def test_no_fabricated_depositor_or_sid(self):
  pkg=compound(self.row(),self.context());self.assertEqual(pkg.source_attributes['SID'],'UNAVAILABLE');self.assertEqual(pkg.source_attributes['depositor_metadata'],'UNAVAILABLE_IN_PROPERTY_PAYLOAD')
 def test_synonym_endpoint_cas_unvalidated(self):
  ctx=dict(self.context(),url='https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/1/synonyms/JSON');pkg=synonym_response({'InformationList':{'Information':[{'CID':1,'Synonym':['64-17-5','ethyl alcohol']}]}},ctx)[0]
  self.assertTrue(pkg.claims[1].source_provenance['CAS_like']);self.assertFalse(pkg.claims[1].dimension_assertions);self.assertEqual(pkg.claims[1].claim_role,'REPORTED_NAME_ASSOCIATION')
  self.assertEqual(evaluate(pkg,'CCO',['constitution'],'TERMINOLOGY',enabled=True)['reconciliation']['result'],'RECONCILIATION_UNRESOLVED')
 def test_property_unknown_synonym_not_known_metadata(self):
  row=dict(self.row(),Synonyms=['supplier label']);pkg=compound(row,self.context());c=pkg.claims[-1]
  self.assertEqual(c.claim_role,'UNKNOWN_ROLE');self.assertIn('RECORD_STRUCTURE',pkg.claim_scopes[c.evidence_id]);self.assertFalse(c.source_provenance['role_established'])
 def test_sid_provenance_and_links_not_deposited_graph(self):
  payload={'PC_Substances':[{'sid':{'id':99,'version':1},'source':{'db':{'name':'synthetic-depositor','source_id':{'str':'fixture99'}}},'synonyms':['ethanol'],'compound':[{'id':{'type':1,'id':{'cid':1}}}]}]}
  ctx=dict(self.context(),url='https://pubchem.ncbi.nlm.nih.gov/rest/pug/substance/sid/99/JSON');pkg=substance(payload,ctx)[0]
  self.assertEqual(pkg.source_record_type,'SUBSTANCE');self.assertEqual(pkg.source_attributes['depositor'],'synthetic-depositor');self.assertFalse(any(c.dimension_assertions for c in pkg.claims));self.assertEqual(pkg.claims[2].original_value,1)
 def test_missing_sid_depositor_retained(self):
  ctx=dict(self.context(),url='https://pubchem.ncbi.nlm.nih.gov/rest/pug/substance/sid/99/JSON');pkg=substance({'PC_Substances':[{'sid':{'id':99}}]},ctx)[0];self.assertEqual(pkg.source_attributes['depositor'],'UNAVAILABLE')
 def test_nsc001_supported_dimension_only(self):
  pkg=EvidencePackage('test','record','1',{});c=interpret(pkg,'n','1-ethyl-1H-imidazole','$.name',candidate='CCn1ccnc1',charge=False)
  self.assertEqual(set(c.dimension_assertions),{'constitution'});self.assertEqual(c.source_provenance['contract_version'],'2.0')
  for claim in c.source_provenance['source_claims']:
   span=claim['source_span'];self.assertEqual(c.original_value[span['start']:span['end']],claim['source_text'])
 def test_nsc002_source_graph_not_candidate_copy(self):
  pkg=EvidencePackage('test','record','1',{});c=interpret(pkg,'n','1-bromo-3-chlorobenzene','$.name',candidate='Brc1ccc(Cl)cc1',charge=False)
  self.assertNotEqual(describe(c.dimension_assertions['constitution']['structures'][0])['smiles'],describe('Brc1ccc(Cl)cc1')['smiles']);self.assertEqual(c.source_provenance['candidate_correspondence']['result'],'DIFFERENT')
  self.assertEqual(evaluate(pkg,'Brc1ccc(Cl)cc1',['constitution'],'TERMINOLOGY',enabled=True)['reconciliation']['result'],'RECONCILIATION_CONFLICT')
 def test_charge_supported_and_unknown_retained(self):
  pkg=EvidencePackage('test','record','1',{});interpret(pkg,'n','1-chloro-2-nitrobenzene','$.name',candidate='Clc1ccccc1[N+](=O)[O-]')
  self.assertEqual(pkg.claims[-1].source_provenance['producer_result']['dimension_result'],'SUPPORTED');self.assertEqual(set(pkg.claims[-1].dimension_assertions),{'protonation_charge'})
  other=EvidencePackage('test','record','2',{});interpret(other,'n','nitrobenzene','$.name',candidate='c1ccccc1[N+](=O)[O-]');self.assertFalse(other.claims[-1].dimension_assertions)
 def test_unknown_charge_does_not_become_support(self):
  pkg=EvidencePackage('test','record','2',{});interpret(pkg,'n','nitrobenzene','$.name',candidate='c1ccccc1[N+](=O)[O-]');out=evaluate(pkg,'c1ccccc1[N+](=O)[O-]',['protonation_charge'],'TERMINOLOGY',enabled=True)
  self.assertEqual(out['reconciliation']['result'],'RECONCILIATION_UNRESOLVED');self.assertFalse(out['reconciliation']['supported_dimensions'])
 def test_inchi_does_not_prove_tautomer(self):
  pkg=EvidencePackage('test','record','1',{});identifier_field(pkg,'i',describe('O=c1cccc[nH]1')['inchi'],'$.inchi','InChI');self.assertEqual(set(pkg.claims[0].dimension_assertions),{'constitution'})
  self.assertEqual(evaluate(pkg,'Oc1ccccn1',['tautomer'],enabled=True)['reconciliation']['result'],'RECONCILIATION_UNRESOLVED')
 def test_validated_mapping_requires_route(self):
  pkg=EvidencePackage('test','record','1',{});validated_mapping(pkg,'i','external:1','$.id','CCO',None,independent=True);self.assertFalse(pkg.claims[0].dimension_assertions)
 def test_cycle_and_candidate_origin_never_support(self):
  for fields in ([{'kind':'structure','value':'CCO','depends_on':1},{'kind':'structure','value':'OCC','depends_on':0}],[{'kind':'name','value':'1-bromo-3-chlorobenzene','candidate_derived':True}]):
   pkg=adapt(dict(source='test',record_id='1',fields=fields),'Brc1cccc(Cl)c1');out=evaluate(pkg,'Brc1cccc(Cl)c1',['constitution'],'TERMINOLOGY',enabled=True)
   self.assertEqual(out['reconciliation']['result'],'RECONCILIATION_UNRESOLVED')
 def test_trailing_text_and_slash_roundtrip(self):
  pkg=EvidencePackage('test','record','1',{});structural_field(pkg,'s','C/C=C/C arbitrary','$.s');self.assertFalse(pkg.claims[0].dimension_assertions)
  for smiles in ('C/C=C/C','C/C=C\\C'):
   p=EvidencePackage('test','record',smiles,{});structural_field(p,'s',smiles,'$.s');self.assertEqual(p.claims[0].original_value,smiles)
  self.assertNotEqual(describe('C/C=C/C')['smiles'],describe('C/C=C\\C')['smiles'])
 def test_parent_salt_not_collapsed(self):
  pkg=EvidencePackage('test','record','1',{});structural_field(pkg,'s','CN hydrochloride','$.s');self.assertFalse(pkg.claims[0].dimension_assertions)
 def test_association_not_promoted_even_compatible_structure(self):
  pkg=EvidencePackage('test','record','1',{});structural_field(pkg,'s','CCO','$.s');c=associated_name(pkg,'alias','ethanol','$.synonym');self.assertFalse(c.source_provenance['verified_exact_alias']);self.assertEqual(pkg.to_dict()['alias_promotion'],'NOT_PERFORMED')
 def test_heavy_water_comparator_limit_is_abstention(self):
  pkg=EvidencePackage('test','record','1',{});structural_field(pkg,'s','[2H]O[2H]','$.s');self.assertEqual(evaluate(pkg,'O',['isotope'],enabled=True)['reconciliation']['result'],'RECONCILIATION_UNRESOLVED')
 def test_partial_dimension_question_preserves_other_conflicts(self):
  pkg=EvidencePackage('test','record','1',{});structural_field(pkg,'s','C[C@H](O)CC','$.s')
  self.assertEqual(evaluate(pkg,'C[C@@H](O)CC',['protonation_charge'],enabled=True)['reconciliation']['result'],'RECONCILIATION_CONFLICT')
 def test_missing_candidate_preserves_package_and_abstains(self):
  pkg=EvidencePackage('test','record','1',{});structural_field(pkg,'s','*CO','$.s');out=evaluate(pkg,None,DIMENSIONS,enabled=True)
  self.assertEqual(out['reconciliation']['result'],'RECONCILIATION_UNRESOLVED');self.assertEqual(pkg.claims[0].original_value,'*CO');self.assertIsNone(out['reconciliation']['candidate_binding'])
 def test_absent_terminology_is_not_full_reconciliation(self):
  pkg=compound({k:v for k,v in self.row().items() if k!='IUPACName'},self.context());out=evaluate(pkg,'CCO',DIMENSIONS,'TERMINOLOGY',enabled=True)
  self.assertEqual(out['reconciliation']['result'],'RECONCILIATION_UNRESOLVED')

if __name__=='__main__':unittest.main()
