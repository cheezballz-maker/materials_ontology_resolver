"""Acquire and pin each v5 phase before running the existing Stage C lifecycle."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
from time import perf_counter, sleep
from urllib.parse import urlencode

from canonical_registry.authoritative_lookup.sources import file_digest, read, write
from ..captures import inputs
from ..cohort import DATA
from ..v3_authority import KEY, acquire as acquire_provider
from .authority_access import GSRS, capture
from .stereo_binding import systematic_name
from .v3_reference import acquire as acquire_nist

ROOT = DATA / "v5"
BOUNDARIES = (0, 200, 800, 2000)
CAS = re.compile(r"\d{2,7}-\d{2}-\d")
ACCESSION = re.compile(r"[A-Z0-9]{10}")
AUTHORITY_FILES = ("provider_queue.json", "gsrs_queue.json", "identifier_queue.json",
                   "gsrs_capture.json", "pubchem_capture.json", "chebi_capture.json", "identifier_reference.json")


def phase_path(number):
    return ROOT / f"phase-{number}-frozen"


def acquire_gsrs(directory):
    path = directory / "gsrs_capture.json"
    packet = read(path)
    records = packet["records"]

    def fetch(key, url):
        if key not in records:
            records[key] = capture(url)
            write(path, packet)
            sleep(.35)
        return records[key].get("data", {})

    for code in read(directory / "gsrs_queue.json"):
        search = fetch("unii_" + code, GSRS + "substances/search?" +
                       urlencode({"q": "root_approvalID:" + code, "top": 3}))
        exact = [r for r in search.get("content", []) if r.get("approvalID") == code]
        if len(exact) == 1 and re.fullmatch(r"[a-fA-F0-9-]{36}", exact[0].get("uuid") or ""):
            fetch("native_" + code, GSRS + "substances(" + exact[0]["uuid"] + ")?view=full")


def acquire(number, *, retry_transport=False):
    start, end = BOUNDARIES[number - 1:number + 1]
    _, warehouse, _ = inputs(ROOT, fresh_limit=end)
    phase_rows = read(ROOT / "fresh.json")[start:end]
    directory = phase_path(number)
    directory.mkdir(exist_ok=True)
    seal = directory / ("retry_seal.json" if retry_transport else "seal.json")
    if seal.exists():
        raise FileExistsError("Phase inputs already sealed")
    if retry_transport:
        original = directory
        directory = directory / "retry"
        directory.mkdir(exist_ok=True)
        for name in (*AUTHORITY_FILES[:3], "queue_coverage.json"):
            if not (directory / name).exists():
                write(directory / name, read(original / name))
    if not (directory / "queue_coverage.json").exists() or read(directory / "queue_coverage.json").get("first_id") != phase_rows[0]["concept_id"]:
        keys, accessions, cases = {}, {}, {}
        for row in phase_rows:
            if row["stratum"] in {"broad", "conflict"}:
                continue
            cid = row["concept_id"]
            _, candidates = warehouse.get(cid, (0, ()))
            for key in row["queries"]["INCHIKEY"]:
                if KEY.fullmatch(key):
                    keys.setdefault(key, cid)
            for candidate in candidates:
                if candidate["substance_type"] == "chemical" and candidate["smiles"]:
                    code, key = candidate["source_id"], candidate["inchikey"]
                    if ACCESSION.fullmatch(code):
                        accessions.setdefault(code, cid)
                    if key and KEY.fullmatch(key):
                        keys.setdefault(key, cid)
            codes = row["queries"]["CAS"]
            if len(codes) == 1 and CAS.fullmatch(codes[0]):
                priority = 0 if systematic_name(row["parent"]["inci"]) else 1 if row["stratum"] == "forms" else 2
                cases.setdefault(codes[0], {"cas": codes[0], "referent": cid, "priority": priority})
        budgets = (100, 220, 360)
        limit = budgets[number - 1]
        write(directory / "provider_queue.json", dict(list(keys.items())[:limit]))
        write(directory / "gsrs_queue.json", list(accessions)[:limit])
        write(directory / "identifier_queue.json", sorted(cases.values(), key=lambda x: x["priority"])[:limit])
        write(directory / "queue_coverage.json", {"fresh": len(phase_rows), "first_id": phase_rows[0]["concept_id"], "keys_available": len(keys),
              "uniis_available": len(accessions), "cas_available": len(cases), "per_queue_budget": limit})
    previous = phase_path(number - 1)
    if (previous / "retry_seal.json").exists():
        previous = previous / "retry"
    for name in AUTHORITY_FILES[3:]:
        destination = directory / name
        if destination.exists():
            continue
        old = ROOT / f"phase-{number}"
        if (old / "retry" / name).exists():
            old /= "retry"
        source = original / name if retry_transport else old / name
        if not source.exists():
            source = DATA / "v4" / name
        evidence = read(source)
        if (previous / name).exists():
            prior = read(previous / name)
            if name == "gsrs_capture.json":
                evidence["records"].update(prior["records"])
            else:
                evidence.update(prior)
        if retry_transport or source.parent != DATA / "v4":
            packets = evidence["records"] if name == "gsrs_capture.json" else evidence
            failed = {"DNS_FAILURE", "TRANSPORT_FAILURE", "TLS_FAILURE", "TIMEOUT", "RETRIEVAL_FAILED"}
            discarded = {key: value for key, value in packets.items() if value["status"] in failed}
            for key in discarded:
                del packets[key]
        if name == "identifier_reference.json":
            # The prior review capture is now a development reference.
            ref = read(DATA / "v4/reference_capture.json")["28069-72-9"]
            evidence[ref["cas"]] = ref
        write(destination, evidence)
    begin = perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(acquire_provider, provider, directory) for provider in ("pubchem", "chebi")]
        jobs += [pool.submit(acquire_gsrs, directory),
                 pool.submit(acquire_nist, directory, "identifier_queue.json", "identifier_reference.json")]
        for job in jobs:
            job.result()
    write(directory / "acquisition_performance.json", {"elapsed_seconds": perf_counter() - begin})
    evidence = [directory / name for name in (*AUTHORITY_FILES, "queue_coverage.json", "acquisition_performance.json")]
    evidence += [ROOT / name for name in ("fresh.json", "freeze.json", "exclusions.json", "blind_source_packets.json")]
    for i in range((end + 59) // 60):
        evidence.extend(ROOT / f"lookup_{i:02}{suffix}" for suffix in (".json", "_executed.sql"))
    write(seal, {str(p.relative_to(ROOT)): file_digest(p) for p in evidence})


def prepare(directory, number, *, create, checkpoint_only):
    start, end = BOUNDARIES[number - 1:number + 1]
    authority = phase_path(number)
    seal = authority / "seal.json"
    if (authority / "retry_seal.json").exists():
        seal = authority / "retry_seal.json"
        authority = authority / "retry"
    if any(file_digest(ROOT / path) != sha for path, sha in read(seal).items()):
        raise ValueError("Sealed v5 evidence changed")
    cache = index_path(directory)
    if create and (directory.exists() or cache.exists()):
        raise FileExistsError("Use a fresh fixture and dedicated index or resume the existing fixture")
    if number > 1:
        previous = phase_path(number - 1)
        blocked = previous / "blocked.json"
        if blocked.exists():
            raise ValueError("Previous phase has a quarantined whole-referent assignment")
        prior = read(previous / "acceptance.json")
        previous_seal = previous / ("retry_seal.json" if (previous / "retry_seal.json").exists() else "seal.json")
        if not prior["passed"] or prior["evidence_seal"] != file_digest(previous_seal):
            raise ValueError("Previous phase did not pass its safety gate")
        if prior["stereo_binding"] != file_digest(Path(__file__).with_name("stereo_binding.py")):
            raise ValueError("The reviewed v5 qualification policy has changed")
    if checkpoint_only:
        index = read(directory / "index_seal.json")
        if file_digest(cache) != index["sha256"] or index["phase_seal"] != file_digest(seal):
            raise ValueError("Sealed v5 derived cache changed")
    elif (directory / "index_seal.json").exists():
        raise ValueError("Sealed v5 run is available for checkpoint replay")
    return {"start": start, "end": end, "authority": authority, "cache": cache, "seal": file_digest(seal),
            "seal_path": str(seal.relative_to(ROOT))}


def index_path(directory):
    return DATA.parent.parent / "enrichment/local" / ("stage_c_v5_" + directory.name + ".sqlite")


def verify_phase(number, directory):
    from xml.etree.ElementTree import parse
    from .verify import verify
    from .v4 import POSITIVE, UNRESOLVED, records, verify_history
    from ..run import run

    metrics = verify(directory)
    suites = parse(ROOT / "tests.xml").getroot().findall("testsuite")
    if not suites or any(int(s.get(field, "0")) for s in suites for field in ("errors", "failures")):
        raise ValueError("Safety regression suite has not passed")
    substance, concepts, decisions, aliases, snapshot = records(directory)
    fresh_ids = {row["concept_id"] for row in read(ROOT / "fresh.json")}
    by_name = {r["designation"]: r for r in decisions if r["referent"] not in fresh_ids}
    for label in UNRESOLVED | POSITIVE:
        row = by_name[label]
        if (label in POSITIVE and row["status"] != "RESOLVED_SUBSTANCE") or (
                label in UNRESOLVED and row["status"] != "UNRESOLVED"):
            raise ValueError(f"Historical control failed: {label}")
        if label in UNRESOLVED and row["source"] in aliases:
            raise ValueError(f"Historical held alias was asserted: {label}")
    stereo = by_name["2-TRANS, 6-CIS-NONADIENOL"]
    if (stereo["status"] != "RESOLVED_SUBSTANCE" or
            stereo["eligibility"]["specificity"]["inchikey"] != "AMXYRHBJZOVHOL-ODYTWBPASA-N"):
        raise ValueError("Known stereochemical false rejection did not close")
    cache = index_path(directory)
    phase_root = phase_path(number)
    seal = phase_root / ("retry_seal.json" if (phase_root / "retry_seal.json").exists() else "seal.json")
    from rdkit import rdBase
    import derived_index
    index = {"sha256": file_digest(cache), "phase_seal": file_digest(seal), "rdkit": rdBase.rdkitVersion,
             "engine_version": derived_index.engine_version(), "fixture_sha256": file_digest(substance),
             "build_inputs": read(directory / "manifest.json")["pins"],
             "policies": read(directory / "manifest.json")["policies"]}
    write(directory / "index_seal.json", index)
    before = (file_digest(substance), file_digest(concepts))
    original = (directory / "run.json").read_bytes()
    try:
        replay = run(directory, v5=True, expansion_phase=number, checkpoint_only=True)
    finally:
        (directory / "run.json").write_bytes(original)
    after = records(directory)
    if (before != (file_digest(substance), file_digest(concepts)) or
            after[2:] != (decisions, aliases, snapshot) or file_digest(cache) != index["sha256"] or
            replay["checkpoint_replays"] != len(decisions)):
        raise ValueError("v5 replay did not reproduce the sealed phase")
    history = verify_history()
    from .v4 import ROOT as V4
    prior_index = read(V4 / "derived_index_seal.json")
    if file_digest(Path(prior_index["path"])) != prior_index["sha256"] or any(
            file_digest(V4 / name) != sha for name, sha in read(V4 / "acquisition_freeze.json")["sha256"].items()):
        raise ValueError("Historical v4 evidence or dedicated cache changed")
    history += len(read(V4 / "acquisition_freeze.json")["sha256"]) + 1
    write(directory / "replay_results.json", {"checkpoint_replays": len(decisions), "canonical_digest": snapshot,
          "fixture_sha256": before, "elapsed_seconds": replay["elapsed_seconds"], "historical_paths": history})
    return metrics


def accept(number, directory, review):
    """Advance only after saved review covers every fresh assignment in the phase."""
    from .v4 import records

    phase_root = phase_path(number)
    manifest = read(directory / "manifest.json")
    if (manifest.get("v5_phase") != number or not (directory / "replay_results.json").exists()
            or (directory / "quarantine.json").exists() or (phase_root / "blocked.json").exists()):
        raise ValueError("A verified replay is required")
    _, _, decisions, aliases, _ = records(directory)
    fresh = {r["concept_id"] for r in read(ROOT / "fresh.json")}
    exact = {r["referent"]: r for r in decisions if r["referent"] in fresh
             and r["status"] == "RESOLVED_SUBSTANCE"}
    findings = read(review)
    if (not exact or set(findings) != set(exact) or any(
            r["structure"] != "SUPPORTED" or r["whole_referent"] != "SUPPORTED" or
            (exact[key]["source"] in aliases and r["alias"] != "SUPPORTED") or not r["references"]
            for key, r in findings.items())):
        raise ValueError("Positive review incomplete or contains a critical finding")
    write(phase_root / "acceptance.json", {"passed": True, "evidence_seal": manifest["evidence"]["v4_inputs"],
          "stereo_binding": manifest["policies"]["stereo_binding"],
          "review_sha256": file_digest(review), "exact_records_reviewed": len(exact),
          "verified_replay_sha256": file_digest(directory / "replay_results.json")})


def review_inputs(directory):
    """Export case packets with predictions withheld for external review."""
    from .v4 import records

    number = read(directory / "manifest.json")["v5_phase"]
    start, end = BOUNDARIES[number - 1:number + 1]
    cohort = {r["concept_id"]: r for r in read(ROOT / "fresh.json")[start:end]}
    planned = {r["concept_id"] for r in read(ROOT / "blind_source_packets.json") if r["phase"] == number}
    _, _, decisions, _, _ = records(directory)
    selected = planned | {r["referent"] for r in decisions if r["status"] == "RESOLVED_SUBSTANCE"}
    packets = []
    for row in sorted(decisions, key=lambda r: r["referent"]):
        key = row["referent"]
        if key not in cohort or key not in selected:
            continue
        original = cohort[key]["parent"]
        graphs = [c["candidate"]["smiles"] for c in row["candidates"]
                  if c.get("candidate") and c["candidate"]["smiles"]]
        graphs.extend(s[0] for s in row["source_evidence"].get("graph_signatures", ()))
        packets.append({"referent": key, "designation": original["inci"], "definition": original["description"],
                        "revision": row["revision"], "cas": original["cas_nos"], "ec": original["ec_nos"],
                        "candidate_structures": sorted(set(graphs))})
    write(directory / "blinded_review_packets.json", packets)


def provisional_review(directory):
    """Compare pinned source and authority fields and flag incomplete positive support."""
    from canonical_registry.chemistry import describe
    from identity_comparator import compare
    from .v4 import records

    manifest = read(directory / "manifest.json")
    number = manifest["v5_phase"]
    authority = (ROOT / manifest["v5_seal_path"]).parent
    if Path(manifest["v5_seal_path"]).name == "retry_seal.json":
        authority /= "retry"
    references = read(authority / "identifier_reference.json")
    fresh = {r["concept_id"]: r for r in read(ROOT / "fresh.json")}
    _, _, decisions, aliases, _ = records(directory)
    review = {}
    flagged = []
    overrides_path = directory / "reference_findings.json"
    findings = read(overrides_path) if overrides_path.exists() else {}
    for row in decisions:
        key = row["referent"]
        if key not in fresh or row["status"] != "RESOLVED_SUBSTANCE":
            continue
        original = fresh[key]["parent"]
        codes = fresh[key]["queries"]["CAS"]
        ref = references.get(codes[0], {}) if len(codes) == 1 else {}
        receipt = row["receipt"]
        scope = row["eligibility"]["source_identity_safety"]
        binding = receipt["supporting_source_evidence"]
        graph = describe(row["eligibility"]["specificity"]["smiles"])
        comparison = None
        sources = [receipt["record_reference"]]
        if ref.get("inchi"):
            comparison = compare(graph, describe(ref["inchi"], "inchi"))["assessment"]
            sources.append(ref["url"])
        direct_claims = [x for x in scope["identifier_observations"]
                         if x["category"] == "CONSISTENT_EXACT_IDENTITY"]
        form_basis = scope["chemical_form"].get("positive_form_basis") or {}
        supported_graph = comparison in {None, "EXACT"}
        supported_source = (scope["scope"] == "EXACT_MOLECULAR_REFERENT" and
                            scope["chemical_form"]["assessment"] == "EXACT_FORM_ESTABLISHED" and
                            bool(direct_claims or binding.get("matching_identifiers") or
                                 binding.get("compared_source_graphs") or form_basis.get("claim")))
        alias = aliases.get(row["source"])
        supported_alias = not alias or (supported_source and
                                         alias == original["inci"] == binding.get("binding_value"))
        if not (supported_graph and supported_source and supported_alias):
            flagged.append(key)
        review[key] = {"designation": row["designation"], "definition": original["description"], "cas": codes,
                       "structure": "SUPPORTED" if supported_graph else "REVIEW_REQUIRED",
                       "whole_referent": "SUPPORTED" if supported_source else "REVIEW_REQUIRED",
                       "alias": "SUPPORTED" if alias and supported_alias else "REVIEW_REQUIRED" if alias else "NOT_ASSERTED",
                       "reference_comparison": comparison, "references": sources,
                       "qualification_basis": receipt["assertion_type"],
                       "independent_specialist": False,
                       "basis": "Source and authority consistency screen using shared operational evidence"}
        if key in findings:
            finding = findings[key]
            review[key]["references"].extend(finding["references"])
            review[key]["case_finding"] = finding["finding"]
            if finding["disposition"] == "REVIEW_REQUIRED":
                review[key]["whole_referent"] = "REVIEW_REQUIRED"
                if alias:
                    review[key]["alias"] = "REVIEW_REQUIRED"
                if key not in flagged:
                    flagged.append(key)
    write(directory / "provisional_positive_review.json", review)
    write(directory / "provisional_review_flags.json", {"requires_case_review": flagged})
    return len(review), flagged


def comparison(directory):
    """The new adapter preserves the v4 decision except for its named pathway."""
    from .v4 import records
    from .restricted_expansion import stats
    from collections import Counter

    substance, _, decisions, aliases, _ = records(directory)
    fresh = {r["concept_id"]: r for r in read(ROOT / "fresh.json")}
    rows = [r for r in decisions if r["referent"] in fresh]
    manifest = read(directory / "manifest.json")
    authority = (ROOT / manifest["v5_seal_path"]).parent
    if Path(manifest["v5_seal_path"]).name == "retry_seal.json":
        authority /= "retry"
    coverage = authority_coverage(rows, fresh, authority)
    scoped = {r["concept_id"]: r for r in read(ROOT / "provisional_blind_scope_screen.json")}
    reviewed_scope = [r for r in rows if r["referent"] in scoped]
    risky_scope = [r["referent"] for r in reviewed_scope if r["status"] == "RESOLVED_SUBSTANCE"]
    if risky_scope:
        write(directory / "quarantine.json", {"referents": risky_scope, "reason": "SOURCE_SCOPE_REVIEW_DISAGREEMENT"})
        raise ValueError(f"Source scope review detected exact mappings requiring quarantine: {risky_scope}")
    changed = [r for r in decisions if (r["receipt"] or {}).get("assertion_type") ==
               "EXPLICIT_STEREO_NAME_AND_SPECIES_CAS"]
    by_status = Counter(r["status"] for r in rows)
    matching = [r["timings"]["canonical_transaction_seconds"] for r in rows
                if "canonical_transaction_seconds" in r["timings"]]
    exact = [r for r in rows if r["status"] == "RESOLVED_SUBSTANCE"]
    from contextlib import closing
    from ..fixture import reader
    with closing(reader(substance)) as db:
        audit_bytes = db.execute("SELECT sum(length(compressed)) FROM resolution_audit_payload").fetchone()[0]
    write(directory / "v5_metrics.json", {
        "fresh": len(rows), "warehouse_candidates": sum(r["candidate_total"] > 0 for r in rows),
        "status": dict(by_status), "outcomes": dict(Counter(r["outcome"] for r in rows)),
        "qualification": dict(Counter(r["eligibility"]["eligibility"] for r in rows)),
        "distinct_targets": len({r["target"] for r in exact}),
        "audit_compressed_bytes": audit_bytes,
        "qualification_reasons": dict(Counter(reason for r in rows for reason in r["eligibility"]["reasons"])),
        "exact_records": [{"referent": r["referent"], "designation": r["designation"], "target": r["target"],
                           "outcome": r["outcome"]} for r in exact],
        "source_form": dict(Counter(r["eligibility"]["source_identity_safety"]["chemical_form"]["assessment"]
                                    for r in rows)),
        "aliases": sum(r["source"] in aliases for r in rows), "matching_transaction_seconds": stats(matching),
        "qualification_seconds": stats([r["timings"]["qualification_seconds"] for r in rows]),
        "scope_seconds": stats([r["timings"]["source_identity_safety_seconds"] for r in rows]),
        "authority": coverage,
        "provisionally_supported_scope_withholds": len(reviewed_scope),
        "new_pathway": [{"referent": r["referent"], "designation": r["designation"], "outcome": r["outcome"],
                         "fresh": r["referent"] in fresh, "target": r.get("target"),
                         "basis": r["receipt"]["supporting_source_evidence"]} for r in changed],
    })


def compare_v4_control():
    """Persist the same-evidence qualification comparison without registry writes."""
    from contextlib import ExitStack
    from canonical_registry.authoritative_lookup.lookup import IdentityLookup
    from canonical_registry.authoritative_lookup.sources import cosing_input
    from canonical_registry.cosing_pilot.staged_assessment import _bridge
    from canonical_registry.identity_sufficiency.contract import Evaluator
    from ..source_identity_safety import SourceIdentitySafety
    from ..v3_authority import retained_source_input
    from .stereo_binding import StereoSpeciesBinding
    from .v4 import ROOT as V4

    rows, warehouse, _ = inputs(V4)
    row = next(r for r in rows if r["concept_id"] == "CIC_00006353")
    total, candidates = warehouse[row["concept_id"]]
    refs = read(V4 / "reference_capture.json")
    source = retained_source_input(row, cosing_input(row))
    results = {}
    with ExitStack() as stack:
        bridge = _bridge(stack)
        for label, improved, evidence in (("v4_same_evidence", False, refs),
                                           ("v5_same_evidence", True, refs),
                                           ("v5_without_nist", True, {})):
            evaluator = Evaluator(bridge.official)
            existing = IdentityLookup(evaluator, {})
            existing.rejected = []
            lookup = StereoSpeciesBinding(existing, evaluator, evidence, bridge.opsin) if improved else existing
            decision, receipt, diagnostics = SourceIdentitySafety(
                lookup, evaluator, evidence, form_gate=True, name_parser=bridge.opsin
            ).evaluate(source, candidates, total)
            results[label] = {"decision": decision, "receipt": receipt, "diagnostics": diagnostics}
        results["original_opsin"] = bridge.opsin(source.evidence.designation)
    write(ROOT / "nonadienol_v4_v5_comparison.json", results)


def authority_coverage(rows, fresh, authority):
    from .authority_access import PUBCHEM, CHEBI, PROPERTIES
    from ..v3_authority import adapt, records

    pc = read(authority / "pubchem_capture.json")
    ch = read(authority / "chebi_capture.json")
    gs = read(authority / "gsrs_capture.json")["records"]
    nist = read(authority / "identifier_reference.json")
    queued_keys = read(authority / "provider_queue.json")
    queued_uniis = set(read(authority / "gsrs_queue.json"))
    queued_cas = {r["cas"] for r in read(authority / "identifier_queue.json")}
    valid_keys = set()
    for provider, packet, entry in records(authority):
        try:
            _, graph = adapt(provider, packet, entry)
        except (ValueError, RuntimeError):
            continue
        valid_keys.add(graph["inchikey"])
    counts = {"submitted_or_cached": 0, "authority_response": 0, "useful_structure": 0,
              "source_binding_receipt": 0, "no_usable_authority_evidence": 0, "conflict": 0}
    for row in rows:
        query = fresh[row["referent"]]["queries"]
        projected = [x["candidate"] for x in row["candidates"] if x.get("candidate")]
        keys = {x["inchikey"] for x in projected if x["inchikey"]} | set(query["INCHIKEY"])
        uniis = {x["source_id"] for x in projected}
        cas = set(query["CAS"])
        references = [nist[c] for c in cas if c in nist]
        packets = [gs["unii_" + u] for u in uniis if "unii_" + u in gs]
        for key in keys:
            url = PUBCHEM + "inchikey/" + key + PROPERTIES
            search = CHEBI + "es_search/?" + urlencode({"term": key, "size": 4, "page": 1})
            packets.extend(p for p in (pc.get(url), ch.get(search)) if p)
        useful = bool(row["receipt"] or valid_keys & keys or any(r["status"] == "STRUCTURAL_REFERENCE" for r in references))
        counts["submitted_or_cached"] += bool(packets or references or keys.intersection(queued_keys)
                                              or uniis & queued_uniis or cas & queued_cas)
        counts["authority_response"] += bool(any(p["status"] == "JSON_CAPTURED" for p in packets)
                                             or any(r.get("sha256") for r in references))
        counts["useful_structure"] += useful
        counts["no_usable_authority_evidence"] += not useful
        counts["source_binding_receipt"] += row["receipt"] is not None
        counts["conflict"] += row["eligibility"]["source_identity_safety"]["chemical_form"]["assessment"] == "IDENTITY_CONFLICT"
    return counts


def export_reviewed(directory):
    from .v4 import records

    _, _, decisions, aliases, _ = records(directory)
    review = read(directory / "provisional_positive_review.json")
    held = {key for key, row in review.items() if row["structure"] != "SUPPORTED" or
            row["whole_referent"] != "SUPPORTED" or row["alias"] == "REVIEW_REQUIRED"}
    write(directory / "provisional_reviewed_exports.json", {
        "status": "PROVISIONAL_ISOLATED_FIXTURE", "held_referents": sorted(held),
        "mappings": [{"referent": row["referent"], "revision": row["revision"], "target": row["target"],
                      "alias": aliases.get(row["source"])} for row in decisions
                     if row["referent"] in review and row["referent"] not in held],
    })
    if held:
        write(directory / "quarantine.json", {"reason": "EXACT_ASSERTION_REVIEW_REQUIRED", "referents": sorted(held)})
    return held


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", type=int, choices=(1, 2, 3))
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--retry-transport", action="store_true")
    args = parser.parse_args()
    if args.verify:
        review_inputs(args.verify.resolve())
        comparison(args.verify.resolve())
        print(verify_phase(args.phase, args.verify.resolve()))
    else:
        acquire(args.phase, retry_transport=args.retry_transport)
