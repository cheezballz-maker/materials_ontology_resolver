"""Reproducible bounded evaluation in a separate persistent development workspace."""
from collections import Counter
from pathlib import Path
from statistics import median
from time import perf_counter
import json
import sqlite3
from contextlib import closing
import sys

from .development import DEFAULT_DB, file_digest, open_development
from .workflow import ChemicalInput, Enrichment

ROOT = Path(__file__).resolve().parents[1]
NAMES = [
    ChemicalInput("butan-2-ol"), ChemicalInput("2-butanol"),
    ChemicalInput("pentan-2-ol", smiles="CCCC(C)O", source_system="DemoInput", source_record_id="pentanol"),
    ChemicalInput("butan-2-ol", smiles="CCC(C)O"), ChemicalInput("butan-2-ol", smiles="CCCCO"),
    ChemicalInput("butan-2-ol", smiles="CCC(C)O garbage"),
    ChemicalInput("2-hydroxypropanoic acid"), ChemicalInput("(2S)-2-hydroxypropanoic acid"),
    ChemicalInput("(2R)-2-hydroxypropanoic acid"), ChemicalInput("but-2-ene"),
    ChemicalInput("2-chlorobutane"), ChemicalInput("2-bromobutane"),
    ChemicalInput("methanesulfonic acid"), ChemicalInput("ethanol", cas="64-17-5"),
    ChemicalInput("ethanol", ec="200-578-6"), ChemicalInput("ethanol", inci_name="methanol"),
    ChemicalInput("polyethylene"), ChemicalInput("steel"), ChemicalInput("essential oil mixture"),
    ChemicalInput("invalid chemical quuxzzz"), ChemicalInput(""), ChemicalInput("iron oxides"),
    ChemicalInput("Cetearyl Alcohol"), ChemicalInput("Acrylates Copolymer"),
    ChemicalInput("bromomethane", smiles="CBr"),
]
PACKETS = ["pubchem", "chebi"]
PROVIDER_NAME = "propan-2-yl 2-hydroxybenzoate"


def inventory(path, table):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        return {"count": db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0],
                "foreign_key_violations": len(db.execute("PRAGMA foreign_key_check").fetchall())}


def evaluate(directory, output):
    protected = [DEFAULT_DB, ROOT / "output/registry.sqlite",
                 *sorted(path for path in (ROOT / "chemical_concept_registry/fixtures").glob("*.sqlite")
                         if path.name.startswith(("demo_", "v11_eval_", "reuse_validation_", "validation_")))]
    before = {str(path.relative_to(ROOT)): file_digest(path) for path in protected}
    permit, concepts = open_development(directory, create=True)
    preview_hashes = [file_digest(permit.path), file_digest(concepts.path)]
    start = perf_counter()
    with Enrichment(directory) as engine:
        previews = engine.batch(NAMES)
        throughput = len(NAMES) / (perf_counter() - start)
        assert preview_hashes == [file_digest(permit.path), file_digest(concepts.path)]
        assert inventory(concepts.path, "concept")["count"] == 0
        assert inventory(permit.path, "substance_identity")["count"] == 560
        rows = [{"preview": preview, "commit": engine.commit(item, preview) if preview["commit_eligible"] else None}
                for item, preview in zip(NAMES, previews, strict=True)]
        assert rows[0]["commit"]["outcome"] == "CONCEPT_CREATED"
        assert rows[1]["commit"]["outcome"] == "CONCEPT_REUSED"
        assert rows[4]["preview"]["outcome"] == "CONFLICT"
        assert rows[5]["preview"]["outcome"] == "INVALID"
        assert rows[len(NAMES) - 1]["preview"]["substance_id"] == "SUB_00000006"
        assert all(not row["commit"] for row in rows[4:9])
        retries = [engine.commit(NAMES[i], previews[i]) for i in (0, 1, 2)]
        assert all(r["outcome"] == "CONCEPT_IDEMPOTENT_REPLAY" for r in retries)
        for provider in PACKETS:
            path = ROOT / "canonical_substance_creation/examples" / f"{provider}_creation_input.json"
            packet = json.loads(path.read_text(encoding="utf-8-sig"))
            item = ChemicalInput(PROVIDER_NAME)
            preview = engine.resolve(item, saved_evidence=packet)
            receipt = engine.commit(item, preview, saved_evidence=packet)
            rows.append({"provider": provider, "preview": preview, "commit": receipt})
            print(provider, preview["outcome"], receipt["outcome"], receipt.get("diagnostics"), flush=True)
        assert rows[-2]["commit"]["outcome"] == "NEW_SUBSTANCE_CREATED"
        assert rows[-1]["commit"]["outcome"] == "EXISTING_SUBSTANCE_REUSED"
        assert rows[-1]["commit"]["committed_id"] == rows[-2]["commit"]["committed_id"]
    with Enrichment(directory, max_candidates=1) as reopened:
        equivalent = reopened.resolve(NAMES[0])
        limited = reopened.resolve(ChemicalInput("methanol"))
    after = {str(path.relative_to(ROOT)): file_digest(path) for path in protected}
    assert before == after
    assert limited["outcome"] == "INCOMPLETE_SEARCH"
    assert equivalent["outcome"] == "EQUIVALENT_CONCEPT"
    commits = [row["commit"] for row in rows if row["commit"] and row["commit"]["committed_id"]]
    report = {"records": rows, "retries": retries, "reopened": equivalent, "limited_search": limited,
              "protected_sha256_before": before, "protected_sha256_after": after, "preview_files_unchanged": True,
              "substances": inventory(permit.path, "substance_identity"), "concepts": inventory(concepts.path, "concept"),
              "metrics": {"preview_outcomes": dict(Counter(row["preview"]["outcome"] for row in rows)),
                          "commit_outcomes": dict(Counter(row["outcome"] for row in commits)),
                          "batch_records_per_second": throughput,
                          "median_preview_seconds": median(row["preview"]["elapsed_seconds"] for row in rows),
                          "substance_comparisons": sum(row["preview"]["substance_comparisons"] for row in rows),
                          "concept_comparisons": sum(row["preview"]["concept_comparisons"] for row in rows),
                          "incomplete_previews": sum(row["preview"]["outcome"] == "INCOMPLETE_SEARCH" for row in rows)}}
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    print(report["metrics"], flush=True)


if __name__ == "__main__":
    evaluate(Path(sys.argv[1]), Path(sys.argv[2]))
