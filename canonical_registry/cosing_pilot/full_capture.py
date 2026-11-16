"""Verify all bounded Trino pages against the two full-table digest profiles."""

import argparse
from datetime import datetime
from hashlib import file_digest, sha256
import json
from pathlib import Path
from uuid import UUID

from .cosing_source import ARRAYS
from .registry import canonical

FIELDS = ("inci_id","inci","normalized_inci","description","cas_nos","ec_nos","functions",
          "created_ts","updated_ts","data_status")
BUCKETS = 48
PAGE_LIMIT = 1000
SOURCE = "delta_lake.mse_dwd.dwd_mse_cosmetics_incis"
SOURCE_COUNT = 30360


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w",encoding="utf-8",newline="\n") as stream:
        stream.write(canonical(value)+"\n")
    temporary.replace(path)


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream,"sha256").hexdigest()


def packet_rows(page, profile):
    bucket = int(profile["bucket"])
    expected = int(profile["rows_total"])
    if (page["bucket"] != bucket or expected != int(profile["distinct_keys"]) or
            expected != len(page["rows"]) or not 0 < expected < PAGE_LIMIT or int(profile["missing_label"])):
        raise ValueError(f"Incomplete or invalid warehouse bucket {bucket}")
    rows = []
    key_before = ""
    digest_stream = sha256()
    for row in page["rows"]:
        packet = row["packet"]
        key = row["inci_id"]
        values = json.loads(packet)
        if (not isinstance(values,list) or len(values) != len(FIELDS) or values[0] != key or
                str(UUID(key)) != key or int(key[:4],16) % BUCKETS != bucket or key <= key_before or
                not isinstance(values[1],str) or not values[1].strip()):
            raise ValueError(f"Invalid or repeated source key, label or packet in bucket {bucket}")
        key_before = key
        digest_stream.update(sha256(packet.encode("utf-8")).hexdigest().upper().encode("ascii"))
        record = dict(zip(FIELDS,values,strict=True))
        for field in ARRAYS:
            if record[field] is not None:
                record[field] = json.loads(record[field])
                if not isinstance(record[field],list):
                    raise ValueError(f"Invalid array in warehouse bucket {bucket}")
        rows.append(record)
    if digest_stream.hexdigest().upper() != profile["bucket_sha256"].upper():
        raise ValueError(f"Content mismatch in warehouse bucket {bucket}")
    return rows


def assemble(directory, output):
    metadata = read(directory / "metadata.json")
    before, after = metadata["before_profile"], metadata["after_profile"]
    if before["rows"] != after["rows"]:
        raise ValueError("Source count or content changed during capture")
    history_before, history_after = metadata["before_history"], metadata["after_history"]
    if not history_before["rows"] or history_before["rows"] != history_after["rows"]:
        raise ValueError("Delta history changed during capture")
    schema_before, schema_after = metadata["before_schema"], metadata["after_schema"]
    if schema_before["rows"] != schema_after["rows"] or tuple(r["column_name"] for r in schema_before["rows"]) != FIELDS:
        raise ValueError("Source schema changed or capture fields do not cover the source schema")
    profiles = before["rows"]
    if [int(row["bucket"]) for row in profiles] != list(range(BUCKETS)):
        raise ValueError("Warehouse bucket inventory was incomplete or contained invalid source keys")
    rows, pages = [], []
    for profile in profiles:
        bucket = int(profile["bucket"])
        page = read(directory / f"bucket_{bucket:02}.json")
        rows.extend(packet_rows(page,profile))
        pages.append({key:value for key,value in page.items() if key != "rows"})
    rows.sort(key=lambda row:row["inci_id"])
    if len(rows) != SOURCE_COUNT or len({row["inci_id"] for row in rows}) != len(rows):
        raise ValueError(f"Snapshot count or uniqueness disagrees with the {SOURCE_COUNT}-record baseline")
    snapshot = output / "source_snapshot.json"
    manifest = output / "source_snapshot_manifest.json"
    if snapshot.exists() or manifest.exists():
        raise FileExistsError("Choose a new destination for the verified snapshot")
    elapsed = (datetime.fromisoformat(metadata["finished_utc"])-datetime.fromisoformat(metadata["started_utc"])).total_seconds()
    write(snapshot,rows)
    write(manifest,{
        "source_table":SOURCE,"row_count":len(rows),"distinct_source_keys":len(rows),"bucket_count":BUCKETS,
        "invalid_source_keys":0,"missing_designations":0,"snapshot_file":snapshot.name,"snapshot_sha256":digest(snapshot),
        "captured_columns":list(FIELDS),"evidence_scope":"all ten parent-table columns; alias and chemistry companions deferred",
        "transport":"arrays decoded as JSON arrays; timestamps as UTC epoch-millisecond strings; status as a decimal string",
        "consistency":"VERIFIED_PRE_POST_PROFILES_AND_BUCKET_CONTENTS","atomic_version_pin":False,
        "capture_elapsed_seconds":elapsed,"pages":pages,**metadata,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args = parser.parse_args()
    assemble(args.pages,args.output)


if __name__ == "__main__":
    main()
