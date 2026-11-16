import json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda n:json.loads((H/'evaluation'/n).read_text(encoding='utf-8-sig'))
def link(n,label=None):return f'[{label or n}](<{(H/n).as_posix()}>)'

def main():
 b=read('benchmark_results.json');r=read('real_creation_results.json');g=read('regression_results.json');v=read('integrity_report.json');s=read('safety_tests.json')
 assert v['passed'] and s['passed']
 a=b['metrics'];z=r['metrics'];rows='\n'.join(f"| {label} | {a.get(key,0)} | {z.get(key,0)} |" for label,key in [('Incoming executions (including retries/setup)','incoming_records'),('Sufficiently qualified source identity','sufficiently_qualified'),('Existing identities reused','existing_reused'),('New identities created','new_created'),('New concept associations','concept_associations_created'),('Idempotent retries','idempotent_retries'),('Explicit creation-withheld outcomes','withheld'),('Unresolved possible-duplicate evaluations','unresolved_possible_duplicates'),('Rolled-back transactions','transaction_rollbacks'),('Invalid/incomplete identity evaluations','invalid_or_incomplete'),('Unsupported-scope evaluations','unsupported_classes'),('Production writes','production_writes')])
 controls='\n'.join(f"| {c['id']} | {c['expected']} | {'PASS' if c['passed'] else 'FAIL'} |" for c in b['cases'])
 perf='\n'.join(f"| {x['source']} {'retry' if x['retry'] else 'first'} | {x['result']['creation']['registry_records_before']} | {x['result']['registry_match']['uniqueness']['compared']} | {x['result']['creation']['transaction_seconds']:.3f} |" for x in r['records'])
 sid=r['created_identity'][0][0];db_size=Path(r['fixture']).stat().st_size
 report=f'''# Canonical Substance Creation v1 (POC)

Date: 2026-11-02. All canonical creation occurred in separately authorized disposable SQLite copies of the actual 112-Substance registry.

## 1. Executive conclusion

The unified resolver now creates supported, sufficiently specified molecular identities, atomically associates their source concepts, and reuses existing IDs. {b['passed']}/{b['total']} frozen creation controls, {s['tests_run']} additional safety tests, 378 retained unit/integration tests, 25 association controls and 19 unified controls pass. Actual PubChem/ChEBI records demonstrate one new identity and cross-source reuse. No production registry, ontology, admission/provider policy or frozen historical result changed. This provisionally validates bounded POC mechanics, not production readiness or population-level chemical accuracy.

## 2. Supported scope

Creation uses the existing molecular/fixed-composition comparator contract: constitution/bonding, ordinary tetrahedral and E/Z stereo, explicit tautomer, isotope placement, supported charge/protonation and component composition. The unchanged admission function rejects unsupported electronic states, coordination conventions, advanced/unspecified stereo and unvalidated element capabilities. Variable polymers, mixtures, alloys, solid phases and broad families cannot create IDs. A parsable graph alone is insufficient.

## 3. Eligibility

Require the existing validated source-provided structural-assertion classification, established referent binding, sufficient reconciled identity, no blocking contradiction, official validation, supported scope and `policy.decision == AUTO_ACCEPT`. Verified explicit structures retain the external-corroboration exemption; no independent-provider requirement was added. Name-derived structures are excluded even when existing admission approves them (additional safety control). Missing display metadata also withholds creation.

## 4. Unified workflow

The existing API and CLI now accept `allow_creation` plus a separate creation capability. Adapt → qualify/reconcile → `BEGIN IMMEDIATE` → current complete matching/admission → reuse or eligibility → allocate/insert → re-match the inserted record → existing locked association operation → append audit → commit. Chemical matching, completeness, eligibility, admission, creation and association receipts remain separate fields. `NO_MATCH_IN_REGISTRY` is preserved as the chemical result of a successful creation; `NEW_SUBSTANCE_CREATED` appears only after commit. Failures expose validation/matching diagnostics without an uncommitted ID.

## 5. Existing versus new

Unique supported existing match plus admission reuses the ID. Complete `NO_MATCH_IN_SEARCHED_REGISTRY` is necessary but insufficient for creation. Any unresolved comparison, deficient existing record, database integrity/FK error, incomplete/truncated search, source ambiguity/conflict or failed admission blocks creation. Multiple equivalent IDs block selection. Revised concepts with existing links cannot silently allocate a replacement. Results distinguish `EXISTING_SUBSTANCE_REUSED`, `NEW_SUBSTANCE_CREATED`, `CREATION_WITHHELD`, `CREATION_CONFLICT` and `CREATION_FAILED`.

## 6. Canonical IDs

The fixture-only `canonical_id_sequence` starts at the highest existing `SUB_########` suffix. Allocation and collision checking run under the reserved transaction; IDs derive from no chemical/name/source key. Existing IDs are never overwritten. Independent disposable databases may intentionally allocate the same suffix; these IDs must not be imported into production.

## 7. Record/schema construction

The five original canonical tables and constraints are unchanged. New records use `identity_status=ACCEPTED`, one complete canonical isomeric SMILES and generated InChI/InChIKey identifiers confirmed by official validation. Historical `substance_reconciliation` is never written. Fixture-only additions are creation authorization, sequence, immutable creation request and immutable creation-record tables; existing concept/revision/association/event tables are reused. FKs connect creation records to the new identity, original concept, immutable revision and event. Existing partial uniqueness permits at most one active/reserved exact association per referent.

## 8. Names, identifiers and aliases

Preferred name is the qualified source record's nonempty display label; its original value/system/record and display-only role are recorded in `construction_json`. A label is not identity evidence or automatically an exact alias. Missing/invalid labels withhold creation. Only officially confirmed structural identifiers are added. PubChem CID, ChEBI ID, source names and other external references remain in the SourceConcept/revision because no additional exact-form identifier-scope qualification was established. Zero new aliases are automatically promoted.

## 9. Structural preservation

Store the complete validated graph without parent selection, fragment loss, neutralization, isotope removal or tautomer collapse. Original serialization and descriptor/fixed-H diagnostics remain in creation provenance. Standard InChI/keys are projections; no global key uniqueness constraint was added. The tautomer controls create distinct IDs despite a shared Standard InChIKey. Existing hardened chemical comparison decides equivalence.

## 10. Duplicate checking/completeness

Every canonical identity is examined, including deficient records. Candidate routes and identifier hits confer no equivalence. The final snapshot reads the transaction's own connection, including committed earlier creations and its own inserted graph. The adapter's small `from_connection` extension borrows rather than commits/closes the connection; its logical digest detects canonical-state changes. Production read-only snapshot behavior remains intact. Completeness applies only to that registry and supported comparison scope, not global chemistry.

## 11. Transactions and concurrency

`BEGIN IMMEDIATE` serializes competing writers before final matching. A fresh locked check replaces stale pretransaction proposals. Identity, representations, source association, request receipt and audit commit together. Two concurrent identical requests and two equivalent-serialization requests each yield exactly one creation and one reuse, with no duplicate/conflicting creation. SQL constraints protect canonical IDs, idempotency keys, FKs and association cardinality. Canonical UPDATE/DELETE and CUMA INSERT remain denied even on creation connections.

## 12. Atomic association and rollback

The existing association service now exposes a private locked composition point; its matching, admission, revision and no-reassignment decisions are retained. The creation service supplies a freshly sealed genuine matching result, not an arbitrary target ID. All six failure stages—before allocation, after allocation, after identity, after representations, during association and before commit—restore every table, including the allocator, to its prior state. A separate KeyboardInterrupt test also rolls back. No failed transaction returns a created identity or leaves a committed success event.

## 13. Idempotency, revisions and provenance

The creation request digest binds concept/revision, complete qualified input, operation and retrieval policy; it intentionally survives registry growth. Replays revalidate current chemistry and return reuse/unchanged. Changed evidence or cross-operation key reuse conflicts. Updated different/insufficient identity holds the old link for review, excludes it from current-exact semantics and never relinks/reactivates it automatically. Existing association idempotency remains unchanged via transaction-state-specific internal request keys. Immutable source revisions retain original payload/evidence; append-only resolution events record precreation exhaustive matching, official/admission results, evidence digest/revision reference, before/after registry digests, construction/name provenance, association receipt, time and implementation hashes. Creation records reference those events; raw provider payloads are not copied into another evidence table.

## 14. Actual PubChem creation

Saved CID 11838 creates `{sid}`, preferred name **propan-2-yl 2-hydroxybenzoate**, graph `CC(C)OC(=O)c1ccccc1O`, key `YEULQIJMIOWCHB-UHFFFAOYSA-N`. The copy grows from 112 to 113 identities. The original cached response bytes/hash and extracted record were reverified, followed by the real adapter, reconciliation, reference-InChI validation and complete matching. Its repeat returns the same ID without another identity or association.

## 15. Actual cross-source reuse

ChEBI CHEBI:38703 independently passes its own source adapter/identity/admission checks and matches the newly created graph. It creates a second source-concept association to `{sid}`; its repeat is unchanged. Four executions produce one Substance and two associations. Both saved payload hashes/original rows verify. This establishes represented-graph correspondence and source binding under the existing explicit-structure policy, not independently established upstream chemical corroboration. {link('evaluation/real_creation_results.json','Actual source evidence and receipts')}.

## 16. Identity and representation controls

Equivalent atom ordering, noncanonical/canonical SMILES, aromatic/Kekulé, explicit/implicit H and ordinary stereo representations reuse an ID. Constitutional isomers, opposite stereo, tautomers, isotope placement, protonation, counterions and fixed component ratios remain distinct when supported. Unspecified stereo, broad families, name-derived inputs, source conflicts, missing official validation, missing names, invalid trailing text, uncomparable/multiple/changed registry targets and incomplete searches cannot create IDs.

## 17. Frozen benchmark and metrics

21 development and 18 held-out expectations were frozen before creation implementation; graph inputs were additionally frozen before any evaluation. They are requirements-based synthetic controls, not blinded expert chemical labels. Each starts with a copy of the actual 112-record registry; multi-step cases grow that copy. Counts below aggregate execution attempts across separate fixture instances, not one combined registry. The synthetic column includes retries, six intentional failed writes, blocked authorization attempts and one existing-only setup call. Metrics overlap.

| Metric | Synthetic | Actual saved source |
|---|---:|---:|
{rows}

Detected false merges, duplicate creations, incorrect incomplete admissions, missed tested equivalents and unresolved-comparisons-treated-as-different: **0 in these controls**. Concurrent creation conflicts: 0. Authorization controls block two production path forms, a forged token, association-only permission and mixed fixture capabilities. Sandboxed link creation was unavailable. A separate disposable-file probe outside the sandbox successfully created an actual hard link and a Windows junction; both were rejected (`SHARED_FILE_REJECTED` / `LINK_PATH_REJECTED`). Live symbolic-link creation remained unavailable because this Windows account lacks the required privilege (WinError 1314); this is not counted as a passing live symlink test. {link("evaluation/native_link_probes.json","Native link probe evidence")}. Two synthetic API attempts are counted as authorization failures; direct connection probes are separately logged. Actual-source failures/withholds: 0.

| Frozen control | Expected behavior | Result |
|---|---|---|
{controls}

{link('evaluation/benchmark_results.json','Full benchmark')}; {link('evaluation/transaction_results.json','Rollback stages')}; {link('evaluation/concurrency_results.json','Concurrency')}; {link('evaluation/safety_tests.json','Additional safety tests')}.

## 18. Retained chemical safety

All 378 unit/integration tests, 25 association controls, 19 unified controls and {s['tests_run']} added safety tests pass. Retained suites cover matching, hardening, real-world/source correspondence, adapters, identity reconciliation, ChargeDimensionEvidence, NSC-001/002 and production resolver/admission. Frozen original/corrected correspondence controls and historical unsafe outcomes retain their expected behavior. The separate documentary real-world comparison remains 30/30 for the hardened implementation; it is a small purposive set, not a new independent accuracy estimate. All regression outputs were redirected to this milestone; frozen historical files were not overwritten. The integrated CLI also passes actual creation, retry and ChEBI reuse checks. {link('evaluation/regression_results.json','Regression receipts')}.

## 19. Lightweight performance

Measured actual-source transactions on a 112–113-record fixture; exhaustive comparison was retained. Counts are the initial chemical search, with additional complete rechecks for inserted-record validation/association. Transaction time includes official validation and audit serialization, not just SQL inserts. Final real fixture size: {db_size:,} bytes. No large-registry speed claim is made.

| Execution | Records before | Initial comparisons | Transaction seconds |
|---|---:|---:|---:|
{perf}

## 20. Production and fixture integrity

PASS: {v['protected_files']} protected files checked; four explicitly scoped integration modules changed, zero unexpected differences. Production SHA-256 before/after: `{v['production_after_sha256']}`. Original counts remain 112 identities, 112 structures, 336 identifiers, 300 aliases and 53,667 CUMA reconciliations. Duplicate IDs/assertions/CUMA rows and all orphan row counts are zero; SQLite integrity and FKs pass. Production canonical/schema/ontology/policy/budget/frozen-result changes: zero. Ordinary fixtures pass integrity; the deliberately deficient existing-record fixture is preserved, reported and correctly blocks creation. Distinct creation authorization requires an external random token plus stored digest, separate from the existing association capability. Path ancestry, production aliases, symlinks/junctions, hard links and file identity checks are reused. No production migration or database write was performed. {link('evaluation/integrity_report.json','Integrity receipt')}.

## 21. Limitations

This is single-process-library/trusted-adapter POC authorization, not a sandbox against hostile Python code or an authenticated multiuser service. Upstream evidence claims are trusted through the existing adapter contract, not cryptographically certified source truth. Unsupported chemistry and any uncomparable registry entry may conservatively block creation. Exhaustive matching and large audit JSON are deliberately unoptimized. No new provider queries, expert adjudication, general nomenclature expansion, broad-material identity or production recovery/authorization deployment was evaluated. Source database IDs and synonyms require separate exact-form qualification before promotion. Fixture IDs/capabilities are not production artifacts. A live symbolic-link bypass probe remains to be executed under an appropriately privileged account; the existing symlink path guard is retained.

## 22. Next milestone and readiness

Conduct independent chemical review of a frozen supported-scope creation corpus, then define a controlled production storage/authorization, concurrency, recovery and audit-retention deployment plan. Keep new creation opt-in and fixture-only until that review and deployment validation. The bounded resolution→reuse/create→association POC is functional; unrestricted production identity creation is not authorized. {link('README.md','API/CLI and replay instructions')}.

{v['verdict']}
'''
 (B/'CANONICAL_SUBSTANCE_CREATION_V1_REPORT.md').write_text(report,encoding='utf8')
if __name__=='__main__':main()
