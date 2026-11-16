"""Reproduce the bounded CosIng readiness evaluation on a new database copy."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from time import perf_counter

from .__main__ import PILOT, audit_paths, historical_comparison, read, write
from .cosing_source import ARRAYS, FIELDS, PARENT, observation
from .readiness import DATA, packets, read_rows, register
from .registry import DomainRegistry
from .staged_assessment import _digest, assess
from .staged_registry import StagedRegistry

OLD_TABLES = ("domain_type","domain_concept","source_revision","assessment","review_comparison")
FOLLOWUP = {"PARFUM","CI 77491","CI 77492","HYDROLYZED WHEAT PROTEIN","GLYCERYL STEARATE",
            "MENTHOL","TOCOPHEROL","WATER","ALCOHOL DENAT."}
ANATOMY = {"leaf":"PO_0025034","fruit":"PO_0009001","seed":"PO_0009010"}


def continuity():
    old, current = [read_rows(DATA / file) for file in ("source_rows.json","readiness_current.json")]
    old_by_key, current_by_key = [{r["inci_id"]:r for r in rows} for rows in (old,current)]
    shared = old_by_key.keys() & current_by_key.keys()
    changed = {}
    for key in sorted(shared):
        original, fresh = [observation(source[key]).payload["source"] for source in (old_by_key,current_by_key)]
        fields = [field for field in FIELDS if original[field] != fresh[field]]
        if fields:
            changed[key] = fields
    return {
        "earlier_capture_comparison":historical_comparison(old),
        "pilot_capture_count":len(old),"current_key_recheck_count":len(current),"shared_keys":len(shared),
        "missing_pilot_keys":sorted(old_by_key.keys()-current_by_key.keys()),
        "unexpected_returned_keys":sorted(current_by_key.keys()-old_by_key.keys()),
        "changed_keys":changed,"changes_by_field":dict(Counter(f for fs in changed.values() for f in fs)),
        "source_timestamp_changes":sum(old_by_key[k].get("updated_ts") != current_by_key[k].get("updated_ts") for k in shared),
        "comparison_scope":"Original pilot keys only. The query cannot observe newly added keys or compare companion claims.",
    }


def _readouts(registry, sources, stages):
    with registry.reader() as db:
        return {
            row["inci_id"]: (
                dict(db.execute("SELECT * FROM domain_concept WHERE source_reference=?",
                                (f'{PARENT}:{row["inci_id"]}',)).fetchone()),
                {kind:db.execute("""SELECT a.* FROM assessment a JOIN domain_concept d USING(concept_id)
                    WHERE d.source_reference=? AND a.revision=d.registered_revision AND a.pipeline_version=?""",
                    (f'{PARENT}:{row["inci_id"]}',version)).fetchone() for kind,version in stages.items()},
            )
            for row in sources
        }


def semantic_review(registry, sources, versions, reference):
    actual = _readouts(registry,sources,versions)
    labels = {source["inci"] for source in sources}
    if labels != reference.keys() or len(labels) != len(sources):
        raise ValueError("Reference must cover the exact set of unique review designations")
    by_group, cases = defaultdict(Counter), []
    for row in sources:
        concept, stages = actual[row["inci_id"]]
        expected = reference[row["inci"]]
        interpretation, resolution = stages["interpretation"],stages["resolution"]
        summary = json.loads(interpretation["summary_json"]) if interpretation else {}
        trace = json.loads(interpretation["trace_json"]).get("interpretation",{}) if interpretation else {}
        assessment = json.loads(resolution["summary_json"])["mapping_preview"] if resolution else {}
        attributes = json.loads(interpretation["attributes_json"]) if interpretation else []
        functions = {f["reported_function"]:f for f in trace.get("functions",[])}
        checks = {
            "source_binding":(concept["preferred_label"] == row["inci"]
                              and concept["source_reference"] == f'{PARENT}:{row["inci_id"]}'),
            "assessment_available":interpretation is not None and resolution is not None,
            "no_committed_target":concept["canonical_target_json"] is None,
            "reported_roles_preserved":set(functions) == set(json.loads(row.get("functions") or "[]")),
        }
        if module := expected.get("module"):
            checks["capability"] = module in summary.get("modules",[])
        if part := expected.get("part"):
            checks["plant_part"] = any(a["predicate"] == "reported_plant_part"
                                        and a["value"].casefold() == part for a in attributes)
            if part in ANATOMY:
                checks["anatomy"] = any(a["predicate"] == "source_anatomical_structure"
                                        and a["value"].endswith(ANATOMY[part]) for a in attributes)
        if preparation := expected.get("preparation"):
            checks["preparation"] = any(a["predicate"] in {
                "reported_botanical_preparation","reported_preparation_qualifier","reported_source_preparation",
            } and isinstance(a["value"],str) and a["value"].casefold() == preparation for a in attributes)
        if role := expected.get("role"):
            checks["contextual_role"] = functions.get(role,{}).get("qualification") == "VOCABULARY_VALIDATED"
        if expected.get("whole_hold"):
            checks["whole_ingredient_gate"] = not assessment.get("eligibility") and not assessment.get("proposal")
        if graph := expected.get("expected_inchikey"):
            checks["molecular_candidate"] = any(a["category"] == "STRUCTURAL"
                and a["value"].get("inchikey") == graph for a in trace.get("assertions",[]))
        for group in ("all",row["cohort"],f'{row["cohort"]}:{row["stratum"]}'):
            tally = by_group[group]
            tally["records"] += 1
            tally["records_with_errors"] += int(not all(checks.values()))
            tally["checks"] += len(checks)
            tally["failed_checks"] += sum(not passed for passed in checks.values())
            tally["conflicts"] += int(trace.get("state") == "CONFLICT")
            tally["multiple_specialists"] += int(len(set(summary.get("modules",[]))-{"generic_ingredient"}) > 1)
            tally["missing_cas_and_ec"] += int(not any(json.loads(row.get(k) or "[]") for k in ARRAYS[:2]))
            tally["generic_fallback"] += int("generic_ingredient" in summary.get("modules",[]))
        cases.append({"key":row["inci_id"],"concept_id":concept["concept_id"],"label":row["inci"],"cohort":row["cohort"],
                      "stratum":row["stratum"],"expected":expected,"checks":checks,"state":trace.get("state"),
                      "modules":summary.get("modules",[]),"attributes":attributes,
                      "roles":{name:f["qualification"] for name,f in functions.items()},
                      "issues":sorted({i["code"] for i in trace.get("issues",[])}),
                      "withheld_graphs":sum(a["category"] == "STRUCTURAL" for a in trace.get("withheld_assertions",[])),
                      "canonical_status":concept["canonical_status"],"resolution":assessment})
    return {"review_status":"PROVISIONAL_SINGLE_REVIEW","by_group":dict(by_group),"cases":cases,
            "failed_critical_checks":[(c["label"],key) for c in cases for key in (
                "source_binding","no_committed_target","whole_ingredient_gate") if c["checks"].get(key) is False]}


def _followups(registry, sources, versions):
    from canonical_registry.ingredient_equivalence.validate_evidence import LEGACY, prior_replay, read as study_read

    outputs = _readouts(registry,sources,versions)
    result = {}
    for row in sources:
        concept, stages = outputs[row["inci_id"]]
        b,c = stages["interpretation"],stages["resolution"]
        trace = json.loads(b["trace_json"])["interpretation"]
        result[row["inci"]] = {"concept_id":concept["concept_id"],"state":trace["state"],
                               "functions":{r["reported_function"]:r["qualification"] for r in trace["functions"]},
                               "issues":sorted({i["code"] for i in trace["issues"]}),
                               "resolution":json.loads(c["summary_json"])["mapping_preview"]}
    replay = prior_replay(None,study_read(LEGACY,"results.json"))
    paired = {}
    for key in ("prior_unaugmented","prior_with_documented_new_evidence"):
        paired[key] = {row["id"]:{"expected":row["expected"],"actual":row["prediction"]["verdict"]}
                       for row in replay[key]["rows"] if row["id"] in {"R04","R21","R23"}}
    with registry.reader() as db:
        stored = [dict(row) for row in db.execute("""SELECT l.preferred_label AS left,r.preferred_label AS right,c.verdict
            FROM review_comparison c JOIN domain_concept l ON l.concept_id=c.left_id
            JOIN domain_concept r ON r.concept_id=c.right_id
            WHERE c.pipeline_version LIKE 'equivalence-v2:%' AND json_extract(c.comparison_json,'$.review.reference')
            IN ('R04','R21','R23') ORDER BY l.preferred_label,r.preferred_label""")]
    return {"cases":result,"prior_evidence_replay":paired,"current_cos_ing_pair_packets":stored}


def run(database, output):
    before = {**audit_paths(),str(PILOT):_digest(PILOT)}
    reference_path = DATA / "readiness_reference.json"
    reference = read(reference_path)["cases"]
    capture = DATA / "readiness_validation.json"
    sources, observations = read_rows(capture),packets(capture)
    inputs = [capture,reference_path,DATA/"readiness_current.json"]
    supplement = DATA / "readiness_supplement.json"
    if supplement.is_file():
        supplement_reference = DATA / "readiness_supplement_reference.json"
        sources.extend(read_rows(supplement))
        observations.extend(packets(supplement))
        reference.update(read(supplement_reference)["cases"])
        inputs.extend((supplement,supplement_reference))
    registry = StagedRegistry(database)
    original = read_rows(DATA / "source_rows.json")
    pilot_keys = {r["inci_id"] for r in original}
    if pilot_keys & {r["inci_id"] for r in sources}:
        raise ValueError("Fresh sample intersects the 407-record pilot")
    registry.initialize(PILOT,legacy_observations=packets(DATA/"source_rows.json",DATA/"companion_rows.json",legacy=True))
    with DomainRegistry(PILOT).reader() as old, registry.reader() as copy:
        preserved = {}
        for table in OLD_TABLES:
            old_rows, migrated = [db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall() for db in (old,copy)]
            assert old_rows == migrated
            preserved[table] = len(migrated)
    start = perf_counter()
    registered = register(registry,observations,"readiness-cohort",batch_size=15)
    a_seconds = perf_counter()-start
    repeated_a = register(registry,reversed(observations),"readiness-repeat",batch_size=18)

    def statuses():
        with registry.reader() as db:
            return dict(db.execute("""SELECT d.canonical_status,count(*) FROM domain_concept d
                JOIN registration_member m USING(concept_id) WHERE m.run_id='readiness-cohort' GROUP BY d.canonical_status"""))

    after_a = statuses()
    start = perf_counter()
    b = assess(registry,"interpret",batch="readiness-cohort")
    b_seconds = perf_counter()-start
    after_b = statuses()
    assert after_a == after_b == {"NOT_EVALUATED":len(sources)}
    start = perf_counter()
    repeated_b = assess(registry,"interpret",batch="readiness-cohort")
    repeated_b_seconds = perf_counter()-start
    print("Stages A and B complete",b["counts"],flush=True)
    start = perf_counter()
    c = assess(registry,"resolve",batch="readiness-cohort",equivalence=True)
    c_seconds = perf_counter()-start
    after_c = statuses()
    start = perf_counter()
    repeated_c = assess(registry,"resolve",batch="readiness-cohort")
    repeated_c_seconds = perf_counter()-start
    print("Stage C complete",c["counts"],flush=True)
    followups = [row for row in original if row["inci"] in FOLLOWUP]
    ids = [row["inci_id"] for row in followups]
    assert {row["inci"] for row in followups} == FOLLOWUP
    followup_b = assess(registry,"interpret",source_ids=ids)
    followup_c = assess(registry,"resolve",source_ids=ids,equivalence=True)
    versions = {"interpretation":b["interpretation_version"],"resolution":c["resolution_version"]}
    review = semantic_review(registry,sources,versions,reference)
    specific = _followups(registry,followups,versions)
    with registry.reader() as db:
        integrity = {
            "sqlite":db.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_key_violations":len(db.execute("PRAGMA foreign_key_check").fetchall()),
            "duplicate_source_bindings":db.execute("SELECT count(*)-count(DISTINCT source_reference) FROM domain_concept").fetchone()[0],
            "approved_mappings":db.execute("SELECT count(*) FROM domain_concept WHERE canonical_target_json IS NOT NULL").fetchone()[0],
            "registered_concepts":db.execute("SELECT count(*) FROM domain_concept").fetchone()[0],
        }
    after = {**audit_paths(),str(PILOT):_digest(PILOT)}
    protected = {"before":before,"after":after,"changed":[path for path in before if before[path] != after.get(path)]}
    write(output.with_name(output.stem+"_protected.json"),protected)
    result = {
        "input_sha256":{p.name:_digest(p) for p in inputs},"pilot_preserved":preserved,"continuity":continuity(),
        "registration":registered,"registration_seconds":a_seconds,"registration_replay":repeated_a,
        "interpretation":b,"interpretation_seconds":b_seconds,"interpretation_replay":repeated_b,
        "interpretation_replay_seconds":repeated_b_seconds,"resolution":c,"resolution_seconds":c_seconds,
        "resolution_replay":repeated_c,"resolution_replay_seconds":repeated_c_seconds,
        "cohort_status":{"after_registration":after_a,"after_interpretation":after_b,"after_resolution":after_c},
        "semantic_review":review,"followups":{"interpretation":followup_b,"resolution":followup_c,**specific},
        "integrity":integrity,"protected_paths":len(before),"protected_changes":len(protected["changed"]),
    }
    write(output,result)
    if protected["changed"] or integrity["sqlite"] != "ok" or integrity["foreign_key_violations"]:
        raise ValueError("Readiness evaluation integrity failure")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",required=True,type=Path,help="New disposable database path")
    parser.add_argument("--output",required=True,type=Path)
    args = parser.parse_args()
    run(args.db,args.output)


if __name__ == "__main__":
    main()
