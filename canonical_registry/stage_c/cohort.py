"""Freeze pilot membership and generate bounded GSRS queries."""

from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3

from canonical_registry.authoritative_lookup.cohort import DATA as LOOKUP, build_query
from canonical_registry.authoritative_lookup.sources import file_digest, read, write
from canonical_registry.cosing_pilot.mapping_preview import development_targets
from canonical_registry.cosing_pilot.stage_b_handoff import INDEX, REGISTRY, StagedRegistry, _inventory
from canonical_registry.identity_sufficiency.contract import digest
from canonical_registry.identity_sufficiency.evaluate import _guards, DATA as SUFFICIENCY

DATA = Path(__file__).with_name("data")
QUOTAS = {"defined_graph": 105, "other_graph": 30, "forms": 45, "conflict": 20, "broad": 20, "identifier": 20}
FORM = re.compile(r"\b(?:hydrate|monohydrate|dihydrate|salt|chloride|sulfate|sodium|potassium|tautomer|solvate)\b|^\([RSEDL0-9,]+\)", re.I)


def freeze(directory=DATA, *, prior=LOOKUP, quotas=QUOTAS, salt="stage-c-v1", extra_exclusions=(), phase_sizes=(),
           include_form_hints=False):
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / "freeze.json").exists():
        raise FileExistsError("Stage C cohort is already frozen")
    previous = read(LOOKUP / "cohort.json")
    qualified = {x["referent"] for x in read(LOOKUP / "results.json") if x["group"] != "GSRS"
                 and x["qualification"]["eligibility"] == "CANDIDATE_READY"}
    excludes = {x["concept_id"] for x in previous + read(SUFFICIENCY / "cosing_cohort.json")} | set(extra_exclusions)
    parents, aliases, _ = _inventory()
    pool = {key: [] for key in quotas}
    with closing(sqlite3.connect(INDEX.as_uri() + "?mode=ro", uri=True)) as db:
        for cid, ref, rev, version, status, payload in db.execute(
            "SELECT concept_id, source_reference, source_revision, stage_b_version, eligibility, evidence_json "
            "FROM stage_c_eligibility ORDER BY concept_id"
        ):
            if cid in excludes:
                continue
            parent = parents[ref.rsplit(":", 1)[-1]]
            evidence = json.loads(payload)
            if status.startswith("NOT_APPLICABLE"):
                group = "broad"
            elif status == "REVIEW_HOLD":
                group = "conflict"
            elif FORM.search(parent["inci"]) and (include_form_hints or evidence["graph_evidence"]):
                group = "forms"
            elif evidence["graph_evidence"] and len(parent["cas_nos"] or []) == 1:
                group = "defined_graph"
            elif evidence["graph_evidence"]:
                group = "other_graph"
            elif parent["cas_nos"] or parent["ec_nos"]:
                group = "identifier"
            else:
                continue
            pool[group].append({"concept_id": cid, "source_reference": ref, "revision": rev, "stage_b_version": version,
                                "old_status": status, "old_evidence": evidence, "parent": parent,
                                "group": "fresh", "stratum": group})
    fresh = [r for g, n in quotas.items()
             for r in sorted(pool[g], key=lambda x: digest([salt, x["concept_id"]]))[:n]]
    if len(fresh) != sum(quotas.values()):
        raise ValueError("A frozen stratum did not meet its quota")
    if phase_sizes:
        if sum(phase_sizes) != len(fresh):
            raise ValueError("Phase sizes differ from the frozen sample size")
        strata = {g: [r for r in fresh if r["stratum"] == g] for g in quotas}
        total = len(fresh)
        fresh = []
        for size in phase_sizes:
            begin = len(fresh)
            end = begin + size
            phase = [r for g, n in quotas.items() for r in strata[g][begin*n//total:end*n//total]]
            if len(phase) != size:
                raise ValueError("Quotas do not divide into the requested phases")
            fresh.extend(sorted(phase, key=lambda r: digest([salt, "order", r["concept_id"]])))
    with StagedRegistry(REGISTRY).reader() as db:
        for row in fresh:
            p = row["parent"]
            row["aliases"] = aliases[p["inci_id"]]
            a = db.execute("SELECT attributes_json,summary_json,trace_json FROM assessment "
                           "WHERE concept_id=? AND revision=? AND pipeline_version=?",
                           (row["concept_id"], row["revision"], row["stage_b_version"])).fetchone()
            row["attributes"], row["summary"], row["trace"] = [json.loads(v) for v in a] if a else ([], {}, {})
            names = {p["inci"].strip().upper()}
            definition = (p["description"] or "").strip()
            if 0 < len(definition) <= 40 and len(definition.split()) <= 4 and re.fullmatch(r"[\w (),-]+", definition):
                names.add(definition.upper())
            trace = row["trace"].get("interpretation", {})
            row["queries"] = {
                "NAME": sorted(names),
                "CAS": sorted({v.strip().upper() for v in p["cas_nos"] or [] if v and v.strip()}),
                "EC": sorted({v.strip().upper() for v in p["ec_nos"] or [] if v and v.strip()}),
                "INCHIKEY": sorted({g["value"]["inchikey"] for g in trace.get("assertions", [])
                                    if g["category"] == "STRUCTURAL" and g["value"].get("inchikey")}),
            }
    write(directory / "fresh.json", fresh)
    shards = {}
    # A phase boundary can share a query shard with the next phase.
    for offset in range(0, len(fresh), 60):
        path = directory / f"lookup_{offset // 60:02}.sql"
        path.write_text(build_query(fresh[offset:offset + 60]), encoding="utf-8")
        shards[path.name] = file_digest(path)
    write(directory / "freeze.json", {
        "selection": f"380 previous lookup cases plus disjoint stratified SHA-256 sample of {len(fresh)} ({salt})",
        "quotas": quotas, "prior_qualified": sorted(qualified), **({"phase_sizes": phase_sizes} if phase_sizes else {}),
        **({"form_stratum": "designation form hints; whole-form evidence evaluated independently"} if include_form_hints else {}),
        "prior_cohort_sha256": file_digest(LOOKUP / "cohort.json"),
        "fresh_sha256": file_digest(directory / "fresh.json"), "sql": shards,
        "protected": _guards(),
        "pins": {name: {"path": str(path), "sha256": file_digest(path)}
                 for name, path in development_targets().items()},
    })
    print(f"Frozen {len(previous)} prior and {len(fresh)} fresh CosIng records")


if __name__ == "__main__":
    freeze()
