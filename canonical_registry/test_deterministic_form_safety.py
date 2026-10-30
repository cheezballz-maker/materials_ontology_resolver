"""General identity-dimension regressions; no case-specific runtime rules."""
import unittest
from chemistry import describe
from source_form import assess,aggregate_dimensions
from test_evidence_retrieval import engine,Provider,row

def claim(smiles):return dict(status='SUCCESS',structure=describe(smiles))

class LocalFormSafetyTests(unittest.TestCase):
    def test_aggregate_difference(self):
        self.assertEqual(aggregate_dimensions({'charge':{'compatibility':'DIFFERENT'},'stereo':{'compatibility':'SUPPORTED'}}),'CONFLICT')
    def test_aggregate_unknown(self):
        self.assertEqual(aggregate_dimensions({'charge':{'compatibility':'UNKNOWN'}}),'UNRESOLVED')
        self.assertEqual(aggregate_dimensions({'charge':{'source':'UNKNOWN','compatibility':'SUPPORTED'}}),'UNRESOLVED')
    def test_equivalent_and_na(self):
        self.assertEqual(aggregate_dimensions({'a':{'compatibility':'EQUIVALENT'},'b':{'compatibility':'NOT_APPLICABLE'}}),'SUPPORTED')
    def test_protonation_conflict_generic(self):
        ion='COC(=O)c1ccc(C(=O)[O-])cc1N';acid='COC(=O)c1ccc(C(=O)O)cc1N'
        r=assess('methyl amino benzenedicarboxylate',claim(ion),[('amino methyl ester benzoic acid',claim(acid))],describe(ion))
        self.assertEqual(r['status'],'CONFLICT');self.assertIn('PROTONATION_DIFFERENT',r['reason_codes']);self.assertEqual(r['dimensions']['protonation_charge']['compatibility'],'DIFFERENT')
    def test_unverified_charge_not_implied_by_parser(self):
        s='C[NH3+]';r=assess('methylamine ion',claim(s),[],describe(s))
        self.assertNotEqual(r['status'],'SUPPORTED');self.assertIn('SOURCE_PROTONATION_SPECIFICITY_UNKNOWN',r['reason_codes'])
    def test_explicit_typed_tautomer_is_locally_eligible_end_to_end(self):
        from test_evidence_retrieval import engine
        r=engine().evaluate('typed source',structure='O=c1cccc[nH]1')
        self.assertEqual(r['evidence']['local_eligibility']['status'],'DETERMINISTIC_LOCAL_EXACT_ELIGIBLE')
    def test_unspecified_tautomer_not_implied_by_parser(self):
        s='O=c1cccc[nH]1';r=assess('a heterocyclic name',claim(s),[],describe(s))
        self.assertNotEqual(r['status'],'SUPPORTED');self.assertIn('SOURCE_TAUTOMER_SPECIFICITY_UNKNOWN',r['reason_codes'])
    def test_explicit_typed_tautomer_may_be_supported(self):
        s='O=c1cccc[nH]1';r=assess('a heterocyclic name',claim(s),[],describe(s),{'explicit_structure':True})
        self.assertEqual(r['status'],'SUPPORTED')
    def test_exact_alias_agrees(self):
        d=describe('CCO');r=assess('ethanol',claim('CCO'),[('ethanol',claim('OCC'))],d)
        self.assertEqual(r['status'],'SUPPORTED')
    def test_broad_alias_does_not_override(self):
        d=describe('C[C@@H](O)CC');r=assess('(R)-butan-2-ol',claim(d['smiles']),[('butan-2-ol',claim('CC(O)CC'))],d)
        self.assertEqual(r['status'],'SUPPORTED')
    def test_specific_conflicting_alias_blocks(self):
        d=describe('CCO');r=assess('ethanol',claim('CCO'),[('methanol',claim('CO'))],d)
        self.assertEqual(r['status'],'CONFLICT')
    def test_local_conflict_precedes_provider(self):
        p=Provider({('name','ethanol'):[row('CCO',CID=702,IUPACName='ethanol')]})
        r=engine({'ethanol':'CCO','methanol':'CO'},p).evaluate('ethanol',['methanol'])
        self.assertEqual(r['status'],'CONFLICT');self.assertEqual(p.queries,[]);self.assertEqual(r['evidence']['local_eligibility']['status'],'NOT_ELIGIBLE')
    def test_complete_name_still_needs_provider(self):
        r=engine({'ethanol':'CCO'},Provider()).evaluate('ethanol')
        self.assertEqual(r['status'],'UNRESOLVED');self.assertEqual(r['evidence']['local_eligibility']['status'],'DETERMINISTIC_LOCAL_EXACT_ELIGIBLE')
        self.assertEqual(r['reason_codes'],['NO_QUALIFYING_CORROBORATION'])

if __name__=='__main__':unittest.main()
