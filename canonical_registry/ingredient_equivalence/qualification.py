"""Qualify reviewed source statements before they reach ingredient adjudication."""

from dataclasses import dataclass, replace
from enum import StrEnum

from canonical_registry.nomenclature_interpretation.contracts import Evidence, require_text

from .contracts import Facet, Family, Ingredient, Qualification, Scope, ScopedDesignation


class ClaimKind(StrEnum):
    WHOLE_DESIGNATION = "WHOLE_DESIGNATION"
    IDENTITY_SPECIFICATION = "IDENTITY_SPECIFICATION"
    MATERIAL = "MATERIAL"
    CONSTITUENT = "CONSTITUENT"
    RELATED_TERM = "RELATED_TERM"
    UNVERIFIED_ALIAS = "UNVERIFIED_ALIAS"


class Origin(StrEnum):
    ORIGINAL_AUTHORITY = "ORIGINAL_AUTHORITY"
    ORIGINAL_SOURCE_RECORD = "ORIGINAL_SOURCE_RECORD"
    UNVERIFIED = "UNVERIFIED"
    PREDICTION = "PREDICTION"


@dataclass(frozen=True)
class AuthorityClaim:
    subject: str
    designation: str
    native_scope: Scope
    kind: ClaimKind
    origin: Origin
    authority: str
    scheme: str
    revision: str
    locator: str
    source: str
    definition: str
    referent: str
    conditions: tuple[str, ...] = ()
    comparison_scope: Scope | None = None
    covers: frozenset[Family] = frozenset()
    field: str | None = None
    partition: str | None = None
    allowed_values: frozenset[str] = frozenset()

    def __post_init__(self):
        for field in ("subject", "designation", "authority", "scheme", "revision", "locator",
                      "source", "definition", "referent"):
            require_text(getattr(self, field), field)
        if not isinstance(self.kind, ClaimKind) or not isinstance(self.origin, Origin):
            raise ValueError("Explicit claim type and origin required")
        if not isinstance(self.native_scope, Scope) or (
            self.comparison_scope is not None and not isinstance(self.comparison_scope, Scope)
        ):
            raise ValueError("Typed nomenclature scope required")
        for text in (*self.conditions, *self.allowed_values):
            require_text(text, "qualifying condition or specification value")
        if self.kind == ClaimKind.WHOLE_DESIGNATION:
            if not self.covers or any(not isinstance(f, Family) for f in self.covers) or not self.conditions:
                raise ValueError("A whole designation requires reviewed family coverage and scope conditions")
        if self.kind == ClaimKind.IDENTITY_SPECIFICATION:
            require_text(self.field, "identity-defining field")
            require_text(self.partition, "reviewed mutually exclusive specification partition")
            if not self.conditions or not self.allowed_values:
                raise ValueError("An identity specification requires applicability and explicit allowed values")

    @property
    def evidence(self):
        return Evidence(self.definition, f"{self.kind.value}:{self.locator}", self.source, self.authority)


def qualify(item: Ingredient, claims: tuple[AuthorityClaim, ...]) -> Ingredient:
    """Project reviewed claims into existing comparison inputs and keep the original provenance.

    The caller authenticates the document and reviews its definition, designation binding and
    any explicitly excluded alternatives. This function checks the input contract and eligibility.
    """
    designations, facets = list(item.designations), list(item.facets)
    for claim in claims:
        if (claim.subject, claim.designation, claim.native_scope) != (item.reference, item.label, item.scope):
            raise ValueError("Claim subject, original designation or native scope does not match ingredient")
        if claim.origin in {Origin.PREDICTION, Origin.UNVERIFIED}:
            continue
        if claim.kind == ClaimKind.WHOLE_DESIGNATION and claim.origin == Origin.ORIGINAL_AUTHORITY:
            designations.append(ScopedDesignation(
                item.reference, claim.authority, claim.revision, claim.referent, claim.covers, claim.evidence,
                claim.scheme, claim.comparison_scope or item.scope, tuple(sorted(set(claim.conditions))),
            ))
        elif claim.kind == ClaimKind.IDENTITY_SPECIFICATION:
            facets.append(Facet(
                item.reference, claim.field, claim.partition, claim.referent, Qualification.DEFINING_EXCLUSIVE,
                claim.evidence, claim.allowed_values, claim.comparison_scope or item.scope,
            ))
        elif claim.kind in {ClaimKind.MATERIAL, ClaimKind.CONSTITUENT}:
            facets.append(Facet(
                item.reference, claim.kind.value.lower(), claim.scheme, claim.referent,
                Qualification.DESCRIPTIVE, claim.evidence,
            ))
    return replace(item, designations=tuple(designations), facets=tuple(facets),
                   authority_claims=item.authority_claims + claims)
