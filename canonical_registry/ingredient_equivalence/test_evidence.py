"""Controls for qualified scope, disjoint specifications, and retrieval separation."""

from dataclasses import replace

import pytest

from .contracts import Family, Ingredient, Scope, Verdict
from .engine import compare
from .qualification import AuthorityClaim, ClaimKind, Origin, qualify
from .retrieval import CandidateIndex
from .validate_evidence import crowded_posting_probe

A = Scope("authority A", "food", "supplier designation")
B = Scope("authority B", "food", "catalogue designation")
JOINT = Scope("cross-reference register", "food", "same qualified ingredient")
FAMILIES = frozenset({Family.PREPARATION})


def item(ref, scope):
    return Ingredient(ref, f"Documented designation {ref}", scope, FAMILIES)


def source_claim(record, kind, **changes):
    fields = dict(subject=record.reference, designation=record.label, native_scope=record.scope,
                  kind=kind, origin=Origin.ORIGINAL_AUTHORITY, authority="reviewed authority",
                  scheme="cross-reference register", revision="2026",
                  locator="entry §1", source="https://example.test/review-fixture",
                  definition="Reviewed original wording for this control.", referent="reference ingredient",
                  conditions=("The same composition and preparation requirements apply.",), covers=FAMILIES)
    fields.update(changes)
    return AuthorityClaim(**fields)


def specification(record, values, *, projected=None):
    return source_claim(
        record, ClaimKind.IDENTITY_SPECIFICATION, field="defining_referent",
        partition="reviewed discrete preparations", allowed_values=frozenset(values), comparison_scope=projected,
    )


def test_cross_nomenclature_requires_an_explicit_common_scope_and_matching_conditions():
    a, b = item("a", A), item("b", B)
    first = source_claim(a, ClaimKind.WHOLE_DESIGNATION, comparison_scope=JOINT)
    second = source_claim(b, ClaimKind.WHOLE_DESIGNATION, comparison_scope=JOINT)
    l, r = qualify(a, (first,)), qualify(b, (second,))
    match = compare(l, r)
    assert match == compare(r, l)
    assert match.verdict == Verdict.EQUIVALENT
    assert match.evaluated_scope == JOINT
    assert match.authority_claims == (first, second)
    for change in (dict(comparison_scope=None), dict(revision="2025"), dict(scheme="another scheme"),
                   dict(conditions=("Only a narrower grade is included.",))):
        other = qualify(b, (replace(second, **change),))
        assert compare(l, other).verdict == Verdict.UNRESOLVED


@pytest.mark.parametrize("origin", [Origin.PREDICTION, Origin.UNVERIFIED, Origin.ORIGINAL_SOURCE_RECORD])
def test_non_authority_provenance_cannot_qualify_whole_equivalence(origin):
    a, b = item("a", A), item("b", A)
    left = qualify(a, (source_claim(a, ClaimKind.WHOLE_DESIGNATION, origin=origin),))
    right = qualify(b, (source_claim(b, ClaimKind.WHOLE_DESIGNATION, origin=origin),))
    assert not left.designations and not right.designations
    assert compare(left, right).verdict == Verdict.UNRESOLVED


def test_material_constituent_and_related_term_do_not_become_designation_equivalence():
    a, b = item("a", A), item("b", A)
    l = qualify(a, (source_claim(a, ClaimKind.MATERIAL), source_claim(a, ClaimKind.RELATED_TERM)))
    r = qualify(b, (source_claim(b, ClaimKind.CONSTITUENT), source_claim(b, ClaimKind.RELATED_TERM),
                    source_claim(b, ClaimKind.UNVERIFIED_ALIAS, origin=Origin.UNVERIFIED)))
    decision = compare(l, r)
    assert decision.verdict == Verdict.UNRESOLVED
    assert decision.relationships[0].kind == "MATERIAL_IS_CONSTITUENT"
    assert decision.relationships[0].subject_object == ("a", "b")
    candidate = CandidateIndex((l, r)).find(l, limit=1)
    assert any(k[0] == "authority_cross_reference" for k in dict(candidate.matches)["b"])


def test_qualification_checks_subject_scope_and_original_designation():
    a, b = item("a", A), item("b", B)
    claim = source_claim(a, ClaimKind.WHOLE_DESIGNATION, comparison_scope=JOINT)
    with pytest.raises(ValueError, match="native scope"):
        qualify(b, (claim,))
    with pytest.raises(ValueError, match="original designation"):
        qualify(a, (replace(claim, designation="Other name"),))


def test_distinctness_requires_disjoint_qualified_sets_at_an_aligned_scope():
    a, b = item("a", A), item("b", B)
    l = qualify(a, (specification(a, {"whole", "concentrated"}, projected=JOINT),))
    partial_overlap = qualify(b, (specification(b, {"concentrated", "filtrate"}, projected=JOINT),))
    disjoint = qualify(b, (specification(b, {"filtrate"}, projected=JOINT),))
    unaligned = qualify(b, (specification(b, {"filtrate"}),))
    decision = compare(l, disjoint)
    assert decision.verdict == Verdict.DISTINCT
    assert decision.evaluated_scope == JOINT
    assert compare(l, partial_overlap).verdict == Verdict.UNRESOLVED
    assert compare(l, unaligned).verdict == Verdict.UNRESOLVED


def test_contradictions_and_unaligned_defining_facets_block_a_whole_binding():
    a, b = item("a", A), item("b", B)
    first = source_claim(a, ClaimKind.WHOLE_DESIGNATION, comparison_scope=JOINT)
    second = source_claim(b, ClaimKind.WHOLE_DESIGNATION, comparison_scope=JOINT)
    l = qualify(a, (first, specification(a, {"whole"}, projected=JOINT)))
    r = qualify(b, (second, specification(b, {"filtrate"}, projected=JOINT)))
    decision = compare(l, r)
    assert decision.verdict == Verdict.UNRESOLVED
    assert "EQUIVALENCE_EVIDENCE_CONTRADICTS_IDENTITY_DISTINCTION" in decision.reasons
    unaligned = qualify(a, (first, specification(a, {"whole"})))
    assert "DEFINING_FACET_OUTSIDE_COMPARISON_SCOPE:defining_referent" in compare(unaligned, r).reasons


def test_broad_posting_control_exposes_the_recall_cost_of_an_unqualified_key():
    capped, open_bucket = crowded_posting_probe()
    assert capped["recall"][50]["pairs_both_directions"] == 0
    assert capped["miss_causes_at_50"] == {"ALL_SHARED_POSTINGS_SUPPRESSED": 1}
    assert open_bucket["recall"][1]["pairs_either_direction"] == 1
    assert open_bucket["recall"][50]["pairs_both_directions"] == 0
    assert open_bucket["miss_causes_at_50"] == {"RANK_OUTSIDE_TOP_50": 1}
    assert open_bucket["candidate_pairs"] == 128 * 127 // 2
