"""Identity-safety regression tests over frozen and small metamorphic controls."""

from dataclasses import replace

import pytest

from canonical_registry.nomenclature_interpretation import InterpretationFramework
from canonical_registry.nomenclature_interpretation.contracts import Evidence, InterpretationResult, Issue, State

from .adapters import from_cosing, verified_cosmetics_target
from .contracts import ScopedDesignation, Verdict
from .engine import compare
from .evaluate import COSMETIC, _synthetic_ingredient, _synthetic_pairs, read
from .retrieval import CandidateIndex


@pytest.mark.parametrize("case,left,right", list(_synthetic_pairs()), ids=[r["id"] for r in read("synthetic_reference.json")])
def test_frozen_identity_control(case, left, right):
    result = compare(left, right)
    assert result.verdict == case["expected"]
    assert set(case["relationships"]) <= {item.kind for item in result.relationships}
    assert result == compare(right, left) == compare(left, right)


def test_interpreter_output_does_not_qualify_equivalence_or_canonical_targets():
    rows = {r["inci"]: r for r in read("warehouse.json")}
    aliases = read("aliases.json")
    framework = InterpretationFramework()

    def item(name):
        row = rows[name]
        return from_cosing(row, [a for a in aliases if a["inci_id"] == row["inci_id"]], COSMETIC, framework)

    aqua, water = item("AQUA"), item("WATER")
    assert aqua.interpretation.assertions and water.interpretation.assertions
    assert compare(aqua, water).verdict == Verdict.UNRESOLVED
    assert not compare(aqua, water).relationships
    assert water.reference in dict(CandidateIndex([aqua, water]).find(aqua).matches)


def test_index_caps_broad_keys_without_truncating_a_strong_alternative():
    items = [_synthetic_ingredient(str(i), {"ids": [["CAS", "shared"]],
                                           "label": "Selected spelling" if i < 2 else f"Other {i}"})
             for i in range(20)]
    found = CandidateIndex(items, max_bucket=3, name_tokens=False).find(items[0])
    assert found.matches == (("1", (("label", "selected spelling"),)),)
    assert found.skipped == ((("reported", "cas", "shared"), 20),)
    assert found == CandidateIndex(reversed(items), max_bucket=3, name_tokens=False).find(items[0])
    with pytest.raises(ValueError, match="Duplicate concept"):
        CandidateIndex([items[0], items[0]])


def test_candidate_retrieval_and_adjudication_have_no_transitive_closure():
    a = _synthetic_ingredient("A", {"families": ["molecular"], "label": "first", "ids": [["CAS", "shared"]]})
    b = _synthetic_ingredient("B", {"families": ["molecular"], "label": "second",
                                    "ids": [["CAS", "shared"]], "aliases": ["third"]})
    c = _synthetic_ingredient("C", {"families": ["molecular"], "label": "third"})
    index = CandidateIndex([a, b, c])
    assert set(dict(index.find(a).matches)) == {"B"}
    assert set(dict(index.find(b).matches)) == {"A", "C"}
    assert compare(a, b).verdict == compare(b, c).verdict == compare(a, c).verdict == Verdict.UNRESOLVED


def test_authoritative_cross_designations_survive_broad_key_limits():
    a, b = next((a, b) for case, a, b in _synthetic_pairs() if case["id"] == "authority-aliases")
    shared = a.designations[0]
    c = replace(b, reference="C", designations=(ScopedDesignation(
        "C", shared.authority, shared.revision, shared.referent, shared.covers, shared.evidence,
    ),))
    result = CandidateIndex([a, b, c], max_bucket=2).find(a)
    assert {match[0] for match in result.matches} == {b.reference, c.reference}
    assert all(key[0] == "name_token" for key, _ in result.skipped)
    assert all(any(key[0] == "designation" for key in evidence) for _, evidence in result.matches)


def test_different_exact_canonical_targets_block_otherwise_equivalent_designations():
    def item(reference, target):
        return _synthetic_ingredient(reference, {
            "families": ["molecular"],
            "designations": [{"referent": "same-authority-entry", "covers": ["molecular"]}],
            "target": {"registry_type": "Substance", "id": target},
        })

    result = compare(item("pair/a", "SUB_00000001"), item("pair/b", "SUB_00000002"))
    assert result.verdict == Verdict.UNRESOLVED
    assert "DIFFERENT_EXACT_TARGETS_REQUIRE_RECONCILIATION" in result.reasons


def test_qualified_preparation_source_remains_a_separate_relationship():
    def item(reference, field):
        return _synthetic_ingredient(reference, {
            "families": ["preparation_mixture"],
            "facets": [{"field": field, "scheme": "fixture-material-v1", "value": "expressed botanical juice",
                        "qualification": "DESCRIPTIVE"}],
        })

    result = compare(item("source", "material"), item("preparation", "preparation_source"))
    assert result.verdict == Verdict.UNRESOLVED
    assert [r.kind for r in result.relationships] == ["PREPARED_FROM_MATERIAL"]
    assert result.relationships[0].subject_object == ("preparation", "source")


def test_unmodeled_defining_qualification_holds_a_positive_authority_binding():
    def item(reference, facets):
        return _synthetic_ingredient(reference, {
            "families": ["molecular"], "facets": facets,
            "designations": [{"referent": "same-authority-entry", "covers": ["molecular"]}],
        })

    first = item("pair/a", [])
    second = item("pair/b", [{"field": "unspecified_policy_slot", "scheme": "fixture", "value": "grade-A",
                              "qualification": "DEFINING_EXCLUSIVE"}])
    result = compare(first, second)
    assert result.verdict == Verdict.UNRESOLVED
    assert "UNSUPPORTED_DEFINING_FACET:unspecified_policy_slot" in result.reasons


def test_localized_graph_conflict_holds_verdict_but_preserves_reviewed_material_relation():
    a, b = next((a, b) for case, a, b in _synthetic_pairs() if case["id"] == "colorant-cross-reference-only")
    designation = Evidence(a.label, "designation", a.reference)
    graph_conflict = Issue("CONFLICTING_STRUCTURE_DIMENSIONS", (designation,), conflict=True)
    interpretation = InterpretationResult(designation, State.CONFLICT, (), (), (), (graph_conflict,), (), ())
    a = replace(a, interpretation=interpretation)
    decision = compare(a, b)
    assert decision.verdict == Verdict.UNRESOLVED
    assert "INTERPRETATION_CONFLICT" in decision.reasons
    assert [r.kind for r in decision.relationships] == ["SHARED_MATERIAL_REFERENT"]
    unknown = replace(a, issues=(Issue("SOURCE_CONFLICT", (designation,), conflict=True),))
    assert compare(unknown, b).relationships == ()


def test_evidence_cannot_be_transferred_between_subjects():
    cases = {case["id"]: (a, b) for case, a, b in _synthetic_pairs()}
    a, b = cases["authority-aliases"]
    with pytest.raises(ValueError, match="different ingredient"):
        replace(b, designations=a.designations)
    a, b = cases["same-graph-only"]
    with pytest.raises(ValueError, match="different ingredient"):
        replace(b, molecular=a.molecular)


def test_cosmetics_status_mapping_is_typed_snapshot_bound_and_separate_from_verdict():
    record = {
        "ingredient_concept_id": "CIC_00000001",
        "source_reference": "fixture:cosmetics",
        "canonical_status": "RESOLVED_SUBSTANCE",
        "canonical_target": {"registry_type": "Substance", "id": "SUB_00000001"},
    }
    def exists(registry, snapshot, kind, identity):
        return (registry, snapshot, kind, identity) == ("substances", "sha256:test", "Substance", "SUB_00000001")

    target = verified_cosmetics_target(record, "substances", "sha256:test", exists)
    a = _synthetic_ingredient(record["source_reference"], {"families": ["molecular"]})
    b = _synthetic_ingredient("B", {"families": ["molecular"]})
    with pytest.raises(ValueError, match="different ingredient"):
        replace(b, chemical_target=target)
    second = verified_cosmetics_target(
        {**record, "ingredient_concept_id": "CIC_00000002", "source_reference": b.reference},
        "substances", "sha256:test", exists,
    )
    decision = compare(replace(a, chemical_target=target), replace(b, chemical_target=second))
    assert decision.verdict == Verdict.UNRESOLVED
    assert decision.relationships[0].kind == "SHARED_EXACT_SUBSTANCE"
    with pytest.raises(ValueError, match="does not exist"):
        verified_cosmetics_target(record, "substances", "sha256:other", exists)
    with pytest.raises(ValueError, match="target type disagree"):
        verified_cosmetics_target({**record, "canonical_status": "RESOLVED_CHEMICAL_CONCEPT"},
                                  "substances", "sha256:test", exists)
    with pytest.raises(ValueError, match="cannot have a canonical target"):
        verified_cosmetics_target({**record, "canonical_status": "UNRESOLVED"}, "substances", "sha256:test", exists)
    record.pop("canonical_target")
    assert verified_cosmetics_target({**record, "canonical_status": "NOT_EVALUATED"},
                                      "substances", "sha256:test", exists) is None
