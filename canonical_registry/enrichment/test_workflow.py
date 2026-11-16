"""Workflow and UI integration controls for concept commits and write isolation."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json
import unittest
import uuid

from canonical_registry.enrichment.development import DEFAULT_DB, file_digest
from canonical_registry.enrichment.workflow import ChemicalInput, Enrichment, _packet, read_inputs
from canonical_registry.chemical_concept_registry.registry import FIXTURES, initialize
from fixture_registry import validate_path
from streamlit.testing.v1 import AppTest


class EnrichmentTests(unittest.TestCase):
    def setUp(self):
        self.path = FIXTURES / f"enrichment_test_{uuid.uuid4().hex}.sqlite"
        self.concepts = initialize(self.path)
        self.store = SimpleNamespace(path=DEFAULT_DB), self.concepts

    def tearDown(self):
        self.path.unlink()

    def engine(self):
        with patch("canonical_registry.enrichment.workflow.open_development", return_value=self.store):
            return Enrichment()

    def test_input_and_protected_path(self):
        self.assertEqual(read_inputs("butan-2-ol\n 2-butanol ")[1].name, " 2-butanol ")
        self.assertEqual(read_inputs("name,smiles\nbutan-2-ol,CCC(C)O", csv_input=True)[0].smiles, "CCC(C)O")
        with self.assertRaises(PermissionError):
            validate_path(DEFAULT_DB)

    def test_caller_cannot_qualify_edited_provider_packet(self):
        path = Path(__file__).resolve().parents[1] / "canonical_substance_creation/examples/pubchem_creation_input.json"
        packet = json.loads(path.read_text(encoding="utf-8-sig"))
        packet["record"]["SMILES"] = "CCO"
        with self.assertRaisesRegex(ValueError, "PROVIDER_ROW_NOT_BOUND_TO_PAYLOAD"):
            _packet(packet)

    def test_batch_preview_conflict_and_reopen(self):
        items = [ChemicalInput("butan-2-ol"), ChemicalInput("butan-2-ol", smiles="CCCCO"),
                 ChemicalInput("butan-2-ol", smiles="CCC(C)O trailing"), ChemicalInput("steel")]
        baseline = file_digest(self.path)
        with self.engine() as engine:
            previews = engine.batch(items)
            self.assertEqual([p["outcome"] for p in previews],
                             ["NEW_CONCEPT_CANDIDATE", "CONFLICT", "INVALID", "OUT_OF_SCOPE"])
            self.assertEqual(file_digest(self.path), baseline)
            receipt = engine.commit(items[0], previews[0])
            self.assertEqual(receipt["outcome"], "CONCEPT_CREATED")
            self.assertEqual(engine.commit(items[1], previews[1])["outcome"], "COMMIT_NOT_ELIGIBLE")
            self.assertEqual(engine.commit(items[0], previews[0])["outcome"], "CONCEPT_IDEMPOTENT_REPLAY")
        with self.engine() as engine:
            equivalent = engine.resolve(ChemicalInput("2-butanol"))
            self.assertEqual(equivalent["outcome"], "EQUIVALENT_CONCEPT")
            self.assertEqual(equivalent["concept_id"], receipt["committed_id"])

    def test_concurrent_source_mapping_and_rollback(self):
        proposal = {"kind": "molecular", "smiles": "CCC(C)O"}
        source_key = ("TestSource", "CHEMICAL_INPUT", "R1", "a")
        with self.assertRaisesRegex(RuntimeError, "INJECTED_TRANSACTION_FAILURE"):
            self.concepts.create_or_reuse(proposal, "butan-2-ol", "failed", source_key=source_key,
                                          fail_after_insert=True)
        with closing(self.concepts.connect()) as db:
            for table in ("concept", "source_mapping", "request"):
                self.assertEqual(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0], 0)
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda key: self.concepts.create_or_reuse(
                proposal, "butan-2-ol", key, source_key=source_key), ("req1", "req2")))
        self.assertEqual({r["outcome"] for r in results}, {"CREATED", "REUSED"})
        self.assertEqual(len({r["concept_id"] for r in results}), 1)
        with self.assertRaisesRegex(ValueError, "SOURCE_CONCEPT_REASSIGNMENT_REQUIRES_REVIEW"):
            self.concepts.create_or_reuse({"kind": "molecular", "smiles": "CCCC(C)O"},
                                          "pentan-2-ol", "changed", source_key=source_key)

    def test_viewer_preview_and_explicit_commit(self):
        app = Path(__file__).resolve().parents[1] / "substance_explorer/app.py"
        initial = file_digest(self.path)
        with patch("canonical_registry.enrichment.development.open_development", return_value=self.store), \
                patch("canonical_registry.enrichment.workflow.open_development", return_value=self.store):
            viewer = AppTest.from_file(str(app), default_timeout=60).run()
            viewer.sidebar.radio[0].set_value("Resolve Chemicals").run()
            viewer.text_area[0].set_value("butan-2-ol")
            next(b for b in viewer.button if b.label == "Preview").click().run()
            self.assertFalse(viewer.exception)
            self.assertEqual(file_digest(self.path), initial)
            viewer.checkbox(key="commit-1-0").check()
            next(b for b in viewer.button if b.label == "Commit selected to development").click().run()
            self.assertFalse(viewer.exception)
        self.assertEqual(self.concepts.search("butan-2-ol"), ["CC_00000001"])


if __name__ == "__main__":
    unittest.main()
