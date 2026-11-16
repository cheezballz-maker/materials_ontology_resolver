"""Qualify reported function labels in a configured application vocabulary."""

from dataclasses import dataclass, field
from collections.abc import Mapping

from .contracts import EvidenceRole, FunctionalRole, ReportedFunction


def _key(text: str) -> str:
    return " ".join(text.upper().split())


@dataclass(frozen=True)
class FunctionVocabulary:
    reference: str
    labels: frozenset[str]
    aliases: Mapping[str, str] = field(default_factory=dict)
    label_references: Mapping[str, str] = field(default_factory=dict)

    def match(self, text: str) -> tuple[str, ...]:
        label = _key(text)
        label = self.aliases.get(label, label)
        if label in self.labels:
            return (label,)
        parts = tuple(self.aliases.get(part, part) for part in label.split(" - "))
        return parts if len(parts) == 2 and all(part in self.labels for part in parts) else ()


def qualify_function(function: ReportedFunction, vocabularies: Mapping[str, FunctionVocabulary]) -> FunctionalRole:
    label = function.evidence.original_value
    reference = function.vocabulary_reference
    vocabulary = vocabularies.get(_key(function.application_context))
    labels = ()
    qualification = "REPORTED"
    if vocabulary:
        labels = vocabulary.match(label)
        references = {vocabulary.label_references.get(term,vocabulary.reference) for term in labels}
        if len(references) == 1 and reference in (None, *references):
            reference = references.pop()
            qualification = "VOCABULARY_VALIDATED" if len(labels) == 1 else "VOCABULARY_COMPONENTS_VALIDATED"
        else:
            qualification = "LABEL_UNMAPPED" if reference in (None,vocabulary.reference) else "VOCABULARY_REFERENCE_UNVERIFIED"
            labels = ()
    return FunctionalRole(label, function.application_context, reference, qualification, function.evidence,
                          EvidenceRole.SUPPORTING, labels)
