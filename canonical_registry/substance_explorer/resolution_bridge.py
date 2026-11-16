"""Read-only resolver calls for interactive inputs, with no source authority."""

from contextlib import ExitStack, closing
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from time import perf_counter

from .registry_search import Query, Registry, ROOT, StructureQueryLimit, proposed_smiles


STRUCTURE_TIMEOUT = 180
NAME_TIMEOUT = 25
MATCH_STATUS = {
    "UNIQUE_CANONICAL_MATCH": "EXACT_MATCH",
    "MULTIPLE_CANONICAL_MATCHES": "MULTIPLE_MATCHES",
    "NO_MATCH_IN_SEARCHED_REGISTRY": "NO_MATCH_IN_REGISTRY",
    "MATCH_UNRESOLVED": "UNRESOLVED",
    "SOURCE_CONFLICT": "UNRESOLVED",
}
REASONS = {
    "IDENTIFIER_RETRIEVAL_ONLY": "An identifier retrieves records. A separate molecular graph is needed for comparison.",
    "REFERENCE_LOOKUP_ONLY": "This input points to a stored record.",
    "UNIQUE_CANONICAL_MATCH": "Exactly one stored canonical structure represents this graph.",
    "MULTIPLE_CANONICAL_MATCHES": "More than one canonical ID represents an equivalent graph. Inspect the IDs for a possible duplicate identity.",
    "NO_MATCH_IN_SEARCHED_REGISTRY": "No equivalent canonical Substance was found in the complete searched registry snapshot.",
    "MATCH_UNRESOLVED": "The matcher could not establish uniqueness or absence.",
    "POTENTIALLY_EQUIVALENT_CANDIDATE_UNRESOLVED": "At least one registry record could not be ruled out by the comparator.",
    "SOURCE_STEREOCHEMISTRY_UNSPECIFIED": "The submitted structure leaves stereochemistry unspecified or partial.",
    "SOURCE_IDENTITY_DIMENSIONS_INCOMPLETE": "The input does not establish all required identity dimensions.",
    "REGISTRY_SNAPSHOT_UNVERIFIED": "The app could not read and verify a complete, stable snapshot.",
    "UNSUPPORTED_STRUCTURE_CAPABILITY": "The parsed structure is outside the interactive comparison capability.",
    "NO_QUALIFYING_CORROBORATION": "Local interpretation lacks the external evidence required for name-based identity.",
    "NO_VALIDATED_CANDIDATE": "Local evidence did not yield a validated molecular candidate.",
    "INCOMPLETE_SOURCE_REFERENT": "The input does not specify a complete chemical referent.",
    "SOURCE_STEREO_UNSPECIFIED": "The name leaves stereochemistry unspecified.",
    "SOURCE_TAUTOMER_SPECIFICITY_UNKNOWN": "The name does not establish a specific tautomer.",
    "SOURCE_INTERPRETATION_INCOMPLETE": "The local name interpretation leaves identity information unresolved.",
    "STEREO_SOURCE_INTENT_UNSPECIFIED": "The source name does not establish which stereochemical form was intended.",
    "EXCLUDED_MATERIAL_FAMILY": "The resolver excludes this material family from its molecular scope.",
    "STRUCTURE_PARSE_FAILED": "The input did not pass strict SMILES validation.",
    "RESOLUTION_TIME_LIMIT": "The worker reached its time limit before a complete result was available.",
    "LOCAL_ENGINE_UNAVAILABLE": "The local name engine could not start. Check the JDK and existing OPSIN bundle.",
    "RESOLUTION_WORKER_FAILED": "The local worker could not finish this evaluation.",
}


def _structure(path, query, result, *, snapshot_loader=None, policy=None):
    from chemistry import describe
    from comparison_session import qualify_source
    from correspondence_models import IncomingConcept
    from evidence_adapter_contract import EvidencePackage, structural_field
    from rdkit import rdBase
    from registry_identity_adapter import RegistrySnapshot
    from registry_matcher import RegistryMatcher
    from registry_matching_models import MatchingInput, RetrievalPolicy

    started = perf_counter()
    timings = {}
    result = {**result, "backend": "RegistryMatcher · represented graph only",
              "search_complete": False, "structural_validity": "NOT_ESTABLISHED",
              "admission_assessed": False, "timings_seconds": timings}
    try:
        with rdBase.BlockLogs():
            proposed_smiles(query.value)  # Apply the interactive input bound before InChI generation.
            descriptor = describe(query.value)
    except StructureQueryLimit as exc:
        return {**result, "status": "UNRESOLVED", "reason_codes": ["UNSUPPORTED_STRUCTURE_CAPABILITY"],
                "structural_validity": "PARSED_ONLY", "detail": str(exc)}
    except ValueError as exc:
        code = "UNSUPPORTED_STRUCTURE_CAPABILITY" if str(exc).startswith("InChI generation failed:") else "STRUCTURE_PARSE_FAILED"
        return {**result, "status": "UNRESOLVED" if code.startswith("UNSUPPORTED") else "VALIDATION_FAILED",
                "structural_validity": "PARSED_ONLY" if code.startswith("UNSUPPORTED") else "FAILED",
                "reason_codes": [code], "detail": str(exc)}

    result.update(structural_validity="PASSED", evidence=descriptor)
    timings["input_validation"] = perf_counter() - started
    stage = perf_counter()
    pkg = EvidencePackage("SubstanceExplorer", "INTERACTIVE_GRAPH", "local-query", {})
    field = structural_field(pkg, "query_graph", query.value, "query",
                             representation="USER_PROPOSED_GRAPH")
    field.source_provenance["binding_policy"] = "QUALIFIED_PARTIAL_ASSERTION"
    # This binding says only what graph the user asked to compare.
    incoming = IncomingConcept(pkg.referent_id, pkg, {
        "status": "ESTABLISHED", "kind": "EXPLICIT_STRUCTURAL_FIELD_REFERENT",
        "document": "Directly typed graph for this interactive comparison only",
        "evidence_ids": [field.evidence_id],
    }, "DEFINED_MULTICOMPONENT_COMPOSITION" if descriptor["components"] > 1 else "DISCRETE_MOLECULAR")
    with rdBase.BlockLogs():
        source = qualify_source(incoming)
    timings["input_qualification"] = perf_counter() - stage
    if source["state"] != "SUFFICIENTLY_SPECIFIED_SOURCE_IDENTITY" or not source["binding_valid"]:
        timings["worker_resolution"] = perf_counter() - started
        return {**result, "status": "UNRESOLVED", "reason_codes": source["obligations"]}

    try:
        stage = perf_counter()
        with ExitStack() as stack, rdBase.BlockLogs():
            before = ()
            if snapshot_loader is None:
                registry = Registry(path)
                before = registry.snapshot_token()
                db = stack.enter_context(closing(registry.connect()))
                db.row_factory = None
                db.execute("BEGIN")
                snapshot = RegistrySnapshot.from_connection(db)
                if registry.count != len(snapshot.entries):
                    raise ValueError("The registry identity inventory changed during loading.")
            else:
                snapshot = snapshot_loader()
            if snapshot.sqlite_integrity != [("ok",)] or snapshot.foreign_key_errors:
                raise ValueError("SQLite integrity or foreign-key checks failed.")
            timings["registry_loading"] = perf_counter() - stage
            stage = perf_counter()
            matcher = RegistryMatcher(snapshot)
            timings["retrieval_setup"] = perf_counter() - stage
            match = matcher.match_identity(
                MatchingInput(incoming), policy or RetrievalPolicy(exhaustive=True, max_candidates=None),
                timings=timings,
            )
            if snapshot_loader is None and registry.snapshot_token() != before:
                raise ValueError("The registry changed during matching.")
    except (OSError, sqlite3.Error, ValueError) as exc:
        return {**result, "status": "UNRESOLVED", "reason_codes": ["REGISTRY_SNAPSHOT_UNVERIFIED"],
                "detail": str(exc)}

    retrieval = match["retrieval"]
    uniqueness = match["uniqueness"]
    complete = retrieval["search_complete"] and uniqueness.get("accounted_records", uniqueness["compared"]) == len(snapshot.entries)
    status = MATCH_STATUS[match["status"]] if complete else "UNRESOLVED"
    sid = match["unique_matched_substance_id"] if status == "EXACT_MATCH" else None
    reasons = [match["status"], *match["source_identity"]["obligations"]]
    if not complete:
        reasons.append("REGISTRY_SNAPSHOT_UNVERIFIED")
    if uniqueness["unresolved_count"]:
        reasons.append("POTENTIALLY_EQUIVALENT_CANDIDATE_UNRESOLVED")
    indexed = set(retrieval["indexed_candidate_ids"])
    comparisons = [
        {**row, "substance_id": row["candidate_substance_id"],
         "structure": snapshot.entries[row["candidate_substance_id"]]["candidate"].structure,
         "retrieval_routes": [route["route"] for route in retrieval["routes"][row["candidate_substance_id"]]]}
        for row in match["candidate_results"]
    ]
    relevant = [row for row in comparisons if row["substance_id"] in indexed
                or row["chemical_status"] != "CHEMICALLY_DIFFERENT"]
    timings["worker_resolution"] = perf_counter() - started
    return {
        **result, "status": status, "reason_codes": list(dict.fromkeys(reasons)),
        "matched_substance_id": sid,
        "matched_name": snapshot.entries[sid]["candidate"].preferred_name if sid else None,
        "search_complete": complete, "registry_count": len(snapshot.entries),
        "snapshot_stamp": list(before),
        "compared_count": uniqueness["compared"], "accounted_count": uniqueness.get("accounted_records", uniqueness["compared"]), "excluded_count": uniqueness.get("excluded_by_necessary_condition", 0), "candidate_count": len(relevant),
        "equivalent_ids": match["supported_candidate_ids"], "relevant_ids": [r["substance_id"] for r in relevant],
        "comparisons": comparisons,
    }


class OfflineEvidence:
    """Explicitly report the absence of provider evidence to the existing resolver."""

    def name(self, value):
        return self.retrieve("name", value)

    def retrieve(self, kind, value):
        return {"status": "NOT_QUERIED", "query": value, "rows": [], "reason": "LOCAL_UI_OFFLINE"}


def _name(query, result):
    from providers import Bridge
    from resolver import Resolver

    try:
        bridge = Bridge()
    except (OSError, subprocess.SubprocessError) as exc:
        return {**result, "status": "UNSUPPORTED_SOURCE",
                "reason_codes": ["LOCAL_ENGINE_UNAVAILABLE"], "detail": str(exc)}
    try:
        offline = OfflineEvidence()
        evidence = Resolver(bridge, offline, offline).evaluate(query.value)
    finally:
        bridge.close()
    return {**result, "status": evidence["status"], "reason_codes": evidence["reason_codes"],
            "evidence": evidence, "backend": "Resolver.evaluate (local evidence)"}


def evaluate(path, query):
    result = {"input": query.raw, "interpretation": query.identifier_type or query.kind,
              "matched_substance_id": None}
    if query.kind not in {"name", "smiles"}:
        code = "IDENTIFIER_RETRIEVAL_ONLY" if query.kind == "identifier" else "REFERENCE_LOOKUP_ONLY"
        return {**result, "status": "UNRESOLVED", "reason_codes": [code]}
    # Import the matcher bootstrap to use the repository's established bindings.
    from canonical_registry.canonical_registry_matching import bootstrap  # noqa: F401

    return _name(query, result) if query.kind == "name" else _structure(path, query, result)


def resolve(path, query):
    """Isolate native chemistry and bound an interactive request."""
    if query.kind not in {"name", "smiles"}:
        return evaluate(path, query)
    fallback = {"input": query.raw, "interpretation": query.kind, "matched_substance_id": None}
    if query.kind == "smiles":
        fallback.update(search_complete=False, structural_validity="NOT_ESTABLISHED", admission_assessed=False)
    started = perf_counter()
    try:
        completed = subprocess.run(
            [sys.executable, "-B", "-m", "canonical_registry.substance_explorer.resolution_bridge", str(path)],
            cwd=ROOT.parent, input=json.dumps(asdict(query)), capture_output=True,
            encoding="utf-8", timeout=STRUCTURE_TIMEOUT if query.kind == "smiles" else NAME_TIMEOUT, check=True,
        )
        result = json.loads(completed.stdout)
        if query.kind == "smiles":
            result["timings_seconds"]["total_resolution"] = perf_counter() - started
        return result
    except subprocess.TimeoutExpired:
        return {**fallback, "status": "UNRESOLVED" if query.kind == "smiles" else "PROCESSING_FAILED",
                "reason_codes": ["RESOLUTION_TIME_LIMIT"]}
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        detail = (getattr(exc, "stderr", None) or str(exc)).strip()[-2000:]
        return {**fallback, "status": "UNRESOLVED" if query.kind == "smiles" else "PROCESSING_FAILED",
                "reason_codes": ["RESOLUTION_WORKER_FAILED"], "detail": detail}


if __name__ == "__main__":
    print(json.dumps(evaluate(Path(sys.argv[1]), Query(**json.load(sys.stdin)))))
