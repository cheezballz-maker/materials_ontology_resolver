"""Count local candidate signals across CosIng without matching new referents."""

from collections import Counter
from contextlib import closing
import json
import sqlite3
from time import perf_counter

from rdkit import rdBase
from canonical_registry.chemistry import describe
from canonical_registry.cosing_pilot.registry import fingerprint
from canonical_registry.cosing_pilot.stage_b_handoff import INDEX, _inventory
from canonical_registry.identity_sufficiency.contract import structure_signature
from canonical_registry.identity_sufficiency.evaluate import _guards
from .lookup import normalize
from .protection import current_baseline
from .sources import DATA, read, warehouse, write


def main():
    start = perf_counter()
    before, _ = current_baseline()
    _, captured, _ = warehouse()
    parents, _, _ = _inventory()
    names, cas, graph_digests = set(), set(), set()
    with rdBase.BlockLogs():
        for _, candidates in captured.values():
            for c in candidates:
                if c["substance_type"] != "chemical" or c["ingredient_type"] != "INGREDIENT SUBSTANCE":
                    continue
                names.add(normalize(c["chemical_name"]))
                if c["smiles"]:
                    try:
                        graph_digests.add(fingerprint(structure_signature(describe(c["smiles"]))))
                    except (ValueError, RuntimeError):
                        pass
                cas.update(route.rsplit(":", 1)[-1] for route in c["routes"]
                           if route.startswith("REPORTED_IDENTIFIER:CAS:"))
    counts, channels = Counter(), Counter()
    seen = set()
    with closing(sqlite3.connect(INDEX.as_uri() + "?mode=ro", uri=True)) as db:
        for cid, ref, status, raw in db.execute(
            "SELECT concept_id,source_reference,eligibility,evidence_json FROM stage_c_eligibility"
        ):
            if cid in seen:
                raise ValueError("Duplicate CosIng concept in local inventory")
            seen.add(cid)
            p = parents[ref.rsplit(":", 1)[1]]
            evidence = json.loads(raw)
            ekeys = {item["graph_digest"] for item in evidence["graph_evidence"]}
            matches = {"name": normalize(p["inci"]) in names, "CAS": bool(cas.intersection(p["cas_nos"] or ())),
                       "full_graph_digest": bool(graph_digests.intersection(ekeys))}
            for channel, matched in matches.items():
                channels[channel] += matched
            counts["records_with_captured_candidate_signal"] += any(matches.values())
            if status.startswith("NOT_APPLICABLE"):
                counts["stage_b_outside_molecular_scope"] += 1
            if status == "REVIEW_HOLD":
                counts["stage_b_review_hold"] += 1
            if status == "REVIEW_HOLD" and "P1" in evidence["risk_priorities"]:
                counts["stage_b_identity_significant_hold"] += 1
            if evidence["graph_evidence"]:
                counts["stage_b_graph_evidence"] += 1
            if p["cas_nos"] or p["ec_nos"]:
                counts["reported_cas_or_ec"] += 1
    results = read(DATA / "results.json")
    evaluated = {row["referent"] for row in results if row["group"] != "GSRS"}
    if len(seen) != 30360 or not evaluated <= seen or _guards() != before:
        raise ValueError("Inventory coverage or protected-state check failed")
    counts["bounded_pilot_auto_qualified"] = sum(row["qualification"]["eligibility"] == "CANDIDATE_READY"
                                                for row in results if row["referent"] in evaluated)
    write(DATA / "inventory_screen.json", {"total": len(seen), "pilot_evaluated": len(evaluated),
                                          "not_evaluated_by_pilot": len(seen) - len(evaluated),
                                          "candidate_channels_nonexclusive": dict(channels), "counts": dict(counts),
                                          "elapsed_seconds": perf_counter() - start,
                                          "scope": "Captured GSRS candidates only; no inventory-wide qualification or matching"})


if __name__ == "__main__":
    main()
