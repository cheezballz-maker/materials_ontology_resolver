"""Use the existing OPSIN bridge and resolver's graph and name interpretation."""

import re
from time import perf_counter
from typing import Protocol

# The existing input qualification layer initializes the shared resolver module paths.
from canonical_registry.enrichment.chemical_qualification import reconcile_graphs
from chemistry import describe, normalize_name
from composition_constraints import check, extract
from name_interpretation import interpret_preferred
from systematic_notation import descriptors

from .contracts import Assertion, Category, EvidenceRole, Issue, ModuleResult, State

__all__ = ["MolecularChemical", "reconcile_graphs"]


class NameParser(Protocol):
    def opsin(self, name: str) -> dict: ...


class MolecularChemical:
    def __init__(self, name_parser: NameParser | None = None, *, timings=None):
        self.name_parser = name_parser
        self.timings = timings

    def _describe(self, *args):
        if self.timings is None:
            return describe(*args)
        start = perf_counter()
        try:
            return describe(*args)
        finally:
            self.timings["rdkit_graph_description_seconds"] += perf_counter()-start
            self.timings["rdkit_graph_description_calls"] += 1

    def interpret(self, item):
        name = item.designation.original_value
        assertions, issues, conventions = [], [], []
        for typed in item.structures:
            try:
                if len(typed.evidence.original_value) > 1200:
                    raise ValueError("Original structure exceeds the interpretation budget")
                graph = self._describe(typed.evidence.original_value, typed.kind.value)
            except (ValueError, RuntimeError) as exc:
                issues.append(Issue("TYPED_STRUCTURE_NOT_VALIDATED", (typed.evidence,), str(exc)))
                continue
            conventions.append(f"TYPED_{typed.kind.name}")
            assertions.append(Assertion(Category.STRUCTURAL, "molecular_graph", graph, EvidenceRole.CANDIDATE_ONLY,
                                        typed.evidence, "STRICT_RDKIT_STRUCTURE"))

        # Reuse the resolver's lexical composition extractor. A reported count
        # is a name constraint. It never generates a graph or binds a salt form.
        composition = extract(name)
        for claim in composition["component_counts"]["value"]:
            conventions.append("NAMED_COMPONENT_COUNT")
            assertions.append(Assertion(
                Category.NOMENCLATURE, "reported_component_count",
                {"component": claim["component"], "count": claim["count"]}, EvidenceRole.DEFINING,
                item.designation, "RESOLVER_COMPOSITION_CONSTRAINTS",
                exclusive_slot="reported_component_count:" + claim["component"],
            ))

        if self.name_parser is not None:
            query = normalize_name(name)
            if len(query) > 1000:
                issues.append(Issue("NAME_INTERPRETATION_BUDGET", (item.designation,)))
            else:
                self._interpret_name(item, query, assertions, issues, conventions)

        if not assertions and not issues:
            return None
        graphs = [a for a in assertions if a.category == Category.STRUCTURAL]
        if item.source_definition and self.name_parser is not None:
            for graph in graphs:
                if graph.method == "OPSIN_THEN_STRICT_RDKIT":
                    issue = self._definition_issue(item, graph.value)
                    if issue:
                        issues.append(issue)
        if composition["component_counts"]["status"] == "SPECIFIED":
            for assertion in graphs:
                comparison = check(composition, assertion.value)
                if comparison["status"] == "CONFLICT":
                    issues.append(Issue("GRAPH_DISAGREES_WITH_NAMED_COMPOSITION", (item.designation, assertion.evidence),
                                        ", ".join(comparison["reason_codes"]), conflict=True))
        state = State.UNCERTAIN
        if graphs:
            state = State.PARTIAL if issues or any(
                any(s["specified"] != "Specified" for s in a.value["stereo"]) or a.value["inchi_warning"]
                for a in graphs
            ) else State.VALIDATED
        elif assertions:
            state = State.PARTIAL
        return ModuleResult("molecular_chemical", state, tuple(dict.fromkeys(conventions)),
                            tuple(assertions), tuple(issues))

    def _interpret_name(self, item, query, assertions, issues, conventions):
        evidence = item.designation
        response = self.name_parser.opsin(query)
        if response["status"] != "SUCCESS":
            if response["status"] != "FAILURE":
                issues.append(Issue("OPSIN_NAME_NOT_ESTABLISHED", (evidence,), response.get("diagnostic")))
            return
        try:
            graph = self._describe(response["smiles"])
            cml_reader = getattr(self.name_parser, "opsin_cml", None)
            cml = cml_reader(query) if cml_reader and descriptors(query) else None
            reading, _ = interpret_preferred(query, {**response, "structure": graph}, cml_result=cml)
        except (ValueError, RuntimeError) as exc:
            issues.append(Issue("NAME_GRAPH_NOT_VALIDATED", (evidence,), str(exc)))
            return
        conventions.append("OPSIN_CHEMICAL_NAME")
        assertions.append(Assertion(Category.NOMENCLATURE, "molecular_name_reading", reading["status"],
                                    EvidenceRole.SUPPORTING, evidence, "RESOLVER_NAME_INTERPRETATION"))
        if reading["status"] not in ("ESTABLISHED", "PARTIAL"):
            issues.append(Issue("OPSIN_NAME_NOT_ESTABLISHED", (evidence,), reading["diagnostic"]))
            return
        if reading["status"] == "PARTIAL":
            issues.append(Issue("MOLECULAR_NAME_UNDERSPECIFIED", (evidence,), reading["diagnostic"]))
        assertions.append(Assertion(Category.STRUCTURAL, "molecular_graph", graph, EvidenceRole.CANDIDATE_ONLY,
                                    evidence, "OPSIN_THEN_STRICT_RDKIT"))

    def _definition_issue(self, item, graph):
        """Treat a simple, explicit identity sentence as a potential contradiction."""
        source = item.source_definition
        sentence = normalize_name(source.original_value)
        statement = re.fullmatch(r"(.{1,180}?) is (.{1,160}?)\.", sentence, re.I)
        if not statement or statement[1].casefold() != normalize_name(item.designation.original_value).casefold():
            return None
        claim = statement[2]
        # Articles, prose and mixture descriptions do not assert a simple
        # chemical name equivalence through this narrow grammar.
        if re.match(r"(?:a|an|the)\b", claim, re.I) or "." in claim:
            return None
        response = self.name_parser.opsin(claim)
        if response["status"] != "SUCCESS":
            return None
        evidence = (item.designation, source)
        try:
            other = self._describe(response["smiles"])
            reading, _ = interpret_preferred(claim, {**response, "structure": other})
            if reading["status"] not in {"ESTABLISHED", "PARTIAL"}:
                return Issue("SOURCE_DEFINITION_GRAPH_COMPARISON_INCOMPLETE", evidence)
            _, relation = reconcile_graphs(graph, other)
        except (ValueError, RuntimeError):
            return Issue("SOURCE_DEFINITION_GRAPH_COMPARISON_INCOMPLETE", evidence)
        if relation.startswith("CONFLICTING_"):
            return Issue("SOURCE_DEFINITION_DISAGREES_WITH_NAME_GRAPH", evidence, relation, conflict=True)
        if relation != "COMPATIBLE":
            return Issue("SOURCE_DEFINITION_GRAPH_COMPARISON_INCOMPLETE", evidence, relation)
        return None
