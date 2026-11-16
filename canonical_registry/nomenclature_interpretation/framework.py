"""Run independent interpreters and reconcile assertions without resolving identities."""

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import replace
from itertools import combinations
import re
from time import perf_counter

from .contracts import (
    Assertion, Category, EvidenceRole, GraphComparison,
    InterpretationInput, InterpretationResult, Interpreter, Issue, State,
)
from .functions import FunctionVocabulary, qualify_function
from .molecular import MolecularChemical, NameParser, reconcile_graphs
from .specialists import (
    BiologicalBiotechnological, Botanical, Colorant, GenericIngredient, InorganicMineral,
    LipidSurfactant, PolymerSilicone, PreparationMixture,
)

MODULE_ORDER = {name:index for index,name in enumerate((
    "molecular_chemical","inorganic_mineral","botanical","biological_biotechnological",
    "polymer_silicone","lipid_surfactant","colorant","preparation_mixture",
))}


def _evidence_order(assertion):
    evidence = assertion.evidence
    return (evidence.source_reference or "",evidence.field,evidence.original_value,evidence.source_label or "",
            str(getattr(assertion,"kind",getattr(assertion,"scheme",""))),
            getattr(assertion,"application_context",""),getattr(assertion,"vocabulary_reference",None) or "")


class InterpretationFramework:
    def __init__(self, *, name_parser: NameParser | None = None,
                 interpreters: tuple[Interpreter, ...] | None = None,
                 function_vocabularies: Mapping[str, FunctionVocabulary] | None = None, timings=None):
        self.timings = timings
        self.interpreters = interpreters if interpreters is not None else (
            MolecularChemical(name_parser,timings=timings), InorganicMineral(), Botanical(),
            BiologicalBiotechnological(), PolymerSilicone(), LipidSurfactant(),
            Colorant(), PreparationMixture(),
        )
        self.function_vocabularies = {
            " ".join(context.upper().split()): vocabulary
            for context, vocabulary in (function_vocabularies or {}).items()
        }

    def interpret(self, item: InterpretationInput) -> InterpretationResult:
        begin = perf_counter() if self.timings is not None else None
        item = replace(item, structures=tuple(sorted(set(item.structures),key=_evidence_order)),
                       identifiers=tuple(sorted(set(item.identifiers),key=_evidence_order)),
                       functions=tuple(sorted(set(item.functions),key=_evidence_order)))
        if begin is not None:
            self.timings["evidence_order_seconds"] += perf_counter()-begin
        modules = []
        for module in self.interpreters:
            start = perf_counter() if self.timings is not None else None
            result = module.interpret(item)
            if start is not None:
                self.timings[type(module).__name__+"_seconds"] += perf_counter()-start
            if result is not None:
                modules.append(result)
        modules.sort(key=lambda m:(MODULE_ORDER.get(m.module,len(MODULE_ORDER)),m.module))
        begin = perf_counter() if self.timings is not None else None
        specialist_supported = any(result.assertions for result in modules)
        if not specialist_supported:
            modules.append(GenericIngredient().interpret(item))
        assertions = [assertion for result in modules for assertion in result.assertions]
        assertions.extend(
            Assertion(Category.IDENTIFIER, identifier.scheme, identifier.evidence.original_value,
                      EvidenceRole.CANDIDATE_ONLY, identifier.evidence, "REPORTED_IDENTIFIER")
            for identifier in item.identifiers
        )
        issues = [issue for result in modules for issue in result.issues]
        graph_indices = [i for i, a in enumerate(assertions) if a.category == Category.STRUCTURAL]
        withheld = _exclusive_conflicts(assertions, issues)
        comparisons = _compare_graphs(assertions, graph_indices, issues, withheld)
        if graph_indices and any(result.whole_referent_graph_unestablished for result in modules):
            issues.append(Issue("WHOLE_REFERENT_GRAPH_UNESTABLISHED", (item.designation,)))
            withheld.update(graph_indices)
        if any(comparison.relation != "COMPATIBLE" for comparison in comparisons):
            withheld.update(graph_indices)
        withheld.update(_dependent_conflicts(assertions,issues))
        if any(issue.conflict for issue in issues):
            withheld.update(graph_indices)
            state = State.CONFLICT
        elif not specialist_supported:
            issues.append(Issue("NO_SUPPORTED_STRUCTURED_INTERPRETATION", (item.designation,)))
            state = State.UNINTERPRETED
        elif issues or any(result.state != State.VALIDATED for result in modules):
            state = State.PARTIAL
        else:
            state = State.VALIDATED

        if begin is not None:
            self.timings["reconciliation_seconds"] += perf_counter()-begin
            begin = perf_counter()
        functions = tuple(qualify_function(function, self.function_vocabularies) for function in item.functions)
        if begin is not None:
            self.timings["role_qualification_seconds"] += perf_counter()-begin
        return InterpretationResult(
            item.designation, state, tuple(modules),
            tuple(a for i, a in enumerate(assertions) if i not in withheld),
            tuple(a for i, a in enumerate(assertions) if i in withheld),
            tuple(issues), functions, tuple(comparisons),
        )


def _compare_graphs(assertions, graph_indices, issues, withheld):
    comparisons = []
    graphs = [assertions[i] for i in graph_indices]
    for left, right in combinations(graphs, 2):
        _, relation = reconcile_graphs(left.value, right.value)
        comparisons.append(GraphComparison(left.evidence, right.evidence, relation))
        if relation != "COMPATIBLE":
            issues.append(Issue(relation, (left.evidence, right.evidence),
                                conflict=relation.startswith("CONFLICTING_")))
    for i, assertion in enumerate(assertions):
        if assertion.category == Category.IDENTIFIER and assertion.predicate.casefold() in {
            "molecularformula", "molecular_formula", "formula",
        } and graphs:
            reported = _formula_counts(assertion.value)
            computed = [_formula_counts(graph.value["formula"]) for graph in graphs]
            evidence = (assertion.evidence, *(graph.evidence for graph in graphs))
            if reported is None or (reported not in computed and None in computed):
                issues.append(Issue("MOLECULAR_FORMULA_COMPARISON_INCOMPLETE", evidence))
            elif reported not in computed:
                issues.append(Issue("MOLECULAR_FORMULA_DISAGREES_WITH_ALL_GRAPHS", evidence, conflict=True))
                withheld.add(i)
        if (assertion.category == Category.IDENTIFIER and assertion.predicate.casefold() == "inchikey"
                and graphs and all(g.value["inchikey"] != assertion.value for g in graphs)):
            issues.append(Issue("INCHIKEY_DISAGREES_WITH_ALL_GRAPHS",
                                (assertion.evidence, *(g.evidence for g in graphs)), conflict=True))
            withheld.add(i)
    return comparisons


_ELEMENT = re.compile(r"([A-Z][a-z]?)([1-9][0-9]*)?")


def _formula_counts(value):
    """Compare simple elemental formulas without dropping hydrate, charge or isotope syntax."""
    value = value.strip()
    if len(value) > 512:
        return None
    parts = list(_ELEMENT.finditer(value))
    if not parts or "".join(part.group() for part in parts) != value:
        return None
    counts = Counter()
    for part in parts:
        counts[part[1]] += int(part[2] or 1)
    return counts


def _exclusive_conflicts(assertions, issues):
    """Only compare claims where an interpreter explicitly declares a single-valued slot."""
    slots = defaultdict(list)
    for i, assertion in enumerate(assertions):
        if assertion.exclusive_slot is not None:
            slots[assertion.exclusive_slot].append(i)
    withheld = set()
    for slot, indexes in slots.items():
        first, *rest = indexes
        if any(assertions[i].value != assertions[first].value for i in rest):
            withheld.update(indexes)
            issues.append(Issue("CONTRADICTORY_EXCLUSIVE_ASSERTIONS",
                                tuple(assertions[i].evidence for i in indexes), slot, conflict=True,
                                affected_slots=(slot,)))
    return withheld


def conflict_dimension(issue):
    if issue.code == "WHOLE_REFERENT_GRAPH_UNESTABLISHED":
        return "WHOLE_REFERENT_ATTRIBUTION"
    if any(slot.startswith("botanical.") for slot in issue.affected_slots):
        return "BOTANICAL_SCOPE"
    if any(slot.startswith("preparation.") for slot in issue.affected_slots):
        return "PREPARATION_SCOPE"
    if ("GRAPH" in issue.code or "STRUCTURE" in issue.code or "INCHI" in issue.code or
            "STEREO" in issue.code or "MOLECULAR_FORMULA" in issue.code):
        return "STRUCTURAL_GRAPH"
    return "CONTRADICTORY_SOURCE_CLAIMS" if issue.conflict else "UNRESOLVED_EVIDENCE"


def _dependent_conflicts(assertions, issues):
    blocked = {slot for issue in issues if issue.conflict for slot in issue.affected_slots}
    unscoped_sources = {e for issue in issues if issue.conflict and not issue.affected_slots
                        and conflict_dimension(issue)=="CONTRADICTORY_SOURCE_CLAIMS" for e in issue.evidence}
    return {i for i,a in enumerate(assertions)
            if a.exclusive_slot in blocked or blocked.intersection(a.depends_on) or a.evidence in unscoped_sources}
