import sqlite3
import json
import unittest
import uuid
from contextlib import closing
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from constraints import (BROADER, DISTINCT, EQUIVALENT, NARROWER, UNRESOLVED, ProposalError,
                         compare, compare_proposals, contains_substance, molecular, validate)
from registry import BASE, FIXTURES, Registry, initialize
from rdkit import Chem

GLUTAMATE = {"kind": "molecular", "smiles": "NC(CCC(=O)O)C(=O)O",
             "stereo_state": "EXPLICITLY_UNSPECIFIED"}
GLUTAMATE_ALT = {**GLUTAMATE, "smiles": "O=C(O)CCC(N)C(=O)O"}
PARTIAL = {"kind": "molecular", "smiles": "C[C@@H](O)C(O)CC",
           "stereo_state": "EXPLICITLY_UNSPECIFIED"}


class ConceptTests(unittest.TestCase):
    def setUp(self):
        self.path = FIXTURES / ("test_" + uuid.uuid4().hex + ".sqlite")
        self.registry = initialize(self.path)

    def tearDown(self):
        for suffix in ("", "-journal", "-wal", "-shm"):
            path = Path(str(self.path) + suffix)
            if path.exists():
                self.assertEqual(path.resolve().parent, FIXTURES.resolve())
                path.unlink()

    def create(self, proposal, label, request):
        return self.registry.create_or_reuse(proposal, label, request)

    def test_creation_reuse_search_revisions_and_idempotency(self):
        a = self.create(GLUTAMATE, "NC(CCC(=O)O)C(=O)O", "a")
        b = self.create(GLUTAMATE_ALT, "O=C(O)CCC(N)C(=O)O", "b")
        self.assertEqual(a["outcome"], "CREATED")
        self.assertEqual(b["outcome"], "REUSED")
        self.assertEqual(a["concept_id"], b["concept_id"])
        self.assertEqual(self.registry.search("  NC(CCC(=O)O)C(=O)O  "), [a["concept_id"]])
        self.assertEqual(self.create(GLUTAMATE, "NC(CCC(=O)O)C(=O)O", "a")["outcome"], "IDEMPOTENT_REPLAY")
        with self.assertRaisesRegex(ValueError, "IDEMPOTENCY_CONFLICT"):
            self.create(GLUTAMATE_ALT, "O=C(O)CCC(N)C(=O)O", "a")
        with closing(self.registry.connect()) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM revision").fetchone()[0], 2)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE revision SET snapshot_json='{}'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM concept")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE concept SET definition_json='{}'")

    def test_partial_stereo_boundaries(self):
        broad = molecular("CC(O)C(O)CC")
        r = molecular(PARTIAL["smiles"])
        s = molecular("C[C@H](O)C(O)CC")
        alternate = molecular("CCC(O)[C@H](O)C")
        self.assertIn("R", [label for _, label in Chem.FindMolChiralCenters(
            Chem.MolFromSmiles(PARTIAL["smiles"]), includeUnassigned=True)])
        self.assertIn("S", [label for _, label in Chem.FindMolChiralCenters(
            Chem.MolFromSmiles("C[C@H](O)C(O)CC"), includeUnassigned=True)])
        self.assertEqual(compare(broad, r), BROADER)
        self.assertEqual(compare(r, broad), NARROWER)
        self.assertEqual(compare(r, s), DISTINCT)
        self.assertEqual(compare(r, alternate), EQUIVALENT)
        self.assertEqual(compare(molecular(GLUTAMATE["smiles"]), molecular(GLUTAMATE_ALT["smiles"])), EQUIVALENT)
        self.assertEqual(compare(molecular("C/C=C/CC(O)C"), molecular("C/C=C\\CC(O)C")), DISTINCT)

    def test_family_membership_scoping(self):
        for family in ("carboxylic_acids", "metal_oxides", "iron_oxides"):
            with self.assertRaisesRegex(ProposalError, "NONCANONICAL_BROAD_TERM"):
                validate({"kind": "family", "family": family})

    def test_unknown_exact_and_unsupported_are_withheld(self):
        for proposal in (
            {**GLUTAMATE, "stereo_state": "UNKNOWN"},
            {**GLUTAMATE, "stereo_state": "CONFLICT"},
            {**GLUTAMATE, "stereo_state": "UNSUPPORTED"},
            {**GLUTAMATE, "smiles": "N[C@@H](CCC(=O)O)C(=O)O"},
            {**GLUTAMATE, "smiles": "[13CH3]C(O)F"},
            {**GLUTAMATE, "smiles": "[NH3+]C(C)C(=O)[O-]"},
            {**GLUTAMATE, "smiles": "CC(O)F.Cl"},
            {**GLUTAMATE, "smiles": "Cl[Pt@SP1](Cl)(N)N"},
            {"kind": "family", "family": "ambiguous_oxide"},
            {"kind": "molecular", "smiles": "CC(O)F", "stereo_state": "EXPLICITLY_UNSPECIFIED", "ignored": "conflicting claim"},
        ):
            with self.subTest(proposal=proposal), self.assertRaises(ProposalError):
                validate(proposal)
        with self.assertRaisesRegex(ProposalError, "DIRECT_TO_SUBSTANCE"):
            molecular("N[C@@H](CCC(=O)O)C(=O)O")
        self.assertEqual(compare_proposals(GLUTAMATE, {**GLUTAMATE, "stereo_state": "UNKNOWN"}), UNRESOLVED)

    def test_incomplete_comparison_prevents_creation(self):
        self.create(GLUTAMATE, "NC(CCC(=O)O)C(=O)O", "a")
        with patch("registry.compare", return_value=UNRESOLVED):
            withheld = self.create(PARTIAL, PARTIAL["smiles"], "b")
        self.assertEqual(withheld["outcome"], "WITHHELD")
        with closing(self.registry.connect()) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM concept").fetchone()[0], 1)

    def test_ambiguous_label_can_retrieve_distinct_concepts(self):
        with self.assertRaisesRegex(ValueError, "LABEL_MEANING_NOT_EQUIVALENT"):
            self.create(GLUTAMATE, "Oxides", "a")

    def test_hierarchy_membership_and_source_mapping(self):
        broad = self.create({"kind": "molecular", "smiles": "CC(O)C(O)CC"}, "CC(O)C(O)CC", "b")["concept_id"]
        partial = self.create(PARTIAL, PARTIAL["smiles"], "p")["concept_id"]
        self.registry.relate(broad, partial)
        self.assertEqual(self.registry.relationships(broad)["narrower"], [partial])
        with self.assertRaises(ValueError):
            self.registry.relate(partial, broad)
        with self.assertRaisesRegex(ValueError, "LEGACY_FAMILY_SOURCE_MAPPING_DISABLED"):
            self.registry.map_source("SYNTHETIC_C", "chemical", "iron-oxides", "primary", broad)

    def test_rollback_and_concurrent_equivalent_requests(self):
        with self.assertRaisesRegex(RuntimeError, "INJECTED_TRANSACTION_FAILURE"):
            self.registry.create_or_reuse(GLUTAMATE, "NC(CCC(=O)O)C(=O)O", "fail", fail_after_insert=True)
        with closing(self.registry.connect()) as db:
            for table in ("concept", "label", "revision", "request"):
                self.assertEqual(db.execute("SELECT count(*) FROM " + table).fetchone()[0], 0)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda key: self.create(GLUTAMATE, "NC(CCC(=O)O)C(=O)O", key), ("race1", "race2")))
        self.assertEqual(sorted(x["outcome"] for x in results), ["CREATED", "REUSED"])
        self.assertEqual(len({x["concept_id"] for x in results}), 1)
        with closing(self.registry.connect()) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM concept").fetchone()[0], 1)
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertFalse(db.execute("PRAGMA foreign_key_check").fetchall())

    def test_writes_outside_fixture_directory_rejected(self):
        for source in (BASE / "output/registry.sqlite",
                       BASE / "warehouse_admission_consolidation/output/normalized_pilot.sqlite"):
            with self.subTest(source=source), self.assertRaises(PermissionError):
                Registry(source)
        with self.assertRaises(PermissionError):
            initialize(BASE / "forbidden.sqlite")


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    results = runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(ConceptTests))
    output = {"tests_run": results.testsRun, "failures": len(results.failures),
              "errors": len(results.errors), "passed": results.wasSuccessful()}
    (Path(__file__).resolve().parent / "test_results.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8")
    if not results.wasSuccessful():
        raise SystemExit(1)
