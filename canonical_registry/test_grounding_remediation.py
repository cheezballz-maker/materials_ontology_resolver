"""Independent source examples; links state the nomenclature, not tool accuracy."""
import unittest
from chemistry import describe
from composition_constraints import extract,check
from form_characterizer import interpret
from identity_comparator import compare
from name_interpretation import normalized_parse_query,interpret_preferred
from source_form import assess,_lexical_variant
from test_evidence_retrieval import engine,Provider,row
from providers import ChEBI

class GroundingRemediationTests(unittest.TestCase):
    # IUPAC P-65.6: disodium carbonate; WHO monograph: dehydroemetine dihydrochloride.
    # https://iupac.qmul.ac.uk/BlueBook/P6.html
    # https://cdn.who.int/media/docs/default-source/medicines/pharmacopoeia/omitted-monographs/dehydroemetine_dihydrochloride.pdf
    def test_independent_salt_counts_are_constraints_only(self):
        p=extract('disodium carbonate');self.assertEqual(p['component_counts']['value'][0]['count'],2)
        self.assertNotEqual(check(p,describe('[Na+].[Na+].[O-]C([O-])=O'))['status'],'SUPPORTED')
        self.assertEqual(extract('dehydroemetine dihydrochloride')['component_counts']['value'][0]['count'],2)

    # WHO lists sodium dihydrogen phosphate monohydrate (p.14).
    # https://cdn.who.int/media/docs/default-source/essential-medicines/2023-eml-expert-committee/applications-for-addition-of-new-medicines/a33_phosphorus.pdf?sfvrsn=9f401afc_2
    def test_independent_hydrate_requires_source_water_semantics(self):
        name='sodium dihydrogen phosphate monohydrate';s=describe('O.[Na+].[O-]P(=O)(O)O')
        self.assertEqual(extract(name)['fixed_water_count']['status'],'UNSPECIFIED')
        p=extract(name,{'form_kind':'hydrate'},s)
        self.assertEqual(p['fixed_water_count']['value'],1)
        self.assertEqual(check(p,s)['status'],'SUPPORTED')
        self.assertNotEqual(check(p,describe('O.O.[Na+].[O-]P(=O)(O)O'))['status'],'SUPPORTED')

    # Gold Book hydrate includes covalently hydrated chloral.
    # https://goldbook.iupac.org/terms/view/15195
    def test_covalent_hydrate_does_not_gain_disconnected_water(self):
        r=interpret(describe('OC(O)C(Cl)(Cl)Cl'),'chloral hydrate')
        self.assertIn('HYDRATION_STOICHIOMETRY_UNKNOWN',r['reason_codes'])

    # IUPAC P-14.8 uses an em dash and (1/1), not the previous slash/colon grammar.
    # https://iupac.qmul.ac.uk/BlueBook/P1.html
    def test_iupac_ratio_retained_but_not_interpreted(self):
        p=extract('ethanol—pyridine (1/1)')
        self.assertEqual(p['component_ratios']['status'],'UNSPECIFIED')
        self.assertEqual(check(p,describe('CCO.c1ccncc1'))['status'],'UNRESOLVED')

    # CAS inverted index nomenclature is real; no generic CAS grammar is installed.
    # https://web.cas.org/marketing/pdf/indexguideapp.pdf sections 104 and 108.
    def test_inversion_and_case_sensitive_descriptors_not_rewritten(self):
        self.assertIsNone(normalized_parse_query('ethanol, 2-chloro-'))
        self.assertFalse(_lexical_variant('(R)-alanine','(r)-alanine'))
        self.assertFalse(_lexical_variant('ethyl-alcohol','ethyl alcohol'))
        result,_=interpret_preferred('unparsed name',{'status':'FAILURE'},alternate_claim={'status':'SUCCESS','structure':describe('CCO')})
        self.assertEqual(result['status'],'UNKNOWN')

    def test_curated_name_correspondence_preserves_descriptor_case(self):
        p=object.__new__(ChEBI);p.max_hits=8
        def response(url):
            if 'es_search' in url:return {'status':'SUCCESS','data':{'total':1,'results':[{'_source':{'chebi_accession':'CHEBI:1'}}]}}
            return {'status':'SUCCESS','url':url,'data':{'name':'(r)-alanine','stars':3,'is_released':True,'default_structure':{'smiles':'CCO'}}}
        p.get=response
        result=p.name('(R)-alanine')
        self.assertEqual(result['rows'],[]);self.assertEqual(result['status'],'INCOMPLETE')
        self.assertEqual(result['excluded_records'][0]['reason'],'NAME_CASE_VARIANT_UNVERIFIED')

    # IUPAC P-9 and P-82 distinguish configurational series, R/S and isotope locants.
    # https://iupac.qmul.ac.uk/BlueBook/P9.html and https://iupac.qmul.ac.uk/BlueBook/P8.html
    def test_dl_does_not_supply_generic_cip_and_isotopes_preserved(self):
        d=describe('N[C@@H](C)C(=O)O')
        self.assertNotEqual(assess('D-alanine',{'status':'SUCCESS','structure':d},[],d)['status'],'SUPPORTED')
        self.assertEqual(compare(describe('CCO'),describe('[13CH3]CO'))['assessment'],'DISTINCT')

    # General independently parsed constitutional conflict, no oxyanion vocabulary.
    def test_two_interpreted_contradictory_source_claims_conflict(self):
        a=describe('CCO');b=describe('CO')
        r=assess('ethanol',{'status':'SUCCESS','structure':a},[('methanol',{'status':'SUCCESS','structure':b})],a)
        self.assertEqual(r['status'],'CONFLICT')
        self.assertIn('SOURCE_CONSTITUTION_CONFLICT',r['reason_codes'])

    def test_fixture_path_is_not_loaded_or_used(self):
        e=engine({'ethanol':'CCO'},Provider({('name','ethanol'):[row('CCO',CID=702,IUPACName='ethanol')]}))
        self.assertFalse(hasattr(e,'reviewed'))
        self.assertEqual(e.evaluate('ethanol')['status'],'AUTO_ACCEPT')

    def test_failed_source_provider_cannot_be_repaired_by_one_hit(self):
        name='ethanol';pub=Provider({('name',name):[row('CCO',CID=702,IUPACName=name)]})
        for status in ('ERROR','NOT_QUERIED'):
            with self.subTest(status=status):
                chebi=Provider({('name',name):{'status':status,'rows':[]}})
                r=engine({name:'CCO'},pub,chebi).evaluate(name)
                self.assertEqual(r['status'],'AUTO_ACCEPT')

if __name__=='__main__':unittest.main()
