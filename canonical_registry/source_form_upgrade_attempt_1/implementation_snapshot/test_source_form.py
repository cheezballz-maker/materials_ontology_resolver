"""Source-specificity safety regressions, with controlled provider evidence."""
import unittest
from chemistry import describe
from source_form import assess,source_claim,_lexical_variant
from test_evidence_retrieval import Provider,engine,row


class SourceFormTests(unittest.TestCase):
    def assert_gate(self,name,smiles,reason,aliases=(),primary_success=True):
        claim=dict(status='SUCCESS',structure=describe(smiles)) if primary_success else dict(status='FAILURE')
        r=assess(name,claim,list(aliases),describe(smiles))
        self.assertIn(reason,r['reason_codes'],r)
        self.assertNotEqual(r['status'],'SUPPORTED')
        return r

    def test_relative_stereo_never_selects_enantiomer(self):
        s='CC(C)(C)OC(=O)N[C@@H]1CCCC[C@H]1N'
        r=self.assert_gate('trans-N-protected-1,2-diaminocyclohexane',s,'SOURCE_STEREO_RELATIVE_ONLY')
        self.assertEqual(r['dimensions']['stereochemistry']['source'],'PARTIALLY_SPECIFIED')
        self.assertEqual(r['dimensions']['stereochemistry']['compatibility'],'OVER_SPECIFIED')

    def test_absolute_stereo_and_geometric_achiral_case(self):
        s='CC(C)(C)OC(=O)N[C@@H]1CCCC[C@H]1N';d=describe(s)
        r=assess('(1R,2R)-N-protected-1,2-diaminocyclohexane',dict(status='SUCCESS',structure=d),[],d)
        self.assertEqual(r['status'],'SUPPORTED',r)
        # E/Z source geometry can specify a unique achiral structure.
        alk='C/C=C/C';d=describe(alk)
        r=assess('trans-but-2-ene',dict(status='SUCCESS',structure=d),[],d)
        self.assertEqual(r['status'],'SUPPORTED',r)

    def test_relative_cis_and_unspecified_stereo(self):
        s='N[C@H]1CCCC[C@H]1O'
        self.assert_gate('cis-2-aminocyclohexanol',s,'SOURCE_STEREO_RELATIVE_ONLY')
        self.assert_gate('2-aminocyclohexanol',s,'SOURCE_STEREO_UNSPECIFIED')

    def test_racemate_does_not_become_enantiomer(self):
        s='N[C@H](C)C(=O)O'
        r=self.assert_gate('DL-alanine',s,'SOURCE_STEREO_ENSEMBLE')
        self.assertEqual(r['dimensions']['stereochemistry']['source'],'ENSEMBLE')

    def test_sulfate_sulfite_conflict_without_name_dictionary(self):
        s='O=S1OCC2(CC2)CO1';alias='cyclic sulfite systematic name'
        r=self.assert_gate('cyclic sulphate of substituted diol',s,'SOURCE_CONSTITUTION_CONFLICT',
                           [(alias,dict(status='SUCCESS',structure=describe(s)))],primary_success=False)
        self.assertEqual(r['status'],'CONFLICT')
        self.assertEqual(r['claims'][1]['claim_type'],'alias')
        self.assertEqual(r['claims'][1]['candidate_comparison'],'EXACT')

    def test_alias_retrieval_cannot_override_sulfate_claim(self):
        name='cyclic sulphate of a substituted diol';alias='5,7-dioxa-6-thiaspiro[2.5]octane 6-oxide'
        s='O=S1OCC2(CC2)CO1'
        p=Provider({('name',name):[row(s)],('name',alias):[row(s)]})
        r=engine({alias:s},p).evaluate(name,[alias])
        self.assertEqual(r['status'],'CONFLICT',r)
        self.assertIn('SOURCE_CONSTITUTION_CONFLICT',r['reason_codes'])
        self.assertFalse(r['evidence']['alias_decisions'][0]['accepted'])

    def test_wrong_alias_alone_is_not_a_record_veto(self):
        s='CCO';d=describe(s);other=describe('CO')
        r=assess('ethanol',dict(status='SUCCESS',structure=d),[('methanol',dict(status='SUCCESS',structure=other))],d)
        self.assertEqual(r['status'],'SUPPORTED');self.assertEqual(len(r['source_claim_conflicts']),1)
        p=Provider({('name','ethanol'):[row(s)],('name','methanol'):[row('CO')]})
        result=engine({'ethanol':s,'methanol':'CO'},p).evaluate('ethanol',['methanol'])
        self.assertEqual(result['status'],'AUTO_ACCEPT');self.assertFalse(result['evidence']['alias_decisions'][0]['accepted'])

    def test_broad_sugar_cannot_inherit_open_chain_or_anomer(self):
        open_form='O=C[C@H](O)[C@@H](O)[C@H](O)[C@H](O)CO'
        self.assert_gate('D-glucose',open_form,'SOURCE_SUGAR_FORM_UNSPECIFIED')
        self.assert_gate('D-glucopyranose',open_form,'SOURCE_ANOMER_UNSPECIFIED')
        d=describe(open_form)
        r=assess('D-glucose',dict(status='SUCCESS',structure=d),[],d,{'explicit_structure':True})
        self.assertEqual(r['status'],'SUPPORTED',r)

    def test_expanded_key_cannot_make_generic_sugar_exact(self):
        s='O=C[C@H](O)[C@@H](O)[C@H](O)[C@H](O)COP(=O)([O-])[O-].[Na+].[Na+].O.O'
        name='D-glucose 6-phosphate disodium salt dihydrate';key=describe(s)['inchikey']
        result=engine({name:s},Provider({('InChIKey',key):[row(s)]})).evaluate(name)
        self.assertEqual(result['status'],'UNRESOLVED');self.assertIn('SOURCE_SUGAR_FORM_UNSPECIFIED',result['reason_codes'])

    def test_unparsed_preferred_name_cannot_inherit_specific_alias(self):
        name='source common alcohol name';alias='ethyl alcohol';s='CCO'
        p=Provider({('name',name):[row(s)],('name',alias):[row(s)]})
        result=engine({alias:s},p).evaluate(name,[alias])
        self.assertEqual(result['status'],'UNRESOLVED')
        self.assertIn('SOURCE_PREFERRED_INTERPRETATION_UNKNOWN',result['reason_codes'])

    def test_validated_key_and_absolute_source_still_resolve(self):
        name='(R)-2-aminopropanoic acid';s='N[C@H](C)C(=O)O';key=describe(s)['inchikey']
        r=engine({name:s},Provider({('InChIKey',key):[row(s)]})).evaluate(name)
        self.assertEqual(r['status'],'AUTO_ACCEPT',r)
        self.assertEqual(r['evidence']['source_form']['dimensions']['stereochemistry']['compatibility'],'SUPPORTED')

    def test_specific_alias_is_not_promoted_when_it_is_broad_relative_name(self):
        s='N[C@H]1CCCC[C@H]1O';name='(1R,2R)-2-aminocyclohexanol';alias='trans-2-aminocyclohexanol'
        p=Provider({('name',name):[row(s)],('name',alias):[row(s)]})
        r=engine({name:s,alias:s},p).evaluate(name,[alias])
        self.assertEqual(r['status'],'AUTO_ACCEPT',r)
        self.assertFalse(r['evidence']['alias_decisions'][0]['accepted'])
        self.assertEqual(r['evidence']['alias_decisions'][0]['reason'],'ALIAS_SOURCE_SPECIFICITY_UNSUPPORTED')

    def test_claim_preserves_text_and_type(self):
        a=source_claim('  ethyl alcohol  ',dict(status='FAILURE'),'alias')
        self.assertEqual(a['text'],'  ethyl alcohol  ');self.assertEqual(a['claim_type'],'alias')

    def test_lexical_link_never_collapses_numeric_locants(self):
        self.assertTrue(_lexical_variant('ethyl-alcohol','ethyl alcohol'))
        self.assertFalse(_lexical_variant('1-23-dimethyl','12-3-dimethyl'))

    def test_single_absolute_label_does_not_cover_unrelated_centers(self):
        s='CC(C)(C)OC(=O)N[C@@H]1CCCC[C@H]1N'
        self.assert_gate('(1R)-trans-1,2-diaminocyclohexane',s,'SOURCE_STEREO_PARTIALLY_SPECIFIED')


if __name__=='__main__':unittest.main(verbosity=2)
