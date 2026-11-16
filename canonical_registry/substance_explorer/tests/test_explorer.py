"""Exercise the live pilot snapshot through the Explorer's read-only entry points."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from canonical_registry.substance_explorer.registry_search import ROOT, Registry, interpret
from canonical_registry.substance_explorer.resolution_bridge import resolve
from canonical_registry.substance_explorer.structure_display import depiction


METHYL_BROMIDE = "SUB_00000006"
WAREHOUSE_ID = "cdfcb72c-0a43-47c1-b698-109b1129622d"
WAREHOUSE_SUB = "SUB_00000113"


def make_snapshot(path, graphs):
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
        for pos, graph in enumerate(graphs, 1):
            sid = f"SUB_{pos:08}"
            db.execute("INSERT INTO substance_identity VALUES (?, ?, 'ACCEPTED')", (sid, f"Fixture {pos}"))
            if graph:
                db.execute("INSERT INTO substance_structure VALUES (?, 'SMILES', ?)", (sid, graph))


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()

    def hits(self, text, **options):
        return self.registry.search(interpret(text), **options)[0]

    def test_exact_id(self):
        [record] = self.hits(METHYL_BROMIDE.lower())
        self.assertEqual(record["substance_id"], METHYL_BROMIDE)
        self.assertEqual(record["identity_status"], "ACCEPTED")

    def test_case_insensitive_preferred_name(self):
        self.assertIn("Preferred name (exact)", self.hits("MeThYl BRomide")[0]["match_basis"])

    def test_literal_partial_name_and_bounded_pagination(self):
        query = interpret("bromo")
        first, more = self.registry.search(query)
        second = self.hits("bromo", page=1)
        self.assertTrue(more)
        self.assertEqual(len(first), 20)
        self.assertTrue({r["substance_id"] for r in first}.isdisjoint(r["substance_id"] for r in second))
        self.assertGreater(len({r["smiles"] for r in first}), 1)
        self.assertEqual(self.hits("%"), [])

    def test_validated_alias(self):
        [record] = self.hits("Bromocycloheptane")
        self.assertEqual(record["substance_id"], "SUB_00000001")
        self.assertIn("Validated alias (exact)", record["match_basis"])

    def test_qualified_identifier(self):
        self.assertEqual(self.hits("PubChemCID:6323")[0]["substance_id"], METHYL_BROMIDE)
        self.assertEqual(self.hits("InChI=1S/CH3Br/c1-2/h1H3")[0]["substance_id"], METHYL_BROMIDE)

    def test_key_retrieval_is_only_a_candidate(self):
        query = interpret("gzuxjhmpeanegy-uhfffaoysa-n")
        self.assertEqual(self.registry.search(query)[0][0]["substance_id"], METHYL_BROMIDE)
        result = resolve(self.registry.path, query)
        self.assertIsNone(result["matched_substance_id"])
        self.assertEqual(result["reason_codes"], ["IDENTIFIER_RETRIEVAL_ONLY"])

    def test_source_reference_and_unlinked_original(self):
        [hit] = self.hits(WAREHOUSE_ID)
        self.assertEqual(hit["substance_id"], WAREHOUSE_SUB)
        self.assertEqual(hit["match_basis"], "PatSnap source reference")
        with closing(self.registry.connect()) as db:
            original = db.execute("""
                SELECT original_substance_id FROM warehouse_pilot p
                WHERE NOT EXISTS(SELECT 1 FROM source_concept c JOIN current_exact_association a USING(concept_id)
                  WHERE c.source_system='PatSnapWarehouse' AND c.source_record_id=p.original_substance_id)
                LIMIT 1
            """).fetchone()[0]
        self.assertEqual(self.hits(original), [])
        self.assertEqual(self.registry.source_record(original)["original_substance_id"], original)

    def test_detail_separates_labels_and_loads_large_audit_on_demand(self):
        record = self.registry.detail(WAREHOUSE_SUB)
        [source] = record["sources"]
        self.assertEqual(source["source_record_id"], WAREHOUSE_ID)
        self.assertIn("substance_master_name_en", source["source_labels"])
        self.assertEqual(record["aliases"], [])
        self.assertNotIn("decision_json", source)
        event_id = source["resolution_event_id"]
        self.assertIsNone(self.registry.audit(METHYL_BROMIDE, event_id))
        audit = self.registry.audit(WAREHOUSE_SUB, event_id)
        self.assertGreater(len(audit["decision_json"]), 100_000)
        self.assertIsInstance(json.loads(audit["decision_json"]), dict)
        self.assertTrue(depiction(record["structures"][0]["structure_value"]).startswith(b"\x89PNG"))
        self.assertIsNone(depiction("C1CC"))

    def test_missing_or_invalid_file(self):
        with self.assertRaises(FileNotFoundError):
            Registry(self.registry.path.with_name("does-not-exist.sqlite"))
        with self.assertRaises(sqlite3.DatabaseError):
            Registry(Path(__file__).resolve())

    def test_read_only_even_after_disabling_query_only(self):
        with closing(self.registry.connect()) as db:
            self.assertEqual(db.execute("PRAGMA query_only").fetchone()[0], 1)
            db.execute("PRAGMA query_only=OFF")
            with self.assertRaisesRegex(sqlite3.OperationalError, "readonly"):
                db.execute("UPDATE substance_identity SET preferred_name='never written' WHERE 0")


class ResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()

    def run_resolution(self, text, path=None):
        result = resolve(path or self.registry.path, interpret(text))
        self.assertNotIn("admission", result)
        self.assertNotIn("matching_proposal", result)
        return result

    def fixture_resolution(self, smiles, graphs):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.sqlite"
            make_snapshot(path, graphs)
            return self.run_resolution("SMILES: " + smiles, path)

    def test_canonical_smiles_uses_nine_dimensions(self):
        result = self.fixture_resolution("CBr", ["CBr", "CC"])
        self.assertEqual(result["status"], "EXACT_MATCH")
        self.assertTrue(result["search_complete"])
        self.assertFalse(result["admission_assessed"])
        self.assertEqual(result["matched_substance_id"], "SUB_00000001")
        self.assertEqual(result["compared_count"], 1)
        self.assertEqual(result["accounted_count"], 2)
        self.assertEqual(len(result["comparisons"][0]["dimension_comparisons"]), 9)

    def test_invalid_smiles_including_trailing_text(self):
        for value in ("CCO arbitrary text", "CN hydrochloride", "C1CC"):
            with self.subTest(value=value):
                self.assertEqual(self.run_resolution(f"SMILES: {value}")["status"], "VALIDATION_FAILED")

    def test_isotope_difference_despite_shared_connectivity(self):
        result = self.fixture_resolution("[13CH3]Br", ["CBr"])
        self.assertEqual(result["status"], "NO_MATCH_IN_REGISTRY")
        [candidate] = result["comparisons"]
        self.assertEqual(candidate["dimension_comparisons"]["isotope"], "EXACT_INCOMPATIBLE")

    def test_complete_pilot_no_match(self):
        result = self.run_resolution("SMILES: [13CH4]")
        self.assertEqual(result["status"], "NO_MATCH_IN_REGISTRY")
        self.assertTrue(result["search_complete"])
        self.assertEqual(result["accounted_count"], self.registry.count)
        self.assertTrue(all(row["chemical_status"] == "CHEMICALLY_DIFFERENT" for row in result["comparisons"]))
        self.assertIsNone(result["matched_substance_id"])

    def test_incomplete_stereo_and_unsupported_electronic_state(self):
        for smiles, reason in (("CC(O)F", "SOURCE_STEREOCHEMISTRY_UNSPECIFIED"),
                               ("[CH3]", "ELECTRONIC_STATE_UNSUPPORTED")):
            with self.subTest(smiles=smiles):
                result = self.run_resolution("SMILES: " + smiles)
                self.assertEqual(result["status"], "UNRESOLVED")
                self.assertIn(reason, result["reason_codes"])
                self.assertFalse(result["search_complete"])

    def test_tautomer_charge_and_component_boundaries(self):
        for query, other, dimension in (
            ("O=c1cccc[nH]1", "Oc1ccccn1", "tautomer"),
            ("C[NH3+]", "CN", "protonation_charge"),
            ("CO.O", "CO", "components"),
        ):
            with self.subTest(query=query):
                result = self.fixture_resolution(query, [other, query])
                self.assertEqual(result["status"], "EXACT_MATCH")
                self.assertEqual(result["matched_substance_id"], "SUB_00000002")
                if query=="CO.O":
                    self.assertEqual(result["excluded_count"],1)
                else:
                    self.assertEqual(result["comparisons"][0]["dimension_comparisons"][dimension], "EXACT_INCOMPATIBLE")

    def test_multiple_equivalent_ids_after_twentieth_record(self):
        result = self.fixture_resolution("BrC", ["CC"] * 20 + ["CBr", "BrC"])
        self.assertEqual(result["status"], "MULTIPLE_MATCHES")
        self.assertTrue(result["search_complete"])
        self.assertEqual(result["compared_count"], 2)
        self.assertEqual(result["accounted_count"], 22)
        self.assertEqual(result["equivalent_ids"], ["SUB_00000021", "SUB_00000022"])
        self.assertIsNone(result["matched_substance_id"])

    def test_deficient_snapshot_withholds_even_a_supported_candidate(self):
        result = self.fixture_resolution("CBr", ["CBr", None])
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertTrue(result["search_complete"])
        self.assertIn("POTENTIALLY_EQUIVALENT_CANDIDATE_UNRESOLVED", result["reason_codes"])
        self.assertIsNone(result["matched_substance_id"])

    def test_unreadable_snapshot_and_timeout_are_incomplete(self):
        result = self.run_resolution("SMILES: CBr", self.registry.path.with_name("missing.sqlite"))
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertFalse(result["search_complete"])
        with patch("canonical_registry.substance_explorer.resolution_bridge.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("controlled worker", 1)):
            result = self.run_resolution("SMILES: CBr")
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertIn("RESOLUTION_TIME_LIMIT", result["reason_codes"])
        self.assertFalse(result["search_complete"])
        with patch("canonical_registry.substance_explorer.resolution_bridge.subprocess.run",
                   side_effect=subprocess.CalledProcessError(1, "controlled worker", stderr="test interruption")):
            result = self.run_resolution("SMILES: CBr")
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertIn("RESOLUTION_WORKER_FAILED", result["reason_codes"])
        self.assertFalse(result["search_complete"])

    def test_ambiguous_name(self):
        result = self.run_resolution("glutamic acid")
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertIn("SOURCE_STEREO_UNSPECIFIED", result["reason_codes"])

    def test_unresolved_free_text_and_no_lexical_match(self):
        self.assertEqual(self.registry.search(interpret("xyzzy nonsense"))[0], [])
        for name, code in (("xyzzy nonsense", "NO_VALIDATED_CANDIDATE"),
                           ("methanol", "NO_QUALIFYING_CORROBORATION")):
            with self.subTest(name=name):
                result = self.run_resolution(name)
                self.assertEqual(result["status"], "UNRESOLVED")
                self.assertIn(code, result["reason_codes"])


class AppTests(unittest.TestCase):
    def test_snapshot_change_expires_displayed_resolution(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.sqlite"
            make_snapshot(path, ["CBr"])
            with patch.dict(os.environ, {"SUBSTANCE_EXPLORER_DB": str(path)}):
                app = AppTest.from_file(
                    str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30,
                ).run()
                app.text_input[0].set_value("SMILES: BrC")
                next(b for b in app.button if b.label == "Search").click().run()
                next(b for b in app.button if b.label == "Attempt Resolution").click().run(timeout=25)
                self.assertEqual(app.session_state.result["status"], "EXACT_MATCH")
                stat = path.stat()
                os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
                app.run()
                self.assertFalse(app.exception)
                self.assertTrue(any("registry changed" in warning.value for warning in app.warning))
                self.assertFalse(any("Structure comparison" in element.value for element in app.markdown))

    def test_search_inspect_resolve_and_reset(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=200).run()
        self.assertEqual(len(app.text_input), 1)
        app.text_input[0].set_value("SMILES: BrC")
        next(b for b in app.button if b.label == "Search").click().run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.session_state["substances-selected"])
        self.assertEqual(app.radio(key="substances-records").value, METHYL_BROMIDE)
        self.assertTrue(any(h.value == "Methyl bromide" for h in app.subheader))
        next(b for b in app.button if b.label == "Attempt Resolution").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Structure comparison" in element.value for element in app.markdown))
        result = app.session_state.result
        self.assertEqual(result["matched_substance_id"], METHYL_BROMIDE)
        self.assertTrue(result["search_complete"])
        from canonical_registry.substance_explorer.registry_access import RegistryAccess, substance_datasets
        default_registry = RegistryAccess(next(iter(substance_datasets().values()))).substances
        self.assertEqual(result["accounted_count"], default_registry.count)
        self.assertTrue(any(h.value == "Methyl bromide" for h in app.subheader))
        app.text_input[0].set_value("bromo")
        next(b for b in app.button if b.label == "Search").click().run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.session_state["substances-selected"])
        self.assertFalse(any("Structure comparison" in element.value for element in app.markdown))


if __name__ == "__main__":
    unittest.main()
