"""Read-only pair adjudication. Retrieval signals never reach the decision rules."""

from collections import defaultdict

from canonical_registry.nomenclature_interpretation.contracts import Evidence, State
from chemistry import describe
from identity_comparator import compare as compare_graphs

from .contracts import AttributeComparison, Decision, Family, Qualification, RegistryType, Relationship, Verdict
from .policies import COMMON, RELATED_FACETS, SLOTS


def evidence_set(values):
    return tuple(sorted(set(values), key=lambda e: (
        e.source_reference or "", e.field, e.original_value, e.source_label or "",
    )))


def _facets(items):
    by_slot = defaultdict(list)
    for item in items:
        by_slot[item.field, item.scheme].append(item)
    return by_slot


def _designation_keys(ingredient):
    keys = defaultdict(set)
    for designation in ingredient.designations:
        scope = designation.comparison_scope or ingredient.scope
        keys[designation.authority, designation.scheme, designation.revision, scope].add(
            (designation.referent, designation.conditions)
        )
    return keys


def _molecular_comparison(left, right, graphs):
    bindings = left.molecular, right.molecular
    evidence = evidence_set(e for b in bindings for e in (b.structure.evidence, b.binding_evidence))
    try:
        comparison = compare_graphs(*graphs)
    except (ValueError, RuntimeError):
        return None, (), ("QUALIFIED_GRAPH_COMPARISON_FAILED",)
    attributes = tuple(AttributeComparison(
        "molecular." + dimension, "canonical-identity-comparator",
        (graphs[0]["smiles"],), (graphs[1]["smiles"],), result, evidence,
    ) for dimension, result in sorted(comparison["dimensions"].items()))
    relationships = ()
    if comparison["assessment"] == "EXACT":
        relationships = (Relationship("SAME_VALIDATED_MOLECULAR_GRAPH", "canonical-identity-comparator",
                                      graphs[0]["smiles"], evidence),)
    elif comparison["assessment"] == "DISTINCT":
        relationships = tuple(Relationship(
            relation, "canonical-identity-comparator", " | ".join(g["smiles"] for g in graphs), evidence,
        ) for relation in comparison["relations"])
    return comparison["assessment"], (attributes, relationships), tuple(comparison["reason_codes"])


def compare(left, right) -> Decision:
    """Compare two distinct source concepts in canonical reference order."""
    if left.reference == right.reference:
        raise ValueError("Use two distinct concept references")
    left, right = sorted((left, right), key=lambda item: item.reference)
    items = left, right
    families = left.families | right.families
    names_left, names_right = map(_designation_keys, items)
    matched_scopes = {
        a.comparison_scope or left.scope
        for a in left.designations for b in right.designations
        if (a.authority, a.scheme, a.revision, a.referent, a.conditions)
        == (b.authority, b.scheme, b.revision, b.referent, b.conditions)
        and (a.comparison_scope or left.scope) == (b.comparison_scope or right.scope)
        and families <= a.covers & b.covers
    }
    comparison_scopes = matched_scopes
    if not comparison_scopes and left.scope != right.scope:
        scoped_slots = [
            {(f.field, f.scheme, f.comparison_scope) for f in item.facets
             if f.qualification == Qualification.DEFINING_EXCLUSIVE and f.comparison_scope is not None}
            for item in items
        ]
        comparison_scopes = {scope for _, _, scope in scoped_slots[0] & scoped_slots[1]}
    evaluated_scope = next(iter(comparison_scopes)) if len(comparison_scopes) == 1 else (
        left.scope if left.scope == right.scope else None
    )
    shared_slots = set(COMMON)
    for family in left.families & right.families:
        shared_slots.update(SLOTS[family])
    all_slots = set(COMMON)
    for family in families:
        all_slots.update(SLOTS[family])

    blockers, distinctions, details = set(), set(), set()
    attributes, relationships, evidence, issues = [], [], [], []
    unlocalized_conflict = False
    for item in items:
        issues.extend(item.issues)
        unlocalized_conflict |= any(issue.conflict for issue in item.issues)
        if item.interpretation is not None:
            conflicts = [issue for issue in item.interpretation.issues if issue.conflict]
            issues.extend(conflicts)
            unlocalized_conflict |= any(issue.code != "CONFLICTING_STRUCTURE_DIMENSIONS" for issue in conflicts)
            if item.interpretation.state == State.CONFLICT:
                blockers.add("INTERPRETATION_CONFLICT")
                unlocalized_conflict |= not conflicts
            if item.molecular and any(module.whole_referent_graph_unestablished
                                      for module in item.interpretation.modules):
                blockers.add("WHOLE_MOLECULAR_BINDING_CONFLICT")
    if any(issue.conflict for issue in issues):
        blockers.add("SOURCE_EVIDENCE_CONFLICT")
    if len(comparison_scopes) > 1:
        blockers.add("MULTIPLE_QUALIFIED_COMPARISON_SCOPES")
    if evaluated_scope is None:
        blockers.add("DIFFERENT_COMPARISON_SCOPES")
    if not left.families or not right.families:
        blockers.add("UNSUPPORTED_OR_UNQUALIFIED_SCOPE")

    graphs = []
    for item in items:
        binding = item.molecular
        if binding:
            evidence.extend((binding.structure.evidence, binding.binding_evidence))
            if Family.MOLECULAR not in item.families:
                blockers.add("MOLECULAR_BINDING_WITHOUT_QUALIFIED_FAMILY")
            try:
                if len(binding.structure.evidence.original_value) > 1200:
                    raise ValueError("Graph budget exceeded")
                graphs.append(describe(binding.structure.evidence.original_value, binding.structure.kind.value))
            except (ValueError, RuntimeError):
                blockers.add("QUALIFIED_GRAPH_VALIDATION_FAILED")
    molecular = None
    graph_blockers = {"SOURCE_EVIDENCE_CONFLICT", "INTERPRETATION_CONFLICT", "WHOLE_MOLECULAR_BINDING_CONFLICT",
                      "QUALIFIED_GRAPH_VALIDATION_FAILED", "MOLECULAR_BINDING_WITHOUT_QUALIFIED_FAMILY"}
    if len(graphs) == 2 and not blockers.intersection(graph_blockers):
        molecular, traces, reasons = _molecular_comparison(left, right, graphs)
        details.update(reasons)
        if traces:
            molecular_attributes, molecular_relations = traces
            attributes.extend(molecular_attributes)
            relationships.extend(molecular_relations)
        if molecular == "DISTINCT":
            distinctions.add("WHOLE_MOLECULAR_IDENTITY_DIFFERS")
        elif molecular != "EXACT":
            blockers.add("WHOLE_MOLECULAR_COMPARISON_INCOMPLETE")

    if left.chemical_target and right.chemical_target:
        a, b = left.chemical_target, right.chemical_target
        proof = evidence_set((a.evidence, b.evidence))
        evidence.extend(proof)
        if (a.registry_type, a.registry, a.snapshot) == (b.registry_type, b.registry, b.snapshot):
            scheme = f"{a.registry_type}/{a.registry}/{a.snapshot}"
            attributes.append(AttributeComparison("canonical_target", scheme, (a.target,), (b.target,),
                                                  "SHARED_TARGET" if a.target == b.target else "DIFFERENT_IDS",
                                                  proof))
            if a.target == b.target and not blockers.intersection(graph_blockers):
                if a.registry_type == RegistryType.SUBSTANCE and molecular == "DISTINCT":
                    blockers.add("CANONICAL_TARGET_CONTRADICTS_WHOLE_GRAPHS")
                else:
                    kind = "SHARED_EXACT_SUBSTANCE" if a.registry_type == RegistryType.SUBSTANCE else "SHARED_CHEMICAL_CONCEPT"
                    relationships.append(Relationship(kind, scheme, a.target, proof))
            elif a.target != b.target and a.registry_type == RegistryType.SUBSTANCE and molecular != "DISTINCT":
                blockers.add("CANONICAL_TARGET_CONTRADICTS_WHOLE_GRAPHS" if molecular == "EXACT"
                             else "DIFFERENT_EXACT_TARGETS_REQUIRE_RECONCILIATION")

    fa, fb = map(lambda item: _facets(item.facets), items)
    gaps = set()
    for key in sorted(fa.keys() | fb.keys()):
        field, scheme = key
        a, b = fa.get(key, ()), fb.get(key, ())
        proof = evidence_set(f.evidence for f in (*a, *b))
        if matched_scopes and any(
            f.qualification == Qualification.DEFINING_EXCLUSIVE
            and (f.comparison_scope or item.scope) != evaluated_scope
            for side, item in zip((a, b), items) for f in side
        ):
            gaps.add(f"DEFINING_FACET_OUTSIDE_COMPARISON_SCOPE:{field}")
            attributes.append(AttributeComparison(field, scheme, tuple(sorted({f.value for f in a})),
                              tuple(sorted({f.value for f in b})), "SCOPE_ALIGNMENT_REQUIRED", proof))
        exclusive = [{f.allowed_values or frozenset({f.value}) for f in side
                      if f.qualification == Qualification.DEFINING_EXCLUSIVE
                      and (f.comparison_scope or item.scope) == evaluated_scope}
                     for side, item in zip((a, b), items)]
        av, bv = (tuple(sorted(set().union(*side))) for side in exclusive)
        if field not in all_slots and any(exclusive):
            gaps.add(f"UNSUPPORTED_DEFINING_FACET:{field}")
            attributes.append(AttributeComparison(field, scheme, av, bv, "UNSUPPORTED_IDENTITY_SLOT", proof))
        elif any(exclusive):
            if any(len(side) > 1 for side in exclusive):
                result = "CONFLICT"
                blockers.add(f"INTERNAL_FACET_CONFLICT:{field}")
            elif not av or not bv or field not in shared_slots:
                result = "INSUFFICIENT_COMPARABLE_EVIDENCE"
                gaps.add(f"UNCOMPARED_QUALIFIED_FACET:{field}")
            elif av == bv:
                result = "AGREES"
            elif set(av).intersection(bv):
                result = "OVERLAPPING_IDENTITY_SPECIFICATIONS"
                gaps.add(f"OVERLAPPING_QUALIFIED_FACET:{field}")
            else:
                result = "INCOMPATIBLE"
                distinctions.add(f"IDENTITY_FACET_DIFFERS:{field}")
            attributes.append(AttributeComparison(field, scheme, av, bv, result, proof))
        if field in RELATED_FACETS and a and b:
            # Several descriptive values may legitimately describe a mixture.
            # A contradictory exclusive value suppresses the associated relationship.
            if not any(len(values) > 1 for values in exclusive):
                for value in sorted({f.value for f in a} & {f.value for f in b}):
                    relationships.append(Relationship(RELATED_FACETS[field], scheme, value, evidence_set(
                        f.evidence for f in (*a, *b) if f.value == value)))
    for material_ref, material, other_ref, other in ((left.reference, fa, right.reference, fb),
                                                    (right.reference, fb, left.reference, fa)):
        for (field, scheme), claims in sorted(material.items()):
            if field == "material":
                for role, relation, participants in (
                    ("constituent", "MATERIAL_IS_CONSTITUENT", (material_ref, other_ref)),
                    ("preparation_source", "PREPARED_FROM_MATERIAL", (other_ref, material_ref)),
                ):
                    supporting = other.get((role, scheme), ())
                    for value in sorted({f.value for f in claims} & {f.value for f in supporting}):
                        relationships.append(Relationship(relation, scheme, value, evidence_set(
                            f.evidence for f in (*claims, *supporting) if f.value == value), participants))

    for key in sorted(names_left.keys() | names_right.keys()):
        av, bv = tuple(sorted(names_left.get(key, ()))), tuple(sorted(names_right.get(key, ())))
        proof = evidence_set(d.evidence for item in items for d in item.designations
                             if (d.authority, d.scheme, d.revision, d.comparison_scope or item.scope) == key)
        state = "SAME_REFERENT" if av and av == bv else "NO_SHARED_REFERENT"
        if len(av) > 1 or len(bv) > 1:
            state = "CONFLICT"
            blockers.add("COMPETING_AUTHORITY_BINDINGS")
        attributes.append(AttributeComparison("nomenclature_referent", "/".join(part for part in key[:3] if part),
                          tuple(x[0] for x in av), tuple(x[0] for x in bv), state, proof))
    if matched_scopes and any(names_left[key] != names_right[key] for key in names_left.keys() & names_right.keys()):
        blockers.add("AUTHORITY_BINDINGS_DISAGREE")
    if matched_scopes and distinctions:
        blockers.add("EQUIVALENCE_EVIDENCE_CONTRADICTS_IDENTITY_DISTINCTION")

    if blockers:
        verdict = Verdict.UNRESOLVED
    elif distinctions:
        verdict = Verdict.DISTINCT
    elif matched_scopes and not gaps:
        verdict = Verdict.EQUIVALENT
    else:
        verdict = Verdict.UNRESOLVED
        if not matched_scopes:
            details.add("NO_QUALIFIED_WHOLE_INGREDIENT_EQUIVALENCE")
    if verdict == Verdict.EQUIVALENT:
        details.add("QUALIFIED_SAME_SCOPED_NOMENCLATURE_REFERENT")
    evidence.extend(Evidence(item.label, "ingredient_label", item.reference) for item in items)
    evidence.extend(e for comparison in attributes for e in comparison.evidence)
    evidence.extend(e for relation in relationships for e in relation.evidence)
    evidence.extend(e for issue in issues for e in issue.evidence)
    if unlocalized_conflict:
        # A localized structural conflict already blocks graph correspondence above.
        # Independent material evidence can survive it, but cannot survive an unlocalized conflict.
        relationships.clear()
    return Decision(
        (left.reference, right.reference), (left.scope, right.scope), verdict,
        tuple(sorted(family.value for family in families)) or ("unsupported",),
        tuple(attributes), tuple(sorted(blockers | distinctions | gaps | details)),
        tuple(sorted(set(relationships), key=lambda r: (r.kind, r.scheme, r.value, r.subject_object or (),
                                                       tuple((e.source_reference or "", e.field, e.original_value,
                                                              e.source_label or "") for e in r.evidence)))),
        evidence_set(evidence),
        tuple(sorted(set(issues), key=lambda issue: (issue.code, issue.detail or "", repr(issue.evidence), issue.conflict))),
        evaluated_scope=evaluated_scope,
        authority_claims=tuple(sorted({claim for item in items for claim in item.authority_claims},
                                     key=lambda claim: (claim.subject, claim.source, claim.locator, claim.kind,
                                                        claim.referent, claim.scheme, claim.definition, claim.origin,
                                                        claim.authority, claim.revision, claim.comparison_scope is not None,
                                                        claim.comparison_scope or claim.native_scope, claim.conditions,
                                                        tuple(sorted(claim.covers)), claim.field or "", claim.partition or "",
                                                        tuple(sorted(claim.allowed_values))))),
    )
