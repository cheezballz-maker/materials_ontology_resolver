"""Verify expansion aliases and associate only dated original claims to parent keys."""

from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
import json

from .full_capture import digest, read, write
from .stage_b_cohort import PARENT_ARCHIVE
from .stage_b_evidence import _eligible_alias
from .stage_b_v2_cohort import OUTPUT

ALIAS_ARCHIVE = OUTPUT/"aliases.json"
MANIFEST = OUTPUT/"companion_manifest.json"
COHORT = OUTPUT/"cohort.json"


def assemble(output=OUTPUT,buckets=10):
    staging = output/"_capture"
    meta = read(staging/"metadata.json")
    cohort = read(output/"cohort.json")
    parent = read(PARENT_ARCHIVE.with_name("source_snapshot_manifest.json"))
    expected_parent = parent["before_profile"]["rows"]
    if (cohort["parent_sha256"]!=parent["snapshot_sha256"] or digest(PARENT_ARCHIVE)!=cohort["parent_sha256"]
            or any(meta[k]["rows"]!=expected_parent for k in ("before_parent","after_parent"))):
        raise ValueError("Registered parent source content has changed")
    profiles = meta["before_profile"]["rows"]
    if profiles!=meta["after_profile"]["rows"] or [int(r["bucket"]) for r in profiles]!=list(range(buckets)):
        raise ValueError("Bounded alias source changed or returned incomplete bucket inventory")
    columns = [c["column_name"] for c in meta["schema"]["rows"]]
    if columns!=["inci_alias_id","inci_id","alias","normalized_alias","lang","alias_type","source",
                 "created_ts","updated_ts","data_status"]:
        raise ValueError("Unexpected warehouse alias schema")
    requested = {x["parent"]["inci_id"] for x in cohort["records"]}
    parents, seen, pages, archive = set(),set(),[],[]
    for profile in profiles:
        bucket = int(profile["bucket"])
        page = read(staging/f"alias_{bucket}.json")
        if not 0<len(page["rows"])==int(profile["rows_total"])==int(profile["distinct_keys"])<1000:
            raise ValueError(f"Invalid alias page length in bucket {bucket}")
        stream = sha256()
        for raw in page["rows"]:
            packet = raw["packet"]
            record = dict(zip(columns,json.loads(packet),strict=True))
            key, alias_id = record["inci_id"], record["inci_alias_id"]
            if (key not in requested or key!=raw["inci_id"] or int(key[:4],16)%buckets!=bucket or
                    alias_id!=raw["row_key"] or alias_id in seen):
                raise ValueError(f"Duplicate or incompatible alias binding in bucket {bucket}")
            stream.update(sha256(packet.encode()).hexdigest().upper().encode())
            parents.add(key)
            seen.add(alias_id)
            archive.append(record)
        if stream.hexdigest().upper()!=profile["sha256"]:
            raise ValueError(f"Alias source content mismatch in bucket {bucket}")
        pages.append({k:v for k,v in page.items() if k!="rows"})
    if parents!=requested:
        raise ValueError("Some selected parents have no verified alias coverage")
    alias_file = output/"aliases.json"
    write(alias_file,sorted(archive,key=lambda r:(r["inci_id"],r["inci_alias_id"])))
    write(output/"companion_manifest.json",{"parent_sha256":parent["snapshot_sha256"],"cohort_sha256":digest(output/"cohort.json"),
         "alias_sha256":digest(alias_file),"aliases":len(archive),"covered_parents":len(parents),
         "parent_cutoff_epoch_ms":int(datetime.fromisoformat(parent["started_utc"]).timestamp()*1000),
         "scope":"complete for selected parent keys; no joint version pin",
         "chemistry":"prior companion archive remains source-reported and unused in interpretation",
         "pages":pages,**meta})


def verified(output=OUTPUT):
    manifest = read(output/"companion_manifest.json")
    alias_file = output/"aliases.json"
    if (manifest["cohort_sha256"]!=digest(output/"cohort.json") or manifest["alias_sha256"]!=digest(alias_file)
            or manifest["parent_sha256"]!=digest(PARENT_ARCHIVE)):
        raise ValueError("Stage B v2 source bundle changed")
    evidence, held, counts = defaultdict(list),defaultdict(list),Counter()
    for row in read(alias_file):
        reason = _eligible_alias(row,manifest["parent_cutoff_epoch_ms"])
        if reason is None:
            evidence[row["inci_id"]].append({k:row[k] for k in ("inci_alias_id","alias_type","alias","source","lang")})
            counts["eligible_original_claim"]+=1
        else:
            held[row["inci_id"]].append({"id":row["inci_alias_id"],"type":row["alias_type"],"reason":reason})
            counts[reason]+=1
    return manifest,evidence,held,dict(counts)


if __name__=="__main__":
    assemble()
