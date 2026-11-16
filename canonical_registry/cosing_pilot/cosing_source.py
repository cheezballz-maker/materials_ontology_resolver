"""Lossless CosIng claim intake for domain registration."""

import json
from uuid import UUID

from .registry import canonical, fingerprint
from .staged_registry import Observation

PARENT = "mse_dwd.dwd_mse_cosmetics_incis"
FIELDS = ("inci_id", "inci", "description", "cas_nos", "ec_nos", "functions", "data_status")
ARRAYS = ("cas_nos", "ec_nos", "functions")
ALIAS_FIELDS = ("inci_alias_id", "alias_type", "alias", "source", "lang")


def _array(value):
    value = json.loads(value) if isinstance(value, str) else value
    if value is not None and not isinstance(value, list):
        raise ValueError("Expected a source array or null")
    return value


def observation(row, companion=None, *, migrate_legacy=False):
    key = row.get("inci_id")
    if not isinstance(key, str) or str(UUID(key)) != key:
        raise ValueError("Expected the original CosIng UUID")
    source = {field: row.get(field) for field in FIELDS}
    original = dict(source)
    for field in ARRAYS:
        values = _array(source[field])
        if values is not None:
            source[field] = sorted(values, key=canonical)
    aliases = None
    evidence = companion if companion is not None else row
    if evidence.get("inci_id") != key:
        raise ValueError("Companion evidence must bind to the same CosIng UUID")
    if "alias_count" in evidence:
        claims = _array(evidence.get("alias_claims")) or []
        if len(claims) != int(evidence["alias_count"]):
            raise ValueError("Truncated CosIng alias packet")
        aliases = sorted(({field: alias.get(field) for field in ALIAS_FIELDS} for alias in claims), key=canonical)
        ids = [alias["inci_alias_id"] for alias in aliases]
        if None in ids or len(set(ids)) != len(ids):
            raise ValueError("Source alias IDs must be present and unique per packet")
    payload = {"source": source, "aliases": aliases}
    legacy = fingerprint({"source": original, "companion_evidence": companion}) if migrate_legacy else None
    return Observation(f"{PARENT}:{key}", row.get("inci"), fingerprint(payload), payload, row.get("updated_ts"), legacy)
