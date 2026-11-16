import json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
def read(n):return json.loads((H/'evaluation'/n).read_text(encoding='utf8'))
def link(n):return f'[{n}](<{(H/n).resolve().as_posix()}>)'
def main():
 i=read('integrity_report.json');bench=read('end_to_end_results.json');real=read('real_source_results.json');assert i['pass_']
 a=bench['metrics'];b=real['metrics']
 table='\n'.join('| '+k+' | '+str(a[k])+' | '+str(b[k])+' |' for k in ('source_records','qualified_identity_evidence','admission_eligible_matches','associations_created','unchanged','revision_reviews','processing_failures','production_writes','new_substances'))
 cases='\n'.join(f"| {r['id']} | {r['expected']} | {r['result']['resolution_status']} | {'PASS' if r['passed'] else 'FAIL'} |" for r in bench['cases'])
 text=f'''# Unified Substance Resolution Pipeline v1 — POC

Date: 2026-10-30.

## Executive summary

The unified backend and CLI connect source adapters, existing evidence qualification/reconciliation, nine-dimension chemistry, exhaustive canonical matching, unchanged admission policy and controlled source-concept association. All **19/19 frozen end-to-end controls**, **378 retained unit/integration tests** and **25 retained association controls** pass. Production data, ontology, policy, aliases, IDs and historical CUMA reconciliation are unchanged at completion. No canonical Substance is created.

Twenty-four real saved-source executions (including retries) use PubChem and ChEBI: two fixture associations created, two idempotent results, 16 bounded no-matches and four unresolved results. There is no processing failure in this real population. The positives share known PubChem ancestry and are mechanics demonstrations, not independent chemical accuracy estimates. No positive ChEBI association is manufactured. Source-only name resolution and unsupported chemistry remain bounded by prior capabilities.

## Architecture and actual module reuse

```mermaid
flowchart TD
  R[Source record] --> A[PubChem / ChEBI / qualified adapter]
  A --> E[Existing IdentityEvidence and referent binding]
  E --> Q[Existing source qualification and reconciliation]
  Q --> M[Multi-route retrieval and hardened chemical comparison]
  M --> D[Registry uniqueness and existing admission policy]
  D --> O[Structured read-only result]
  D --> P[Existing sealed proposal and locked revalidation]
  P --> F[Marked disposable association database]
```

The orchestration is {link('unified_resolver.py')}. It does not parse nomenclature, create identity keys or change Architecture B. It reuses `pubchem_adapter`, `chebi_adapter`, `comparison_session`, `RegistryMatcher`, `SourceConcept`, `SourceRevision`, `AssociationService` and `FixturePermit`. Partial-stereo and isotope fixes remain in their validated wrappers. No new chemistry rule was introduced.

The common adapter interface is `adapt(record) -> AdaptedRecord(concept, revision, incoming)`. Native PubChem/ChEBI adapters call the existing qualified field adapters through the existing record-input constructor. The `qualified` adapter decodes the existing serialized IncomingConcept/EvidencePackage format. Trusted future adapters may register against the same interface; complete INCI/patent ingestion and a new name parser are not implemented. Adapters establish source meaning and claims, never canonical matches.

Read-only resolution invokes matching once. Persistence uses the existing prepare match and the mandatory transaction-time revalidation; it does not add a preliminary third match. Repeated parsing inside existing validators is retained, with existing memoization. No correctness wrapper was removed for architectural cleanliness.

## Input and output contracts

Programmatic API:

```python
resolver = SubstanceResolver(official_validator=bridge.official)
result = resolver.resolve(record, 'pubchem', registry_path)
result = resolver.resolve(record, 'pubchem', fixture_permit,
                          persist_association=True)
```

Provider packets contain original `record`, documented `provenance`, optional `source_revision`, `source_timestamp`, `referent_key` and existing qualified admission evidence. Revision labels default to `local-v1`; they do not claim an upstream provider version. The source record ID and referent identify the concept, not its displayed name. Normalization uses a copied input and preserves original claims. Multiple referents require separate scoped evidence packages and declared referent keys.

The output separates source concept/revision, identity evidence, reconciliation summary, candidate retrieval, per-candidate dimension comparisons, registry uniqueness, admission and association receipt. Detailed evidence is stored once in the full response. `--verbosity summary` retains dimension results and an evidence digest while reducing the evidence body. Chemical status and overall workflow status are distinct:

| Situation | Chemical status | Workflow / association |
|---|---|---|
| Sufficient unique existing identity | EXACT_MATCH | Admission reported separately |
| Successful new fixture link | EXACT_MATCH | ASSOCIATED / CREATED, committed and current-exact |
| Valid unchanged retry | EXACT_MATCH | EXACT_MATCH / UNCHANGED |
| Multiple equivalent IDs | MULTIPLE_MATCHES | No selected ID |
| Incomplete source/search/unsupported comparison | UNRESOLVED | No selected ID |
| Qualified source contradiction | SOURCE_CONFLICT | No selected ID |
| Complete bounded negative | NO_MATCH_IN_REGISTRY | No new identity |
| Changed/insufficient revision against old link | Original new-record chemical assessment retained | REVIEW_REQUIRED, no selected top-level ID |

`VALIDATION_FAILED`, `UNSUPPORTED_SOURCE`, `PERSISTENCE_NOT_AUTHORIZED` and `PROCESSING_FAILED` are explicit non-chemical errors. The software does not relabel unexpected failures as chemical uncertainty. An invalid structure fails validation; unsupported parseable chemistry remains unresolved. An injected association error returns PROCESSING_FAILED, with requested/failed association flags and no committed association. If a later presentation step fails after commit, the actual committed receipt is preserved.

Two justified integration corrections were made in the new orchestration only: persisted `recorded_at` is read from immutable revision storage rather than replaced by the retry time, and association requests/failures/commits are explicitly distinguished. `provenance.evaluated_at` is the new evaluation time. Unpersisted revisions are labelled unstored and have no fabricated stored timestamp.

## Admission and association handling

Verified, directly source-provided, sufficiently specified structures retain the agreed external-corroboration exemption. They still require binding, structural/form validation, no blocking contradiction, complete unique matching and official validation/admission. Shared source ancestry does not invalidate legitimate structural comparison and is not counted as independent corroboration.

Name-derived graphs retain existing external-corroboration requirements. Even a positive read-only name match is ineligible for persistent association in v1. A frozen qualified-name control returns EXACT_MATCH with failed admission and no association; raw unqualified interpretation cannot fill source specificity. Broad glutamic-acid evidence retrieves specific fixture candidates without acquiring an exact identity.

Persistent calls require the existing marked fixture capability, not a write boolean or arbitrary Substance ID. The existing service seals proposals, verifies source/revision/evidence, reruns complete matching and unchanged admission under BEGIN IMMEDIATE, checks current target/state, and atomically commits audit and eligible associations. Foreign keys, unique reserved exact links, canonical-write denial, path/link protection and idempotency remain unchanged. No new persistent schema was added.

Default idempotency keys bind the normalized concept, source revision and evidence. A changed record preserves old revisions. Different or insufficient new meanings put prior links on review, with no automatic reassignment, deletion or reactivation. The head is processing order, not reconstructed upstream chronology. No distributed synchronization or revision merging was added. Broad/unresolved concepts can be stored with audit history and no exact association; the CLI broad-source persistence check demonstrates this audit-only commit.

## End-to-end evaluation

The 12 development and seven public held-out controls were frozen before orchestration implementation; source/target chemical graphs reuse prior CUMA-independent frozen seeds. Expected workflow outcomes were declared independently of resolver predictions. They are synthetic workflow controls, not blind chemical adjudication or real provider corroboration.

| Case | Expected | Actual | Result |
|---|---|---|---|
{cases}

The cases cover exact matches, repeat processing, many-to-one, broad names, name-derived admission failure, stereo uncertainty, tautomer/charge/isotope/component distinctions, source conflict, incomplete search, duplicate IDs, bounded absence, revision review, unsupported adapters, invalid structures and actual rollback. The rollback control checks the disposable database has neither association nor resolution-event rows after the injected failure. No downstream matching decision is supplied to the entry point.

Full results: {link('evaluation/end_to_end_results.json')}; errors: {link('evaluation/error_handling_results.json')}; association receipts: {link('evaluation/association_results.json')}.

| Metric | Synthetic frozen workflow executions | Real saved-source executions |
|---|---:|---:|
{table}

The synthetic chemical assessments contain six exact matches, four unresolved, five bounded negatives, one conflict and one multiple-match result. Two inputs fail before chemical assessment (unsupported/invalid); the transaction-failure control had already matched chemically but did not persist. Five matching evaluations pass admission, while only two new associations commit. This is deliberate separation of stages.

Real saved-source chemical outcomes are four exact evaluations, 16 bounded negatives and four unresolved; the four exact evaluations are two source concepts each processed twice. Both systems use the same downstream workflow. Twenty of 24 evaluations qualify sufficient source identity. Real exact association targets are CID 1049 → SUB_00000112 and CID 6323 → SUB_00000006 in the copied fixture. Unresolved inputs include the previously documented stereo/component-scope cases. No equivalent is claimed for any absent real record.

Actual source receipts: {link('evaluation/real_source_results.json')}. The available ChEBI data establishes no positive against this registry; real cross-source many-to-one positives remain zero. Two explicitly synthetic source systems independently supply ethanol graph representations through the `qualified` adapter and both associate to the same fixture identity: {link('evaluation/synthetic_cross_source_results.json')}. This is cardinality/integration evidence only.

## CLI and inspectability

Executable entry: {link('run.py')}. Full usage and programmatic contract: {link('README.md')}. From the workspace root:

```powershell
python canonical_registry/unified_substance_resolution/run.py --input canonical_registry/unified_substance_resolution/examples/pubchem_input.json
python canonical_registry/unified_substance_resolution/run.py --input canonical_registry/unified_substance_resolution/examples/chebi_input.json --source-type chebi --verbosity summary
python canonical_registry/unified_substance_resolution/run.py --input canonical_registry/unified_substance_resolution/examples/pubchem_input.json --persist --permit-file canonical_registry/unified_substance_resolution/evaluation/session.permit.json --output canonical_registry/unified_substance_resolution/evaluation/result-1.json
```

Repeat with the same permit and a new output filename for UNCHANGED. `--registry` selects the read-only base. `--indexed-only`, `--max-candidates`, `--no-official-validation` preserve their existing limits. JSON output is machine-readable; a concise status/ID/association summary goes to stderr. No frontend dependency was added. Private `*.permit.json` capabilities remain local and ignored. The result file must be new and separate from the permit. Persistence paths remain restricted by the existing fixture factory/authorization model.

CLI smoke checks produced ASSOCIATED for pyridine, EXACT_MATCH/UNCHANGED on retry, bounded ChEBI no-match, and an unlinked broad concept with an audit-only commit. Results are under `evaluation/cli_*.json`; capability tokens are never included in resolution results.

## Regressions and integrity

All 378 retained unit/integration tests and 25 association controls pass with redirected outputs. This covers matching, controlled reuse, hardening, source-to-candidate correspondence, evidence adapters, reconciliation, charge, NSC-001/002, production resolver/admission and historical chemical safety. The established isotope/stereo fixes, tautomer distinctions, source conflicts and provider rules are unchanged. Unexpected chemical outcome changes: zero. Production writes and new Substances: zero.

A regression-runner redirection error initially rewrote four historical matching result files. Comparison showed identical evidence and chemical outcomes; only Python set-iteration list order differed. The runner was corrected to replace only the top-level output root. The four files were restored **byte-for-byte against their pre-task SHA-256 values**, including the original array ordering; no reference label or chemical value was altered. The exceptional repair is documented in {link('evaluation/historical_restoration.json')}, not part of pipeline execution. Final verification finds **{i['protected_files']} protected files unchanged**. See {link('evaluation/integrity_report.json')} and {link('evaluation/regression_results.json')}.

## Limits and next functional milestone

The unified existing-identity path is functional and provisionally validated for further POC development, not production deployment. The actual positives share known ancestry. The small public benchmark is synthetic/non-blind and lacks qualified expert review. Missing local caches/registry/JARs limit fresh-checkout historical replay. Unsupported chemistry, broad concepts and physical-form ambiguity remain unresolved. Name-derived persistence and complete INCI/patent ingestion are deferred. There were no new provider requests.

For a later, separately authorized **new-identity POC**, the minimum extension is:

1. Accept only sufficient coherent identity evidence across all relevant dimensions, with unchanged official/admission requirements; names retain corroboration requirements.
2. Under one controlled transaction, rerun complete candidate retrieval/comparison against the latest registry and recheck uniqueness immediately before insertion. Bounded no-match alone is not creation authorization.
3. Allocate a fresh opaque Substance ID and populate the existing identity/name, validated aliases, identifiers and full structures without destructive parent normalization. Do not use a name, CID or key as the Substance ID.
4. Link the new identity to its qualified source concept/revision through the existing association/audit model atomically.
5. Serialize competing creators, re-evaluate before insert, enforce appropriate database uniqueness/idempotency, and test representation-equivalent graphs plus identity-significant alternate forms. A Standard InChIKey alone cannot enforce exact graph identity, particularly for tautomers.
6. Reuse current adapters, comparators, specificity/reconciliation, official validation, source revisions and transaction/audit mechanisms; add a narrowly authorized creation boundary and concurrent-creation controls. Do not infer this authorization from the current fixture association capability.

No creation operation is implemented here. The recommended next milestone is this bounded disposable new-identity design/evaluation after reviewing the unified result contract; general deployment/security infrastructure is outside this functional POC.

{i['verdict']}
'''
 (B/'UNIFIED_SUBSTANCE_RESOLUTION_PIPELINE_V1_REPORT.md').write_text(text,encoding='utf8')
if __name__=='__main__':main()
