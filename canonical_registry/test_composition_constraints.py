import unittest
from chemistry import describe
from composition_constraints import extract,check
from identity_comparator import compare
from test_evidence_retrieval import engine,Provider,row

class CompositionConstraintTests(unittest.TestCase):
    def check(self,name,smiles,assertion=None):return check(extract(name,assertion),describe(smiles))
    def test_disodium_requires_two(self):
        name='compound disodium salt'
        matched=self.check(name,'[Na+].[Na+].[O-]C(=O)C');self.assertEqual(matched['status'],'UNRESOLVED');self.assertEqual(matched['checked'][0]['observed'],2)
        self.assertIn('COMPONENT_COUNT_MISMATCH',self.check(name,'[Na+].[O-]C(=O)C')['reason_codes'])
    def test_dipotassium_requires_two(self):
        name='compound dipotassium salt'
        matched=self.check(name,'[K+].[K+].[O-]C(=O)C');self.assertEqual(matched['status'],'UNRESOLVED');self.assertEqual(matched['checked'][0]['observed'],2)
        self.assertIn('COMPONENT_COUNT_MISMATCH',self.check(name,'[K+].[O-]C(=O)C')['reason_codes'])
    def test_dihydrochloride_counts_equivalents_not_proton_sites(self):
        p=extract('compound dihydrochloride');self.assertEqual(p['component_counts']['value'][0]['count'],2)
        self.assertEqual(p['formal_charges']['status'],'UNSPECIFIED')
        self.assertEqual(check(p,describe('CN.Cl.Cl'))['status'],'UNRESOLVED')
        self.assertIn('COMPONENT_COUNT_MISMATCH',check(p,describe('CN.Cl'))['reason_codes'])
    def test_ratio_requires_typed_original_component_claims(self):
        n='ethanol / methanol (1:2)';a={'source_components':[{'name':'ethanol','structure':'CCO'},{'name':'methanol','structure':'CO'}]}
        p=extract(n,a);self.assertEqual(p['component_ratios']['status'],'UNSPECIFIED');self.assertFalse(p['components']['complete'])
        self.assertEqual(check(p,describe('CCO.CO.CO'))['status'],'UNRESOLVED')
        self.assertEqual(check(p,describe('CCO.CO'))['status'],'UNRESOLVED')
        self.assertEqual(check(extract(n),describe('CCO.CO.CO'))['status'],'UNRESOLVED')
    def test_ionic_pair_preserves_explicit_graph_and_charges(self):
        n='methylammonium chloride';p=extract(n,source_structure=describe('C[NH3+].[Cl-]'))
        self.assertEqual(check(p,describe('C[NH3+].[Cl-]'))['status'],'SUPPORTED')
        self.assertEqual(check(p,describe('CN.Cl'))['status'],'CONFLICT')
    def test_explicit_charged_name_recorded_without_inference(self):
        p=extract('borate(1-), potassium (1:1)');self.assertEqual(p['formal_charges']['value'][0]['charge'],-1)
        self.assertEqual(p['component_ratios']['status'],'UNSPECIFIED')
    def test_fixed_hydrates_require_source_adduct_semantics(self):
        for prefix,n in [('mono',1),('di',2),('tri',3)]:
            name='compound '+prefix+'hydrate';a={'form_kind':'hydrate'}
            p=extract(name,a,describe('CCO'+'.O'*n));self.assertEqual((p['fixed_water_count']['status'],p['fixed_water_count']['value']),('SPECIFIED',n))
            self.assertEqual(check(p,describe('CCO'+'.O'*n))['status'],'SUPPORTED')
            self.assertEqual(extract(name)['fixed_water_count']['status'],'UNSPECIFIED')
    def test_wrong_hydrate_count_rejected(self):
        r=self.check('compound dihydrate','CCO.O',{'form_kind':'hydrate'})
        self.assertIn('FIXED_HYDRATE_COUNT_MISMATCH',r['reason_codes'])
    def test_fractional_hydrate_does_not_miscompare_formula_units(self):
        p=extract('compound dihydrochloride hemihydrate')
        r=check(p,describe('CN.CN.Cl.Cl.Cl.Cl.O'))
        self.assertEqual(r['status'],'UNRESOLVED')
        self.assertNotIn('COMPONENT_COUNT_MISMATCH',r['reason_codes'])
    def test_unnumbered_and_fractional_hydrates_abstain(self):
        for n in ['compound hydrate','compound hemihydrate','compound hydrated','compound xH2O']:
            p=extract(n);self.assertEqual(p['fixed_water_count']['status'],'UNSPECIFIED',n)
            self.assertEqual(check(p,describe('CCO.O'))['status'],'UNRESOLVED')
    def test_neutral_hcl_and_ionic_salt_not_equated(self):
        a=describe('CN.Cl');b=describe('C[NH3+].[Cl-]')
        self.assertEqual(a['inchikey'],b['inchikey']);self.assertEqual(compare(a,b)['assessment'],'DISTINCT')
    def test_added_component_rejected_when_source_component_set_complete(self):
        source=describe('CCO.CO.CO');p=extract('typed adduct',source_structure=source)
        r=check(p,describe('CCO.CO.CO.O'));self.assertIn('IDENTITY_DIMENSION_CONFLICT',r['reason_codes'])
    def test_unowned_ratio_not_inferred(self):
        self.assertEqual(extract('compound hydrochloride (1:2)')['component_ratios']['status'],'UNSPECIFIED')
        source=describe('CN.Cl.Cl');p=extract('compound hydrochloride (1:2)',source_structure=source)
        self.assertEqual(check(p,source)['status'],'UNRESOLVED')
    def test_contradictory_source_water_count_rejected(self):
        p=extract('compound dihydrate',{'form_kind':'hydrate','solvent_counts':{'water':1}})
        self.assertEqual(p['fixed_water_count']['status'],'CONFLICTING')
        self.assertEqual(check(p,describe('CCO.O'))['status'],'CONFLICT')
    def test_resolver_blocks_candidate_before_admission(self):
        s='CC(=O)[O-].[Na+].O';name='sodium acetate dihydrate'
        r=engine({name:s},Provider()).evaluate(name,assertion={'form_kind':'hydrate'})
        self.assertEqual(r['status'],'CONFLICT');self.assertIn('FIXED_HYDRATE_COUNT_MISMATCH',r['reason_codes'])
    def test_provider_cannot_repair_generic_hydrate(self):
        p=extract('compound hydrate');self.assertEqual(check(p,describe('CCO.O'))['status'],'UNRESOLVED')
    def test_conflicting_count_claims_abstain(self):
        p=extract('compound disodium trisodium salt');self.assertEqual(p['component_counts']['status'],'CONFLICTING')
        self.assertEqual(check(p,describe('[Na+].[Na+].CCO'))['status'],'CONFLICT')
    def test_extra_component_cannot_be_accepted_from_incomplete_source(self):
        self.assertEqual(check(extract('ethanol'),describe('CCO.O'))['status'],'UNRESOLVED')
    def test_explicit_source_graph_enforces_identity_and_hydrogens(self):
        source=describe('CN.Cl');p=extract('methylamine hydrochloride',source_structure=source)
        self.assertEqual(check(p,source)['status'],'SUPPORTED')
        self.assertEqual(check(p,describe('C[NH3+].[Cl-]'))['status'],'CONFLICT')
    def test_source_parser_cannot_hide_an_unnamed_water_component(self):
        source=describe('CCO.O.[Na+]')
        p=extract('sodium ethanol',source_structure=source,source_structure_kind='SOURCE_NAME_PARSE')
        self.assertFalse(p['components']['complete'])
        self.assertEqual(check(p,source)['status'],'UNRESOLVED')
    def test_source_parser_cannot_establish_salt_stoichiometry(self):
        source=describe('CC(=O)[O-].[Na+]')
        p=extract('sodium acetate',source_structure=source,source_structure_kind='SOURCE_NAME_PARSE')
        self.assertFalse(p['components']['complete'])
        self.assertEqual(p['components']['status'],'UNSPECIFIED')
        self.assertEqual(check(p,source)['status'],'UNRESOLVED')
    def test_provider_cannot_upgrade_hydrochloride_protonation(self):
        name='methylamine hydrochloride';s='C[NH3+].[Cl-]'
        r=engine({name:s},Provider({('name',name):[row(s)]})).evaluate(name)
        self.assertNotEqual(r['status'],'AUTO_ACCEPT')
        self.assertTrue(any(x in r['reason_codes'] for x in ('MULTICOMPONENT_SOURCE_INCOMPLETE','MULTICOMPONENT_SEMANTICS_UNKNOWN')))

if __name__=='__main__':unittest.main()
