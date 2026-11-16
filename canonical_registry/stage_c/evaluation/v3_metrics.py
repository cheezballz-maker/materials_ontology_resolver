"""Summarize v3 provider overlap and paired benchmark results."""

import argparse
from collections import Counter
from contextlib import closing
import json
import math
from statistics import median

from canonical_registry.authoritative_lookup.sources import read, write
from ..fixture import open_fixture, reader
from ..v3_authority import ROOT


def summarize(run):
    permit, _, _ = open_fixture(run)
    with closing(reader(permit.path)) as db:
        rows = [json.loads(raw) for raw, in db.execute("SELECT result_json FROM stage_c_request")]
        identifiers = dict(db.execute("""SELECT identifier_type,count(*) FROM substance_identifier
            WHERE substance_id IN (SELECT substance_id FROM substance_creation_record WHERE event_id IN
                (SELECT event_id FROM stage_c_request)) GROUP BY identifier_type"""))
    overlaps, chosen, admissions, reasons, contribution = (Counter() for _ in range(5))
    fresh_ids = {r["concept_id"] for r in read(ROOT / "fresh.json")}
    fresh_status = Counter()
    examples = []
    for row in rows:
        if row["referent"] in fresh_ids:
            fresh_status[row["outcome"]] += 1
        if row["status"] == "UNRESOLVED":
            reasons.update(row["eligibility"]["reasons"])
        receipt = row["receipt"]
        if not receipt or row["eligibility"]["eligibility"] != "CANDIDATE_READY":
            continue
        primary = receipt["authority"]
        names = {p["authority"] for p in receipt.get("cross_provider_support", [])} | {primary}
        overlaps[" + ".join(sorted(names))] += 1
        contribution.update(names)
        chosen[primary] += 1
        if row["status"] == "RESOLVED_SUBSTANCE":
            admissions[primary] += 1
        examples.append({"referent": row["referent"], "designation": row["designation"], "primary": primary,
                         "authorities": sorted(names), "status": row["status"], "target": row.get("target")})
    paired = {}
    for mode in ("baseline", "compact"):
        payload = read(ROOT.parent / "v2" / f"v3-{mode}" / "profile.json")
        tests = payload["rows"]
        times = [r["seconds"] for r in tests if r["target"]]
        times.sort()
        paired[mode] = {"median_seconds": median(times), "p95_nearest_rank_seconds": times[math.ceil(.95 * len(times)) - 1],
                        "total_seconds": sum(times), "fixture_bytes": payload["fixture_bytes"],
                        "setup_seconds": payload["setup_seconds"], "warm_seconds": payload["warm_seconds"],
                        "read_and_integrity_seconds": sum(r["profile"]["seconds"].get("snapshot_read_and_integrity", 0)
                                                          for r in tests),
                        "outcomes": [[r["name"], r["status"], r["outcome"], r["target"]] for r in tests]}
    if paired["baseline"]["outcomes"] != paired["compact"]["outcomes"]:
        raise ValueError("Benchmark outcomes diverged")
    transaction_times = sorted(r["timings"]["canonical_transaction_seconds"] for r in rows
                               if "canonical_transaction_seconds" in r["timings"])
    source_reuse = {}
    for row in rows:
        if row["status"] == "RESOLVED_SUBSTANCE":
            source_reuse.setdefault(row["target"], []).append([row["source"], row["designation"]])
    acquisition = {}
    for provider in ("gsrs", "pubchem", "chebi"):
        capture = read(ROOT / f"{provider}_capture.json")
        requests = list(capture.get("records", capture).values())
        acquisition[provider] = {"responses": len(requests), "http": dict(Counter(r["http_status"] for r in requests)),
                                 "request_seconds": sum(r["seconds"] for r in requests)}
    write(run / "authority_and_performance.json", {"chosen": dict(chosen), "overlap": dict(overlaps),
          "provider_referent_counts": dict(contribution), "fresh_outcomes": dict(fresh_status),
          "resolved_by_primary": dict(admissions), "unresolved_reasons": dict(reasons), "examples": examples,
          "created_identity_identifier_rows": identifiers, "acquisition": acquisition,
          "multi_source_targets": {k: v for k, v in source_reuse.items() if len(v) > 1},
          "integrated_transaction_p95_seconds": transaction_times[math.ceil(.95 * len(transaction_times)) - 1],
          "paired": paired, "speedup": paired["baseline"]["median_seconds"] / paired["compact"]["median_seconds"]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default="pilot-v3-verified")
    args = parser.parse_args()
    if not args.run.isascii() or not args.run.replace("-", "").isalnum():
        parser.error("Use a simple run name")
    summarize(ROOT.parent / args.run)
