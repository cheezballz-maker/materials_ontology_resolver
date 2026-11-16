"""Run the bounded pilot or inspect the local registry."""

import argparse
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from uuid import UUID

from .mapping_preview import MappingPreview
from .organization import coverage, organize, review_pairs
from .registry import DomainRegistry, canonical, fingerprint

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
DATA = PACKAGE / "data"
PILOT = PACKAGE / "local" / "cosing_pilot.sqlite"


def read(path):
    import json
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, result):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(canonical(result) + "\n", encoding="utf-8")
    temporary.replace(path)


def source_cohort():
    sources, rows = (read(DATA / name) for name in ("source_rows.json", "companion_rows.json"))
    evidence = {r["inci_id"]: r for r in rows}
    keys = {r["inci_id"] for r in sources}
    if not 300 <= len(sources) <= 500 or len(keys) != len(sources) or len(evidence) != len(rows) or not keys <= evidence.keys():
        raise ValueError("Pilot input is outside the expected cohort bounds or source coverage")
    if any(str(UUID(key)) != key for key in keys):
        raise ValueError("Pilot source key must be the original UUID")
    return sources, evidence


def audit_paths():
    from canonical_registry.substance_explorer.registry_access import snapshot_digest
    path_list = ROOT / "ingredient_equivalence" / "evidence_validation" / "freeze.json"
    cache = ROOT / "enrichment" / "local" / "chemical_index.sqlite"
    paths = [*read(path_list)["protected_sha256_before"], *(str(cache) + suffix for suffix in ("","-wal","-shm","-journal"))]
    return {name: snapshot_digest(Path(name)) if Path(name).is_file() else None for name in paths}


def historical_comparison(sources):
    current = {r["inci_id"]: r["inci"] for r in sources}
    old = read(ROOT / "ingredient_equivalence" / "evaluation" / "warehouse.json")
    older_labels = {r["inci"]: r["inci_id"] for r in old}
    return {
        "older_capture_rows": len(old), "current_cohort_rows": len(current),
        "keys_present_in_both": sum(r["inci_id"] in current for r in old),
        "shared_key_different_name": sum(r["inci_id"] in current and r["inci"] != current[r["inci_id"]] for r in old),
        "same_name_different_key": sum(n in older_labels and k != older_labels[n] for k, n in current.items()),
        "same_label_key_pairs": sum(older_labels.get(n) == k for k, n in current.items()),
    }


def run(*, dry_run, verify_repeat=False):
    from providers import Bridge
    from canonical_registry.substance_explorer.registry_access import snapshot_digest
    from rdkit import rdBase
    start = perf_counter()
    before = audit_paths()
    sources, evidence = source_cohort()
    source_files = (DATA / "source_rows.json", DATA / "companion_rows.json", DATA / "external_reviews.json")
    source_digests = {p.name: snapshot_digest(p) for p in source_files}
    external_reviews = read(source_files[-1])
    with ExitStack() as stack, rdBase.BlockLogs():
        bridge = Bridge(build_directory=stack.enter_context(TemporaryDirectory(dir=PACKAGE)))
        stack.callback(bridge.close)
        mapping = MappingPreview(bridge)
        records, ingredients = organize(sources, evidence, bridge, mapping)
        organized = perf_counter()
        comparisons, candidates = review_pairs(ingredients, external_reviews)
        analyzed = perf_counter()
        mapping.verify_snapshots()
    inherited_evidence = [
        *(ROOT / "ingredient_equivalence" / "evaluation" / file for file in (
            "real_reference.json", "real_review.json", "warehouse.json", "aliases.json")),
        ROOT / "ingredient_equivalence" / "evidence_validation" / "authority_inputs.json",
    ]
    policy_files = [
        *sorted(p for folder in (PACKAGE, ROOT / "nomenclature_interpretation", ROOT / "ingredient_equivalence")
                for p in folder.glob("*.py") if not p.name.startswith("test_")),
        PACKAGE / "schema_v1.sql", ROOT / "providers.py", ROOT / "RegistryBridge.java",
        ROOT / "canonical_registry_matching" / "registry_identity_adapter.py",
        ROOT / "canonical_registry_matching" / "constitution_index.py",
        *inherited_evidence,
    ]
    version = "cosing-org-v1:" + fingerprint([
        bridge.digest, rdBase.rdkitVersion, mapping.identities, {p.relative_to(ROOT).as_posix(): snapshot_digest(p) for p in policy_files},
        source_digests["external_reviews.json"],
    ])[:20]
    db = DomainRegistry(PILOT)
    if not dry_run:
        PILOT.parent.mkdir(exist_ok=True)
    started_write = perf_counter()
    plan = None
    if verify_repeat:
        initial = snapshot_digest(PILOT) if PILOT.exists() else None
        plan = db.ingest(records, comparisons=comparisons, pipeline_version=version, dry_run=True)
        if initial != (snapshot_digest(PILOT) if PILOT.exists() else None):
            raise ValueError("Pilot database changed during dry-run preflight")
    transaction = db.ingest(records, comparisons=comparisons, pipeline_version=version, dry_run=dry_run)
    finished = perf_counter()
    repeat = None
    if verify_repeat:
        initial_digest = snapshot_digest(PILOT)
        replay = db.ingest(records, comparisons=comparisons, pipeline_version=version)
        repeat = {
            "new_ids": sum(row["created"] for row in replay["records"]),
            "new_revisions": sum(row["revision_inserted"] for row in replay["records"]),
            "new_assessments": sum(row["assessment_inserted"] for row in replay["records"]),
            "new_comparisons": replay["comparison_inserts"],
            "same_ids": [r["id"] for r in transaction["records"]] == [r["id"] for r in replay["records"]],
            "same_database_sha256": snapshot_digest(PILOT) == initial_digest,
            "dry_run_preflight_matches": plan == transaction,
        }
        if any(repeat[k] for k in ("new_ids","new_revisions","new_assessments","new_comparisons")) or not (
            repeat["same_ids"] and repeat["same_database_sha256"]
        ):
            raise ValueError("Pilot replay did not reproduce the registered state")
    protections = audit_paths()
    if before != protections:
        raise ValueError("A protected canonical file changed during the pilot")
    rows = transaction["records"]
    observed = {
        "pipeline_version": version, "mode": "dry_run" if dry_run else "persisted",
        "input_sha256": source_digests, "protected_sha256_before": before, "protected_sha256_after": protections,
        "canonical_registry_snapshots": mapping.identities, "opsin_sha256": bridge.digest,
        "historical_capture_comparison": historical_comparison(sources),
        "coverage": coverage(records),
        "repeat_check": repeat,
        "cohorts": {cohort: coverage(r for r in records if r.summary["cohort"] == cohort)
                    for cohort in sorted({r.summary["cohort"] for r in records})},
        "registration": {
            "source_records": len(sources), "registered": sum(not r["held"] for r in rows), "created": sum(r["created"] for r in rows),
            "held": sum(r["held"] for r in rows), "new_revisions": sum(r["revision_inserted"] for r in rows),
            "new_assessments": sum(r["assessment_inserted"] for r in rows),
            "possible_label_collisions": sum(r["possible_shared_label"] for r in rows),
            "canonical_status": dict(Counter(r["status"] for r in rows)), "rows": rows,
        },
        "comparisons": {
            "retrieved_unique_pairs": candidates, "assessed_pairs": len(comparisons),
            "stored_this_run": transaction["comparison_inserts"], "outcomes": dict(Counter(c.verdict for c in comparisons)),
            "reference_checks": [
                {"left": c.left, "right": c.right, "verdict": c.verdict, **c.evidence["review"]}
                for c in comparisons if c.evidence.get("review") is not None
            ],
        },
        "timings_seconds": {"organization": organized - start, "pair_review": analyzed - organized,
                            "sqlite_transaction": finished - started_write, "elapsed": finished - start},
    }
    if not dry_run:
        with db.reader() as conn:
            observed["database"] = {
                "file": str(PILOT.relative_to(ROOT)), "bytes": PILOT.stat().st_size, "sha256": snapshot_digest(PILOT),
                "integrity": [r[0] for r in conn.execute("PRAGMA integrity_check")],
                "foreign_key_errors": [tuple(r) for r in conn.execute("PRAGMA foreign_key_check")],
                "canonical_targets_committed": conn.execute("SELECT count(canonical_target_json) FROM domain_concept").fetchone()[0],
            }
    return observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    register = commands.add_parser("ingest", help="Organize the retained source cohort")
    register.add_argument("--dry-run", action="store_true", help="Calculate assignments in memory")
    register.add_argument("--results", type=Path, help="Write evaluation results from a persisted run")
    register.add_argument("--verify-repeat", action="store_true", help="Check that a repeat transaction makes no changes")
    search = commands.add_parser("search", help="Find pilot concepts")
    search.add_argument("query", nargs="?", default="")
    search.add_argument("--limit", type=int, default=25)
    inspect = commands.add_parser("inspect", help="Show identity, qualified descriptors, roles and review summaries")
    inspect.add_argument("id")
    inspect.add_argument("--trace", action="store_true")
    args = parser.parse_args()
    if args.command == "ingest":
        if args.dry_run and (args.results or args.verify_repeat):
            parser.error("Dry-run output goes to stdout and skips persisted replay checks")
        result = run(dry_run=args.dry_run, verify_repeat=args.verify_repeat)
        if args.results:
            write(args.results, result)
    elif args.command == "search":
        result = DomainRegistry(PILOT).search(args.query, limit=args.limit)
    else:
        result = DomainRegistry(PILOT).detail(args.id)
        if result is None:
            parser.error("Unknown pilot concept ID")
        if result["assessment"] and not args.trace:
            result["assessment"].pop("trace")
    print(canonical(result))


if __name__ == "__main__":
    main()
