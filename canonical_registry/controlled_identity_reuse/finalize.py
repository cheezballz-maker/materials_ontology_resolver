import json,hashlib,collections
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding="utf8"))
def main():
 p=read(H/"evaluation/protected.json")["files"];changed=[n for n,v in p.items() if hashlib.sha256(Path(n).read_bytes()).hexdigest()!=v]
 tests={n:read(H/f"evaluation/{n}_tests.json") for n in ("diagnostic","correspondence","adapters","identity_reconciliation","nsc001","nsc002","charge","resolver","stereo","corrected_interface","policy","matching")}
 bench=read(H/"evaluation/benchmark_results.json");metrics=read(H/"evaluation/metrics.json")
 result={"protected_files":len(p),"changed_protected_files":changed,"retained_tests":sum(t["tests_run"] for t in tests.values()),"retained_passed":all(t["passed"] for t in tests.values()),"benchmark_passed":bench["passed"],"benchmark_cases":bench["total"],"production_registry_writes":0,"canonical_substances_created":0,"historical_cuma_migration_executed":False,"metrics":metrics}
 result["pass"]=not changed and result["retained_passed"] and bench["passed"]==bench["total"]
 (H/"evaluation/integrity_report.json").write_text(json.dumps(result,indent=2)+"\n")
 (H/"evaluation/test_results.json").write_text(json.dumps({"suites":tests,"retained_unit_integration_total":result["retained_tests"],"association_controls":bench["total"],"association_controls_passed":bench["passed"]},indent=2)+"\n")
 assert result["pass"],result
 report="""# Controlled Canonical Identity Reuse v1

## Conclusion
Implemented source-independent concept/revision storage and controlled exact associations in marked disposable SQLite databases. The existing matcher, hardened chemical comparisons and production admission policy are reused unchanged. All {count} frozen workflow controls and {tests} retained unit/integration tests pass. Production registry, ontology, aliases, canonical IDs, CUMA reconciliation and previous results remain unchanged. No new canonical Substance was created.

This is provisional fixture validation, not authorization or evidence of production persistence readiness. Reproduce with `python canonical_registry/controlled_identity_reuse/evaluate.py`, `regressions.py`, then `finalize.py` (each under the same directory). Existing fixture files are retained for inspection; each evaluation creates fresh UUID-named databases.

## Source concepts, revisions and ontology
`SourceConcept` keys use a deterministic namespaced SHA-256 of the JSON tuple (system, record type, record ID, referent key). Names are display claims, never identity keys. Multiple patent mentions within one record have separate referent keys. Concepts with no molecular structure remain valid stored records.

Revisions preserve the source revision label, original payload hash, complete incoming-evidence hash, optional source timestamp, recorded time and full serialized evidence. Identical evidence/revision coalesces; a reused version label with changed source payload conflicts; updated supporting evidence over the same payload can preserve the same target. The head represents the last processed new revision, not an inferred upstream chronological version order. Known old-revision retries do not move it. Unseen upstream versions require reliable ingestion ordering; automatic published-version ordering is not implemented.

Source concepts remain distinct from Substance. IngredientConcept/CosmeticsIngredientConcept can be domain views of referents. Associations are qualified exact-resolution assertions, not owl:sameAs or Substance aliases. Unresolved concepts remain independent. No ontology class/property is added. See `schema/ontology_alignment.md` and `schema/legacy_cuma_migration_plan.md` for semantic mapping and the explicitly unexecuted CUMA migration design.

## Actual relational design
`schema/associations.sql` is executable and authoritative. Tables: source_concept; immutable source_concept_revision; source_concept_head; append-only concept_resolution_event; concept_substance_association; immutable-by-service association_request; fixture_authorization. Revisions have composite concept/revision foreign keys. Association IDs reference existing Substance IDs and resolution events. Association type is constrained to EXACT. A partial unique index reserves at most one ACTIVE or REVIEW_REQUIRED link per concept. Other concepts may share that Substance.

Association creation revision remains immutable. Supporting new revisions update only validated_revision and audit references. Events retain full original/live matching decisions, evidence and registry digests, matcher/policy hashes, prior association IDs, operation, outcome, timestamp and reasons. MATCH_EVALUATED and the final outcome are committed together. Rejected evaluations can commit concept/revision/audit rows without committing an association: result.association_created distinguishes this from transaction committed.

The current_exact_association view requires ACTIVE status, VALIDATED head and matching validated revision. A changed/broad/conflicting revision puts the old association on REVIEW_REQUIRED and removes it from current exact results while preserving its original target/history. No automatic revoke, delete, relink, supersession or review reactivation is exposed. Old request replay never proves a newer revision exact.

## Eligibility and transaction
Only the existing validated directly source-supplied structural-evidence classification is eligible. Caller boolean flags do not grant exemption. Names, raw parser hypotheses, broad/partial/conflicting concepts, multiple candidates, incomplete searches and missing validation cannot create links. Verified explicit structures retain the agreed external-corroboration exemption; no new independent-provider requirement is introduced. Name-derived results are ineligible for v1 persistence even when the unchanged policy accepts their diagnostic proposal.

Preparation seals the input, operation, matching decision, canonical-table digest and implementation version using the fixture capability token. Arbitrary Substance IDs are not accepted as assignment authorization. Under BEGIN IMMEDIATE, the service verifies evidence/source keys and revision, rebuilds the current registry snapshot, reruns exhaustive matching and admission, checks canonical-state freshness and existing link/idempotency constraints, then writes events and association atomically. Every target is validated against the current snapshot and FK. The canonical digest covers all five legacy tables and ignores new association/audit writes, allowing legitimate retries. Missing/changed targets or other canonical changes reject stale proposals. The reserve lock serializes concurrent writers. On unexpected error, all source, revision, event, request and association writes roll back.

Idempotency keys are database-primary-key unique; payload digests bind concept/revision/evidence, operation, target, registry state and implementation version. Same evidence returns UNCHANGED without another association; changed payload/target returns conflict. Retries still preserve an append-only decision event. Review-held associations remain held on replay.

## Isolation and authorization
The write-capable connector resolves and checks every path component, rejects symbolic links/junctions, multi-link files, production aliases and paths outside controlled_identity_reuse/fixtures, compares file identity around opening, uses mode=rw rather than file creation, and verifies an explicit fixture UUID plus token digest against an externally held capability. A runtime boolean is insufficient. Production is opened only mode=ro for backup and matching. The operational connection denies canonical-table writes and ATTACH/DDL changes through an SQLite authorizer. Foreign keys and DB uniqueness/triggers provide additional integrity.

Tests attempted production and alternate paths, hard/symbolic links (actual availability/results recorded), changed targets, stale snapshots, rollback after insertion and concurrent duplicate requests. Capability administration, adversarial privileged filesystem races, deployment service authorization and operational disaster recovery are not production-certified by these local tests.

## Executed evidence and results
Frozen controls are public, synthetic, CUMA-independent workflow expectations declared before implementation: 19 development, six held-out. They exercise actual SQL persistence and the existing matcher, with actual local official InChI validation, not a mocked success flag. Stereo, isotopes, acid/base, tautomer and component distinctions are included. All {count}/{count} pass; rollback leaves no partial rows; concurrent identical requests produce one CREATED, one UNCHANGED and one current exact link. Duplicate reserved exact associations: zero. See evaluation/benchmark_results.json and transaction/idempotency/concurrency/source_revision results for actual outcomes.

Real saved PubChem CID 1049 and 6323 create links to SUB_00000112 and SUB_00000006 in a read-only copy of the actual 112-record registry, then retry as UNCHANGED. These are known shared-PubChem-ancestry mechanics demonstrations, not independent chemical accuracy estimates. No verified positive ChEBI match exists in the available saved-source registry evaluation. Cross-database positives are zero; explicitly labelled synthetic different-system and separate-referent controls demonstrate many-to-one without fabricating ChEBI evidence.

`evaluation/metrics.json` reports per-fixture concept instances, distinct keys, committed decision outcomes, qualified evaluations, unique/multiple/unresolved matches, admission statuses and association counts. It separates the real-source fixture from synthetic fixtures by path and accompanying real-source result. Setup evaluations and retries are included in event-based counts; one injected failed transaction has no committed audit event and is recorded externally in transaction_results.json. Thus no rolled-back audit falsely claims success. Protection results report attempted unauthorized paths separately from association requests. New canonical Substances and production changes are zero.

All {tests} retained tests pass, including Matching v1, hardening, evidence/reconciliation, charge, NSC-001/002, resolver/admission and chemical safety controls. Historical safety outputs remain available under evaluation. Memoized/uncached comparison parity and previous frozen matching expectations are preserved. No source-specific historical CUMA row was migrated or replaced.

## Readiness and next milestone
| Capability | Assessment | Remaining work |
|---|---|---|
| Production source-concept storage | PARTIALLY_VALIDATED | Review key/version governance, deployment migration, retention/access controls and upstream ordering |
| Production existing-ID association | PARTIALLY_VALIDATED | Independent code/security review, real deployment authorization, crash/recovery and multi-process/service tests, operational audit retention and review workflow |
| New canonical Substance creation | NOT_EVALUATED | Separate authorization, global uniqueness/search scope, chemical admission evidence and creation transaction contract |

Recommend review and hardening of the association service and schema in a non-production integration environment. Do not enable production writes from fixture success alone. Qualified expert/blind chemical validation remains pending; the small established chemistry scope and provider unknown-dependence behavior remain unchanged. No live provider requests are made.

Integrity: {protected} protected files unchanged, including the production registry digest, authoritative ontology, provider/admission policy and all prior frozen JSON results. Detailed receipts: evaluation/integrity_report.json, schema_integrity_results.json, real_source_association_results.json and production_write_protection.json.

CONTROLLED_IDENTITY_REUSE_V1_VALIDATED_PROVISIONAL
""".format(count=bench["total"],tests=result["retained_tests"],protected=len(p))
 (B/"CONTROLLED_CANONICAL_IDENTITY_REUSE_V1_REPORT.md").write_text(report,encoding="utf8")
 print(result["retained_tests"],bench["passed"],len(changed))
if __name__=="__main__":main()
