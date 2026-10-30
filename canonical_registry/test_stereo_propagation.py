import unittest
import xml.etree.ElementTree as ET
from chemistry import describe
from providers import Bridge
from resolver import Resolver
from name_interpretation import interpret_preferred
from systematic_notation import descriptors,map_descriptors
from form_characterizer import interpret
from source_form import assess
from test_evidence_retrieval import Provider,row

BRIDGEHEAD='(3aR,4S,5R,6aS)-4-(tert-Butyldimethylsilyloxy)methyl-5-hydroxy-hexahydro-2H-cyclopenta[b]furan-2-one'

class StereoPropagationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.bridge=Bridge()
    @classmethod
    def tearDownClass(cls):cls.bridge.close()
    def source(self,name):
        claim=self.bridge.opsin(name);self.assertEqual(claim['status'],'SUCCESS',claim)
        claim['structure']=describe(claim['smiles']);cml=self.bridge.opsin_cml(name)
        interpretation,profile=interpret_preferred(name,claim,cml_result=cml)
        return claim,interpretation,profile,cml
    def test_bridgehead_full_source_path(self):
        claim,ni,profile,_=self.source(BRIDGEHEAD);m=profile['stereo_locant_mapping']
        self.assertEqual(m['status'],'MAPPED');self.assertEqual([x['descriptor'] for x in m['mappings']],['3aR','4S','5R','6aS'])
        self.assertTrue(all(x['verification']=='VERIFIED' for x in m['mappings']))
        f=interpret(claim['structure'],BRIDGEHEAD,source_profile=profile)
        self.assertTrue(f['source_stereo_used']);self.assertNotIn('STEREO_SOURCE_INTENT_UNSPECIFIED',f['reason_codes'])
        gate=assess(BRIDGEHEAD,claim,[],claim['structure'],source_profile=profile)
        self.assertEqual(gate['dimensions']['stereochemistry']['compatibility'],'SUPPORTED')
        d=claim['structure'];pub=Provider({('InChIKey',d['inchikey']):[row(claim['smiles'])]})
        r=Resolver(self.bridge,pub,Provider(),reviewed_evidence='no_test_runtime_evidence.json').evaluate(BRIDGEHEAD)
        self.assertNotIn('STEREO_SOURCE_INTENT_UNSPECIFIED',r['reason_codes'])
        self.assertTrue(r['evidence']['source_name_profile']['stereo_locant_mapping']['status']=='MAPPED')
    def test_unique_stereogenic_duplicate_locant(self):
        name='(1S)-1-phenyl-1,2,3,4-tetrahydroisoquinoline'
        claim,ni,p,_=self.source(name);m=p['stereo_locant_mapping']
        self.assertEqual(ni['status'],'UNKNOWN');self.assertEqual((m['status'],m['reason']),('UNKNOWN','LOCANT_SCOPE_UNRESOLVED'))
        self.assertFalse(interpret(claim['structure'],name,source_profile=p)['source_stereo_used'])
    def test_duplicate_locants_with_two_stereogenic_atoms_abstains(self):
        name='(2R,3S)-2-bromo-3-chloropentane';claim,ni,p,cml=self.source(name)
        root=ET.fromstring(cml['cml']);ns={'c':'http://www.xml-cml.org/schema'}
        atom=next(a for a in root.findall('.//c:atom',ns) if any(x.get('value')=='3' for x in a.findall('c:label',ns)))
        ET.SubElement(atom,'{http://www.xml-cml.org/schema}label',{'value':'2','dictRef':'cmlDict:locant'})
        r=map_descriptors(ET.tostring(root,encoding='unicode'),claim['structure']['smiles'],descriptors('(2R)-2-bromo-3-chloropentane'))
        self.assertEqual((r['status'],r['reason']),('UNKNOWN','LOCANT_SCOPE_UNRESOLVED'))
    def test_unestablished_local_scope_abstains_even_if_only_one_eligible(self):
        name='(1S)-1-phenyl-1,2,3,4-tetrahydroisoquinoline';claim,_,_,cml=self.source(name)
        entries=descriptors('substituent [(1S)-fragment]')
        r=map_descriptors(cml['cml'],claim['structure']['smiles'],entries)
        self.assertEqual((r['status'],r['reason']),('UNKNOWN','LOCANT_SCOPE_UNRESOLVED'))
    def test_duplicate_locant_across_components_abstains(self):
        name='(1S)-1-phenyl-1,2,3,4-tetrahydroisoquinoline';claim,_,_,cml=self.source(name)
        root=ET.fromstring(cml['cml']);ns={'c':'http://www.xml-cml.org/schema'}
        array=root.find('.//c:atomArray',ns)
        atom=ET.SubElement(array,'{http://www.xml-cml.org/schema}atom',{'id':'a9999','elementType':'Na','formalCharge':'1'})
        ET.SubElement(atom,'{http://www.xml-cml.org/schema}label',{'value':'1','dictRef':'cmlDict:locant'})
        target=describe('[Na+].'+claim['structure']['smiles'])
        r=map_descriptors(ET.tostring(root,encoding='unicode'),target['smiles'],descriptors(name))
        self.assertEqual((r['status'],r['reason']),('UNKNOWN','LOCANT_SCOPE_UNRESOLVED'))
    def test_multiple_stereocentres_all_propagated(self):
        name='(2R,3S)-2-bromo-3-chloropentane';claim,_,p,_=self.source(name)
        self.assertEqual(len(p['stereo_locant_mapping']['mappings']),2)
        self.assertTrue(interpret(claim['structure'],name,source_profile=p)['source_stereo_used'])
        p['stereo_locant_mapping']['mappings'].pop()
        self.assertFalse(interpret(claim['structure'],name,source_profile=p)['source_stereo_used'])
    def test_ez_mappings_propagate(self):
        name='(2E,4Z)-hepta-2,4-diene';claim,_,p,_=self.source(name)
        self.assertEqual([x['element'] for x in p['stereo_locant_mapping']['mappings']],['bond','bond'])
        self.assertTrue(interpret(claim['structure'],name,source_profile=p)['source_stereo_used'])
    def test_different_candidate_cannot_use_source_mapping(self):
        name='(2R,3S)-2-bromo-3-chloropentane';_,_,p,_=self.source(name)
        different=describe('CC[C@@H](Cl)[C@@H](Br)C')
        self.assertNotEqual(different['smiles'],p['stereo_locant_mapping']['source_smiles'])
        self.assertFalse(interpret(different,name,source_profile=p)['source_stereo_used'])

if __name__=='__main__':unittest.main()
