"""Measure local storage and retrieval cost with synthetic labels and source keys."""

import argparse
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from canonical_registry.ingredient_equivalence.contracts import Ingredient, Scope
from canonical_registry.ingredient_equivalence.retrieval import CandidateIndex
from canonical_registry.nomenclature_interpretation.contracts import Evidence, ReportedIdentifier

from .registry import COSMETICS, DomainRegistry, DomainType, Registration, canonical, fingerprint


def run(count=32000):
    if count < 30360:
        raise ValueError("Benchmark requires at least 30,360 records")
    domain = DomainType("food-ingredient-demo", "FID")
    scope = Scope("Synthetic source terms", "food", "storage exercise")
    records = [
        Registration(domain, f"synthetic.food:{i:08d}", f"Designation {i:08d}", fingerprint(["food", i]))
        for i in range(count)
    ]
    records.append(Registration(COSMETICS, "synthetic.cosmetics:demo", "Designation demo", fingerprint("demo")))
    with TemporaryDirectory(dir=Path(__file__).resolve().parent) as temp:
        db = DomainRegistry(Path(temp) / "benchmark.sqlite")
        start = perf_counter()
        first = db.ingest(records, pipeline_version="synthetic-storage")
        ingest = perf_counter() - start
        size = db.path.stat().st_size
        start = perf_counter()
        replay = db.ingest(records, pipeline_version="synthetic-storage")
        reingest = perf_counter() - start
        elapsed = []
        with db.reader() as conn:
            plan = conn.execute("EXPLAIN QUERY PLAN SELECT concept_id FROM domain_concept WHERE source_reference=?",
                                (records[0].source_reference,)).fetchone()[3]
            for row in records[:2000]:
                start = perf_counter()
                assert conn.execute("SELECT concept_id FROM domain_concept WHERE source_reference=?",
                                    (row.source_reference,)).fetchone()
                elapsed.append(perf_counter() - start)
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        recovered = DomainRegistry(db.path).search(records[-1].source_reference)[0]["ingredient_concept_id"]
        assert size == db.path.stat().st_size and recovered == "CIC_00000001"
    items = [
        Ingredient(r.source_reference, r.label, scope, reported_identifiers=(
            ReportedIdentifier("synthetic selective key", Evidence(str(i // 2), "synthetic key", r.source_reference)),
            ReportedIdentifier("synthetic broad key", Evidence("all", "synthetic key", r.source_reference)),
        ))
        for i, r in enumerate(records)
    ]
    start = perf_counter()
    index = CandidateIndex(items)
    build = perf_counter() - start
    start = perf_counter()
    stats = Counter()
    for item in items:
        result = index.find(item, limit=3)
        stats["candidates"] += len(result.matches)
        stats["postings_visited"] += result.postings_visited
        stats["queries_with_suppression"] += bool(result.skipped)
    return {
        "records": len(records), "food_config_records": count,
        "ingest_seconds": ingest, "ingest_records_per_second": len(records) / ingest,
        "reingest_seconds": reingest, "reingest_records_per_second": len(records) / reingest,
        "created_first": sum(r["created"] for r in first["records"]),
        "created_repeat": sum(r["created"] for r in replay["records"]),
        "reopened_cosmetics_id": recovered, "database_bytes_after_ingest_and_replay": size,
        "indexed_source_query_plan": plan, "lookup_count": len(elapsed),
        "lookup_median_ms": sorted(elapsed)[len(elapsed)//2]*1000,
        "integrity": integrity, "candidate_index_seconds": build, "candidate_query_seconds": perf_counter() - start,
        "candidate_pairs": stats["candidates"] // 2, "postings_visited": stats["postings_visited"],
        "queries_with_suppression": stats["queries_with_suppression"],
        "possible_pairs": len(records)*(len(records)-1)//2,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    result = canonical(run())
    if options.output:
        options.output.write_text(result + "\n", encoding="utf-8")
    print(result)
