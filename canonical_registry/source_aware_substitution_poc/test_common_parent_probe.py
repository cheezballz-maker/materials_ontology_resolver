import copy
import json
import unittest
from pathlib import Path
from common_parent_probe import compare
from rdkit import Chem

HERE = Path(__file__).resolve().parent

class CommonParentProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {x['name']: x for x in json.loads((HERE / 'development_observations.json').read_text(encoding='utf8'))}

    def test_same_source_is_only_an_observation(self):
        for name in ('1-methyl-1H-pyrazole', '1-ethyl-1H-pyrazole', '1-methyl-1H-imidazole'):
            with self.subTest(name=name):
                result = compare(self.rows[name], self.rows[name])
                self.assertEqual(result['observation'], 'ALL_TARGETS_AGREE')
                self.assertEqual(result['operation'], 'OPERATION_UNKNOWN')

    def test_different_position_is_not_a_semantic_decision(self):
        result = compare(self.rows['1-methyl-1H-pyrazole'], self.rows['3-methyl-1H-pyrazole'])
        self.assertEqual(result['observation'], 'ALL_TARGETS_DIFFER')
        self.assertEqual(result['operation'], 'OPERATION_UNKNOWN')

    def test_unreliable_inputs_abstain(self):
        a = self.rows['1-methyl-1H-pyrazole']
        for change in ('clone', 'warning', 'span', 'bond'):
            b = copy.deepcopy(a)
            if change == 'clone': b['events'][0]['clone_activity'] = True
            elif change == 'warning': b['warnings'] = 'warning'
            elif change == 'span': b['events'][0]['locant_span_verified'] = False
            else: b['events'][0]['graph_bond_verified'] = False
            self.assertEqual(compare(a, b)['observation'], 'UNKNOWN')

    def test_incompatible_fragments_and_limits_abstain(self):
        a = self.rows['1-methyl-1H-pyrazole']
        self.assertEqual(compare(a, self.rows['1-ethyl-1H-pyrazole'])['observation'], 'UNKNOWN')
        self.assertEqual(compare(a, a, 0)['observation'], 'UNKNOWN')

    def test_isotope_and_component_changes_do_not_match(self):
        a = self.rows['1-methyl-1H-pyrazole']
        b = copy.deepcopy(a)
        b['cml'] = b['cml'].replace('id="a1" elementType="C"', 'id="a1" elementType="C" isotopeNumber="13"', 1)
        self.assertEqual(compare(a, b)['observation'], 'UNKNOWN')
        c = copy.deepcopy(a)
        c['cml'] = c['cml'].replace('</atomArray>', '<atom id="extra" elementType="Cl" formalCharge="-1"/></atomArray>', 1)
        self.assertEqual(compare(a, c)['observation'], 'UNKNOWN')

    def test_symmetric_parent_never_selects_a_convenient_mapping(self):
        # Artificial trace records exercise enumeration only; they are not
        # evidence that a real nomenclature trace is complete.
        mol = Chem.AddHs(Chem.MolFromSmiles('Cc1ccccc1'))
        Chem.Kekulize(mol, clearAromaticFlags=True)
        atoms = ''.join('<atom id="a%d" elementType="%s"/>' % (a.GetIdx(), a.GetSymbol()) for a in mol.GetAtoms())
        orders = {Chem.BondType.SINGLE: 'S', Chem.BondType.DOUBLE: 'D'}
        bonds = ''.join('<bond atomRefs2="a%d a%d" order="%s"/>' % (b.GetBeginAtomIdx(), b.GetEndAtomIdx(), orders[b.GetBondType()]) for b in mol.GetBonds())
        cml = '<cml xmlns="http://www.xml-cml.org/schema"><molecule><atomArray>' + atoms + '</atomArray><bondArray>' + bonds + '</bondArray></molecule></cml>'
        event = {'parent_atom':'a1', 'attachment_atom':'a0', 'clone_activity':False, 'graph_bond_verified':True, 'locant_span_verified':True, 'substituent_span_status':'OBSERVED_CONTIGUOUS_PARSER_TOKENS'}
        row = {'status':'SUCCESS', 'warnings':'', 'ambiguous':False, 'single_selected_parse':True, 'events':[event], 'cml':cml}
        self.assertEqual(compare(row, row)['observation'], 'SYMMETRY_AMBIGUOUS')
        self.assertEqual(compare(row, row, 1)['reason'], 'MAPPING_LIMIT')

if __name__ == '__main__': unittest.main()
