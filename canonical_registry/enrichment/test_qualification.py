"""Qualification controls use actual chemistry, independent of provider availability."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from canonical_registry.enrichment.workflow import ChemicalInput, Enrichment
from canonical_registry.enrichment.chemical_qualification import MolecularInputAdapter, InputAdapters, QualificationError, qualified
from canonical_registry.enrichment.chemical_qualification import ChemicalInputSourceAdapter
from canonical_registry.chemical_concept_registry.constraints import molecular
from providers import Bridge
from resolver import Resolver
from canonical_registry.substance_explorer.resolution_bridge import OfflineEvidence

class QualificationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge=Bridge()
        offline=OfflineEvidence()
        cls.local=Resolver(cls.bridge,offline,offline)
        cls.adapter=MolecularInputAdapter()
    @classmethod
    def tearDownClass(cls):
        cls.bridge.close()
    def test_equivalent_names_and_structures(self):
        graphs=[]
        for item in (ChemicalInput("water"),ChemicalInput("oxidane"),ChemicalInput("",smiles="O"),
                     ChemicalInput("",inchi="InChI=1S/H2O/h1H2")):
            graph,record=self.adapter.interpret(item,self.local,self.bridge)
            graphs.append(graph["smiles"])
            self.assertTrue(qualified(record.incoming.concept.evidence_package))
        self.assertEqual(set(graphs),{"O"})
    def test_proof_and_mutation(self):
        _,record=self.adapter.interpret(ChemicalInput("water"),self.local,self.bridge)
        pkg=record.incoming.concept.evidence_package
        self.assertTrue(qualified(deepcopy(pkg)))
        pkg.source_attributes["original_input"]["name"]="ethanol"
        self.assertFalse(qualified(pkg))
    def test_no_official_authority(self):
        class Unavailable:
            def official(self,_):return {"status":"ERROR","agrees":False}
        with self.assertRaisesRegex(QualificationError,"OFFICIAL_INCHI_NOT_CONFIRMED"):
            self.adapter.interpret(ChemicalInput("",smiles="O"),self.local,Unavailable())
    def test_contradictions_and_unsupported_meaning(self):
        for item in (ChemicalInput("water",smiles="CCO"),
                     ChemicalInput("",smiles="O",inchikey="bad"),
                     ChemicalInput("",smiles="O trailing"),
                     ChemicalInput("2-hydroxypropanoic acid"),
                     ChemicalInput("carboxylic acids"),ChemicalInput("",cas="7732-18-5")):
            with self.subTest(item=item),self.assertRaises(QualificationError):
                self.adapter.interpret(item,self.local,self.bridge)
    def test_open_and_partial_supported(self):
        for item in (ChemicalInput("butan-2-ol"),ChemicalInput("",smiles="C[C@H](O)C(O)CC")):
            graph,_=self.adapter.interpret(item,self.local,self.bridge)
            self.assertEqual(molecular(graph["smiles"])["kind"],"molecular")
    def test_adapter_configuration(self):
        adapters=InputAdapters()
        adapters.register("other",MolecularInputAdapter())
        self.assertIsInstance(adapters.get("other"),MolecularInputAdapter)
        with self.assertRaises(ValueError):adapters.register("other",MolecularInputAdapter())
    def test_existing_unified_substance_entry_point(self):
        from pathlib import Path
        from unified_resolver import SubstanceResolver
        service=SubstanceResolver(official_validator=self.bridge.official)
        service.adapters.register("chemical-input",ChemicalInputSourceAdapter(self.local,self.bridge))
        path=Path(__file__).resolve().parents[1]/"canonical_registry_matching/fixtures/D01.sqlite"
        result=service.resolve({"name":"water"},"chemical-input",path,diagnostic_verbosity="summary")
        self.assertEqual(result["resolution_status"],"NO_MATCH_IN_REGISTRY",result)
        self.assertTrue(result["admission"]["admission_eligible"])
        self.assertFalse(result["creation"]["committed"])
        conflict=service.resolve({"name":"water","smiles":"CCO"},"chemical-input",path)
        self.assertEqual(conflict["resolution_status"],"SOURCE_CONFLICT")
        self.assertIn("CONFLICTING_STRUCTURE_DIMENSIONS",conflict["reason_codes"])
        without_validator=SubstanceResolver()
        without_validator.adapters.register("chemical-input",ChemicalInputSourceAdapter(self.local,self.bridge))
        withheld=without_validator.resolve({"name":"water"},"chemical-input",path)
        self.assertFalse(withheld["admission"]["admission_eligible"])
        self.assertIn("OFFICIAL_INCHI_NOT_CONFIRMED",withheld["reason_codes"])
