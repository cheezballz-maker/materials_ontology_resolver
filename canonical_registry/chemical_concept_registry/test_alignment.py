"""Focused controls for the molecular-only canonical identity contract."""
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest
import uuid

from canonical_registry.enrichment.development import open_development
from canonical_registry.chemical_concept_registry.identity_contract import (
    classify, identity_record, migrate, preferred_label, supported_definition,
)
from canonical_registry.chemical_concept_registry.constraints import molecular, contains_substance, compare, BROADER, DISTINCT
from canonical_registry.chemical_concept_registry.registry import initialize, FIXTURES, SCHEMA
from canonical_registry.substance_explorer.registry_access import ConceptSnapshot


class AlignmentTests(unittest.TestCase):
    def setUp(self):
        self.path = FIXTURES / f"alignment_{uuid.uuid4().hex}.sqlite"
        self.registry = initialize(self.path)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_exact_requires_validated_contract(self):
        self.assertEqual(classify(validation="EXACT_IDENTITY_VALIDATED"), "EXACT_MOLECULAR_IDENTITY")
        self.assertEqual(classify(validation="PARSED"), "UNSUPPORTED_MOLECULAR_INTERPRETATION")
        self.assertEqual(classify(conflicts=True), "INVALID_OR_CONFLICTING_INPUT")

    def test_open_partial_and_conflicting_stereo(self):
        broad = molecular("CC(O)C(O)CC")
        partial = molecular("C[C@@H](O)C(O)CC")
        self.assertEqual(compare(broad, partial), BROADER)
        self.assertEqual(compare(partial, molecular("C[C@H](O)C(O)CC")), DISTINCT)
        self.assertEqual(classify(partial), "PARTIALLY_SPECIFIED_MOLECULAR_IDENTITY")

    def test_broad_terms_rejected(self):
        for family in ("carboxylic_acids", "metal_oxides", "iron_oxides"):
            proposal = {"kind": "family", "family": family}
            self.assertEqual(classify(proposal), "NONCANONICAL_BROAD_TERM")
            with self.assertRaisesRegex(ValueError, "NONCANONICAL_BROAD_TERM"):
                self.registry.create_or_reuse(proposal, family, family)

    def test_unsupported_dimensions(self):
        for graph in ("[13CH3]C(O)F", "[NH3+]C(C)C(=O)[O-]", "CC(O)F.O"):
            with self.assertRaises(ValueError):
                molecular(graph)
        self.assertEqual(classify({"kind": "molecular", "smiles": "CC(O)F",
                                   "uncertainty": "tautomer"}), "UNSUPPORTED_MOLECULAR_INTERPRETATION")

    def test_label_and_equivalent_reuse(self):
        a = self.registry.create_or_reuse({"kind": "molecular", "smiles": "CCC(C)O"}, "butan-2-ol", "a")
        b = self.registry.create_or_reuse({"kind": "molecular", "smiles": "OC(CC)C"}, "2-butanol", "b")
        self.assertEqual(a["concept_id"], b["concept_id"])
        record = self.registry.get(a["concept_id"])
        self.assertIn("unassigned stereochemistry", record["preferred_label"])
        self.assertEqual(record["identity"]["registry_type"], "ChemicalConcept")
        for label in ("(2R)-butan-2-ol", "carboxylic acids", "ethanol"):
            with self.assertRaisesRegex(ValueError, "LABEL_MEANING_NOT_EQUIVALENT"):
                self.registry.create_or_reuse({"kind": "molecular", "smiles": "CCC(C)O"}, label, label)

    def test_membership(self):
        definition = molecular("CCC(C)O")
        self.assertEqual(contains_substance(definition, "CC[C@H](C)O"), "SUPPORTED")
        self.assertEqual(contains_substance(definition, "CCC(C)O"), "UNRESOLVED")
        self.assertEqual(contains_substance({"kind": "family", "family": "carboxylic_acids"}, "CC(=O)O"), "UNRESOLVED")

    def test_legacy_migration_preserves_ids_and_audit(self):
        self.path.unlink()
        db = sqlite3.connect(self.path, isolation_level=None)
        db.executescript(SCHEMA)
        db.execute("INSERT INTO concept VALUES('CC_00000001','Metal oxides',?,CURRENT_TIMESTAMP)",
                   (json.dumps({"kind": "family", "family": "metal_oxides"}),))
        db.execute("INSERT INTO concept VALUES('CC_00000002','incorrect exact label',?,CURRENT_TIMESTAMP)",
                   (json.dumps(molecular("CCC(C)O")),))
        before = db.execute("SELECT * FROM concept").fetchall()
        migrate(db)
        migrate(db)
        self.assertEqual(before, db.execute("SELECT * FROM concept").fetchall())
        self.assertEqual(db.execute("SELECT status FROM concept_alignment ORDER BY concept_id").fetchall(),
                         [("HISTORICAL_EXCLUDED",), ("ACTIVE",)])
        self.assertFalse(db.execute("PRAGMA foreign_key_check").fetchall())
        db.close()
        snapshot = ConceptSnapshot(self.path)
        self.assertEqual(snapshot.count, 1)
        self.assertIsNone(snapshot.detail("CC_00000001"))
        self.assertNotEqual(snapshot.detail("CC_00000002")["preferred_label"], "incorrect exact label")
        self.assertEqual(snapshot.search()[0]["concept_id"], "CC_00000002")
        with self.assertRaises(KeyError):
            self.registry.get("CC_00000001")

    def test_historical_view_is_read_only(self):
        self.path.unlink()
        db = sqlite3.connect(self.path)
        db.executescript(SCHEMA)
        db.execute("INSERT INTO concept VALUES('CC_00000001','Metal oxides',?,CURRENT_TIMESTAMP)",
                   (json.dumps({"kind": "family", "family": "metal_oxides"}),))
        db.commit()
        db.close()
        before = self.path.read_bytes()
        view = ConceptSnapshot(self.path)
        self.assertEqual(view.count, 0)
        self.assertEqual(before, self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
