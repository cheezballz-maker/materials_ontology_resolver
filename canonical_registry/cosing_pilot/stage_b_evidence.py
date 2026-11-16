"""Verify the companion capture and qualify source-bound original assertions."""

from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
import json
from uuid import UUID

from .full_capture import digest, read, write
from .stage_b_cohort import OUTPUT, PARENT_ARCHIVE

INTERPRETATION_TYPES = {"SMILES","INCHI","INCHI_KEY","MOLECULAR_FORMULA","CAS_NO","EC_NO"}


def archive():
    capture = OUTPUT/"_capture"
    meta = read(capture/"metadata.json")
    cohort = read(OUTPUT/"cohort.json")
    parent_manifest = read(PARENT_ARCHIVE.with_name("source_snapshot_manifest.json"))
    if cohort["parent_sha256"] != parent_manifest["snapshot_sha256"] or digest(PARENT_ARCHIVE) != cohort["parent_sha256"]:
        raise ValueError("The cohort does not belong to the registered parent archive")
    for phase in ("before","after"):
        profile = meta[phase]["parent"]["rows"]
        if profile != parent_manifest["before_profile"]["rows"]:
            raise ValueError("Parent claims or keys changed since registration")
    for key in ("alias_scope","chem_scope"):
        if meta["before"][key]["rows"]!=meta["after"][key]["rows"]:
            raise ValueError(f"Source relationship profile changed during capture: {key}")
    all_keys = {r["inci_id"] for r in read(PARENT_ARCHIVE)}
    selected = {r["parent"]["inci_id"] for r in cohort["records"]}
    results = {}
    for name, valid in (("alias",selected),("chem",all_keys)):
        profile = meta["before"][name+"_profile"]["rows"]
        if profile != meta["after"][name+"_profile"]["rows"] or int(profile[0]["bucket"]) < 0:
            raise ValueError(f"{name} source content or valid parent keys changed during capture")
        schema = meta["schema"][name]["rows"]
        names = [f["column_name"] for f in schema]
        arrays = {f["column_name"] for f in schema if f["data_type"].startswith("array(")}
        archived, parents, record_keys, pages = [], set(), set(), []
        for bucket in profile:
            number = int(bucket["bucket"])
            page = read(capture/f"{name}_{number}.json")
            if len(page["rows"]) != int(bucket["rows_total"]) or len(page["rows"]) >= 1000:
                raise ValueError(f"{name} capture page size mismatch")
            checksum = sha256()
            for row in page["rows"]:
                key, record_key = row["inci_id"], row.get("row_key")
                packet = row["packet"]
                record = dict(zip(names,json.loads(packet),strict=True))
                expected_key = record.get("inci_alias_id") if name=="alias" else key
                if key not in valid or key != record["inci_id"] or record_key != expected_key or record_key in record_keys:
                    raise ValueError(f"{name} source relationship mismatch or duplicate")
                checksum.update(sha256(packet.encode()).hexdigest().upper().encode())
                record_keys.add(record_key)
                parents.add(key)
                for field in arrays:
                    if record[field] is not None:
                        record[field] = json.loads(record[field])
                archived.append(record)
            if checksum.hexdigest().upper() != bucket["sha256"].upper():
                raise ValueError(f"{name} raw packet digest mismatch in bucket {number}")
            pages.append({k:v for k,v in page.items() if k!="rows"})
        if name=="alias" and parents!=selected:
            raise ValueError("The alias capture does not cover every selected parent")
        if name=="chem" and len(archived)!=int(meta["before"]["chem_scope"]["rows"][0]["rows_total"]):
            raise ValueError("Chemistry capture does not cover the verified full source count")
        path = OUTPUT/("aliases.json" if name=="alias" else "chemistry.json")
        archived.sort(key=lambda r:(r["inci_id"],r.get("inci_alias_id") or ""))
        write(path,archived)
        results[name] = {"file":path.name,"sha256":digest(path),"records":len(archived),"parent_keys":len(parents),
                         "pages":pages,"scope":"bounded selected parents" if name=="alias" else "whole companion table"}
    cutoff = int(datetime.fromisoformat(parent_manifest["started_utc"]).timestamp()*1000)
    write(OUTPUT/"companion_manifest.json",{"parent_sha256":cohort["parent_sha256"],"parent_cutoff_epoch_ms":cutoff,
          "cohort_sha256":digest(OUTPUT/"cohort.json"),"archives":results,"atomic_cross_table_pin":False,**meta})


def _eligible_alias(row, cutoff):
    kind, value = row["alias_type"], row["alias"]
    if not isinstance(kind,str) or not kind.strip():
        return "MISSING_ALIAS_TYPE"
    if kind not in INTERPRETATION_TYPES:
        return "ARCHIVE_ONLY_ALIAS_TYPE"
    try:
        key = row["inci_alias_id"]
        if str(UUID(key))!=key:
            return "INVALID_ALIAS_RECORD_ID"
        timestamps = [int(row[field]) for field in ("created_ts","updated_ts") if row[field] is not None]
    except (TypeError,ValueError):
        return "INVALID_ALIAS_PROVENANCE"
    if not timestamps or max(timestamps)>cutoff:
        return "ALIAS_REVISION_UNESTABLISHED_FOR_PARENT_CAPTURE"
    if row["data_status"]!="1":
        return "ALIAS_STATUS_NOT_ACTIVE"
    if not isinstance(value,str) or not value.strip() or any(ord(c)<32 and c not in "\t\r\n" for c in value):
        return "INVALID_OR_EMPTY_ORIGINAL_VALUE"
    return None


def verified():
    manifest = read(OUTPUT/"companion_manifest.json")
    if manifest["cohort_sha256"]!=digest(OUTPUT/"cohort.json"):
        raise ValueError("Cohort digest changed")
    evidence = defaultdict(list)
    held = defaultdict(list)
    counts = Counter()
    for name,item in manifest["archives"].items():
        path = OUTPUT/item["file"]
        if digest(path)!=item["sha256"]:
            raise ValueError(f"Companion archive changed: {name}")
        if name!="alias":
            continue  # The chemistry file is provenance only, regardless of reported confidence.
        for row in read(path):
            reason = _eligible_alias(row,manifest["parent_cutoff_epoch_ms"])
            if reason:
                held[row["inci_id"]].append({"id":row["inci_alias_id"],"type":row["alias_type"],"reason":reason})
                counts[reason] += 1
            else:
                evidence[row["inci_id"]].append({k:row[k] for k in ("inci_alias_id","alias_type","alias","source","lang")})
                counts["accepted_for_candidate_interpretation"] += 1
    return manifest,evidence,held,dict(counts)


if __name__=="__main__":
    archive()
