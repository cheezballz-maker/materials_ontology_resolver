import unittest
from chemistry import describe
from evidence_model import assess,availability,qualifying_lineage,CORROBORATES,CONTRADICTS,NON_DISCRIMINATING,UNAVAILABLE
from test_evidence_retrieval import engine,Provider

def row(smiles,name='ethanol',provider='PubChem',kind='name',origin='source_preferred_name',value=None):
    d=describe(smiles)
    r=dict(provider=provider,SMILES=smiles,InChI=d['inchi'],InChIKey=d['inchikey'],CID=123,IUPACName=name,
           provenance=dict(query=value or name,query_type=kind,query_origin=origin,query_status='SUCCESS',record_id='123'))
    return r

class QualificationTests(unittest.TestCase):
    def test_exact_name_unknown_dependence(self):
        a=assess(row('CCO'),describe('CCO'));self.assertEqual(a['state'],CORROBORATES);self.assertTrue(qualifying_lineage(a))
    def test_exact_identifier(self):
        a=assess(row('CCO',kind='PubChemCID',origin='source_identifier',value='123'),describe('CCO'));self.assertEqual(a['state'],CORROBORATES)
    def test_no_fuzzy_or_manual_metadata_bypass(self):
        r=row('CCO',name='Ethanol');r['provenance']['query']='ethanol';r['evidence_qualification']={'source_claim_correspondence':'VERIFIED','form_preservation':'DOCUMENTED','represented_dimensions':['connectivity']}
        self.assertEqual(assess(r,describe('CCO'))['state'],NON_DISCRIMINATING)
    def test_tautomer_normalized(self):
        self.assertEqual(assess(row('O=c1cccc[nH]1'),describe('O=c1cccc[nH]1'))['reason'],'TAUTOMER_FORM_NOT_DISCRIMINATED')
    def test_salt_parent(self):
        self.assertEqual(assess(row('CN'),describe('C[NH3+].[Cl-]'))['reason'],'CHARGE_OR_COMPONENT_FORM_NOT_DISCRIMINATED')
    def test_stereo_mismatch(self):
        a=assess(row('C[C@@H](O)CC',name='(R)-butan-2-ol'),describe('C[C@H](O)CC'))
        self.assertEqual(a['state'],CONTRADICTS)
    def test_known_dependence_cannot_qualify(self):
        r=row('CCO');r['provenance']['source_dependence_classification']='SOURCE_DEPENDENCE_KNOWN'
        self.assertFalse(qualifying_lineage(assess(r,describe('CCO'))))
    def test_unavailable_neutral(self):self.assertEqual(availability('ERROR'),UNAVAILABLE)
    def test_inconsistent_identifier(self):
        r=row('CCO');r['InChIKey']=describe('CO')['inchikey'];self.assertEqual(assess(r,describe('CCO'))['reason'],'INVALID_OR_INCONSISTENT_PROVIDER_STRUCTURE')
    def test_key_only_is_insufficient(self):
        r=row('CO',kind='InChIKey',origin='validated_hypothesis',value=describe('CCO')['inchikey'])
        self.assertEqual(assess(r,describe('CCO'))['state'],NON_DISCRIMINATING)
    def test_complete_name_with_unavailable_other_provider(self):
        p=Provider({('name','ethanol'):[row('CCO')]})
        unavailable=Provider({('name','ethanol'):{'status':'ERROR','rows':[]}})
        result=engine({'ethanol':'CCO'},p,unavailable).evaluate('ethanol')
        self.assertEqual(result['status'],'AUTO_ACCEPT')
    def test_partial_source_cannot_be_completed_by_provider(self):
        name='trans-2-aminocyclohexanol';s='N[C@H]1CCCC[C@H]1O'
        p=Provider({('name',name):[row(s,name=name)]})
        self.assertNotEqual(engine({name:s},p,Provider()).evaluate(name)['status'],'AUTO_ACCEPT')

if __name__=='__main__':unittest.main()
