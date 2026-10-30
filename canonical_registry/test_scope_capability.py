"""Scope holds exercise representation capability, not ontology membership."""
import unittest
from chemistry import describe
from form_characterizer import interpret
from test_evidence_retrieval import engine

class ScopeCapabilityTests(unittest.TestCase):
    def test_ordinary_organic_and_inorganic_molecules(self):
        self.assertEqual(interpret(describe('CCO'),'ethanol')['specification'],'SPECIFIED')
        self.assertEqual(interpret(describe('O'),'water')['specification'],'SPECIFIED')
    def test_simple_ionic_compound_is_capability_hold(self):
        r=interpret(describe('[Na+].[Cl-]'),'sodium chloride',{'form_kind':'salt'})
        self.assertIn('UNSUPPORTED_MULTICOMPONENT_CAPABILITY',r['reason_codes'])
    def test_element_outside_tested_envelope_is_capability_hold(self):
        r=interpret(describe('[Fe+2]'),'iron(2+)')
        self.assertIn('UNSUPPORTED_ELEMENT_CAPABILITY',r['reason_codes'])
    def test_coordination_complex_is_capability_hold(self):
        r=engine().evaluate('copper complex',structure='N->[Cu+2]<-N')
        self.assertEqual(r['status'],'UNRESOLVED');self.assertIn('UNSUPPORTED_STRUCTURE_CAPABILITY',r['reason_codes'])
    def test_organometallic_is_capability_hold(self):
        r=interpret(describe('C[Mg]Br'),'methylmagnesium bromide')
        self.assertIn('UNSUPPORTED_COORDINATION_CAPABILITY',r['reason_codes'])
    def test_extended_structure_proxy_is_capability_not_ontology_claim(self):
        r=interpret(describe('O=[Si]=O'),'silicon dioxide')
        self.assertIn('UNSUPPORTED_DISCRETE_STRUCTURE_CAPABILITY',r['reason_codes'])

if __name__=='__main__':unittest.main()
