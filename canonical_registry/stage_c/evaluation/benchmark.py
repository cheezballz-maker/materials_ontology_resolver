"""Measure paired fixture runs using the same frozen Stage C v1 inputs."""

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack, closing
import functools
import json
from pathlib import Path
import sqlite3
from time import perf_counter

from rdkit import rdBase
from canonical_registry.authoritative_lookup.sources import cosing_input, gsrs_input, gsrs_controls, read, write
from canonical_registry.cosing_pilot.staged_assessment import _bridge
from canonical_registry.identity_sufficiency.contract import Evaluator
from canonical_registry.identity_sufficiency.evaluate import _guards
from canonical_registry.stage_c.captures import inputs, references
from canonical_registry.stage_c.cohort import DATA
from canonical_registry.stage_c.fixture import initialize, reader
from canonical_registry.stage_c.workflow import StageC
import creation_transaction
import constitution_index
import derived_index
import registry_identity_adapter
import transactional_association

NAMES = ("WATER", "ALCOHOL", "AQUA", "GLYCERIN", "CITRIC ACID", "ALCOHOL DENAT.")


class Profiler:
    def __init__(self):
        self.durations = Counter()
        self.calls = Counter()

    def install(self, stack, target, name, label):
        original = getattr(target, name)

        @functools.wraps(original)
        def timed(*args, **kwargs):
            start = perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                self.durations[label] += perf_counter() - start
                self.calls[label] += 1
        setattr(target, name, timed)
        stack.callback(setattr, target, name, original)

    def snapshot(self):
        return {"seconds": dict(self.durations), "calls": dict(self.calls)}


def benchmark(label, *, compact=False):
    freeze = read(DATA / "freeze.json")
    protected = _guards()
    if protected != freeze["protected"]:
        raise ValueError("Protected inputs changed")
    directory = DATA / "v2" / label
    start = perf_counter()
    permit, concepts, fixture = initialize(directory, freeze["pins"], compact=compact)
    setup_seconds = perf_counter() - start
    derived_index.CACHE = Path(derived_index.CACHE).with_name(f"stage_c_{label}_index.sqlite")
    # Prime an isolated cache identically for both fixtures. Keep its one-time cost separate.
    start = perf_counter()
    snapshot = registry_identity_adapter.RegistrySnapshot(permit.path)
    constitution_index.ConstitutionIndex(snapshot)
    warm_seconds = perf_counter() - start
    rows, warehouse, _ = inputs()
    authority, _, _ = references()
    by_name = {r["parent"]["inci"]: r for r in rows if r["parent"]["inci"] in NAMES}
    gsrs, companions = gsrs_controls()
    ethanol = next(r for r in gsrs if r["chemical_name"] == "ALCOHOL")
    work = []
    for name in NAMES:
        row = by_name[name]
        total, candidates = warehouse.get(row["concept_id"], (0, []))
        work.append((name, cosing_input(row), candidates, total, False, False))
    work += [("GSRS ALCOHOL", gsrs_input(ethanol, companions.get(ethanol["chemical_id"], {})),
              [{**ethanol, "routes": []}], 1, True, False), ("ALCOHOL replay", *work[1][1:-1], True)]
    results = []
    with ExitStack() as stack, rdBase.BlockLogs():
        engine = StageC(permit, concepts, Evaluator(_bridge(stack).official), authority)
        for name, source, candidates, total, authority_source, replay in work:
            profile = Profiler()
            with ExitStack() as patch:
                for target, method, phase in (
                    (creation_transaction, "connect_creation", "connection"),
                    (registry_identity_adapter.RegistrySnapshot, "_read_rows", "snapshot_read_and_integrity"),
                    (registry_identity_adapter.RegistrySnapshot, "_build_entries", "snapshot_materialization"),
                    (registry_identity_adapter.RegistrySnapshot, "_logical_digest", "snapshot_digest"),
                    (creation_transaction, "assess", "creation_eligibility"),
                    (creation_transaction, "allocate", "allocate_id"),
                    (creation_transaction, "insert", "identity_insert"),
                    (creation_transaction, "insert_representations", "representations_insert"),
                    (creation_transaction.AssociationService, "_associate_locked", "association_including_recheck"),
                    (creation_transaction, "registry_digest", "creation_registry_digest"),
                    (transactional_association, "registry_digest", "association_registry_digest"),
                    (creation_transaction, "encode_audit", "creation_audit"),
                    (constitution_index.ConstitutionIndex, "__init__", "constitution_index"),
                ):
                    profile.install(patch, target, method, phase)
                start = perf_counter()
                result = engine.process(source, candidates, total, authority_source=authority_source, replay=replay)
                elapsed = perf_counter() - start
            results.append({"name": name, "status": result["status"], "outcome": result["outcome"],
                            "target": result.get("target"), "seconds": elapsed,
                            "transaction_seconds": result["timings"].get("canonical_transaction_seconds"),
                            "profile": profile.snapshot()})
            print(name, result["outcome"], round(elapsed, 3), flush=True)
            write(directory / "profile.json", {"rows": results, "setup_seconds": setup_seconds, "warm_seconds": warm_seconds,
                                                "fixture_bytes": permit.path.stat().st_size,
                                                "compaction": fixture["compaction"]})
    with closing(reader(permit.path)) as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not db.execute("PRAGMA foreign_key_check").fetchone()
    assert _guards() == protected


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    parser.add_argument("--compact", action="store_true")
    options = parser.parse_args()
    if not options.label.isascii() or not options.label.replace("-", "").isalnum():
        parser.error("Use a simple fixture run name")
    benchmark(options.label, compact=options.compact)
