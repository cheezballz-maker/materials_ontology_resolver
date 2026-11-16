"""Pilot input adapters and capture of previously retrieved provider records."""

from collections import Counter
from dataclasses import replace
import json

from canonical_registry.chemistry import describe
from canonical_registry.cosing_pilot.full_capture import read, write, digest as file_digest
from canonical_registry.identity_sufficiency import evaluate as previous
from canonical_registry.identity_sufficiency.adapters import COSING_DOC, cosing, gsrs
from canonical_registry.identity_sufficiency.contract import Claim, digest, structure_signature
from providers import GSRS
from .cohort import DATA
from .lookup import SourceReferent, AuthorityRecord, normalize

ROOT = DATA.parents[1]
FIELDS = ("chemical_id", "source_id", "chemical_name", "ingredient_type", "substance_type",
          "smiles", "inchikey", "molecular_formula", "source", "updated_ts", "routes")


def warehouse():
    cohort = read(DATA / "cohort.json")
    freeze = read(DATA / "freeze.json")
    if file_digest(DATA / "cohort.json") != freeze["cohort_sha256"]:
        raise ValueError("Frozen cohort digest mismatch")
    results, shards = {}, []
    for number, sql in enumerate(sorted(freeze["sql"])):
        path = DATA / sql
        if file_digest(path) != freeze["sql"][sql]:
            raise ValueError("Frozen query digest mismatch")
        capture = read(path.with_suffix(".json"))
        expected = {r["concept_id"] for r in cohort[60 * number:60 * (number + 1)]}
        seen = set()
        if not capture.get("query_id") or len(capture["rows"]) > len(expected):
            raise ValueError("Invalid bounded query receipt")
        for row in capture["rows"]:
            ref = row["ref"]
            if ref not in expected or ref in seen:
                raise ValueError("Unexpected or duplicate source key in query receipt")
            seen.add(ref)
            candidates = [dict(zip(FIELDS, record, strict=True)) for record in json.loads(row["candidates"])]
            total = int(row["total_candidates"])
            if len(candidates) != min(10, total) or len({c["chemical_id"] for c in candidates}) != len(candidates):
                raise ValueError("Candidate count does not match query receipt")
            for candidate in candidates:
                candidate["routes"] = json.loads(candidate["routes"])
            results[ref] = (total, candidates)
        shards.append({"sql": sql, "receipt": path.with_suffix(".json").name, "query_id": capture["query_id"],
                       "seconds": capture["elapsed_seconds"], "rows": len(seen),
                       "receipt_sha256": file_digest(path.with_suffix(".json"))})
    return cohort, results, shards


def cosing_input(row):
    parent = row["parent"]
    evidence = cosing(row, parent, row["aliases"])
    names = tuple(a for a in row["aliases"] if a["alias_type"] in {"IUPAC", "INN_ISO_AN", "INCI", "INCI_USA"}
                  and isinstance(a["alias"], str) and a["alias"].strip())
    claims = tuple(Claim("lookup-source-name:" + a["inci_alias_id"], "REPORTED_NAME", a["alias"],
                         "SCOPE_UNESTABLISHED", row["concept_id"], a["source"] or "CosIng", (), COSING_DOC,
                         a["inci_alias_id"], digest(a), namespace=a["alias_type"]) for a in names)
    evidence = replace(evidence, claims=(*evidence.claims, *claims))
    graphs = []
    for claim in evidence.claims:
        if claim.kind in {"SMILES", "INCHI"}:
            try:
                graphs.append(structure_signature(describe(claim.value, claim.kind.lower())))
            except (ValueError, RuntimeError):
                evidence = replace(evidence, holds=(*evidence.holds, "INVALID_REPORTED_GRAPH"))
    return SourceReferent(
        evidence=evidence, record_type="CosIng ingredient record",
        names=tuple(dict.fromkeys((parent["inci"], *(a["alias"] for a in names)))),
        definition=parent.get("description") or "",
        identifiers={n: tuple(sorted({v.strip() for v in parent[k] or [] if isinstance(v, str) and v.strip()}))
                     for n, k in (("CAS", "cas_nos"), ("EC", "ec_nos"))},
        graph_signatures=tuple(sorted(set(graphs))),
    )


def _manifest_record(path, payload, provider):
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": file_digest(path),
            "url": payload.get("url"), "retrieved_at": payload.get("retrieved_at"), "provider": provider}


def capture_archives(cohort, results, controls):
    names = {normalize(n) for row in cohort for n in row["queries"]["NAME"]}
    names.update(normalize(a["alias"]) for row in cohort for a in row["aliases"]
                 if a["alias_type"] in {"IUPAC", "INN_ISO_AN"} and a.get("alias"))
    keys = {key for row in cohort for key in row["queries"]["INCHIKEY"]}
    hits = [x for _, rows in results.values() for x in rows] + controls
    uniis = {x["source_id"] for x in hits}
    keys.update(x["inchikey"] for x in hits if x.get("inchikey"))
    cache = {"GSRS": [], "ChEBI": [], "PubChem": []}
    counts = Counter()
    seen_files = set()
    for provider, glob in (("GSRS", "*/run/gsrs_cache"), ("ChEBI", "*/run/chebi_cache"),
                           ("PubChem", "*/run/http_cache")):
        for directory in sorted(ROOT.glob(glob)):
            for path in sorted(directory.glob("*.json")):
                key = provider, path.name
                if key in seen_files:
                    continue
                try:
                    payload = read(path)
                except (OSError, ValueError):
                    counts[provider + "_unreadable"] += 1
                    continue
                if payload.get("status") != "SUCCESS":
                    continue
                seen_files.add(key)
                body = payload.get("data") or {}
                if not isinstance(body, dict):
                    continue
                if provider == "GSRS":
                    if body.get("approvalID") not in uniis or not body.get("structure"):
                        continue
                    records = [body]
                elif provider == "ChEBI":
                    if not body.get("chebi_accession") or not (
                        normalize(body.get("ascii_name") or "") in names or
                        (body.get("default_structure") or {}).get("standard_inchi_key") in keys
                    ):
                        continue
                    records = [body]
                else:
                    original = payload.get("rows") or body.get("PropertyTable", {}).get("Properties", [])
                    records = [r for r in original if r.get("CID") and (
                        r.get("InChIKey") in keys or normalize(payload.get("query") or "") in names)]
                if records:
                    cache[provider].append({"capture": _manifest_record(path, payload, provider), "records": records})
    native = previous.NATIVE
    payload = read(native)
    if payload["approvalID"] in uniis:
        cache["GSRS"].append({"capture": _manifest_record(native, {"url": previous.NATIVE_URL}, "GSRS"),
                             "records": [payload]})
    references = previous.DATA / "authority_receipts.json"
    # Only archived authority facts. No prior ingredient-keyed binding or eligibility.
    cache["NIST_ECHA_FDA"] = {"capture": _manifest_record(references, {}, "archived authority facts"),
                            "records": list(read(references)["gsrs"].values())}
    extracted = DATA / "nist_webbook.json"
    if extracted.exists():
        cache["NIST"] = {"capture": _manifest_record(extracted, {}, "NIST Chemistry WebBook"),
                         "records": read(extracted)}
    write(DATA / "authority_cache.json", {"providers": cache, "archive_diagnostics": dict(counts)})


def authority_records(cache):
    by_unii, supplemental, rejected = {}, [], []
    for entry in cache["GSRS"]:
        for record in entry["records"]:
            try:
                native = GSRS.record(record, entry["capture"]["url"])
                if not native["structure_references"]:
                    raise ValueError("GSRS_STRUCTURE_REFERENCES_MISSING")
            except (ValueError, RuntimeError, KeyError) as exc:
                rejected.append({"UNII": record.get("approvalID"), "reason": str(exc), "capture": entry["capture"]})
                continue
            names = tuple(n["name"] for n in record.get("names", []) if n.get("name") and n.get("displayName")
                          and not n.get("deprecated"))
            cas = tuple(sorted({c["code"] for c in record.get("codes", []) if c.get("code")
                               and c.get("codeSystem") == "CAS" and c.get("type") == "PRIMARY"}))
            item = AuthorityRecord(
                entity="UNII:" + native["UNII"], authority="NCATS GSRS native", structure_type="SMILES",
                structure=native["SMILES"], inchikey=native["InChIKey"], names=names,
                identifiers={"UNII": (native["UNII"],), "CAS": cas},
                document=native["url"], locator="structure; integer moieties; referenced definition",
                provenance={**entry["capture"], "structure_references": native["structure_references"],
                            "native_revision": record.get("version"), "native_names": native["names"]},
                complete_composition=True,
            )
            by_unii.setdefault(native["UNII"], []).append(item)
    for entry in cache["NIST_ECHA_FDA"]["records"]:
        item = AuthorityRecord(
            entity=entry["entity"], authority="NIST Chemistry WebBook", structure_type="INCHI",
            structure=entry["structure"]["inchi"], inchikey=entry["structure"]["key"],
            names=(entry["preferred_name"],), identifiers={"UNII": (entry["unii"],), "CAS": (entry["cas"],),
                                                            "EC": (entry["ec"],)},
            document=entry["structure"]["url"], locator="Standard InChI",
            provenance={**cache["NIST_ECHA_FDA"]["capture"], "ECHA": entry["echa"], "FDA": entry["fda_url"],
                        "FDA_key": entry["fda_key"], "formula": entry["fda_formula"]},
        )
        by_unii.setdefault(entry["unii"], []).append(item)
    for entry in cache.get("NIST", {}).get("records", []):
        item = AuthorityRecord(
            entity="NIST:" + entry["id"], authority="NIST Chemistry WebBook", structure_type="INCHI",
            structure=entry["inchi"], inchikey=entry["key"], names=(entry["name"],),
            identifiers={"CAS": (entry["cas"],)}, document=entry["url"], locator="IUPAC Standard InChI",
            provenance={**cache["NIST"]["capture"], "formula": entry["formula"],
                        "supporting_document": entry["url"],
                        "stage_c_cas_cross_reference": entry.get("cross_reference") == "NIST_SPECIES_CAS"},
        )
        by_unii.setdefault("CAS:" + entry["cas"], []).append(item)
    for provider in ("PubChem", "ChEBI"):
        for entry in cache[provider]:
            for record in entry["records"]:
                if provider == "PubChem":
                    entity = "CID:" + str(record["CID"])
                    names = (record.get("IUPACName") or "",)
                    graph = record.get("SMILES") or record.get("IsomericSMILES")
                    expected = record.get("InChI"), record.get("InChIKey")
                else:
                    entity = record["chebi_accession"]
                    names = (record.get("ascii_name") or "",)
                    structural = record.get("default_structure") or {}
                    graph = structural.get("smiles")
                    expected = structural.get("standard_inchi"), structural.get("standard_inchi_key")
                status = "NO_SUPPORTED_MOLECULAR_GRAPH"
                if graph:
                    try:
                        parsed = describe(graph)
                        status = ("STRICT_STRUCTURE_AGREES" if expected == (parsed["inchi"], parsed["inchikey"])
                                  else "STRUCTURAL_DESCRIPTORS_DIFFER")
                    except (ValueError, RuntimeError):
                        status = "INVALID_STRUCTURE"
                supplemental.append({"entity": entity, "authority": provider, "names": names, "structure": graph,
                                     "inchikey": expected[1], "validation": status, "capture": entry["capture"],
                                     "role": "CANDIDATE_ONLY"})
    return by_unii, supplemental, rejected


def gsrs_controls():
    return previous._inputs()


def gsrs_input(row, companions):
    evidence = gsrs(row, companions)
    return SourceReferent(evidence, row["substance_type"], (row["chemical_name"],), "",
                          {"UNII": (row["source_id"],)})
