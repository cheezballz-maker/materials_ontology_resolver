import unittest
from chemistry import describe
from name_interpretation import NameInterpretationEvidence, interpret_preferred
from test_evidence_retrieval import engine, Provider, row


class NameInterpretationTests(unittest.TestCase):
    def test_relative_stereo_is_partial(self):
        x,_=interpret_preferred('trans-1,2-cyclohexanediamine', {'status':'FAILURE'})
        self.assertEqual((x['status'],x['diagnostic']),('PARTIAL','NAME_UNDERSPECIFIED'))

    def test_common_name_is_not_established_by_retrieval(self):
        name='Sitagliptin';s='N[C@@H](Cc1ccccc1)C(=O)O'
        r=engine(pub=Provider({('name',name):[row(s)]}),chebi=Provider({('name',name):[row(s)]})).evaluate(name,aliases=['other specific name'])
        self.assertEqual(r['evidence']['name_interpretation']['status'],'UNKNOWN')
        self.assertNotEqual(r['status'],'AUTO_ACCEPT')

    def test_unknown_source_claim_conflict(self):
        x,_=interpret_preferred('1,1-cyclopropane cyclic sulfate',{'status':'FAILURE'},['1,1-cyclopropane cyclic sulfite'])
        self.assertEqual(x['status'],'UNKNOWN')

    def test_bad_alias_does_not_override_established_preferred(self):
        x,_=interpret_preferred('ethyl sulfate',{'status':'SUCCESS','structure':describe('CCOS(=O)(=O)O')},['ethyl sulfite'])
        self.assertEqual(x['status'],'ESTABLISHED')

    def test_unsupported_notation_is_not_underspecification(self):
        x,_=interpret_preferred('2,3,3-trimethyl-4,5-benzo compound',{'status':'FAILURE'})
        self.assertEqual((x['status'],x['diagnostic']),('UNKNOWN','NAME_NOTATION_UNSUPPORTED'))

    def test_future_evidence_not_yet_applied(self):
        evidence=NameInterpretationEvidence('Sitagliptin','C[C@H](O)C','ESTABLISHED','unverified')
        x,_=interpret_preferred('Sitagliptin',{'status':'FAILURE'},evidence=evidence)
        self.assertEqual(x['status'],'UNKNOWN');self.assertFalse(x['future_evidence_applied'])

    def test_typed_source_structure_conflicting_with_name(self):
        s='CCO';p=Provider({('InChIKey',describe(s)['inchikey']):[row(s)]})
        r=engine({'methanol':'CO'},pub=p).evaluate('methanol',structure=s)
        self.assertEqual(r['evidence']['name_interpretation']['status'],'CONFLICTING')
        self.assertNotEqual(r['status'],'AUTO_ACCEPT')

    def test_alias_cannot_establish_unknown_preferred(self):
        x,_=interpret_preferred('uninterpreted name',{'status':'FAILURE'},['ethanol'])
        self.assertEqual(x['status'],'UNKNOWN')

if __name__=='__main__':unittest.main()
