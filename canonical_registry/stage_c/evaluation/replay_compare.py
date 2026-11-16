"""Compare independent Stage C fixture runs without timestamp or event-ID noise."""

import argparse
from contextlib import closing
import json

from canonical_registry.authoritative_lookup.sources import write
from fixture_registry import registry_digest
from ..cohort import DATA
from ..fixture import open_fixture, reader


def stable_results(directory):
    permit, _, _ = open_fixture(directory)
    with closing(reader(permit.path)) as db:
        rows = [json.loads(raw) for raw, in db.execute("SELECT result_json FROM stage_c_request")]
        aliases = db.execute("SELECT source_key,substance_id,alias FROM stage_c_exact_alias ORDER BY 1,2,3").fetchall()
        graph_digest = registry_digest(db)
    by_source = {r["source"]: (r["revision"], r["status"], r["outcome"], r.get("target"),
                 r["eligibility"]["eligibility"], r["eligibility"]["reasons"]) for r in rows}
    return by_source, aliases, graph_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", default="pilot-v2")
    parser.add_argument("--second", default="pilot-v2-final")
    parser.add_argument("--count", type=int, default=328)
    args = parser.parse_args()
    if any(not value.isascii() or not value.replace("-", "").isalnum() for value in (args.first, args.second)):
        parser.error("Use simple fixture run names")
    first, second = DATA / args.first, DATA / args.second
    before, after = stable_results(first), stable_results(second)
    if len(before[0]) != args.count or before != after:
        raise ValueError("Independent fixture replays differ")
    write(second / "replay_comparison.json", {"records": len(after[0]), "alias_assertions": len(after[1]),
                                               "canonical_registry_digest": after[2],
                                               "source_revision_outcome_target_agreement": True})
    print(f"Independent fixture agreement for {len(after[0])} decisions and {len(after[1])} alias assertions")


if __name__ == "__main__":
    main()
