import unittest
from chemistry import describe
from evidence_model import *
from test_evidence_retrieval import engine,Provider

def qualified(smiles):
    d=describe(smiles)
    return dict(SMILES=smiles,InChI=d['inchi'],InChIKey=d['inchikey'],provider='PubChem',CID=1,IUPACName='ethanol',
        provenance={'record_id':'r1','query_type':'name','query':'ethanol','query_origin':'source_preferred_name','query_status':'SUCCESS'})

class EvidenceModelTests(unittest.TestCase):
    def test_unavailable_and_no_match_neutral(self):
        self.assertEqual(availability('ERROR'),UNAVAILABLE);self.assertEqual(availability('NOT_QUERIED'),UNAVAILABLE)
        self.assertEqual(availability('SUCCESS'),NO_MATCH)
    def test_exact_independent_qualified_record(self):
        x=assess(qualified('CCO'),describe('CCO'));self.assertEqual(x['state'],CORROBORATES);self.assertTrue(qualifying_lineage(x))
    def test_genuine_vs_unproven_contradiction(self):
        r=qualified('CO');self.assertEqual(assess(r,describe('CCO'))['state'],CONTRADICTS)
        r['provenance']['query']='different name';self.assertEqual(assess(r,describe('CCO'))['state'],NON_DISCRIMINATING)
    def test_form_normalization_may_not_corroborate_or_contradict(self):
        r=qualified('C[NH3+].[Cl-]')
        self.assertEqual(assess(r,describe('CN.Cl'))['state'],NON_DISCRIMINATING)
    def test_known_source_dependence_not_independent(self):
        r=qualified('CCO');r['provenance']['source_dependence_classification']='SOURCE_DEPENDENCE_KNOWN'
        self.assertFalse(qualifying_lineage(assess(r,describe('CCO'))))
    def test_complete_name_one_independent_and_other_unavailable(self):
        for status in ('ERROR','NOT_QUERIED'):
            p=Provider({('name','ethanol'):[qualified('CCO')]});c=Provider({('name','ethanol'):{'status':status,'rows':[]}})
            r=engine({'ethanol':'CCO'},p,c).evaluate('ethanol');self.assertEqual(r['status'],'AUTO_ACCEPT')
            self.assertTrue(any(x['provider']=='PubChem' and x['state']=='CORROBORATES' for x in r['evidence']['retrieval']['provider_states']))
            self.assertTrue(any(x['provider']=='ChEBI' and x['state']=='UNAVAILABLE' for x in r['evidence']['retrieval']['provider_states']))
    def test_complete_name_one_independent_and_no_match(self):
        p=Provider({('name','ethanol'):[qualified('CCO')]})
        self.assertEqual(engine({'ethanol':'CCO'},p,Provider()).evaluate('ethanol')['status'],'AUTO_ACCEPT')
    def test_typed_source_without_external_evidence(self):
        unavailable=Provider({('name','unparsed'):{'status':'ERROR','rows':[]}})
        self.assertEqual(engine({},unavailable,unavailable).evaluate('unparsed',structure='CCO')['status'],'AUTO_ACCEPT')
    def test_partial_source_cannot_be_repaired_by_three_providers(self):
        name='trans-2-aminocyclohexanol';s='N[C@H]1CCCC[C@H]1O';p=Provider({('name',name):[qualified(s)]})
        self.assertNotEqual(engine({name:s},p,p,p).evaluate(name)['status'],'AUTO_ACCEPT')
    def test_verified_conflicting_same_source_blocks(self):
        name='ethanol';p=Provider({('name',name):[qualified('CCO'),qualified('CO')]})
        r=engine({name:'CCO'},p,Provider()).evaluate(name)
        self.assertEqual(r['status'],'UNRESOLVED');self.assertEqual(r['provider_routes'][0]['state'],PROVIDER_RECORD_AMBIGUOUS)
    def test_provider_conflict_cannot_promote_partial_source_form_to_conflict(self):
        name='D-alanine';source='N[C@@H](C)C(=O)O';other='N[C@H](C)C(=O)O'
        p=Provider({('name',name):[qualified(other)]})
        r=engine({name:source},p,Provider()).evaluate(name)
        self.assertEqual(r['status'],'UNRESOLVED')
        self.assertTrue(all(x['state']!='CONTRADICTS' for x in r['evidence_states']))

if __name__=='__main__':unittest.main()
