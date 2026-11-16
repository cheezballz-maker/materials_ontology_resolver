"""Validate and combine frozen warehouse and authority captures."""

import json

from canonical_registry.authoritative_lookup.sources import (
    FIELDS, authority_records, file_digest, gsrs_controls, read, warehouse, write,
)
from .cohort import DATA, LOOKUP


def inputs(directory=DATA, *, fresh_limit=None):
    freeze = read(directory / "freeze.json")
    if file_digest(directory / "fresh.json") != freeze["fresh_sha256"] or (
        file_digest(LOOKUP / "cohort.json") != freeze["prior_cohort_sha256"]
    ):
        raise ValueError("Stage C cohort changed")
    cohort, candidates, queries = warehouse()
    fresh = read(directory / "fresh.json")
    for index, (filename, expected_digest) in enumerate(sorted(freeze["sql"].items())):
        if fresh_limit is not None and index * 60 >= fresh_limit:
            break
        path = directory / filename
        if file_digest(path) != expected_digest:
            raise ValueError("Frozen SQL changed")
        receipt = read(path.with_suffix(".json"))
        allowed = {x["concept_id"] for x in fresh[index * 60:(index + 1) * 60]}
        if not receipt["query_id"]:
            raise ValueError("Missing warehouse query provenance")
        seen = set()
        for row in receipt["rows"]:
            ref, count = row["ref"], int(row["total_candidates"])
            records = [dict(zip(FIELDS, a, strict=True)) for a in json.loads(row["candidates"])]
            if ref not in allowed or ref in seen or len(records) != min(10, count) or (
                len({r["chemical_id"] for r in records}) != len(records)
            ):
                raise ValueError("Warehouse result violates frozen candidate bounds")
            seen.add(ref)
            for record in records:
                record["routes"] = json.loads(record["routes"])
            candidates[ref] = (count, records)
        queries.append({"query_id": receipt["query_id"], "seconds": receipt["elapsed_seconds"],
                        "rows": len(seen), "receipt_sha256": file_digest(path.with_suffix(".json"))})
    return cohort + fresh, candidates, queries


def references():
    captured = read(LOOKUP / "authority_cache.json")["providers"]
    additional = DATA / "nist_species.json"
    if additional.exists():
        captured["NIST"]["records"] += [{**entry, "cross_reference": "NIST_SPECIES_CAS"} for entry in read(additional)]
        captured["NIST"]["capture"] = {**captured["NIST"]["capture"],
                                        "stage_c_sha256": file_digest(additional), "sha256": file_digest(additional)}
    native = DATA / "gsrs_native.json"
    if native.exists():
        captured["GSRS"].extend(read(native))
    return authority_records(captured)


def reference_queue():
    """Select a bounded general authority acquisition queue without matching."""
    rows, candidates, _ = inputs()
    selected = []
    for row in rows:
        if row["stratum"] != "defined_graph":
            continue
        total, found = candidates.get(row["concept_id"], (0, []))
        if total != 1 or not found:
            continue
        candidate = found[0]
        codes = row["queries"]["CAS"]
        if (len(codes) == 1 and candidate["substance_type"] == "chemical"
            and candidate["ingredient_type"] == "INGREDIENT SUBSTANCE"
            and candidate["inchikey"] in row["queries"]["INCHIKEY"]
            and candidate["chemical_name"] == row["parent"]["inci"]
            and "REPORTED_IDENTIFIER:CAS:" + codes[0] in candidate["routes"]
            and candidate["smiles"] and "." not in candidate["smiles"]):
            selected.append({"referent": row["concept_id"], "name": candidate["chemical_name"],
                             "cas": codes[0], "unii": candidate["source_id"], "expected_key": candidate["inchikey"],
                             "nist_id": "C" + codes[0].replace("-", "")})
    write(DATA / "authority_queue.json", selected[:32])
    for r in selected[:32]:
        print(r["nist_id"], r["unii"], r["name"])


if __name__ == "__main__":
    reference_queue()
