"""Comparison contracts. Qualified fields are supplied by a trusted evidence reviewer."""

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from canonical_registry.nomenclature_interpretation.contracts import (
    Evidence, InterpretationResult, Issue, ReportedIdentifier, TypedStructure, require_text,
)

if TYPE_CHECKING:
    from .qualification import AuthorityClaim


class Family(StrEnum):
    MOLECULAR = "molecular"
    INORGANIC = "inorganic"
    METALLIC = "metallic_material"
    COLORANT = "colorant"
    BOTANICAL = "botanical"
    POLYMER = "polymer_silicone"
    LIPID = "lipid_surfactant"
    BIOLOGICAL = "biological"
    PREPARATION = "preparation_mixture"


class Verdict(StrEnum):
    EQUIVALENT = "EQUIVALENT"
    DISTINCT = "DISTINCT"
    UNRESOLVED = "UNRESOLVED"


class Qualification(StrEnum):
    # The scheme defines a closed, single-valued identity slot at this scope.
    DEFINING_EXCLUSIVE = "DEFINING_EXCLUSIVE"
    DESCRIPTIVE = "DESCRIPTIVE"


def require_provenance(evidence: Evidence) -> None:
    require_text(evidence.source_reference, "qualified evidence source reference")


@dataclass(frozen=True, order=True)
class Scope:
    nomenclature: str
    application: str
    specificity: str

    def __post_init__(self):
        for key in ("nomenclature", "application", "specificity"):
            require_text(getattr(self, key), key)


@dataclass(frozen=True)
class ScopedDesignation:
    """Authority-bound whole ingredient, covering the listed families at the comparison scope.

    Revision identifies the mapping/authority snapshot, not the source concept revision.
    A generic synonym, regulatory cross-reference or chemical identifier is ineligible.
    """

    subject: str
    authority: str
    revision: str
    referent: str
    covers: frozenset[Family]
    evidence: Evidence
    scheme: str = ""
    comparison_scope: Scope | None = None
    conditions: tuple[str, ...] = ()

    def __post_init__(self):
        for key in ("subject", "authority", "revision", "referent"):
            require_text(getattr(self, key), key)
        if not self.covers or any(not isinstance(x, Family) for x in self.covers):
            raise ValueError("A scoped designation must cover at least one supported family")
        if self.comparison_scope is not None and not isinstance(self.comparison_scope, Scope):
            raise ValueError("A designation comparison scope must be a Scope")
        for value in self.conditions:
            require_text(value, "designation condition")
        require_provenance(self.evidence)


@dataclass(frozen=True)
class Facet:
    """Reviewed normalized value. Scheme includes qualifiers, units and vocabulary version."""

    subject: str
    field: str
    scheme: str
    value: str
    qualification: Qualification
    evidence: Evidence
    allowed_values: frozenset[str] = frozenset()
    comparison_scope: Scope | None = None

    def __post_init__(self):
        for key in ("subject", "field", "scheme", "value"):
            require_text(getattr(self, key), key)
        if not isinstance(self.qualification, Qualification):
            raise ValueError("Explicit facet qualification is required")
        if self.comparison_scope is not None and not isinstance(self.comparison_scope, Scope):
            raise ValueError("A facet comparison scope must be a Scope")
        if self.allowed_values and self.qualification != Qualification.DEFINING_EXCLUSIVE:
            raise ValueError("Only defining facets may restrict the allowed values")
        for value in self.allowed_values:
            require_text(value, "allowed facet value")
        require_provenance(self.evidence)


class RegistryType(StrEnum):
    SUBSTANCE = "Substance"
    CHEMICAL_CONCEPT = "ChemicalConcept"


@dataclass(frozen=True)
class ChemicalTarget:
    """An existing resolved registry link already validated against the named snapshot."""

    subject: str
    registry_type: RegistryType
    registry: str
    snapshot: str
    target: str
    evidence: Evidence

    def __post_init__(self):
        if not isinstance(self.registry_type, RegistryType):
            raise ValueError("Typed chemical registry link required")
        for key in ("subject", "registry", "snapshot", "target"):
            require_text(getattr(self, key), key)
        require_provenance(self.evidence)


@dataclass(frozen=True)
class MolecularBinding:
    """An independently reviewed, whole-referent graph. May be chemically underspecified."""

    subject: str
    structure: TypedStructure
    binding_evidence: Evidence

    def __post_init__(self):
        require_text(self.subject, "molecular binding subject")
        require_provenance(self.structure.evidence)
        require_provenance(self.binding_evidence)


@dataclass(frozen=True)
class Ingredient:
    reference: str
    label: str
    scope: Scope
    families: frozenset[Family] = frozenset()
    designations: tuple[ScopedDesignation, ...] = ()
    facets: tuple[Facet, ...] = ()
    chemical_target: ChemicalTarget | None = None
    molecular: MolecularBinding | None = None
    interpretation: InterpretationResult | None = None
    reported_identifiers: tuple[ReportedIdentifier, ...] = ()
    search_aliases: tuple[Evidence, ...] = ()
    issues: tuple[Issue, ...] = ()
    authority_claims: tuple["AuthorityClaim", ...] = ()

    def __post_init__(self):
        require_text(self.reference, "concept reference")
        require_text(self.label, "ingredient label")
        if any(not isinstance(x, Family) for x in self.families):
            raise ValueError("Explicit qualified ingredient families required")
        if any(d.subject != self.reference for d in self.designations):
            raise ValueError("Designation binding belongs to a different ingredient")
        if any(f.subject != self.reference for f in self.facets):
            raise ValueError("Facet belongs to a different ingredient")
        if self.chemical_target and self.chemical_target.subject != self.reference:
            raise ValueError("Chemical target belongs to a different ingredient")
        if self.molecular and self.molecular.subject != self.reference:
            raise ValueError("Molecular binding belongs to a different ingredient")
        if any(claim.subject != self.reference for claim in self.authority_claims):
            raise ValueError("Authority claim belongs to a different ingredient")
        if self.interpretation is not None:
            designation = self.interpretation.designation
            if (designation.source_reference, designation.original_value) != (self.reference, self.label):
                raise ValueError("Interpretation belongs to a different ingredient")


@dataclass(frozen=True)
class AttributeComparison:
    attribute: str
    scheme: str
    left: tuple[str, ...]
    right: tuple[str, ...]
    result: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class Relationship:
    kind: str
    scheme: str
    value: str
    evidence: tuple[Evidence, ...]
    subject_object: tuple[str, str] | None = None


@dataclass(frozen=True)
class Decision:
    concepts: tuple[str, str]
    scopes: tuple[Scope, Scope]
    verdict: Verdict
    rules: tuple[str, ...]
    attributes: tuple[AttributeComparison, ...]
    reasons: tuple[str, ...]
    relationships: tuple[Relationship, ...]
    evidence: tuple[Evidence, ...]
    issues: tuple[Issue, ...]
    policy_version: str = "ingredient-equivalence/1.1"
    evaluated_scope: Scope | None = None
    authority_claims: tuple["AuthorityClaim", ...] = ()
