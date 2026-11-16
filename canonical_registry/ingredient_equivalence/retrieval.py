"""Inverted candidate index. All hits are advisory and bucket exclusions are visible."""

from collections import defaultdict
from dataclasses import dataclass
import re

from .contracts import Ingredient
from chemistry import describe, normalize_name
from .policies import RELATED_FACETS, SLOTS


FACET_KEYS = frozenset(RELATED_FACETS) | frozenset(
    field for fields in SLOTS.values() for field in fields
) - {"composition_scope", "material_form", "preparation", "denaturing", "architecture", "plant_part"}
INTERPRETER_HINTS = {
    "reported_taxon_text", "ColourIndex", "ColourIndexGenericName", "reported_polyether_grade",
    "reported_polymer_designation_number", "reported_polymer_name_segments",
}
WEIGHTS = {
    "designation": 100, "canonical": 60, "graph_candidate": 55, "authority_cross_reference": 42,
    "label": 35, "reported": 25, "facet": 18, "interpreter_hint": 12, "name_token": 4,
}
GENERIC_TOKENS = {"acid", "sodium", "calcium", "potassium", "extract", "mixture", "powder", "solution"}


def keys(item: Ingredient, *, name_tokens: bool = False) -> set[tuple[str, ...]]:
    """Use normalized names, typed IDs and grounded descriptors without global category blocks."""
    out = {("label", normalize_name(name).casefold()) for name in
           (item.label, *(e.original_value for e in item.search_aliases))}
    out.update(("reported", i.scheme.casefold(), normalize_name(i.evidence.original_value))
               for i in item.reported_identifiers)
    out.update(("designation", d.authority, d.scheme, d.revision, d.referent,
                (d.comparison_scope or item.scope).nomenclature,
                (d.comparison_scope or item.scope).application,
                (d.comparison_scope or item.scope).specificity) for d in item.designations)
    if name_tokens:
        out.update(("name_token", token) for token in re.findall(r"[^\W_]+", item.label.casefold())
                   if len(token) >= 5 and token not in GENERIC_TOKENS)
    out.update(("authority_cross_reference", c.authority, c.scheme, c.referent)
               for c in item.authority_claims
               if c.kind == "RELATED_TERM" and c.origin == "ORIGINAL_AUTHORITY")
    out.update(("facet", f.field, f.scheme, f.value) for f in item.facets if f.field in FACET_KEYS)
    if target := item.chemical_target:
        out.add(("canonical", target.registry_type.value, target.registry, target.target))
    if item.molecular and len(item.molecular.structure.evidence.original_value) <= 1200:
        structure = item.molecular.structure
        try:
            graph = describe(structure.evidence.original_value, structure.kind.value)
            out.add(("graph_candidate", graph["inchikey"]))
        except (ValueError, RuntimeError):
            pass  # The adjudicator reports validation failures for directly compared pairs.
    if item.interpretation is not None:
        for assertion in item.interpretation.assertions:
            if assertion.predicate in INTERPRETER_HINTS and isinstance(assertion.value, str):
                out.add(("interpreter_hint", assertion.predicate, normalize_name(assertion.value).casefold()))
    return out


@dataclass(frozen=True)
class CandidateResult:
    reference: str
    matches: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...]
    skipped: tuple[tuple[tuple[str, ...], int], ...]
    candidate_count: int = 0
    postings_visited: int = 0


class CandidateIndex:
    def __init__(self, items, *, max_bucket=64, name_tokens=True):
        if not isinstance(max_bucket, int) or max_bucket < 2:
            raise ValueError("Bucket limit must be an integer of at least two")
        self._max_bucket = max_bucket
        self._name_tokens = name_tokens
        self._postings = defaultdict(list)
        self._counts = defaultdict(int)
        self._keys = {}
        for item in items:
            if item.reference in self._keys:
                raise ValueError("Duplicate concept reference in candidate index")
            item_keys = keys(item, name_tokens=name_tokens)
            self._keys[item.reference] = (item, item_keys)
            for key in item_keys:
                self._counts[key] += 1
                if key[0] == "designation":
                    self._postings[key].append(item.reference)
                elif self._counts[key] == max_bucket + 1:
                    del self._postings[key]
                elif self._counts[key] <= max_bucket:
                    self._postings[key].append(item.reference)

    def find(self, item: Ingredient, *, limit: int | None = None) -> CandidateResult:
        if limit is not None and (not isinstance(limit, int) or limit < 1):
            raise ValueError("Candidate limit must be a positive integer")
        matches = defaultdict(list)
        skipped = []
        postings_visited = 0
        stored = self._keys.get(item.reference)
        query_keys = stored[1] if stored and stored[0] is item else keys(item, name_tokens=self._name_tokens)
        for key in sorted(query_keys):
            count = self._counts.get(key, 0)
            if count > self._max_bucket and key[0] != "designation":
                skipped.append((key, count))
            else:
                posting = self._postings.get(key, ())
                postings_visited += len(posting)
                for reference in posting:
                    if reference != item.reference:
                        matches[reference].append(key)
        refs = sorted(matches) if limit is None else sorted(matches, key=lambda ref: (
            -sum(WEIGHTS[key[0]] for key in matches[ref]), ref,
        ))[:limit]
        return CandidateResult(item.reference, tuple((ref, tuple(matches[ref])) for ref in refs),
                               tuple(skipped), len(matches), postings_visited)
