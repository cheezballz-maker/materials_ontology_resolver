from dataclasses import replace

import pytest

from canonical_registry.authoritative_lookup.lookup import AuthorityRecord, SourceReferent
from canonical_registry.authoritative_lookup.sources import cosing_input, read
from canonical_registry.chemistry import describe
from canonical_registry.identity_sufficiency.contract import Claim, Evidence, Evaluator, WHOLE
from ..cohort import DATA
from ..source_identity_safety import SourceIdentitySafety, identifier_observations, scope_observations
from ..v3_authority import retained_source_input


def official(graph):
    return {"status": "SUCCESS", "agrees": True, "inchi": graph["inchi"], "inchikey": graph["inchikey"]}


def source(name, definition=None, cas=()):
    claims = (Claim("definition", "DEFINITION", definition, "SCOPE_UNESTABLISHED", "test", "source",
                    ("SOURCE_RECORD",), "source-document", "definition", "rev"),) if definition else ()
    evidence = Evidence("test", "source:test", "rev", name, claims)
    return SourceReferent(evidence, "test", (name,), definition or "", {"CAS": cas})


class QualifiedLookup:
    authorities = {}

    def evaluate(self, incoming, candidates, total, *, authority_source):
        return ({"eligibility": "CANDIDATE_READY", "resolution_pathway": "SUBSTANCE", "evidence_pathway": "B_NOMENCLATURE",
                 "specificity": describe("CCO"), "reasons": []}, {"assertion_type": "test binding"}, [])


@pytest.mark.parametrize("name,definition,reason", [
    ("Hypothetical isostearate", None, "SOURCE_WHOLE_BRANCH_SPECIFICATION_MISSING"),
    ("Source ester", "It is the diester of glycol and branched chain nonanoic acids.", "SOURCE_DEFINITION_SCOPE_CONFLICT"),
    ("Source material", "The representative structure corresponds to its primary constituent.", "SOURCE_DEFINITION_SCOPE_CONFLICT"),
])
def test_reusable_scope_holds(name, definition, reason):
    result, receipt, _ = SourceIdentitySafety(QualifiedLookup(), Evaluator(official), {}).evaluate(source(name, definition), [], 0)
    assert result["eligibility"] == "REVIEW_HOLD" and reason in result["reasons"] and receipt is None


def test_revision_bound_exact_specification_can_satisfy_branch_obligation():
    s = source("Hypothetical isostearate")
    c = Claim("scope", "SMILES", "CCO", WHOLE, "test", "source", ("STRUCTURE", "REFERENT", "SPECIFICATION"),
              "source-document", "whole structure specification", "rev")
    for revision, expected in (("rev", "CANDIDATE_READY"), ("older", "REVIEW_HOLD")):
        updated = replace(s, evidence=replace(s.evidence, claims=(replace(c, revision=revision),)))
        decision, _, _ = SourceIdentitySafety(QualifiedLookup(), Evaluator(official), {}).evaluate(updated, [], 0)
        assert decision["eligibility"] == expected
    assert not scope_observations(source("ISOPROPYL ALCOHOL").evidence, "ISOPROPYL ALCOHOL")


def test_cas_mismatch_preserves_structure_distinction_and_unknown_cas_is_diagnostic():
    e = describe("CCO")
    ref = describe("COC")
    operational = {"a": {"status": "STRUCTURAL_REFERENCE", "cas": "a", "inchi": ref["inchi"], "inchikey": ref["inchikey"]}}
    for key, expected in (("a", "REVIEW_HOLD"), ("b", "CANDIDATE_READY")):
        got, receipt, _ = SourceIdentitySafety(QualifiedLookup(), Evaluator(official), operational).evaluate(source("ethanol", cas=(key,)), [], 0)
        assert got["eligibility"] == expected
        assert bool(receipt) == (key == "b")


def test_qualified_native_identifier_compares_full_forms_and_untyped_is_insufficient():
    target, opposite = describe("C[C@H](O)CC"), describe("C[C@@H](O)CC")
    link = {"source_id": "ID", "chemical_id": "chemical", "substance_type": "chemical", "ingredient_type": "INGREDIENT SUBSTANCE",
            "routes": ["REPORTED_IDENTIFIER:CAS:a"], "smiles": opposite["smiles"], "inchikey": opposite["inchikey"]}
    record = AuthorityRecord("ID", "test", "SMILES", opposite["smiles"], opposite["inchikey"], ("test",),
                             {"CAS": ("a",)}, "authority-document", "structure", {"sha256": "captured"})
    a = identifier_observations(source("test", cas=("a",)), target, [link], {"ID": [record]}, {})
    assert a[0]["category"] == "DISTINCT_CHEMICAL_FORMS"
    a = identifier_observations(source("test", cas=("a",)), target, [link], {"ID": [replace(record, identifiers={})]}, {})
    assert a[0]["category"] == "INSUFFICIENT_CORRESPONDENCE"


def test_historical_failures_without_record_specific_holds():
    known = read(DATA / "v3" / "review_holds.json")
    cases = [r for r in read(DATA / "v3" / "fresh.json") if r["concept_id"] in known]
    ref = describe("InChI=1S/C9H14O2/c1-2-11-9(10)8-6-4-3-5-7-8/h3-4,8H,2,5-7H2,1H3", "inchi")
    references = {"15111-56-5": {"status": "STRUCTURAL_REFERENCE", "cas": "15111-56-5",
                                  "inchi": ref["inchi"], "inchikey": ref["inchikey"]}}
    for row in cases:
        incoming = retained_source_input(row, cosing_input(row))
        graph = describe(incoming.graph_signatures[0][0])

        class HistoricalProposal(QualifiedLookup):
            def evaluate(self, incoming, candidates, total, *, authority_source):
                result, receipt, diagnostics = super().evaluate(incoming, candidates, total, authority_source=authority_source)
                return {**result, "specificity": graph}, receipt, diagnostics

        result, receipt, _ = SourceIdentitySafety(HistoricalProposal(), Evaluator(official), references).evaluate(incoming, [], 0)
        assert result["eligibility"] == "REVIEW_HOLD" and receipt is None
        assert not any(code.startswith("REVIEWED_") for code in result["reasons"])


def test_profiling_is_not_part_of_replay_evidence(monkeypatch):
    from .. import workflow

    class Checkpoint:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def execute(self, *args):
            return self

        def fetchone(self):
            return None

        def close(self):
            return None

    monkeypatch.setitem(workflow.StageC.process.__globals__, "connect_creation", lambda _: Checkpoint())
    fingerprints = []

    def adapt(s, decision, receipt):
        fingerprints.append(decision.copy())
        return None

    monkeypatch.setitem(workflow.StageC.process.__globals__, "_adapt", adapt)
    engine = object.__new__(workflow.StageC)
    engine.authority_digest, engine.permit = "frozen", None
    engine.lookup = SourceIdentitySafety(QualifiedLookup(), Evaluator(official), {})

    class Create:
        def _execute(self, *args, **kwargs):
            return None

    engine.creation = Create()
    for _ in range(2):
        assert "source_identity_safety_seconds" in engine.process(source("ethanol"), [], 0)["timings"]
    assert fingerprints[0] == fingerprints[1]
    assert "source_identity_safety_seconds" not in fingerprints[0]
