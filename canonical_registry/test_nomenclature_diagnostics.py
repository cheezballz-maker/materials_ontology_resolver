import unittest
from nomenclature_refinement.semantic_diagnostics import indicated_hydrogen_tokens

class IndicatedHydrogenDiagnosticsTests(unittest.TestCase):
    def test_two_independent_iupac_examples(self):
        for name,locant in [('1H-pyrrole','1'),('3H-pyrrole','3')]:
            with self.subTest(name=name):
                self.assertEqual(indicated_hydrogen_tokens(name)[0]['locant'],locant)
                self.assertEqual(indicated_hydrogen_tokens(name)[0]['source_tautomer_support'],'NOT_ESTABLISHED')
    def test_absent_and_added_token(self):
        self.assertEqual(indicated_hydrogen_tokens('pyrrole'),[])
        self.assertEqual(indicated_hydrogen_tokens('naphthalen-1(2H)-one')[0]['locant'],'2')
    def test_unmapped_multiple_tokens_do_not_certify_structure(self):
        observations=indicated_hydrogen_tokens('2H,5H-pyrano[2,3-b]pyran')
        self.assertEqual([x['locant'] for x in observations],['2','5'])
        self.assertTrue(all(x['grammatical_scope']=='UNVERIFIED' and x['candidate_atom']=='UNMAPPED' for x in observations))
    def test_non_token_and_unknown_input(self):
        self.assertEqual(indicated_hydrogen_tokens('H2O'),[])
        self.assertEqual(indicated_hydrogen_tokens(None),[])

if __name__=='__main__':unittest.main()
