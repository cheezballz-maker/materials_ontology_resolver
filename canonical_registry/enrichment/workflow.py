"""Preview and commit chemical inputs through the existing chemistry and write services."""
from contextlib import ExitStack, closing
from dataclasses import asdict, dataclass
from pathlib import Path
import csv
import hashlib
import io
import json
import sqlite3
from time import perf_counter

from .development import open_development
from adapter_registry import ProviderAdapter
from chemistry import describe
from comparison_session import qualify_source
from creation_eligibility import assess
from creation_transaction import CreationService
from providers import Bridge
from registry_identity_adapter import RegistrySnapshot
from registry_matcher import RegistryMatcher
from registry_matching_models import RetrievalPolicy
from resolver import Resolver
from source_concept_models import digest
from canonical_registry.chemical_concept_registry.constraints import molecular
from canonical_registry.chemical_concept_registry.unified_chemical import reconcile_graphs
from canonical_registry.substance_explorer.registry_search import (
    Registry, Query,
)
from canonical_registry.substance_explorer.resolution_bridge import OfflineEvidence

MAX_BATCH = 30

@dataclass(frozen=True)
class ChemicalInput:
    name: str
    smiles: str = ""
    inchi: str = ""
    inchikey: str = ""
    cas: str = ""
    ec: str = ""
    inci_name: str = ""
    source_system: str = ""
    source_record_id: str = ""
    referent_key: str = "primary-record-referent"


def read_inputs(text, *, csv_input=False):
    if not csv_input:
        return [ChemicalInput(line) for line in text.splitlines() if line.strip()]
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "name" not in reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("CSV_REQUIRES_UNIQUE_HEADERS_AND_NAME")
    if not set(reader.fieldnames) <= set(ChemicalInput.__dataclass_fields__):
        raise ValueError("UNKNOWN_CSV_HEADER")
    inputs = []
    for row in reader:
        if None in row or None in row.values():
            raise ValueError("INVALID_CSV_ROW_WIDTH")
        inputs.append(ChemicalInput(**row))
    return inputs


def _packet(packet):
    """Verify saved provider rows against the locally retained payload before adapting."""
    source = packet["source_type"]
    if source not in {"pubchem", "chebi"}:
        raise ValueError("UNSUPPORTED_SAVED_PROVIDER")
    raw, provenance = packet["record"], packet["provenance"]
    path = Path(provenance["payload_path"])
    if path.stat().st_size > 10_000_000:
        raise ValueError("PROVIDER_PAYLOAD_TOO_LARGE")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != provenance["payload_sha256"]:
        raise ValueError("PROVIDER_PAYLOAD_DIGEST_MISMATCH")
    payload = json.loads(data)
    rows = (payload.get("rows") or payload.get("PropertyTable", {}).get("Properties", [])) if source == "pubchem" else [payload.get("data", payload)]
    if raw not in rows or provenance["url"] != payload["url"]:
        raise ValueError("PROVIDER_ROW_NOT_BOUND_TO_PAYLOAD")
    # Do not pass caller-supplied admission, official validation or form flags.
    return ProviderAdapter("PubChem" if source == "pubchem" else "ChEBI").adapt(
        {key: packet[key] for key in ("record", "provenance", "source_revision") if key in packet})


class Enrichment:
    def __init__(self, directory=None, *, max_candidates=750, input_adapters=None, input_adapter="molecular"):
        self.permit, self.concepts = open_development() if directory is None else open_development(directory)
        self.substances = Registry(self.permit.path)
        self.policy = RetrievalPolicy(max_candidates=max_candidates)
        from .chemical_qualification import InputAdapters
        self.input_adapters = input_adapters or InputAdapters()
        self.input_adapter = self.input_adapters.get(input_adapter)
        self.bridge = Bridge()
        offline = OfflineEvidence()
        self.local = Resolver(self.bridge, offline, offline)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.bridge.close()

    def resolve(self, item, *, saved_evidence=None):
        with ExitStack() as stack:
            return self._evaluate(item, saved_evidence, None, self._snapshot_loader(stack))

    def batch(self, inputs, *, saved_evidence=None):
        inputs = list(inputs)
        if not 1 <= len(inputs) <= MAX_BATCH:
            raise ValueError(f"BATCH_REQUIRES_1_TO_{MAX_BATCH}_INPUTS")
        packets = [None] * len(inputs) if saved_evidence is None else list(saved_evidence)
        if len(packets) != len(inputs):
            raise ValueError("BATCH_EVIDENCE_MUST_ALIGN_WITH_INPUTS")
        with ExitStack() as stack:
            snapshot = self._snapshot_loader(stack)
            return [self._evaluate(item, packet, None, snapshot)
                    for item, packet in zip(inputs, packets, strict=True)]

    def _snapshot_loader(self, stack):
        snapshot = None

        def get_snapshot():
            nonlocal snapshot
            if snapshot is None:
                db = stack.enter_context(closing(sqlite3.connect(
                    self.permit.path.as_uri() + "?mode=ro", uri=True)))
                db.execute("PRAGMA query_only=ON")
                db.execute("BEGIN")
                snapshot = RegistrySnapshot.from_connection(db)
            return snapshot

        return get_snapshot

    def commit(self, item, preview, *, saved_evidence=None):
        if not preview.get("commit_eligible") or preview.get("input") != asdict(item):
            return {"input": asdict(item), "outcome": "COMMIT_NOT_ELIGIBLE", "committed_id": None}
        return self._evaluate(item, saved_evidence, preview, None)

    def _evaluate(self, item, packet, preview, snapshot):
        started = perf_counter()
        result = dict(input=asdict(item), outcome="UNRESOLVED", commit_eligible=False,
                      committed_id=None, substance_id=None, concept_id=None, diagnostics=[],
                      interpretation=None, substance_comparisons=0, concept_comparisons=0,
                      validation="NOT_ESTABLISHED")
        try:
            self._run(item, packet, preview, snapshot, result)
        except (ValueError, KeyError, OSError, RuntimeError, sqlite3.Error) as error:
            result.update(outcome="COMMIT_FAILED" if preview else "PROCESSING_FAILED",
                          commit_eligible=False, diagnostics=[str(error)])
        result["elapsed_seconds"] = round(perf_counter() - started, 6)
        return result

    def _run(self, item, packet, preview, snapshot, result):
        def finish(outcome, *reasons):
            result.update(outcome=outcome, diagnostics=list(reasons))

        from .chemical_qualification import QualificationError
        if not all(isinstance(value, str) for value in asdict(item).values()):
            finish("INVALID", "INPUT_FIELDS_MUST_BE_STRINGS")
            return
        if not item.referent_key.strip():
            finish("INVALID", "REFERENT_KEY_REQUIRED")
            return
        if bool(item.source_system.strip()) != bool(item.source_record_id.strip()):
            finish("INVALID", "SOURCE_NAMESPACE_AND_RECORD_ID_REQUIRED_TOGETHER")
            return
        result["substance_candidates"] = []
        result["concept_candidates"] = self.concepts.search(item.name) if item.name.strip() else []
        if item.name.strip():
            hits, _ = self.substances.search(Query(item.name, "name", item.name))
            result["substance_candidates"] = [r["substance_id"] for r in hits]
        for kind, value in (("CASRegistryNumber", item.cas), ("ECNumber", item.ec), ("InChIKey", item.inchikey)):
            if value:
                hits, _ = self.substances.search(Query(value, "identifier", value, kind))
                result["substance_candidates"].extend(row["substance_id"] for row in hits)
        result["substance_candidates"] = sorted(set(result["substance_candidates"]))
        try:
            selected, normalized = self.input_adapter.interpret(item, self.local, self.bridge)
        except QualificationError as error:
            finish(error.status, *error.reasons)
            return
        result["interpretation"] = selected
        open_stereo = any(feature["specified"] != "Specified" for feature in selected["stereo"])
        if packet is not None:
            provider = _packet(packet)
            evidence = qualify_source(provider.incoming.concept)
            provider_graph = evidence["graph_view"]
            if evidence["source_conflicts"]:
                finish("CONFLICT", "PROVIDER_SOURCE_EVIDENCE_CONFLICT")
                return
            if not provider_graph or reconcile_graphs(selected, describe(provider_graph))[1] != "COMPATIBLE":
                finish("CONFLICT", "PROVIDER_INPUT_GRAPH_MISMATCH")
                return
            # Provider referents retain their established mapping semantics.
            interpretation_audit = normalized.incoming.concept.evidence_package.source_attributes
            normalized = provider
            normalized.incoming.concept.provenance["enrichment_input"] = asdict(item)
            normalized.incoming.concept.provenance["chemical_interpretation"] = interpretation_audit
        if open_stereo:
            if packet is not None:
                finish("UNRESOLVED", "PROVIDER_OPEN_CONCEPT_BINDING_UNSUPPORTED")
                return
            self._concept(item, selected, result, preview)
            return
        # The idempotency key includes the complete qualified evidence, so an
        # adapter/audit revision cannot reuse an older key with a changed payload.
        proof = digest([asdict(item), selected["smiles"], packet, asdict(normalized)])
        result["commit_proof"] = proof
        if preview:
            if preview.get("commit_proof") != proof or preview["outcome"] not in {
                    "NEW_SUBSTANCE_CANDIDATE", "EXACT_SUBSTANCE_MATCH"}:
                finish("COMMIT_REVALIDATION_FAILED", "PREVIEW_EVIDENCE_CHANGED")
                return
            start = perf_counter()
            receipt = CreationService(self.permit, self.bridge.official).execute(
                normalized, "enrichment:" + proof, retrieval_policy=self.policy)
            diagnostics = receipt["reasons"]
            if receipt["outcome"] == "EXISTING_SUBSTANCE_REUSED":
                diagnostics = [reason for reason in diagnostics if reason != "COMPLETE_NO_MATCH_REQUIRED"]
            result.update(outcome=receipt["outcome"], diagnostics=diagnostics,
                          committed_id=receipt["substance_id"] if receipt["outcome"] in {
                              "NEW_SUBSTANCE_CREATED", "EXISTING_SUBSTANCE_REUSED"} else None,
                          validation="CONTROLLED_SUBSTANCE_RECEIPT",
                          substance_comparisons=receipt["matching"]["uniqueness"]["compared"],
                          commit_seconds=round(perf_counter() - start, 6))
            return
        registry = snapshot()
        if registry.sqlite_integrity != [("ok",)] or registry.foreign_key_errors:
            finish("INCOMPLETE_SEARCH", "REGISTRY_INTEGRITY_FAILURE")
            return
        match = RegistryMatcher(registry,
                                official_validator=self.bridge.official).match(normalized.incoming, self.policy)
        result["substance_comparisons"] = match["uniqueness"]["compared"]
        if not match["retrieval"]["search_complete"]:
            finish("INCOMPLETE_SEARCH", "REGISTRY_SEARCH_INCOMPLETE")
        elif match["status"] == "UNIQUE_CANONICAL_MATCH" and match["admission"]["admission_eligible"] and match["matching_proposal"]:
            result.update(commit_eligible=True, substance_id=match["unique_matched_substance_id"],
                          validation="ADMISSION_ELIGIBLE")
            finish("EXACT_SUBSTANCE_MATCH")
        elif match["status"] == "MULTIPLE_CANONICAL_MATCHES":
            finish("MULTIPLE_CANDIDATES", "MULTIPLE_CANONICAL_MATCHES")
        else:
            eligibility = assess(normalized.incoming, match)
            result.update(commit_eligible=eligibility["eligible"],
                          validation="ADMISSION_ELIGIBLE" if eligibility["eligible"] else "NOT_ESTABLISHED")
            finish("NEW_SUBSTANCE_CANDIDATE" if eligibility["eligible"] else "UNRESOLVED",
                   *eligibility["reasons"])

    def _concept(self, item, graph, result, preview):
        proposal = {"kind": "molecular", "smiles": graph["smiles"]}
        try:
            molecular(graph["smiles"])
        except ValueError as error:
            result.update(outcome="UNSUPPORTED", diagnostics=[str(error)])
            return
        official = self.bridge.official(graph)
        if not official["agrees"] or official["status"] not in {"SUCCESS", "WARNING"}:
            result["diagnostics"] = ["OFFICIAL_INCHI_NOT_CONFIRMED"]
            return
        proof = digest([asdict(item), proposal, official])
        result.update(commit_proof=proof, validation="VALIDATED_OPEN_STEREO_GRAPH")
        if preview:
            if preview.get("commit_proof") != proof or preview["outcome"] not in {
                    "NEW_CONCEPT_CANDIDATE", "EQUIVALENT_CONCEPT"}:
                result.update(outcome="COMMIT_REVALIDATION_FAILED", diagnostics=["PREVIEW_EVIDENCE_CHANGED"])
                return
            key = ((item.source_system, "CHEMICAL_INPUT", item.source_record_id, item.referent_key)
                   if item.source_system else None)
            start = perf_counter()
            receipt = self.concepts.create_or_reuse(
                proposal, item.name or graph["smiles"], "enrichment:" + proof,
                evidence={"input": asdict(item), "official": official, "policy": "enrichment-v1"},
                source_key=key,
            )
            result.update(outcome="CONCEPT_" + receipt["outcome"], committed_id=receipt.get("concept_id"),
                          concept_comparisons=receipt.get("comparisons", 0),
                          commit_seconds=round(perf_counter() - start, 6))
            return
        proposed = self.concepts.propose(proposal)
        result["concept_comparisons"] = len(proposed["comparisons"])
        matches = proposed["matches"]
        if proposed["unresolved"] or len(matches) > 1:
            result.update(outcome="MULTIPLE_CANDIDATES" if len(matches) > 1 else "INCOMPLETE_SEARCH",
                          diagnostics=["CONCEPT_EQUIVALENCE_NOT_ESTABLISHED"])
            return
        result.update(outcome="EQUIVALENT_CONCEPT" if matches else "NEW_CONCEPT_CANDIDATE",
                      concept_id=matches[0] if matches else None, commit_eligible=True)
