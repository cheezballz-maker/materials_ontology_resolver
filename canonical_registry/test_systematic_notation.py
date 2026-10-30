import unittest
from chemistry import describe
from providers import Bridge
from name_interpretation import normalized_parse_query,interpret_preferred
from systematic_notation import source_annotations,descriptors,map_descriptors


class SystematicNotationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.bridge=Bridge()
    @classmethod
    def tearDownClass(cls):cls.bridge.close()

    def mapping(self,name):
        claim=self.bridge.opsin(name);self.assertEqual(claim['status'],'SUCCESS',claim)
        cml=self.bridge.opsin_cml(name);self.assertEqual(cml['status'],'SUCCESS',cml)
        return map_descriptors(cml['cml'],describe(claim['smiles'])['smiles'],descriptors(name))

    def test_bridgehead_stereo_locants(self):
        name='(3aR,4S,5R,6aS)-4-(tert-Butyldimethylsilyloxy)methyl-5-hydroxy-hexahydro-2H-cyclopenta[b]furan-2-one'
        x=self.mapping(name);self.assertEqual(x['status'],'MAPPED',x)
        self.assertEqual([(v['locant'],v['configuration']) for v in x['mappings']],[('3a','R'),('4','S'),('5','R'),('6a','S')])
        self.assertEqual(len({v['atom_index'] for v in x['mappings']}),4)

    def test_multiple_stereocentres_are_mapped(self):
        x=self.mapping('(2R,3S)-2-bromo-3-chloropentane')
        self.assertEqual(x['status'],'MAPPED',x);self.assertEqual(len(x['mappings']),2)
        self.assertEqual({v['configuration'] for v in x['mappings']},{'R','S'})
        self.assertEqual(len({v['atom_index'] for v in x['mappings']}),2)

    def test_multiple_alkene_locants(self):
        x=self.mapping('(2E,4Z)-hepta-2,4-diene')
        self.assertEqual(x['status'],'MAPPED',x);self.assertEqual([v['configuration'] for v in x['mappings']],['E','Z'])
        self.assertEqual(len({v['bond_index'] for v in x['mappings']}),2)

    def test_symmetric_mapping_does_not_guess(self):
        x=self.mapping('(2E,4E)-hexa-2,4-diene')
        self.assertEqual((x['status'],x['reason']),('UNKNOWN','GRAPH_MAPPING_AMBIGUOUS'))

    def test_wrong_descriptor_does_not_get_mapped(self):
        name='(2R,3S)-2-bromo-3-chloropentane';r=self.bridge.opsin(name);c=self.bridge.opsin_cml(name)
        x=map_descriptors(c['cml'],describe(r['smiles'])['smiles'],descriptors('(2S,3S)-2-bromo-3-chloropentane'))
        self.assertEqual(x['status'],'UNKNOWN')

    def test_relative_series_and_rotation_remain_separate(self):
        x=source_annotations('trans-L(+)-2,3-dihydroxy compound')
        self.assertEqual([t.lower() for t in x['relative_stereo']],['trans'])
        self.assertEqual(x['configurational_series'],['L']);self.assertEqual(x['optical_rotation'],['(+)'])
        self.assertEqual(x['descriptors'],[]);self.assertEqual(x['explicit_charges'],[])

    def test_bounded_registry_inversion(self):
        self.assertIsNone(normalized_parse_query('ethanol, 2-chloro-'))
        self.assertIsNone(normalized_parse_query('ethanol, 2-methyl-'))
        self.assertIsNone(normalized_parse_query('butanol, 2-chloro-'))

    def test_charge_counterions_ratios_are_literal(self):
        x=source_annotations('Borate(1-), trifluoro(prop-2-en-1-yl)-, potassium (1:1)')
        self.assertEqual(x['explicit_charges'],[-1]);self.assertEqual(x['counterion_terms'],['potassium']);self.assertEqual(x['component_ratios'],[[1,1]])
        self.assertEqual(source_annotations('disodium salt')['counterion_terms'],['disodium'])

    def test_unsupported_mapping_stays_unknown(self):
        name='(2R,3S)-2-bromo-3-chloropentane';r=self.bridge.opsin(name);r['structure']=describe(r['smiles'])
        x,_=interpret_preferred(name,r,cml_result={'status':'FAILURE'})
        self.assertEqual((x['status'],x['diagnostic']),('UNKNOWN','NAME_NOTATION_UNSUPPORTED'))

    def test_relative_stereo_is_not_absolute(self):
        x,_=interpret_preferred('trans-1,2-cyclohexanediamine',{'status':'FAILURE'})
        self.assertEqual(x['status'],'PARTIAL')

if __name__=='__main__':unittest.main()
