"""Source-neutral contracts for interpreting a designation and its reported evidence."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class Category(StrEnum):
    STRUCTURAL = "STRUCTURAL"
    NOMENCLATURE = "NOMENCLATURE"
    IDENTIFIER = "IDENTIFIER"
    MATERIAL = "MATERIAL"


class EvidenceRole(StrEnum):
    DEFINING = "DEFINING"
    SUPPORTING = "SUPPORTING"
    CANDIDATE_ONLY = "CANDIDATE_ONLY"


class State(StrEnum):
    VALIDATED = "VALIDATED"
    PARTIAL = "PARTIAL"
    UNCERTAIN = "UNCERTAIN"
    UNINTERPRETED = "UNINTERPRETED"
    CONFLICT = "CONFLICT"


class StructureKind(StrEnum):
    SMILES = "smiles"
    INCHI = "inchi"


def require_text(value: str, field: str, *, multiline: bool = False) -> None:
    allowed = "\t\r\n" if multiline else ""
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 and c not in allowed for c in value):
        raise ValueError(f"{field} must be nonblank text without control characters")


@dataclass(frozen=True)
class Evidence:
    original_value: str
    field: str
    source_reference: str | None = None
    source_label: str | None = None

    def __post_init__(self):
        require_text(self.original_value, "original_value", multiline=True)
        require_text(self.field, "field")


@dataclass(frozen=True)
class TypedStructure:
    kind: StructureKind
    evidence: Evidence

    def __post_init__(self):
        if not isinstance(self.kind, StructureKind):
            raise ValueError("Structure type must be explicitly SMILES or InChI")


@dataclass(frozen=True)
class ReportedIdentifier:
    scheme: str
    evidence: Evidence

    def __post_init__(self):
        require_text(self.scheme, "identifier scheme")


@dataclass(frozen=True)
class ReportedFunction:
    evidence: Evidence
    application_context: str
    vocabulary_reference: str | None = None

    def __post_init__(self):
        require_text(self.application_context, "application context")
        if self.vocabulary_reference is not None:
            require_text(self.vocabulary_reference, "vocabulary reference")


@dataclass(frozen=True)
class FunctionalRole:
    reported_function: str
    application_context: str
    vocabulary_reference: str | None
    qualification: str
    evidence: Evidence
    evidence_role: EvidenceRole
    qualified_vocabulary_labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class InterpretationInput:
    designation: Evidence
    structures: tuple[TypedStructure, ...] = ()
    identifiers: tuple[ReportedIdentifier, ...] = ()
    functions: tuple[ReportedFunction, ...] = ()
    source_definition: Evidence | None = None

    def __post_init__(self):
        require_text(self.designation.original_value, "designation")


@dataclass(frozen=True)
class Assertion:
    category: Category
    predicate: str
    value: str | int | dict
    evidence_role: EvidenceRole
    evidence: Evidence
    method: str
    exclusive_slot: str | None = None
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class Issue:
    code: str
    evidence: tuple[Evidence, ...] = ()
    detail: str | None = None
    conflict: bool = False
    affected_slots: tuple[str, ...] = ()


@dataclass(frozen=True)
class GraphComparison:
    left: Evidence
    right: Evidence
    relation: str


@dataclass(frozen=True)
class ModuleResult:
    module: str
    state: State
    conventions: tuple[str, ...] = ()
    assertions: tuple[Assertion, ...] = ()
    issues: tuple[Issue, ...] = ()
    whole_referent_graph_unestablished: bool = False


@dataclass(frozen=True)
class InterpretationResult:
    designation: Evidence
    state: State
    modules: tuple[ModuleResult, ...]
    assertions: tuple[Assertion, ...]
    withheld_assertions: tuple[Assertion, ...]
    issues: tuple[Issue, ...]
    functions: tuple[FunctionalRole, ...]
    graph_comparisons: tuple[GraphComparison, ...]


class Interpreter(Protocol):
    def interpret(self, item: InterpretationInput) -> ModuleResult | None:
        """Return None if the module found no recognizable convention or applicable input."""
