"""Index Stage B evidence and prepare a read-only Stage C eligibility handoff."""

from collections import Counter, defaultdict
from contextlib import ExitStack, closing
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
from time import perf_counter

from .benchmark_readiness import peak_rss
from .full_capture import digest, read, write
from .full_stage_b_capture import MANIFEST, OUTPUT as FULL, PARENT_ARCHIVE, _page
from .registry import canonical, fingerprint
from .stage_b_evidence import _eligible_alias
from .stage_b_handoff_recovery import OUTPUT, REGISTRY
from .stage_b_v3_gate import IDENTITY_PREDICATES
from .staged_assessment import _bridge
from .staged_registry import StagedRegistry

POLICY = "COSING_STAGE_C_ELIGIBILITY_V1"
INDEX = OUTPUT/"handoff.sqlite"
STRUCTURAL = {"SMILES","INCHI","INCHI_KEY","MOLECULAR_FORMULA"}
REPORTED_ALIAS_SOURCES = {"COSING","GLOBAL COSING","FDA_GSRS_UNII"}
SCOPE_HOLDS = {"COMPOUND_PREPARATION_SCOPE_REVIEW","COMPOUND_BOTANICAL_ATTACHMENT_REVIEW",
               "MINERAL_CONSTITUENT_SCOPE_REVIEW"}
MOLECULAR_AUDIT_LABELS = {"ETHANOL","WATER","UREA","ACETONE","GLYCERIN","ACETIC ACID","L-LACTIC ACID"}
INCOMPLETE = {"TYPED_STRUCTURE_NOT_VALIDATED","INCOMPLETE_TYPED_STRUCTURE_EVIDENCE",
              "MOLECULAR_FORMULA_COMPARISON_INCOMPLETE","SOURCE_DEFINITION_GRAPH_COMPARISON_INCOMPLETE",
              "STRUCTURE_COMPARISON_INCOMPLETE","STEREO_COMPARISON_INCOMPLETE"}
SCHEMA = """
CREATE TABLE review_triage (
  item_id INTEGER PRIMARY KEY, concept_id TEXT NOT NULL, original_reason TEXT NOT NULL,
  priority TEXT NOT NULL CHECK(priority IN ('P0','P1','P2','P3')), action TEXT NOT NULL,
  evidence_json TEXT NOT NULL
);
CREATE INDEX review_by_risk ON review_triage(priority,original_reason,concept_id);
CREATE INDEX review_by_concept ON review_triage(concept_id);
CREATE TABLE stage_c_eligibility (
  concept_id TEXT PRIMARY KEY, source_reference TEXT NOT NULL, source_revision TEXT NOT NULL,
  stage_b_version TEXT, eligibility TEXT NOT NULL, whole_referent_scope TEXT NOT NULL,
  pathway TEXT, review_required INTEGER NOT NULL CHECK(review_required IN (0,1)),
  policy_version TEXT NOT NULL, evidence_json TEXT NOT NULL
);
CREATE INDEX eligibility_by_route ON stage_c_eligibility(eligibility,pathway,concept_id);
CREATE INDEX eligibility_by_source ON stage_c_eligibility(source_reference,source_revision);
"""


def alias_shape(value):
    s = (value or "").strip()
    if re.fullmatch(r"InChI=1S?/\S+",s) or re.fullmatch(r"[A-Z]{14}-[A-Z]{10}-[A-Z]",s):
        return "STRUCTURAL_IDENTIFIER"
    if re.fullmatch(r"(?:[0-9]{2,7}-[0-9]{2}-[0-9]|[0-9]{3}-[0-9]{3}-[0-9])",s):
        return "REGISTRY_IDENTIFIER"
    if re.fullmatch(r"(?:[A-Z][a-z]?[0-9]*)+",s) and re.search(r"\d",s):
        return "FORMULA_LIKE"
    if re.fullmatch(r"(?:Cl|Br|[BCNOPSFIbcnops]){2,}",s):
        return "STRUCTURE_LIKE"
    if not re.search(r"\s",s) and re.search(
            r"(?:\[[A-Za-z+\-0-9@]+\]|[BCNOPSbcno][=#@\\/][BCNOPSbcno\[]|[BCNOPSbcno]1[^ ]+1|"
            r"[BCNOPSbcno]\((?:[=#])?(?:Cl|Br|[BCNOPSbcno]))",s):
        return "STRUCTURE_LIKE"
    return "LEXICAL_OR_OTHER"


def alias_triage(row, parent, typed, cutoff):
    raw = row.get("alias")
    if not isinstance(raw,str) or not raw.strip() or any(ord(c)<32 and c not in "\t\r\n" for c in raw):
        return "P3","LEGITIMATELY_EXCLUDED","INVALID_OR_EMPTY_VALUE"
    shape = alias_shape(raw)
    identity_like = shape!="LEXICAL_OR_OTHER"
    if row["data_status"]!="1":
        return "P3","LEGITIMATELY_EXCLUDED","INACTIVE_SOURCE_CLAIM"
    dates = [int(row[k]) for k in ("created_ts","updated_ts") if row[k] is not None]
    if not dates or max(dates)>cutoff:
        return ("P1" if identity_like else "P2"),"REVIEW_REQUIRED","SOURCE_REVISION_UNESTABLISHED"
    if (row.get("source") or "").strip().upper() not in REPORTED_ALIAS_SOURCES:
        return ("P1" if identity_like else "P2"),"REVIEW_REQUIRED","UNSUPPORTED_ALIAS_AUTHORITY"
    if any(x["alias"]==raw and x["source"]==row["source"] for x in typed):
        return "P3","SUPPORTED_DUPLICATE_QUALIFICATION","EXACT_DUPLICATE_OF_QUALIFIED_ORIGINAL_CLAIM"
    if " ".join(raw.casefold().split())==" ".join(parent["inci"].casefold().split()):
        return "P3","AUTOMATIC_CLASSIFICATION","REPEATS_SOURCE_DESIGNATION"
    if identity_like:
        return "P1","REVIEW_REQUIRED",shape
    definition = parent.get("description") or ""
    if len(raw.strip())>4 and re.search(r"\b(?:extract of|obtained from|contains)\s+(?:the\s+)?"
                                         +re.escape(raw.strip())+r"(?!\w)",definition,re.I):
        return "P2","REVIEW_REQUIRED","REPORTED_CONSTITUENT_OR_SOURCE_MATERIAL"
    if re.search(r"(?:\d[,()]|\b(?:\d+[RSEZ]|cis|trans)\b|\b(?:hydrate|hydrochloride|"
                 r"salt|racemate|isomer|complex|tautomer|deuterated)\b)",raw,re.I):
        return "P2","REVIEW_REQUIRED","CHEMICAL_NAME_OR_FORM_ROLE_UNESTABLISHED"
    return "P3","AUTOMATIC_CLASSIFICATION","UNQUALIFIED_LEXICAL_CLAIM_NO_IDENTITY_USE"


@dataclass
class Trace:
    attrs: list
    summary: dict
    trace: dict

    @property
    def interpretation(self):
        return self.trace.get("interpretation",{})

    @property
    def graphs(self):
        return [a for a in self.interpretation.get("assertions",[]) if a["category"]=="STRUCTURAL"]

    @property
    def withheld(self):
        return [a for a in self.interpretation.get("withheld_assertions",[]) if a["category"]=="STRUCTURAL"]

    @property
    def issues(self):
        return {i["code"] for i in self.interpretation.get("issues",[])}

    @property
    def guard(self):
        return any(m["whole_referent_graph_unestablished"] for m in self.interpretation.get("modules",[]))

    @property
    def p0(self):
        blocked = {s for i in self.interpretation.get("issues",[]) if i["conflict"] for s in i.get("affected_slots",[])}
        return (any(a["predicate"] in IDENTITY_PREDICATES or a.get("exclusive_slot") in blocked
                    or blocked.intersection(a.get("depends_on",[])) for a in self.attrs)
                or any(a["evidence_role"]!="CANDIDATE_ONLY" for a in self.graphs+self.withheld)
                or bool(self.graphs and (self.guard or self.summary.get("state")=="CONFLICT")))


def conflict_patterns(t, parent):
    labels = set()
    issues = t.issues
    if t.guard or "WHOLE_REFERENT_GRAPH_UNESTABLISHED" in issues:
        labels.add("WHOLE_VS_CONSTITUENT_SCOPE_UNESTABLISHED")
    if any("STEREO" in c for c in issues):
        labels.add("STEREOCHEMICAL_CONFLICT_OR_INCOMPLETENESS")
    if any("FORMULA" in c or "INCHIKEY" in c for c in issues):
        labels.add("FORMULA_OR_IDENTIFIER_INCONSISTENCY")
    if "TYPED_STRUCTURE_NOT_VALIDATED" in issues:
        labels.add("INVALID_OR_UNSUPPORTED_TYPED_REPRESENTATION")
    if any("DEFINITION" in c for c in issues):
        labels.add("PREFERRED_NAME_AND_DEFINITION_DISAGREE")
    g = [a["value"] for a in t.graphs+t.withheld]
    if len({(x["charge"],x["components"]) for x in g})>1:
        labels.add("CHARGE_OR_COMPONENT_COMPOSITION_DIFFERS")
    if len({x["inchi"].split("/")[1] for x in g})>1:
        labels.add("REPRESENTATIONS_HAVE_DIFFERENT_FORMULAE")
    if len({x["inchikey"].split("-")[0] for x in g})>1:
        labels.add("INCHI_CONNECTIVITY_BLOCK_DIFFERS")
    if any(x["inchikey"].split("-")[0]==y["inchikey"].split("-")[0] and x["inchikey"]!=y["inchikey"]
           for i,x in enumerate(g) for y in g[i+1:]):
        labels.add("SHARED_CONNECTIVITY_BLOCK_DIFFERENT_FULL_KEYS")
    if re.search(r"\b(?:hydrate|hydrochloride|solvate|salt)\b",parent["inci"],re.I):
        labels.add("SOURCE_REPORTS_SALT_HYDRATE_OR_SOLVATE_TERM")
    if "CONFLICTING_STRUCTURE_DIMENSIONS" in issues:
        labels.add("STRUCTURAL_DIMENSION_CONFLICT")
    return sorted(labels or {"STRUCTURAL_CONFLICT_UNSPECIFIED"})


def broad_scope(parent,t):
    definition = parent["description"] or ""
    if re.search(r"\b(?:is|are)\s+(?:a|an|the)\s+(?:class of|mixture of|blend of|complex mixture|distribution of)\b",
                 definition,re.I):
        return "SOURCE_DEFINITION_EXPLICIT_CLASS_OR_MIXTURE"
    descriptors = {a["predicate"] for a in t.attrs}
    if descriptors & {"reported_preparation_qualifier","reported_source_preparation","reported_botanical_preparation",
                      "reported_preparation_process","reported_polymer_category","reported_polyether_grade",
                      "reported_polymer_designation_number","reported_biological_category"}:
        if t.guard or not t.graphs:
            return "QUALIFIED_PREPARATION_POLYMER_OR_BIOLOGICAL_SCOPE"
    if t.guard and re.search(r"\b(?:extract|filtrate|ferment|hydrolysate|conditioned media|copolymer|crosspolymer)\b",
                             parent["inci"],re.I):
        return "EXPLICIT_BROAD_OR_PREPARATION_DESIGNATION"
    return None


def _graph_signature(graph):
    return tuple(graph[k] for k in ("smiles","inchi","inchikey","fixed_h_inchi"))


def _candidate(parent,t,aliases):
    if t.guard or t.withheld or t.issues&INCOMPLETE:
        return None,"GRAPH_SCOPE_OR_RECONCILIATION_INCOMPLETE"
    if t.summary.get("state") not in {"VALIDATED","PARTIAL"}:
        return None,"INTERPRETATION_NOT_QUALIFIED_FOR_SCREEN"
    exact = [a for a in t.graphs if a["method"]=="OPSIN_THEN_STRICT_RDKIT"]
    typed = [a for a in t.graphs if a["method"]=="STRICT_RDKIT_STRUCTURE"]
    if not exact or not typed:
        return None,"PREFERRED_NAME_AND_TYPED_SOURCE_CORROBORATION_REQUIRED"
    typed_originals = {f"mse_dwd.dwd_mse_cosmetics_inci_aliases:{r['inci_alias_id']}":r
                       for r in aliases if r["alias_type"] in {"SMILES","INCHI"}}
    if not any((source:=typed_originals.get(a["evidence"]["source_reference"])) and
               a["evidence"]["original_value"]==source["alias"] and
               source.get("referent_scope")=="VERIFIED_WHOLE_INGREDIENT" for a in typed):
        return None,"ORIGINAL_SOURCE_GRAPH_BINDING_UNESTABLISHED"
    if len({_graph_signature(a["value"]) for a in t.graphs})!=1:
        return None,"FULL_GRAPH_OR_FORM_AGREEMENT_UNESTABLISHED"
    if len(t.graphs)>1 and (not t.interpretation.get("graph_comparisons") or
            any(c["relation"]!="COMPATIBLE" for c in t.interpretation["graph_comparisons"])):
        return None,"GRAPH_AGREEMENT_UNESTABLISHED"
    graph = exact[0]["value"]
    if (graph["components"]!=1 or graph["charge"] or graph["radicals"] or graph["isotopes"] or
            graph["atoms"]>100 or re.search(r"\b(?:salt|hydrate|solvate|complex|mixture|blend|racemate|isomers?)\b",
                                           parent["inci"],re.I)):
        return None,"CHEMICAL_FORM_REQUIRES_EXPLICIT_SCOPE_REVIEW"
    readings = {a["value"] for a in t.interpretation["assertions"] if a["predicate"]=="molecular_name_reading"}
    unspecified = [a for a in graph["stereo"] if a["specified"]!="Specified"]
    if unspecified:
        if (readings=={"PARTIAL"} and len(unspecified)<=4 and all(a["type"] in {"Atom_Tetrahedral","Bond_Double"} for a in unspecified)
                and re.search(r"\b(?:unspecified|undefined) stereochemistry\b",parent["description"] or "",re.I)):
            return (graph,"CHEMICAL_CONCEPT"),"EXPLICIT_GRAPH_GROUNDED_STEREO_UNDERSPECIFICATION"
        return None,"STEREOCHEMISTRY_SCOPE_NOT_EXPLICIT"
    if readings!={"ESTABLISHED"} or graph["inchi_warning"]:
        return None,"FULLY_SPECIFIED_NAME_READING_REQUIRED"
    return (graph,"SUBSTANCE"),"CONSISTENT_SOURCE_NAME_AND_ORIGINAL_TYPED_GRAPH"


def eligibility(parent,t,aliases,priorities,official,hold=False):
    if hold or t.p0:
        return "REVIEW_HOLD","PROCESSING_OR_INTEGRITY_HOLD",None,"STAGE_B_INCOMPLETE_OR_CRITICAL",None
    if t.summary.get("state")=="CONFLICT" or "P0" in priorities or "P1" in priorities:
        return "REVIEW_HOLD","IDENTITY_SIGNIFICANT_EVIDENCE_UNRESOLVED",None,"CONFLICT_OR_P1_REVIEW",None
    if scope := broad_scope(parent,t):
        return "NOT_APPLICABLE_TO_EXACT_MOLECULAR_RESOLUTION","SOURCE_SUPPORTS_NONDISCRETE_SCOPE",None,scope,None
    candidate, reason = _candidate(parent,t,aliases)
    if candidate:
        graph,pathway = candidate
        validation = official(graph)
        if (validation.get("status") in {"SUCCESS","WARNING"} and validation.get("agrees")
                and validation.get("inchi")==graph["inchi"] and validation.get("inchikey")==graph["inchikey"]):
            return "CANDIDATE_READY","CONSISTENT_NAMED_WHOLE_REFERENT",pathway,reason,validation
        reason = "OFFICIAL_VALIDATION_UNCONFIRMED"
        return "NEEDS_MORE_EVIDENCE","WHOLE_REFERENT_UNESTABLISHED",None,reason,validation
    return "NEEDS_MORE_EVIDENCE","WHOLE_REFERENT_UNESTABLISHED",None,reason,None


def _inventory():
    parent = {r["inci_id"]:r for r in read(PARENT_ARCHIVE)}
    manifest = read(MANIFEST)
    if digest(PARENT_ARCHIVE)!=manifest["parent_sha256"]:
        raise ValueError("Parent snapshot changed")
    by_key = defaultdict(list)
    for number,profile in manifest["buckets"].items():
        if digest(FULL/"capture"/profile["file"])!=profile["file_sha256"]:
            raise ValueError("Alias capture changed")
        _,rows,_ = _page(int(number),profile["profile"],parent)
        for row in rows:
            by_key[row["inci_id"]].append(row)
    return parent,by_key,manifest["parent_cutoff_epoch_ms"]


def _triage(item,parent,aliases,typed,cutoff,t,recovery):
    reason = item["reason"]
    if t.p0:
        return "P0","CONTAIN","PUBLISHED_IDENTITY_OR_DEPENDENCY_VIOLATION",{}
    if reason=="MISSING_ALIAS_QUALIFICATION":
        raw = [a for a in aliases if not (a["alias_type"] or "").strip()]
        if not raw:
            raise ValueError("Missing-qualification item has no original claim")
        results = [{"id":a["inci_alias_id"],"source":a["source"],"value":a["alias"],
                    "priority":p,"action":act,"cause":cause} for a in raw
                   for p,act,cause in (alias_triage(a,parent,typed,cutoff),)]
        precedence = {"REVIEW_REQUIRED":0,"SUPPORTED_DUPLICATE_QUALIFICATION":1,
                      "AUTOMATIC_CLASSIFICATION":2,"LEGITIMATELY_EXCLUDED":3}
        first = min(results,key=lambda x:(x["priority"],precedence[x["action"]],x["id"]))
        return first["priority"],first["action"],first["cause"],{"claims":results}
    if reason=="STRUCTURAL_CONFLICT":
        return "P1","HOLD_EXACT_PATH","CONFLICTING_STRUCTURE_EVIDENCE",{"patterns":conflict_patterns(t,parent),
            "issues":sorted(t.issues),"independent_descriptors":len(t.attrs),
            "structure_claims":[{"reference":a["evidence"]["source_reference"],"method":a["method"],
                                 "graph_digest":fingerprint(_graph_signature(a["value"])),
                                 "disposition":"WITHHELD" if a in t.withheld else "RETAINED_CANDIDATE"}
                                for a in t.graphs+t.withheld],
            "review_scope":"QUALIFY_OR_CORROBORATE_WHOLE_REFERENT"}
    if reason in SCOPE_HOLDS:
        related = [h for h in t.trace.get("publication_review",{}).get("withheld",[]) if h["reason"]==reason]
        p = "P1" if reason=="MINERAL_CONSTITUENT_SCOPE_REVIEW" or (
            reason=="COMPOUND_PREPARATION_SCOPE_REVIEW" and bool(t.graphs+t.withheld)) else "P2"
        return p,"REVIEW_WITHHELD_SCOPE",reason,{"affected_assertions":related}
    if reason in {"RECONCILIATION_TIMEOUT","WORKER_EXCEPTION"}:
        return ("P3","RECOVERED_PROCESSING_ITEM",reason,{}) if recovery=="COMPLETED" else (
            "P1","DOCUMENTED_PROCESSING_HOLD",reason,{})
    if reason=="NONSTRUCTURAL_CONFLICT":
        relevant = [i for i in t.interpretation.get("issues",[]) if i["conflict"]]
        p = "P1" if t.graphs+t.withheld else "P2"
        return p,"REVIEW_CONFLICT_SCOPE",reason,{"issues":relevant}
    raise ValueError(f"Unknown original queue reason {reason}")


def run():
    start = perf_counter()
    recovery = read(OUTPUT/"recovery.json")
    parent,alias_rows,cutoff = _inventory()
    source = StagedRegistry(REGISTRY)
    before = digest(REGISTRY)
    queue = defaultdict(list)
    old_queue = read(FULL/"review_queue.json")
    for index,item in enumerate(old_queue,1):
        queue[item["concept_id"]].append((index,item))
    if len(old_queue)!=9698 or len(queue)!=7968:
        raise ValueError("Original review inventory changed")
    dispositions = {cid:x["disposition"] for cid,x in recovery["records"].items()}
    counts,triage,causes,patterns,totals,routes,claim_actions,typed_authorities,reason_counts = (
        Counter() for _ in range(9))
    samples,validation = defaultdict(list),[]
    temp = INDEX.with_suffix(".building")
    if temp.exists():
        temp.unlink()
    policy_hash = fingerprint([POLICY,digest(Path(__file__)),digest(MANIFEST),recovery["version"]])
    official_cache = {}
    with ExitStack() as stack,closing(sqlite3.connect(temp)) as out,source.reader() as db:
        bridge = None

        def official(graph):
            nonlocal bridge
            k = _graph_signature(graph)
            if k not in official_cache:
                if bridge is None:
                    bridge = _bridge(stack)
                official_cache[k] = bridge.official(graph)
            return official_cache[k]

        out.executescript(SCHEMA)
        rows = db.execute("""WITH latest AS (
          SELECT a.*,row_number() OVER (PARTITION BY a.concept_id ORDER BY a.rowid DESC) AS rn
          FROM assessment a JOIN source_head h ON h.concept_id=a.concept_id AND h.observed_revision=a.revision
          WHERE a.attempted=0 AND json_extract(a.summary_json,'$.stage')='INTERPRETATION')
        SELECT d.concept_id,d.source_reference,h.observed_revision,d.canonical_status,a.pipeline_version,
               a.attributes_json,a.summary_json,a.trace_json
        FROM domain_concept d JOIN source_head h USING(concept_id)
        LEFT JOIN latest a ON a.concept_id=d.concept_id AND a.rn=1 ORDER BY d.concept_id""")
        for cid,reference,revision,canonical_status,version,attributes,summary,trace in rows:
            key = reference.rsplit(":",1)[1]
            raw = alias_rows[key]
            typed = [a for a in raw if _eligible_alias(a,cutoff) is None]
            typed_authorities.update(a["source"] or "UNREPORTED" for a in raw if a["alias_type"] in STRUCTURAL)
            t = Trace(json.loads(attributes) if attributes else [],json.loads(summary) if summary else {},
                      json.loads(trace) if trace else {})
            if version and (t.interpretation["designation"]["source_reference"]!=reference or
                            t.interpretation["designation"]["original_value"]!=parent[key]["inci"]):
                raise ValueError(f"Assessment source binding mismatch {cid}")
            if canonical_status not in {"NOT_EVALUATED","UNRESOLVED"} or t.p0:
                raise ValueError(f"Critical published scope or canonical status on {cid}")
            priorities = set()
            for item_id,item in queue[cid]:
                if item["source_record"]!=key:
                    raise ValueError(f"Original queue source mismatch {cid}")
                p,action,cause,detail = _triage(item,parent[key],raw,typed,cutoff,t,dispositions.get(cid))
                priorities.add(p)
                triage[p,action]+=1
                if item["reason"]=="MISSING_ALIAS_QUALIFICATION":
                    causes[cause]+=1
                    totals["alias_item_"+action]+=1
                    claim_actions.update(x["action"] for x in detail["claims"])
                patterns.update(detail.get("patterns",[]))
                ev = {"original_item":item,"cause":cause,"stage_b_evidence":{
                    "source_reference":reference,"source_revision":revision,"assessment_version":version},**detail}
                out.execute("INSERT INTO review_triage VALUES (?,?,?,?,?,?)",
                            (item_id,cid,item["reason"],p,action,canonical(ev)))
                group = item["reason"]+" / "+p
                if len(samples[group])<3:
                    samples[group].append({"concept_id":cid,"name":parent[key]["inci"],"reason":cause,
                                          "action":action,"evidence":detail})
                if item["reason"]=="MISSING_ALIAS_QUALIFICATION" and len(samples["alias cause "+cause])<3:
                    samples["alias cause "+cause].append({"concept_id":cid,"name":parent[key]["inci"],"evidence":detail})
            missing = not version
            cls,scope,route,reason,proof = eligibility(parent[key],t,typed,priorities,official,missing)
            counts[cls]+=1
            reason_counts[reason]+=1
            if route:
                routes[route]+=1
            graph_evidence = [{"reference":a["evidence"]["source_reference"],"method":a["method"],
                               "graph_digest":fingerprint(_graph_signature(a["value"])),
                               "disposition":"RETAINED_CANDIDATE" if a in t.graphs else "WITHHELD"}
                              for a in t.graphs+t.withheld]
            totals.update({"registered":1,"with_stage_b":bool(version),"with_qualified_descriptors":bool(t.attrs),
                           "with_molecular_candidate_evidence":bool(graph_evidence),"with_withheld_or_conflicting_structure":
                           bool(t.withheld or any("STRUCTURE" in x and x.startswith("CONFLICT") for x in t.issues))})
            ev = {"reason":reason,"source_key":key,"evidence_revision":revision,"source_reference":reference,
                  "graph_evidence":graph_evidence,"issues":sorted(t.issues),"risk_priorities":sorted(priorities),
                  "original_structural_claims":[{"id":a["inci_alias_id"],"type":a["alias_type"],
                       "reported_source":a["source"],"stage_b_exclusion":_eligible_alias(a,cutoff)}
                       for a in raw if a["alias_type"] in STRUCTURAL],
                  "manifest_sha256":recovery["manifest"],"official_validation":proof,
                  "qualification_limit":"PLANNING_ONLY_NO_CANONICAL_TARGET_LOOKUP"}
            if cid in dispositions:
                recovered = recovery["records"][cid]
                ev["recovery"] = {"event":recovered["event"],"disposition":recovered["disposition"],
                                  "diagnostic":recovered["execution"].get("reason")}
            out.execute("INSERT INTO stage_c_eligibility VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (cid,reference,revision,version,cls,scope,route,int(cls in {"REVIEW_HOLD","NEEDS_MORE_EVIDENCE"}
                         or bool(priorities&{"P0","P1","P2"})),policy_hash,canonical(ev)))
            if len(samples["eligibility "+cls])<6:
                samples["eligibility "+cls].append({"concept_id":cid,"name":parent[key]["inci"],"scope":scope,"evidence":ev})
            controls = []
            if "generic_ingredient" in t.summary.get("modules",[]):
                controls.append("generic fallback")
            if t.guard and t.withheld:
                controls.append("candidate graph with withheld whole attribution")
            if cls=="CANDIDATE_READY":
                controls.append("defined molecular candidate")
            if parent[key]["inci"] in MOLECULAR_AUDIT_LABELS:
                controls.append("named molecular controls")
            if scope=="SOURCE_SUPPORTS_NONDISCRETE_SCOPE":
                controls.append("explicit broad scope")
            for control in controls:
                if len(samples[control])<6:
                    samples[control].append({"concept_id":cid,"name":parent[key]["inci"],"eligibility":cls,"evidence":ev})
            if cid in dispositions:
                validation.append({"concept_id":cid,"classification":cls,"recovery":dispositions[cid],"reason":reason})
        if totals["registered"]!=30360 or sum(triage.values())!=9698:
            raise ValueError("Operational output coverage mismatch")
        out.commit()
        if out.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or digest(REGISTRY)!=before:
            raise ValueError("Operational index integrity or working-registry digest failed")
    temp.replace(INDEX)
    write(OUTPUT/"triage_eligibility_metrics.json",{"policy":POLICY,"policy_version":policy_hash,
        "inventory":dict(totals),"eligibility":dict(counts),"potential_pathways":dict(routes),
        "triage":{f"{p}/{a}":n for (p,a),n in triage.items()},"missing_alias_item_causes":dict(causes),
        "missing_alias_claim_actions":dict(claim_actions),"typed_graph_authorities":dict(typed_authorities),
        "eligibility_reasons":dict(reason_counts),
        "structural_diagnostic_patterns":dict(patterns),"original_items":len(old_queue),
        "original_queue_concepts":7968,"official_checks":len(official_cache),"working_registry_sha256":before,
        "elapsed_seconds":perf_counter()-start,"index_bytes":INDEX.stat().st_size,"peak_bytes":peak_rss(),
        "protected_registry_checksums":recovery["protected_after"]})
    write(OUTPUT/"validation_samples.json",{"status":"PROVISIONAL_NO_INDEPENDENT_SPECIALIST",
        "sample_groups":dict(samples),"all_recovery_records":validation})


if __name__=="__main__":
    run()
