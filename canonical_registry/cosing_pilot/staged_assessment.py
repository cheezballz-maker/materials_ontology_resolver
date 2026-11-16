"""Run and cache explicit assessment stages against specific source revisions."""

from collections import Counter
from contextlib import ExitStack
from dataclasses import asdict, replace
from hashlib import file_digest
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from time import perf_counter

from rdkit import rdBase

from canonical_registry.ingredient_equivalence.adapters import from_cosing
from canonical_registry.ingredient_equivalence.evaluate import COSMETIC
from canonical_registry.nomenclature_interpretation import InterpretationFramework
from canonical_registry.nomenclature_interpretation.contracts import (
    Assertion, Category, Evidence, FunctionalRole, GraphComparison, InterpretationResult, Issue, ModuleResult, State,
)
from canonical_registry.nomenclature_interpretation.cosing_preview_adapter import COSMETICS_FUNCTIONS, adapt_cosing_preview
from providers import Bridge, DEFAULT_JAR

from .cosing_source import PARENT
from .organization import _apply_review, _reviewed_inputs, assertion_audit, review_pairs, supported_attributes
from .registry import canonical, fingerprint

ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES = {
    "molecular_chemical", "inorganic_mineral", "botanical", "biological_biotechnological",
    "polymer_silicone", "lipid_surfactant", "colorant", "preparation_mixture", "generic_ingredient",
}
HEAD = """SELECT d.concept_id,d.source_reference,d.registered_revision,h.observed_revision,
                 h.present,h.continuity_hold,p.payload_json
          FROM domain_concept d JOIN source_head h USING(concept_id)
          LEFT JOIN source_payload p ON p.concept_id=d.concept_id AND p.revision=h.observed_revision"""


def _digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def _policy_files(folders):
    return {
        path.relative_to(ROOT).as_posix(): _digest(path)
        for folder in folders for path in sorted((ROOT / folder).rglob("*.py"))
        if not path.name.startswith("test_") and "evaluation" not in path.parts and "fixtures" not in path.parts
    }


def interpretation_version(typed_only):
    paths = ("nomenclature_interpretation",)
    dependencies = {"rdkit": rdBase.rdkitVersion, "source_adapter": _digest(ROOT / "cosing_pilot/cosing_source.py"),
                    "support_policy": _digest(ROOT / "cosing_pilot/organization.py"),
                    "stage": _digest(Path(__file__))}
    for name in ("chemistry.py", "providers.py", "RegistryBridge.java"):
        dependencies[name] = _digest(ROOT / name)
    if not typed_only:
        dependencies["jar"] = _digest(DEFAULT_JAR)
        dependencies["java"] = subprocess.run(["java", "-version"], capture_output=True, text=True,
                                               timeout=15, check=True).stderr
    return "interpretation-v2:" + fingerprint([typed_only, dependencies, _policy_files(paths)])


def _restore(trace):
    def assertion(item):
        return Assertion(**{**item,"depends_on":tuple(item.get("depends_on",())),
                            "evidence": Evidence(**item["evidence"])})

    def issue(item):
        return Issue(**{**item,"affected_slots":tuple(item.get("affected_slots",())),
                        "evidence": tuple(Evidence(**e) for e in item["evidence"])})

    return InterpretationResult(
        Evidence(**trace["designation"]), trace["state"],
        tuple(ModuleResult(m["module"], m["state"], tuple(m["conventions"]),
                           tuple(map(assertion,m["assertions"])), tuple(map(issue,m["issues"])),
                           m["whole_referent_graph_unestablished"]) for m in trace["modules"]),
        tuple(map(assertion,trace["assertions"])), tuple(map(assertion,trace["withheld_assertions"])),
        tuple(map(issue,trace["issues"])),
        tuple(FunctionalRole(**{**f,"evidence":Evidence(**f["evidence"]),
                               "qualified_vocabulary_labels":tuple(f["qualified_vocabulary_labels"])})
              for f in trace["functions"]),
        tuple(GraphComparison(Evidence(**g["left"]),Evidence(**g["right"]),g["relation"])
              for g in trace["graph_comparisons"]),
    )


def _select(registry, concept_ids, source_ids, batch):
    filters = ["substr(d.source_reference,1,?)=?"]
    args = [len(PARENT)+1,PARENT+":"]
    for column, values in (
        ("d.concept_id", [item.upper() for item in concept_ids]),
        ("d.source_reference", [item if ":" in item else f"{PARENT}:{item}" for item in source_ids]),
    ):
        if values:
            filters.append(f"{column} IN ({','.join('?' for _ in values)})")
            args.extend(values)
    with registry.reader() as db:
        registry._verify(db,(2,))
        if batch:
            run = db.execute("SELECT completed FROM registration_run WHERE run_id=?",(batch,)).fetchone()
            if run is None or not run[0]:
                raise ValueError("Select a completed registration batch")
            filters.append("""EXISTS(SELECT 1 FROM registration_member m WHERE m.run_id=?
                              AND m.concept_id=d.concept_id AND m.revision=h.observed_revision)""")
            args.append(batch)
        return db.execute(HEAD+" WHERE "+" AND ".join(filters)+" ORDER BY d.concept_id",args).fetchall()


def _eligible(row, pending):
    return row["present"] and row["payload_json"] and (
        pending or (not row["continuity_hold"] and row["registered_revision"] == row["observed_revision"]))


def _current(db, row, pending):
    fresh = db.execute(HEAD+" WHERE d.concept_id=?",(row["concept_id"],)).fetchone()
    return fresh is not None and _eligible(fresh,pending) and dict(fresh) == dict(row)


def _cache(db, row, version):
    return db.execute("SELECT * FROM assessment WHERE concept_id=? AND revision=? AND pipeline_version=?",
                      (row["concept_id"],row["observed_revision"],version)).fetchone()


def _insert(db, row, version, attempted, attributes, roles, summary, trace):
    return db.execute("INSERT INTO assessment VALUES(?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                      (row["concept_id"],row["observed_revision"],version,int(attempted),canonical(attributes),
                       canonical(roles),canonical(summary),canonical(trace))).rowcount


class _AssessmentBridge(Bridge):
    failures = 0
    elapsed = 0.0
    calls = 0

    def request(self, kind, value):
        start = perf_counter()
        response = super().request(kind,value)
        self.elapsed += perf_counter()-start
        self.calls += 1
        self.failures += int(response[0] == "ERROR")
        return response


def _bridge(stack):
    bridge = _AssessmentBridge(build_directory=stack.enter_context(TemporaryDirectory(dir=ROOT / "cosing_pilot")))
    stack.callback(bridge.close)
    return bridge


def _interpret(registry, rows, version, *, typed_only, pending, capability, overlay=None, timings=None,
               after_commit=None):
    counts = Counter()
    with ExitStack() as stack, rdBase.BlockLogs():
        framework = None
        bridge = None
        for row in rows:
            if not _eligible(row,pending):
                counts["source_held_or_payload_unavailable"] += 1
                continue
            with registry.reader() as db:
                cached = _cache(db,row,version)
            if cached:
                summary = json.loads(cached["summary_json"])
                if summary.get("input_error"):
                    counts["cached_invalid_source_packet"] += 1
                else:
                    counts["cached" if not capability or capability in summary["modules"] else "capability_excluded"] += 1
                continue
            packet = json.loads(row["payload_json"])
            provenance = None
            if overlay is not None:
                packet["source"],packet["aliases"],provenance = overlay(row,packet)
            try:
                item = adapt_cosing_preview(packet["source"],packet["aliases"] or [],
                                           include_registry_claims=overlay is not None)
            except ValueError as error:
                summary = {"stage":"INTERPRETATION","modules":[],"input_error":"INVALID_SOURCE_PACKET"}
                with registry.writer() as db:
                    if _current(db,row,pending):
                        added = _insert(db,row,version,False,(),(),summary,{"diagnostic":str(error)})
                        counts["invalid_source_packet" if added else "cached_invalid_source_packet"] += 1
                    else:
                        counts["stale"] += 1
                continue
            if framework is None:
                bridge = None if typed_only else _bridge(stack)
                framework = InterpretationFramework(name_parser=bridge,
                                                     function_vocabularies={"cosmetics":COSMETICS_FUNCTIONS},
                                                     timings=timings)
            failures = bridge.failures if bridge is not None else 0
            result = framework.interpret(item)
            if provenance is not None:
                result = _hold_incomplete_structure(result,provenance)
            if bridge is not None and bridge.failures != failures:
                counts["retryable_provider_failure"] += 1
                continue
            modules = [module.module for module in result.modules]
            attributes = supported_attributes(result)
            roles = tuple(asdict(role) for role in result.functions if role.qualification.startswith("VOCABULARY_")
                          and role.qualified_vocabulary_labels)
            summary = {"stage":"INTERPRETATION","modules":modules,"state":result.state,
                       "aliases_observed":packet["aliases"] is not None,
                       "chemical_candidate":("molecular_chemical" in modules or any(
                           a.category == Category.STRUCTURAL for a in (*result.assertions,*result.withheld_assertions)))}
            with registry.writer() as db:
                if _current(db,row,pending):
                    trace = {"interpretation":asdict(result)}
                    if provenance is not None:
                        trace["companion_evidence"] = provenance
                        trace["assertion_audit"] = assertion_audit(result)
                    added = _insert(db,row,version,False,attributes,roles,summary,trace)
                    if capability and capability not in modules:
                        counts["capability_excluded"] += 1
                        counts["screened_and_cached"] += added
                    else:
                        counts["assessed" if added else "cached"] += 1
                else:
                    counts["stale"] += 1
            if after_commit is not None:
                after_commit(counts)
        if bridge is not None and timings is not None:
            timings["opsin_transport_seconds"] += bridge.elapsed
            timings["opsin_transport_calls"] += bridge.calls
    return dict(counts)


def _hold_incomplete_structure(result,provenance):
    structural_types = {"SMILES","INCHI","INCHI_KEY","MOLECULAR_FORMULA"}
    if not any(row["type"] in structural_types for row in provenance["held_aliases"]):
        return result
    graphs = tuple(a for a in result.assertions if a.category==Category.STRUCTURAL)
    if not graphs:
        return result
    issue = Issue("INCOMPLETE_TYPED_STRUCTURE_EVIDENCE",(result.designation,))
    return replace(result,state=State.CONFLICT if result.state==State.CONFLICT else State.PARTIAL,
                   assertions=tuple(a for a in result.assertions if a.category!=Category.STRUCTURAL),
                   withheld_assertions=(*result.withheld_assertions,*graphs),issues=(*result.issues,issue))


class _CachedInterpretation:
    def __init__(self, result):
        self.result = result

    def interpret(self, item):
        if item.designation != self.result.designation:
            raise ValueError("Interpretation designation and source packet disagree")
        return self.result


def _equivalence(registry, eligible, version):
    prior = _reviewed_inputs()
    ingredients, by_source = {}, {}
    for row, cached in eligible:
        packet = json.loads(row["payload_json"])
        source, aliases = packet["source"], packet["aliases"] or []
        result = _restore(json.loads(cached["trace_json"])["interpretation"])
        item = from_cosing(source,aliases,COSMETIC,_CachedInterpretation(result))
        ingredients[item.reference] = _apply_review(item,source,aliases,prior)
        by_source[item.reference] = row
    from .readiness import DATA

    external = json.loads((DATA / "external_reviews.json").read_text(encoding="utf-8"))
    comparisons, _ = review_pairs(ingredients,external)
    added = 0
    with registry.writer() as db:
        for comparison in comparisons:
            left, right = by_source[comparison.left], by_source.get(comparison.right)
            if not _current(db,left,False) or (right is not None and not _current(db,right,False)):
                continue
            added += db.execute("""INSERT INTO review_comparison VALUES(?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING""",
                (left["concept_id"],left["observed_revision"],comparison.right,right["concept_id"] if right else None,
                 right["observed_revision"] if right else comparison.external_revision,version,
                 comparison.verdict,canonical(comparison.evidence))).rowcount
    return len(comparisons), added


def _resolve(registry, rows, interpretation_key, *, capability, equivalence):
    from .mapping_preview import MappingPreview, development_targets

    counts = Counter()
    eligible = []
    with registry.reader() as db:
        for row in rows:
            if not _eligible(row,False):
                counts["source_held_or_payload_unavailable"] += 1
                continue
            cached = _cache(db,row,interpretation_key)
            if cached is None:
                counts["interpretation_required"] += 1
                continue
            summary = json.loads(cached["summary_json"])
            if summary.get("input_error"):
                counts["invalid_interpretation_input"] += 1
            elif capability and capability not in summary["modules"]:
                counts["capability_excluded"] += 1
            else:
                eligible.append((row,cached))
    if not eligible:
        return {"counts":dict(counts),"resolution_version":None}
    snapshots = {kind:_digest(path) for kind,path in development_targets().items()}
    policy = _policy_files(("chemical_concept_registry","enrichment","ingredient_equivalence"))
    root_policy = {path.name:_digest(path) for path in ROOT.glob("*.py") if not path.name.startswith("test_")}
    version = "resolution-v2:" + fingerprint([interpretation_key,snapshots,policy,root_policy,
                                                _digest(DEFAULT_JAR),_digest(ROOT / "cosing_pilot/mapping_preview.py")])
    with ExitStack() as stack, rdBase.BlockLogs():
        mapping = None
        for row, cached in eligible:
            with registry.reader() as db:
                if _cache(db,row,version):
                    counts["cached"] += 1
                    continue
            summary, trace = json.loads(cached["summary_json"]),json.loads(cached["trace_json"])
            attempted = summary["chemical_candidate"]
            preview = {"disposition":"NOT_EVALUATED"}
            if attempted:
                if mapping is None:
                    mapping = MappingPreview(_bridge(stack))
                    if any(mapping.identities[k]["snapshot_sha256"] != h for k,h in snapshots.items()):
                        raise ValueError("Target snapshots changed before resolution")
                failures = mapping.bridge.failures
                preview = mapping.assess(_restore(trace["interpretation"]))
                if mapping.bridge.failures != failures:
                    counts["retryable_provider_failure"] += 1
                    continue
            with registry.writer() as db:
                if not _current(db,row,False):
                    counts["stale"] += 1
                    continue
                if attempted:
                    mapping.verify_snapshots()
                summary.update(stage="RESOLUTION", interpretation_version=interpretation_key, mapping_preview=preview)
                inserted = _insert(db,row,version,attempted,json.loads(cached["attributes_json"]),
                                   json.loads(cached["roles_json"]),summary,trace)
                counts["assessed" if inserted else "cached"] += 1
                if inserted and attempted:
                    counts["chemical_attempted"] += 1
                    counts[preview["disposition"]] += 1
                    db.execute("""UPDATE domain_concept SET canonical_status='UNRESOLVED'
                                  WHERE concept_id=? AND canonical_status='NOT_EVALUATED'""",(row["concept_id"],))
    if equivalence:
        from .readiness import DATA

        evidence = [*sorted((ROOT / "ingredient_equivalence/evaluation").glob("*.json")),
                    ROOT / "ingredient_equivalence/evidence_validation/authority_inputs.json",
                    DATA / "external_reviews.json"]
        pair_version = "equivalence-v2:" + fingerprint([version,[(_digest(p),p.name) for p in evidence]])
        counts["pairs_evaluated"],counts["pairs_inserted"] = _equivalence(registry,eligible,pair_version)
    return {"counts":dict(counts),"resolution_version":version,"target_snapshots":snapshots}


def assess(registry, stage, *, concept_ids=(), source_ids=(), batch=None, capability=None,
           typed_only=False, pending=False, equivalence=False):
    if not (concept_ids or source_ids or batch or capability):
        raise ValueError("Select concepts by ID, source ID, batch, or capability")
    if capability and capability not in CAPABILITIES:
        raise ValueError("Unknown interpretation capability")
    if stage not in {"interpret","resolve"} or (pending and stage != "interpret"):
        raise ValueError("Unsupported assessment operation")
    rows = _select(registry,concept_ids,source_ids,batch)
    version = interpretation_version(typed_only)
    if stage == "interpret":
        result = {"counts":_interpret(registry,rows,version,typed_only=typed_only,pending=pending,
                                     capability=capability)}
    else:
        result = _resolve(registry,rows,version,capability=capability,equivalence=equivalence)
    return {**result,"selected":len(rows),"interpretation_version":version}
