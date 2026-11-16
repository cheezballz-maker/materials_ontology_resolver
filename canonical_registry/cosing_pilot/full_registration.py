"""Preflight, register and audit the verified complete CosIng parent snapshot."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from json import loads
from pathlib import Path
import re
from statistics import median
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

from .benchmark_readiness import peak_rss
from .cosing_source import PARENT, observation
from .full_capture import FIELDS, SOURCE, SOURCE_COUNT, digest, read, write
from .readiness import DATA, packets, register
from .registry import DomainRegistry, canonical, fingerprint
from .staged_registry import StagedRegistry

PILOT = DATA.parent / "local" / "cosing_pilot.sqlite"
ROOT = DATA.parents[1]
UNCHANGED_TABLES = ("domain_concept","source_revision","assessment","review_comparison",
                    "source_payload","source_head","source_review")
STATUSES = ("NOT_EVALUATED","UNRESOLVED","RESOLVED_SUBSTANCE","RESOLVED_CHEMICAL_CONCEPT")


def require(condition,message):
    if not condition:
        raise ValueError(message)


def protected_paths():
    frozen = read(ROOT / "ingredient_equivalence/evidence_validation/freeze.json")["protected_sha256_before"]
    configuration = ROOT / "enrichment/local/registries.json"
    configured = read(configuration)
    paths = {Path(name) for name in frozen}
    paths.update((PILOT,configuration,ROOT/"enrichment/local/chemical_index.sqlite",
                  Path(configured["association"]["path"]),Path(configured["concept_database"]),
                  PILOT.with_name("cosing_registration_readiness_v2.sqlite")))
    paths.update(Path(str(path)+suffix) for path in tuple(paths) if path.suffix == ".sqlite"
                 for suffix in ("-wal","-shm","-journal"))
    return {str(path):digest(path) if path.is_file() else None for path in sorted(paths)}


def _state_digest(db):
    result = {}
    for table in UNCHANGED_TABLES:
        checksum = sha256()
        for row in db.execute(f"SELECT * FROM {table} ORDER BY rowid"):
            checksum.update(canonical(tuple(row)).encode("utf-8")+b"\n")
        result[table] = checksum.hexdigest()
    return result


def _pilot_state():
    with DomainRegistry(PILOT).reader() as db:
        data = {table:[tuple(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY rowid")]
                for table in ("domain_type","domain_concept","source_revision","assessment","review_comparison")}
        by_source = {row["source_reference"]:dict(row) for row in db.execute("SELECT * FROM domain_concept")}
    require(len(by_source)==len(data["domain_concept"])==407,"Expected the original 407 unique pilot bindings")
    return data, by_source


def _check_preservation(db,pilot_tables,pilot):
    for table in ("assessment","review_comparison"):
        current = [tuple(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY rowid")]
        require(current == pilot_tables[table],f"Stage A changed original {table} rows")
    revisions = [tuple(row) for row in db.execute("SELECT * FROM source_revision ORDER BY rowid LIMIT ?",
                                                 (len(pilot_tables["source_revision"]),))]
    require(revisions == pilot_tables["source_revision"],"Stage A changed original source revision history")
    bindings = []
    for ref, original in sorted(pilot.items()):
        current = db.execute("SELECT * FROM domain_concept WHERE source_reference=?",(ref,)).fetchone()
        require(current is not None and dict(current)==original,f"Pilot concept changed: {ref}")
        bindings.append({"before":original["concept_id"],"after":current["concept_id"],"source_reference":ref,
                         "canonical_status":current["canonical_status"]})
    return bindings


def _initialize(registry,pilot_tables):
    archive = packets(DATA/"source_rows.json",DATA/"companion_rows.json",legacy=True)
    registry.initialize(PILOT,legacy_observations=archive)
    with registry.reader() as db:
        for table, rows in pilot_tables.items():
            observed = [tuple(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY rowid")]
            require(observed == rows,f"Migration changed {table}")
        require(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                and not db.execute("PRAGMA foreign_key_check").fetchall(),"Migration failed SQLite integrity")


def _audit(registry,observations,pilot_tables,pilot,run_id):
    by_source = {row.source_reference:row for row in observations}
    status = {"existing":Counter(dict.fromkeys(STATUSES,0)),"new":Counter(dict.fromkeys(STATUSES,0))}
    representatives = []
    have_new_example = False
    with registry.reader() as db:
        registry._verify(db,(2,))
        bindings = _check_preservation(db,pilot_tables,pilot)
        sqlite_check = [row[0] for row in db.execute("PRAGMA integrity_check")]
        foreign_keys = db.execute("PRAGMA foreign_key_check").fetchall()
        require(sqlite_check == ["ok"] and not foreign_keys,"Registration failed SQLite integrity")
        run = db.execute("SELECT * FROM registration_run WHERE run_id=?",(run_id,)).fetchone()
        require(run is not None and tuple(run[k] for k in ("full_snapshot","completed","expected_count","next_offset"))
                == (1,1,len(by_source),len(by_source)),"Complete run checkpoint is inconsistent")
        members, historical, all_refs, ids = set(), [], set(), set()
        for row in db.execute("""SELECT d.*,h.present,h.observed_revision,m.revision AS run_revision,m.source_version,
                                   r.observed_label,p.payload_json,p.content_key
                FROM domain_concept d JOIN source_head h USING(concept_id)
                LEFT JOIN registration_member m ON m.concept_id=d.concept_id AND m.run_id=?
                JOIN source_revision r ON r.concept_id=d.concept_id AND r.fingerprint=h.observed_revision
                JOIN source_payload p ON p.concept_id=d.concept_id AND p.revision=h.observed_revision
                ORDER BY d.concept_id""",(run_id,)):
            ref, cid = row["source_reference"],row["concept_id"]
            require(ref not in all_refs and cid not in ids and re.fullmatch(r"CIC_[0-9]{8}",cid),
                    f"Duplicate or invalid concept binding: {ref}")
            all_refs.add(ref)
            ids.add(cid)
            known = ref in pilot
            status["existing" if known else "new"][row["canonical_status"]] += 1
            if not known:
                require(row["canonical_status"]=="NOT_EVALUATED" and row["canonical_target_json"] is None,
                        f"Stage A assigned unsupported canonical state to {cid}")
            if not row["present"]:
                require(known and row["run_revision"] is None and ref not in by_source,"Unexpected historical record")
                historical.append({"concept_id":cid,"source_reference":ref})
                continue
            obs = by_source.get(ref)
            require(obs is not None and row["run_revision"]==row["observed_revision"] and
                    row["source_version"]==obs.source_version and row["observed_label"]==obs.label and
                    (known or row["preferred_label"]==obs.label),"Source snapshot binding does not reconcile")
            members.add(ref)
            payload = loads(row["payload_json"])
            require(payload["source"]==obs.payload["source"] and fingerprint(payload)==row["content_key"],
                    f"Observed source payload mismatch: {ref}")
            if row["preferred_label"] in {"WATER","PARFUM","AQUA","CALCIUM OXIDE","POLYQUATERNIUM-62"} or (
                    not known and not have_new_example):
                representatives.append({key:row[key] for key in (
                    "concept_id","preferred_label","source_reference","canonical_status",
                    "registered_revision","observed_revision")})
                have_new_example = have_new_example or not known
        require(members==by_source.keys(),"Current registered key set differs from the complete capture")
        table_count = db.execute("SELECT count(*) FROM domain_concept").fetchone()[0]
        membership_count = db.execute("SELECT count(*) FROM registration_member WHERE run_id=?",(run_id,)).fetchone()[0]
        require(table_count==len(all_refs) and membership_count==len(members),"Unjoined concept or membership rows")
        lookup_ms = []
        for obs in observations[::max(1,len(observations)//1000)]:
            start = perf_counter()
            found = db.execute("SELECT concept_id FROM domain_concept WHERE source_reference=?",
                               (obs.source_reference,)).fetchone()
            lookup_ms.append((perf_counter()-start)*1000)
            require(found is not None,"Indexed source lookup failed")
        events = dict(db.execute("SELECT event,count(*) FROM source_review GROUP BY event"))
        integrity = {"schema_version":2,"sqlite_integrity":sqlite_check,"foreign_key_violations":0,
                     "registered_concepts":table_count,"current_source_bindings":len(members),
                     "missing_current_keys":0,"duplicate_source_bindings":0,"invalid_concept_ids":0,
                     "historical_only":historical,"preserved_pilot_bindings":bindings,"completed_run":dict(run),
                     "assessments":len(pilot_tables["assessment"]),"advisory_comparisons":len(pilot_tables["review_comparison"]),
                     "statuses":{key:dict(counts) for key,counts in status.items()},"representative_records":representatives,
                     "lookup_count":len(lookup_ms),"lookup_median_ms":median(lookup_ms),
                     "lookup_p95_ms":sorted(lookup_ms)[int(.95*(len(lookup_ms)-1))],
                     "source_review_events":events,"core_table_digests":_state_digest(db)}
    integrity["source_review_queue"] = registry.source_queue()
    return integrity


def _preflight(observations,pilot_tables,pilot,run_id,batch_size):
    with TemporaryDirectory(dir=DATA.parent) as temporary:
        registry = StagedRegistry(Path(temporary)/"preflight.sqlite")
        _initialize(registry,pilot_tables)
        checkpoint = register(registry,observations,run_id,batch_size=batch_size,
                              complete_count=len(observations),max_batches=1)
        require(not checkpoint["completed"],"Choose a batch size that exercises a partial checkpoint")

        def interrupt(offset):
            require(offset==checkpoint["offset"],"Unexpected interruption offset")
            raise KeyboardInterrupt

        with registry.reader() as db:
            before = _state_digest(db)
        try:
            register(registry,observations,run_id,batch_size=batch_size,complete_count=len(observations),
                     batch_hook=interrupt)
        except KeyboardInterrupt:
            pass
        else:
            raise ValueError("Failure injection did not interrupt the transaction")
        with registry.reader() as db:
            durable = db.execute("SELECT next_offset,completed FROM registration_run WHERE run_id=?",(run_id,)).fetchone()
            require(tuple(durable)==(checkpoint["offset"],0) and _state_digest(db)==before,
                    "Interrupted batch changed the prior committed state")
        start = perf_counter()
        resumed = register(registry,observations,run_id,batch_size=batch_size,complete_count=len(observations))
        recovery_seconds = perf_counter()-start
        audit = _audit(registry,observations,pilot_tables,pilot,run_id)
        added = checkpoint["created"]+resumed["created"]
        return {"checkpoint":checkpoint,"resumed":resumed,"interrupted_batch_rolled_back":True,
                "recovery_seconds":recovery_seconds,"expected_new":added,"expected_reused":len(observations)-added,
                "expected_new_revisions":checkpoint["new_revisions"]+resumed["new_revisions"],
                "expected_held_observations":checkpoint["held"]+resumed["held"],
                "expected_historical_only":len(audit["historical_only"])}


def run(manifest_path,database,output,batch_size,resume):
    manifest = read(manifest_path)
    require(manifest["source_table"]==SOURCE and manifest["row_count"]==SOURCE_COUNT
            and manifest["consistency"]=="VERIFIED_PRE_POST_PROFILES_AND_BUCKET_CONTENTS","Unverified source manifest")
    require(manifest["snapshot_file"]=="source_snapshot.json","Unexpected source snapshot path")
    snapshot = manifest_path.with_name(manifest["snapshot_file"])
    require(digest(snapshot)==manifest["snapshot_sha256"],"Source snapshot differs from the verified capture")
    source = read(snapshot)
    require(len(source)==SOURCE_COUNT and all(set(row)==set(FIELDS) for row in source),"Snapshot scope mismatch")
    start = perf_counter()
    observations = [observation(row) for row in source]
    packet_seconds = perf_counter()-start
    run_id = "cosing-full-v1-"+manifest["snapshot_sha256"]
    before = protected_paths()
    registry = StagedRegistry(database)
    require(registry.path not in {Path(path) for path in before},"The selected path is a protected artifact")
    pilot_tables,pilot = _pilot_state()
    start = perf_counter()
    preflight = _preflight(observations,pilot_tables,pilot,run_id,batch_size)
    preflight_seconds = perf_counter()-start
    print("Dry run verified",preflight["expected_new"],"new and",preflight["expected_reused"],"reused",flush=True)
    if resume:
        with registry.reader() as db:
            registry._verify(db,(2,))
            _check_preservation(db,pilot_tables,pilot)
            checkpoint = db.execute("SELECT 1 FROM registration_run WHERE run_id=?",(run_id,)).fetchone()
            require(checkpoint is not None,"Resume requires the same verified snapshot and an existing run")
    else:
        _initialize(registry,pilot_tables)
    start = perf_counter()
    registered = register(registry,observations,run_id,batch_size=batch_size,complete_count=len(observations))
    register_seconds = perf_counter()-start
    integrity = _audit(registry,observations,pilot_tables,pilot,run_id)
    require(sum(integrity["statuses"]["new"].values())==preflight["expected_new"]
            and len(integrity["source_review_queue"])>=preflight["expected_held_observations"]
            and len(integrity["historical_only"])==preflight["expected_historical_only"],
            "Persistent result disagrees with the preflight")
    if not resume:
        require(registered["created"]==preflight["expected_new"]
                and registered["new_revisions"]==preflight["expected_new_revisions"],"Persistent allocation differs from dry run")
    database_bytes = registry.path.stat().st_size
    start = perf_counter()
    replay = register(registry,reversed(observations),run_id+"-replay",batch_size=batch_size,complete_count=len(observations))
    replay_seconds = perf_counter()-start
    require(replay["created"]==replay["new_revisions"]==replay["missing"]==0,"Replay changed allocation or revisions")
    repeat_audit = _audit(registry,observations,pilot_tables,pilot,run_id+"-replay")
    require(repeat_audit["core_table_digests"]==integrity["core_table_digests"],"Replay changed registry core tables")
    after = protected_paths()
    require(before==after,"A protected artifact changed during registration")
    forbidden = {"rdkit","providers","resolver","canonical_registry.cosing_pilot.staged_assessment",
                 "canonical_registry.nomenclature_interpretation","canonical_registry.ingredient_equivalence"}
    require(not forbidden.intersection(sys.modules),"A chemistry dependency was loaded during Stage A")
    normalized = defaultdict(list)
    for row in source:
        if row["normalized_inci"]:
            normalized[row["normalized_inci"]].append({"inci_id":row["inci_id"],"inci":row["inci"]})
    write(output,{"snapshot_sha256":manifest["snapshot_sha256"],"database":registry.path.name,"preflight":preflight,
                 "capture_seconds":manifest["capture_elapsed_seconds"],"preflight_seconds":preflight_seconds,
                 "packet_preparation_seconds":packet_seconds,"registration_seconds":register_seconds,
                 "registration_records_per_second":len(observations)/register_seconds if not resume else None,
                 "replay_seconds":replay_seconds,"peak_process_rss_bytes":peak_rss(),
                 "database_bytes_before_replay":database_bytes,"database_bytes_after_replay":registry.path.stat().st_size,
                 "registration":registered,"replay":replay,"replay_run":repeat_audit["completed_run"],
                 "core_tables_identical_on_replay":True,"integrity":integrity,
                 "shared_normalized_designations":{label:rows for label,rows in normalized.items() if len(rows)>1},
                 "protected":{"before":before,"after":after,"changes":[]},"execution_scope":"Stage A only"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--db",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--batch-size",type=int,default=500)
    parser.add_argument("--resume",action="store_true")
    args = parser.parse_args()
    run(args.manifest,args.db,args.output,args.batch_size,args.resume)


if __name__ == "__main__":
    main()
