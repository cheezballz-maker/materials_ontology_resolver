"""Create one named disposable demonstration, without writing to Substance."""
import json
import sqlite3
import time
import uuid
from pathlib import Path

from registry import BASE, FIXTURES, initialize, sha

ONTOLOGY = Path(r"C:\Users\IT PatsnapSG\OneDrive - Patsnap\13. PatSnap\13. Materials Ontology\Ontology\substance_ontology.ttl")
SEED = BASE / "output/registry.sqlite"
PILOT = BASE / "warehouse_admission_consolidation/output/normalized_pilot.sqlite"
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "evaluation.json"


def main():
    before = {str(path): sha(path) for path in (ONTOLOGY, SEED, PILOT)}
    path = FIXTURES / ("demo_" + uuid.uuid4().hex + ".sqlite")
    registry = initialize(path)
    cases = [
        ("metal", {"kind": "family", "family": "metal_oxides"}, "Metal oxides"),
        ("iron", {"kind": "family", "family": "iron_oxides"}, "Iron oxides"),
        ("acid", {"kind": "family", "family": "carboxylic_acids"}, "Carboxylic acids"),
        ("glutamate", {"kind": "molecular", "smiles": "NC(CCC(=O)O)C(=O)O",
                       "stereo_state": "EXPLICITLY_UNSPECIFIED"}, "Glutamic acid, stereo unspecified"),
        ("glutamate_alternate", {"kind": "molecular", "smiles": "O=C(O)CCC(N)C(=O)O",
                                 "stereo_state": "EXPLICITLY_UNSPECIFIED"}, "Glutamic acid, unspecified configuration"),
        ("two_centers_broad", {"kind": "molecular", "smiles": "CC(O)C(O)CC",
                               "stereo_state": "EXPLICITLY_UNSPECIFIED"}, "Two centers unspecified"),
        ("center_r", {"kind": "molecular", "smiles": "C[C@@H](O)C(O)CC",
                      "stereo_state": "EXPLICITLY_UNSPECIFIED"}, "One center R"),
        ("center_s", {"kind": "molecular", "smiles": "C[C@H](O)C(O)CC",
                      "stereo_state": "EXPLICITLY_UNSPECIFIED"}, "One center S"),
        ("center_r_alternate", {"kind": "molecular", "smiles": "CCC(O)[C@H](O)C",
                                "stereo_state": "EXPLICITLY_UNSPECIFIED"}, "One center R, alternate"),
    ]
    results = []
    for key, proposal, label in cases:
        start = time.perf_counter()
        result = registry.create_or_reuse(proposal, label, "demo:" + key)
        results.append({"case": key, **result, "seconds": time.perf_counter() - start})
    by_name = {row["case"]: row for row in results}
    assert by_name["glutamate"]["concept_id"] == by_name["glutamate_alternate"]["concept_id"]
    assert by_name["center_r"]["concept_id"] == by_name["center_r_alternate"]["concept_id"]
    assert by_name["center_r"]["concept_id"] != by_name["center_s"]["concept_id"]
    registry.relate(by_name["metal"]["concept_id"], by_name["iron"]["concept_id"])
    registry.relate(by_name["two_centers_broad"]["concept_id"], by_name["center_r"]["concept_id"])
    registry.map_source("SYNTHETIC_COSMETICS", "ingredient", "iron-oxides", "primary", by_name["iron"]["concept_id"])
    registry.map_source("SYNTHETIC_C", "chemical", "iron-oxides", "primary", by_name["iron"]["concept_id"])
    registry.include_substance(by_name["acid"]["concept_id"], "SUB_00000007", SEED)
    start = time.perf_counter()
    search = registry.search("Glutamic acid, unspecified configuration")
    lookup_seconds = time.perf_counter() - start
    assert search == [by_name["glutamate"]["concept_id"]]
    from contextlib import closing
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_errors = db.execute("PRAGMA foreign_key_check").fetchall()
        counts = {name: db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in
                  ("concept", "label", "revision", "event", "request", "narrower", "membership", "source_mapping")}
    assert integrity == "ok" and not foreign_key_errors
    after = {str(p): sha(p) for p in (ONTOLOGY, SEED, PILOT)}
    assert before == after
    output = {"fixture_database": str(path), "cases": results, "table_counts": counts,
              "lookup_seconds": lookup_seconds, "database_bytes": path.stat().st_size,
              "integrity": integrity, "foreign_key_errors": foreign_key_errors,
              "protected_sha256_before": before, "protected_sha256_after": after,
              "source_mappings": "SYNTHETIC_ONLY", "real_membership": "SUB_00000007",
              "chemical_accuracy_certification": "NOT_EVALUATED"}
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
