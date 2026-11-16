"""Independent CLI for source registration, interpretation, and resolution review."""

import argparse
import json
from pathlib import Path
from uuid import UUID

from .cosing_source import PARENT, observation
from .registry import COSMETICS, canonical
from .staged_registry import StagedRegistry

DATA = Path(__file__).with_name("data")


def read_rows(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data["rows"] if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("Expected a list of source records")
    return rows


def packets(source, companion=None, *, legacy=False):
    rows = read_rows(source)
    if companion is None:
        return [observation(row) for row in rows]
    evidence = read_rows(companion)
    by_key = {row["inci_id"]: row for row in evidence}
    if len(by_key) != len(evidence):
        raise ValueError("Duplicate source keys in companion evidence")
    if legacy and not {row["inci_id"] for row in rows} <= by_key.keys():
        raise ValueError("The legacy cohort requires its original companion evidence")
    return [observation(row, by_key.get(row["inci_id"]), migrate_legacy=legacy) for row in rows]


def register(registry, rows, run_id, **options):
    return registry.register(rows, domain=COSMETICS, namespace=PARENT, run_id=run_id, **options)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    migration = commands.add_parser("migrate")
    migration.add_argument("--from-pilot", required=True, type=Path)
    migration.add_argument("--pilot-packets", action="store_true",
                           help="Restore archived payloads for the 407-record pilot copy")
    intake = commands.add_parser("register")
    intake.add_argument("--input", required=True, type=Path)
    intake.add_argument("--companion", type=Path)
    intake.add_argument("--run-id", required=True)
    intake.add_argument("--batch-size", type=int, default=500)
    intake.add_argument("--complete-count", type=int)
    intake.add_argument("--max-batches", type=int)
    for name in ("interpret", "resolve"):
        stage = commands.add_parser(name)
        stage.add_argument("--concept-id", action="append", default=[])
        stage.add_argument("--source-id", action="append", default=[])
        stage.add_argument("--batch")
        stage.add_argument("--capability", help="Interpretation module name")
        stage.add_argument("--typed-only", action="store_true", help="Use the separate no-name-parser cache")
        if name == "interpret":
            stage.add_argument("--pending", action="store_true", help="Interpret the current held revision")
        else:
            stage.add_argument("--equivalence", action="store_true")
    commands.add_parser("queue")
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit",type=int,default=25)
    review = commands.add_parser("review")
    review.add_argument("concept_id")
    review.add_argument("revision")
    review.add_argument("--action", choices=("defer", "adopt", "confirm-separate", "confirm-continuity"), required=True)
    review.add_argument("--actor", required=True)
    review.add_argument("--note", required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("concept_id")
    args = parser.parse_args(argv)
    registry = StagedRegistry(args.db)
    result = None
    if args.command == "init":
        registry.initialize()
    elif args.command == "migrate":
        rows = packets(DATA / "source_rows.json", DATA / "companion_rows.json",
                       legacy=True) if args.pilot_packets else None
        registry.initialize(args.from_pilot, legacy_observations=rows)
    elif args.command == "register":
        result = register(registry, packets(args.input, args.companion), args.run_id,
                          batch_size=args.batch_size, complete_count=args.complete_count,
                          max_batches=args.max_batches)
    elif args.command == "queue":
        result = registry.source_queue()
    elif args.command == "search":
        query = args.query.strip()
        try:
            query = f"{PARENT}:{UUID(query)}"
        except ValueError:
            pass
        result = registry.search(query,limit=args.limit)
    elif args.command == "inspect":
        result = registry.detail(args.concept_id)
    elif args.command == "review":
        registry.review_source(args.concept_id, args.revision, action=args.action, actor=args.actor, note=args.note)
    else:
        from .staged_assessment import assess

        result = assess(registry, args.command, concept_ids=args.concept_id, source_ids=args.source_id,
                        batch=args.batch, capability=args.capability, typed_only=args.typed_only,
                        pending=getattr(args, "pending", False), equivalence=getattr(args, "equivalence", False))
    print(canonical(result))


if __name__ == "__main__":
    main()
