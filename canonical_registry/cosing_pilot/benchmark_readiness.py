"""Benchmark only source registration and recovery in disposable SQLite registries."""

import argparse
import json
from pathlib import Path
from statistics import median
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

from .registry import DomainType, fingerprint
from .staged_registry import Observation, StagedRegistry

DOMAIN = DomainType("SyntheticFoodIngredient", "SFI")
NAMESPACE = "readiness-benchmark"
SIZES = (1000,10000,30360,100000)


def observation(index, label=None, identifier=None):
    label = label or f"Fixture designation {index:08d}"
    payload = {"label":label,"identifier":identifier}
    return Observation(f"{NAMESPACE}:{index:08d}",label,fingerprint(payload),payload)


def peak_rss():
    if sys.platform != "win32":
        from resource import RUSAGE_SELF, getrusage

        return getrusage(RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
    import ctypes as c
    from ctypes import wintypes as w

    class Counters(c.Structure):
        _fields_ = [("cb",w.DWORD),("faults",w.DWORD)] + [(name,c.c_size_t) for name in (
            "peak","working","quota_peak_paged","quota_paged","quota_peak_nonpaged","quota_nonpaged",
            "pagefile","peak_pagefile",
        )]

    handle = c.windll.kernel32.GetCurrentProcess
    handle.restype = w.HANDLE
    info = c.windll.psapi.GetProcessMemoryInfo
    info.argtypes = [w.HANDLE,c.POINTER(Counters),w.DWORD]
    counters = Counters()
    counters.cb = c.sizeof(counters)
    if not info(handle(),c.byref(counters),counters.cb):
        raise OSError("Cannot read peak working set")
    return counters.peak


def measure(size, directory):
    start = perf_counter()
    rows = [observation(i) for i in range(size)]
    build_seconds = perf_counter()-start
    registry = StagedRegistry(directory / "benchmark.sqlite")
    registry.initialize()

    def intake(data, run_id, **kwargs):
        return registry.register(data,domain=DOMAIN,namespace=NAMESPACE,run_id=run_id,**kwargs)

    start = perf_counter()
    original = intake(rows,"original",complete_count=size)
    register_seconds = perf_counter()-start
    original_size = registry.path.stat().st_size
    start = perf_counter()
    replay = intake(reversed(rows),"replay",complete_count=size)
    replay_seconds = perf_counter()-start
    replay_size = registry.path.stat().st_size
    assert original["created"] == size and replay["created"] == replay["new_revisions"] == 0
    with registry.reader() as db:
        lookup_ms = []
        for row in rows[::max(1,size//1000)]:
            start = perf_counter()
            assert db.execute("SELECT concept_id FROM domain_concept WHERE source_reference=?",
                              (row.source_reference,)).fetchone()
            lookup_ms.append((perf_counter()-start)*1000)

    changed_count = max(2,size//100)
    changes = [observation(i,identifier=f"revised-{i}") for i in range(changed_count)]
    changes[0] = observation(0,"Renamed fixture",identifier="revised-0")
    start = perf_counter()
    delta = intake(changes,"delta")
    revision_seconds = perf_counter()-start
    assert delta["new_revisions"] == delta["held"] == changed_count
    snapshot = [*changes,*rows[changed_count:-1],observation(size)]
    start = perf_counter()
    first = intake(snapshot,"changed",complete_count=size,max_batches=1)
    first_batch_seconds = perf_counter()-start
    assert not first["completed"]

    def interrupt(offset):
        assert offset == first["offset"]
        raise KeyboardInterrupt

    try:
        intake(snapshot,"changed",complete_count=size,batch_hook=interrupt)
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError("Interruption did not reach the transaction")
    with registry.reader() as db:
        checkpoint = db.execute("SELECT next_offset,completed FROM registration_run WHERE run_id='changed'").fetchone()
        members = db.execute("SELECT count(*) FROM registration_member WHERE run_id='changed'").fetchone()[0]
        assert tuple(checkpoint) == (first["offset"],0) and members == first["offset"]
        assert db.execute("SELECT count(*) FROM source_head WHERE present=0").fetchone()[0] == 0
    start = perf_counter()
    resumed = intake(snapshot,"changed",complete_count=size)
    resume_seconds = perf_counter()-start
    assert resumed["missing"] == resumed["created"] == 1
    with registry.reader() as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
        assert db.execute("SELECT count(*) FROM domain_concept").fetchone()[0] == size+1
        assert db.execute("SELECT count(*) FROM assessment").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM domain_concept WHERE canonical_status<>'NOT_EVALUATED'").fetchone()[0] == 0
    return {"fixture":"synthetic food domain","records":size,"input_build_seconds":build_seconds,
            "registration_seconds":register_seconds,"total_build_and_registration_seconds":build_seconds+register_seconds,
            "records_per_second":size/register_seconds,"reingestion_seconds":replay_seconds,
            "initial_db_bytes":original_size,"replay_db_bytes":replay_size,
            "final_db_bytes":registry.path.stat().st_size,"lookup_median_ms":median(lookup_ms),
            "lookup_p95_ms":sorted(lookup_ms)[int(0.95*(len(lookup_ms)-1))],
            "revision_update_seconds":revision_seconds,"changed_records":changed_count,
            "first_batch_seconds":first_batch_seconds,"rolled_back_batch_offset":first["offset"],
            "resume_seconds":resume_seconds,"resume_result":resumed,"peak_process_rss_bytes":peak_rss(),
            "reingestion_result":replay,"integrity":"PASS"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size",type=int)
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    if args.size:
        with TemporaryDirectory(dir=Path(__file__).parent) as directory:
            result = measure(args.size,Path(directory))
    else:
        result = [json.loads(subprocess.run([sys.executable,"-B","-m",__spec__.name,"--size",str(size)],
                                            check=True,capture_output=True,text=True).stdout) for size in SIZES]
    serialized = json.dumps(result,indent=2)+"\n"
    if args.output:
        args.output.write_text(serialized,encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
