"""Compare paired performance and verify targeted, independently sourced controls."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import json
from math import ceil
from statistics import median

from canonical_registry.authoritative_lookup.sources import read, write
from canonical_registry.chemistry import describe
from ..cohort import DATA
from ..fixture import open_fixture, reader


def benchmark_summary():
    base = DATA / "v2"
    profiles = {mode: read(base / mode / "profile.json") for mode in ("baseline", "optimized")}
    equivalent = [[(r["name"], r["status"], r["outcome"], r["target"]) for r in p["rows"]]
                  for p in profiles.values()]
    if equivalent[0] != equivalent[1] or len(equivalent[0]) != 8:
        raise ValueError("Paired benchmark outcomes differ")
    result = {}
    for mode, profile in profiles.items():
        durations = sorted(r["seconds"] for r in profile["rows"] if r["target"])
        created = [r["seconds"] for r in profile["rows"] if r["outcome"] == "NEW_SUBSTANCE_CREATED"
                   and not r["name"].endswith("replay")]
        phases, calls = Counter(), Counter()
        for row in profile["rows"]:
            phases.update(row["profile"]["seconds"])
            calls.update(row["profile"]["calls"])
        result[mode] = {"setup_seconds": profile["setup_seconds"], "warm_seconds": profile["warm_seconds"],
                        "median_seconds": median(durations), "p95_nearest_rank_seconds": durations[ceil(.95 * len(durations)) - 1],
                        "total_seconds": sum(durations), "new_admission_median_seconds": median(created),
                        "fixture_bytes": profile["fixture_bytes"], "profile_seconds": dict(phases), "profile_calls": dict(calls)}
    result["speedup"] = result["baseline"]["median_seconds"] / result["optimized"]["median_seconds"]
    write(base / "benchmark_comparison.json", result)
    return result


def review_controls(directory):
    permit, _, _ = open_fixture(directory)
    by_name = defaultdict(list)
    with closing(reader(permit.path)) as db:
        for name, payload in db.execute("SELECT designation,result_json FROM stage_c_request"):
            row = json.loads(payload)
            if row["source"].startswith("mse_dwd.dwd_mse_cosmetics_incis:"):
                by_name[name].append(row)
        checks = []
        for expected in read(DATA / "v2" / "reference_checks.json")["cases"]:
            matched = by_name[expected["designation"]]
            if len(matched) != 1:
                raise ValueError("Missing or ambiguous reference control")
            r = matched[0]
            actual_key = None
            if r["status"] == "RESOLVED_SUBSTANCE":
                [(structure,)] = db.execute("SELECT structure_value FROM substance_structure WHERE substance_id=? "
                                           "AND structure_type='SMILES'", (r["target"],)).fetchall()
                actual_key = describe(structure)["inchikey"]
            expected_status = expected.get("expected_status", "RESOLVED_SUBSTANCE")
            correct = r["status"] == expected_status and actual_key == expected.get("expected_key")
            checks.append({**expected, "source": r["source"], "actual_status": r["status"],
                           "actual_key": actual_key, "correct": correct})
        write(directory / "reference_results.json", checks)
        if not all(r["correct"] for r in checks):
            raise ValueError("A targeted independent reference check differs")
    return checks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default="pilot-v2-final")
    options = parser.parse_args()
    if not options.run.isascii() or not options.run.replace("-", "").isalnum():
        parser.error("Use a simple run name")
    print(benchmark_summary())
    print(review_controls(DATA / options.run))
