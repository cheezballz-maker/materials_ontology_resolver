from contextlib import closing
from pathlib import Path
import sqlite3
import unittest
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from canonical_registry.substance_explorer.registry_access import (
    RegistryAccess, concept_datasets, snapshot_digest, substance_datasets,
)
from canonical_registry.substance_explorer.registry_search import Query, interpret
from canonical_registry.substance_explorer.tests.test_explorer import make_snapshot


class ConsolidatedViewerTests(unittest.TestCase):
    def test_development_commit_is_searchable_in_default_explorer(self):
        root = Path(__file__).resolve().parents[2]
        demo = concept_datasets()["demo"]
        with TemporaryDirectory(dir=root / "enrichment/local/test-tmp") as directory:
            path = Path(directory) / "committed.sqlite"
            make_snapshot(path, ["O"])
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("UPDATE substance_identity SET preferred_name='water'")
            original = snapshot_digest(path)
            with patch("canonical_registry.enrichment.development.open_development", return_value=(
                    SimpleNamespace(path=path), SimpleNamespace(path=demo.path))), patch.dict(
                    "os.environ", {"SUBSTANCE_EXPLORER_DB": ""}):
                substances = substance_datasets()
                self.assertEqual(next(iter(substances)), "development")
                self.assertEqual(concept_datasets()["development"].path, demo.path)
                app = AppTest.from_file(str(root / "substance_explorer/app.py"), default_timeout=30).run()
                app.text_input(key="substances-search").set_value("water")
                next(button for button in app.button if button.label == "Search").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.radio(key="substances-records").value, "SUB_00000001")
                self.assertTrue(any(h.value == "water" for h in app.subheader))
            self.assertEqual(snapshot_digest(path), original)

    def test_uninitialized_development_keeps_read_only_pilot_fallback(self):
        with patch("canonical_registry.enrichment.development.open_development", side_effect=FileNotFoundError), patch.dict(
                "os.environ", {"SUBSTANCE_EXPLORER_DB": ""}):
            self.assertEqual(next(iter(substance_datasets())), "pilot")
            self.assertNotIn("development", concept_datasets())

    def test_live_read_only_view_sees_wal_commits(self):
        from canonical_registry.substance_explorer.registry_search import Registry
        root = Path(__file__).resolve().parents[2]
        with TemporaryDirectory(dir=root / "enrichment/local/test-tmp") as directory:
            path = Path(directory) / "live.sqlite"
            make_snapshot(path, ["O"])
            with closing(sqlite3.connect(path)) as writer:
                writer.execute("PRAGMA journal_mode=WAL")
                registry = Registry(path, live=True)
                before = registry.snapshot_token()
                writer.execute("UPDATE substance_identity SET preferred_name='water'")
                writer.commit()
                self.assertTrue(registry.search(interpret("water"))[0])
                self.assertNotEqual(before, registry.snapshot_token())
                with closing(registry.connect()) as reader:
                    with self.assertRaises(sqlite3.OperationalError):
                        reader.execute("DELETE FROM substance_identity")
                with self.assertRaisesRegex(ValueError, "checkpointed"):
                    Registry(path)

    def test_read_only_candidate_lookup_and_snapshot_bound_membership(self):
        with patch.dict("os.environ", {"SUBSTANCE_EXPLORER_DB": ""}):
            substances = substance_datasets()
        concepts = concept_datasets()
        access = RegistryAccess(substances["pilot"], concepts["demo"])
        self.assertEqual(access.substances.count, 560)
        self.assertEqual(access.concepts.count, 4)
        for registry, sql in (
            (access.substances, "DELETE FROM substance_identity"),
            (access.concepts, "DELETE FROM concept"),
        ):
            with closing(registry.connect()) as db:
                with self.assertRaises(sqlite3.OperationalError):
                    db.execute(sql)
        rows, _ = access.substances.search(interpret("formula:CH3Br"))
        self.assertTrue(rows)
        self.assertTrue(all("Formula" in row["match_basis"] for row in rows))
        self.assertFalse(access.concepts.search("carboxylic acids"))
        self.assertFalse(access.concepts.search("iron oxides"))
        self.assertTrue(access.concepts.search("formula:C5H9NO4"))
        self.assertEqual(access.concepts.count, 4)
        query = Query("", "browse", "")
        for linked in (True, False):
            filtered, more = access.substances.search(query, size=2, source_linked=linked)
            self.assertEqual(len(filtered), 2)
            self.assertTrue(more)
            self.assertTrue(all(bool(access.substances.detail(r["substance_id"])["sources"]) == linked for r in filtered))
        self.assertEqual(RegistryAccess(substances["pilot"], concepts["validation"]).concepts.count, 19)

    def test_streamlit_search_and_relationship_navigation(self):
        with patch.dict("os.environ", {"SUBSTANCE_EXPLORER_DB": ""}):
            self.check_navigation()

    def check_navigation(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        app.sidebar.radio[0].set_value("Chemical Concepts").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.sidebar.selectbox)
        self.assertTrue(app.radio(key="concepts-records").options)
        self.assertFalse(app.json)
        self.assertTrue(any("unassigned stereochemistry" in h.value for h in app.subheader))
        app.text_input(key="concepts-search").set_value("iron oxides")
        next(button for button in app.button if button.label == "Search").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(any("Metal oxides" == h.value for h in app.subheader))

    def test_streamlit_substance_formula_search_opens_id_directly(self):
        with patch.dict("os.environ", {"SUBSTANCE_EXPLORER_DB": ""}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
            app.text_input(key="substances-search").set_value("CH3Br")
            app.selectbox(key="substances-field").select("Formula")
            next(button for button in app.button if button.label == "Search").click().run()
            self.assertEqual(app.radio(key="substances-records").value, "SUB_00000006")
            self.assertFalse(app.exception)
            self.assertTrue(any(h.value == "Methyl bromide" for h in app.subheader))
