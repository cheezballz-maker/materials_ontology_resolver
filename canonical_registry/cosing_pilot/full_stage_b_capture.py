"""Verify full Stage B parent and companion source captures from read-only Trino."""

from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from uuid import UUID

from .full_capture import digest, read, write
from .stage_b_cohort import PARENT_ARCHIVE
from .stage_b_evidence import _eligible_alias

OUTPUT = Path(__file__).with_name("data")/"full_stage_b_v1"
CAPTURE = OUTPUT/"capture"
MANIFEST = OUTPUT/"source_manifest.json"
BUCKETS = 64
ALIAS_COLUMNS = ("inci_alias_id","inci_id","alias","normalized_alias","lang","alias_type","source",
                 "created_ts","updated_ts","data_status")


def source_bucket(key):
    return int(key[:4],16)%BUCKETS


def read_capture(name):
    return read(CAPTURE/f"{name}.json")


def source_inventory():
    baseline = read(PARENT_ARCHIVE.with_name("source_snapshot_manifest.json"))
    if digest(PARENT_ARCHIVE)!=baseline["snapshot_sha256"]:
        raise ValueError("Registered parent archive digest differs from its manifest")
    before,after = (read_capture(f"parent_{phase}") for phase in ("before","after"))
    parent_rows = baseline["before_profile"]["rows"]
    if before["rows"]!=parent_rows or after["rows"]!=parent_rows:
        raise ValueError("Live parent content differs from the registered archive")
    parents = {}
    for row in read(PARENT_ARCHIVE):
        key = row["inci_id"]
        if str(UUID(key))!=key or key in parents:
            raise ValueError("Invalid or duplicate registered parent key")
        parents[key] = row
    if len(parents)!=30360:
        raise ValueError("Unexpected registered parent population")
    return parents, baseline, [before["query_id"],after["query_id"]]


def _page(number, profile, parents):
    page = read_capture(f"alias_{number:02}")
    pieces = page["rows"]
    if [int(r["part"]) for r in pieces]!=list(range(len(pieces))) or len(pieces)>=999:
        raise ValueError(f"Truncated or nonconsecutive alias chunks in bucket {number}")
    stream = sha256()
    previous = ""
    used, rows = set(), []
    for i, piece in enumerate(pieces):
        packets = json.loads(piece["packets"])
        if not 1<=len(packets)<=12 or i<len(pieces)-1 and len(packets)!=12:
            raise ValueError(f"Incomplete alias chunk in bucket {number}")
        for packet in packets:
            row = dict(zip(ALIAS_COLUMNS,json.loads(packet),strict=True))
            key, parent = row["inci_alias_id"],row["inci_id"]
            if not isinstance(key,str) or key<=previous or parent not in parents or source_bucket(parent)!=number:
                raise ValueError(f"Duplicate, unordered or unbound alias row in bucket {number}")
            previous = key
            used.add(parent)
            rows.append(row)
            stream.update(sha256(packet.encode("utf-8")).hexdigest().upper().encode("ascii"))
    if (len(rows),len(rows),len(used),stream.hexdigest().upper())!=(
            int(profile["rows_total"]),int(profile["distinct_alias_keys"]),int(profile["distinct_parents"]),profile["sha256"]):
        raise ValueError(f"Alias count, key coverage or digest mismatch in bucket {number}")
    return page["query_id"],rows,used


def freeze():
    parents,registered,parent_queries = source_inventory()
    before,after = (read_capture(f"alias_{phase}") for phase in ("before","after"))
    if before["rows"]!=after["rows"] or [int(r["bucket"]) for r in before["rows"]]!=list(range(BUCKETS)):
        raise ValueError("Alias source profile changed or is incomplete")
    ids,covered,stats = set(),set(),Counter()
    buckets = {}
    cutoff = int(datetime.fromisoformat(registered["started_utc"]).timestamp()*1000)
    for profile in before["rows"]:
        number = int(profile["bucket"])
        query, rows, used = _page(number,profile,parents)
        row_keys = {r["inci_alias_id"] for r in rows}
        if ids&row_keys:
            raise ValueError("Duplicate alias record keys across buckets")
        ids.update(row_keys)
        covered.update(used)
        stats.update(_eligible_alias(r,cutoff) or "ELIGIBLE_ORIGINAL_ALIAS" for r in rows)
        file = f"alias_{number:02}.json"
        buckets[str(number)] = {"profile":profile,"query_id":query,"file":file,"file_sha256":digest(CAPTURE/file)}
    files = ("parent_before.json","parent_after.json","alias_before.json","alias_after.json")
    document = {"parent_sha256":registered["snapshot_sha256"],"parent_queries":parent_queries,
        "parent_cutoff_epoch_ms":cutoff,"parent_count":len(parents),"parents_with_aliases":len(covered),
        "parents_without_aliases":len(parents)-len(covered),"alias_count":len(ids),"alias_eligibility":dict(stats),
        "alias_profile_queries":[before["query_id"],after["query_id"]],"buckets":buckets,
        "profile_files":{name:digest(CAPTURE/name) for name in files},
        "sql_files":{name:digest(OUTPUT/name) for name in ("parent_profile.sql","alias_profile.sql","alias_bucket.sql")},
        "cross_table_consistency":"matching before/after content digests; no atomic cross-table version pin"}
    if MANIFEST.exists():
        if read(MANIFEST)!=document:
            raise ValueError("A frozen source manifest cannot be replaced")
    else:
        write(MANIFEST,document)
    return document


def load_bucket(manifest, number, parents):
    bucket = manifest["buckets"][str(number)]
    path = CAPTURE/bucket["file"]
    if digest(path)!=bucket["file_sha256"]:
        raise ValueError(f"Frozen alias bucket {number} changed")
    query, rows, _ = _page(number,bucket["profile"],parents)
    if query!=bucket["query_id"]:
        raise ValueError("Frozen alias query lineage changed")
    eligible,held = defaultdict(list),defaultdict(list)
    for row in rows:
        key = row["inci_id"]
        reason = _eligible_alias(row,manifest["parent_cutoff_epoch_ms"])
        if reason:
            held[key].append({"id":row["inci_alias_id"],"type":row["alias_type"],"reason":reason})
        else:
            eligible[key].append({k:row[k] for k in ("inci_alias_id","alias_type","alias","source","lang")})
    return eligible,held,path


if __name__=="__main__":
    m = freeze()
    print(f"Verified {m['parent_count']:,} registered parents and {m['alias_count']:,} original companion rows.")
