# OPSIN operation-lineage semantic POC

## Outcome

The isolated POC now records a mapped indicated-H/added-H parent snapshot and ordered low-level atom/bond mutations, and a separate bounded graph-correspondence utility enumerates candidate mappings. **It does not yet establish operation-source provenance, complete operation lineage, or mobile-H completeness.** Consequently every evaluated semantic control remains `UNKNOWN`; no admission-changing behavior or feature flag was introduced. The requested `SUPPORTED` and chemically established `DIFFERENT` outcomes have **not** been validated.

No provider gate, provider logic, ontology or registry schema was changed. The existing optional diagnostic adapter remains fail-closed. A feature flag would be required before any future admission-changing implementation; adding an inert flag now would not make the missing semantic capability available.

## Pinned build and instrumentation

The upstream source is OPSIN 2.9.0 commit `b91b610af5ab07560fedb20730d7aef46bb2bca0`; the official dependency jar SHA-256 is `627ee5da4af551f9c4d1d766f545eb7cf519a344776e0bb677247a47abac0252`. The existing source-token ownership patch is retained unchanged. An additional isolated [operation patch](operation_semantic_poc/operation-instrumentation.patch) instruments `TraceProbe`, `Atom`, `Bond` and `FragmentManager` to observe bond creation/removal, bond-order changes, element and charge changes, proton count changes and spare-valency changes. It records operation order, target atom object IDs, and pre/post local snapshots. It does **not** alter the installed production OPSIN or select atoms itself. See the [build manifest](operation_semantic_poc/opsin_operation_build_manifest.json).

The [trace schema](operation_semantic_poc/operation_trace_schema.json) separates parent source token/span, owning fragment and atom, an operation cursor and parent snapshot, observed mutations, same-result final CML state, graph correspondence, mobile-H completeness and constraint result. Mutation events record `SOURCE_NOT_CAPTURED`: neither source spans nor source-explicit versus generated attribution are proven for these operations. Only mutations directly involving the H-mapped atom are retained in the per-claim record. Transformations affecting other atoms can be relevant to the same tautomer or suffix, so this is **not an exhaustive operation lineage**. Atom replacement, fragment-merge lineage and clone transformations are not fully instrumented.

The POC distinguishes indicated H from added indicated H; [IUPAC Blue Book P-14.7](https://iupac.qmul.ac.uk/BlueBook/P1.html#P-14.7) describes their different naming roles. For `1-methyl-1H-pyrazole`, the observed mapped N has a subsequent bond creation to carbon and no final H neighbor; for `3H-pyrrole`, the mapped carbon gains two explicit H neighbors. The observations are consistent with the need to compose operations, but the probe cannot independently attribute the bond to the methyl source token or prove every operation. `pyridin-2(1H)-one` maps the added-H node, but the suffix's carbonyl transformation occurs beyond the H atom and is not established by the per-atom trace. No rule assumes an indicated-H token means exactly one final H.

## Graph correspondence and constraint boundary

The [graph correspondence utility](nomenclature_semantic_integration/graph_correspondence.py) builds a graph from the **same result's CML**, enumerates all matches to the resolver candidate with element, isotope, charge, aromaticity, bond, H-count and component checks, and reports all mappings up to a fixed cap. It rejects invalid structures, radicals, isotopic H and potential or specified stereo because CML parity handling has not been validated. Mismatches and exhausted limits return `UNKNOWN`, not a chemical contradiction. If symmetry leaves multiple mappings, a per-atom predicate may return a common result only when every enumerated mapping agrees; the helper's `ALL_TRUE` / `ALL_FALSE` results are graph observations, not source-form `SUPPORTED` / `DIFFERENT` decisions.

Of 14 independent controls with both same-result CML and a saved 3.0-SNAPSHOT candidate, 10 have one graph mapping and four have multiple mappings. These results do not validate source grammar or cover stereo-bearing molecules. [Graph controls](operation_semantic_poc/graph_correspondence_controls.json) and the test log include symmetry disagreement, mapping-cap, charge, isotope, stereo, multicomponent and malformed-input abstention.

A future semantic `SUPPORTED` requires an explicit or otherwise justified source claim, source-to-fragment/atom provenance, all relevant operation lineage, same-result final-state derivation, validated resolver-graph correspondence, complete mobile-H coverage and no conflicting source claims. `DIFFERENT` requires the same provenance and completeness plus a demonstrated incompatible candidate. Missing provenance, warnings, normalization without original offsets, repeated words, untracked clones, unsupported stereo, ambiguous mappings with differing conclusions, and incomplete sites yield `UNKNOWN`. The current POC meets neither full criterion, so it cannot produce either admission-relevant state.

## Independent controls and value

The [27 operation controls](operation_semantic_poc/operation_lineage_controls.json) include the eight requested indicated-H, substitution, added-H and nested-name examples, plus warnings, parse failures, Unicode normalization, repeated words and clone cases. Nineteen runs have at least one observed low-level mutation on a mapped atom. All 27 semantic results remain `UNKNOWN`; see [constraint controls](operation_semantic_poc/semantic_constraint_controls.json). The control suite checks parent snapshots, operation ordering, observed substitution-related bond creation, incomplete added-H handling and separate nested atoms. A candidate graph mismatch is tested as `UNKNOWN`: **no chemically established `DIFFERENT` contradiction control is yet available**, and it would be misleading to count that as passed.

Operation-aware admission value is therefore not established: **0 controls gained `SUPPORTED`, 0 gained `DIFFERENT`, 27 remain `UNKNOWN`**. No admission-changing code exists, so there were no newly blocked or released cases attributable to it; this is not evidence of an error rate for a future implementation.

## CUMA and gate evaluation

The requested operation-aware [81-case replay](operation_semantic_poc/semantic_81_case_replay.json) is explicitly **not run**: independent admission-supporting and contradiction controls have not been validated, and the task requires those controls before applying the capability to the corpus. The file lists all 81 prior cases and their previous token-mapping state, with operation lineage and post-change eligibility marked unavailable. No recovered-case count is asserted.

The current-policy saved-evidence helper was rerun for the 224-record deterministic cohort, without the operation probe or new provider queries. It still reports **102 eligible and 81 withheld out of 183 previously confirmed correct**, and **0 of 1 confirmed incorrect locally eligible**. Adjudicable local precision is **102/102 = 100%**, exact 95% CI **96.45%–100%**; local recall against all 225 frozen reference-confirmed identities is **102/225 = 45.33%**, exact 95% CI **38.71%–52.08%**. Fifteen eligible cases have no adjudicable reference. These are unchanged current-policy observations, not a validated operation-aware cohort result. See [cohort metrics](operation_semantic_poc/semantic_cohort_metrics.json).

The saved current-policy [external-gate comparison](operation_semantic_poc/semantic_gate_value.json) remains A/B/C/D **7/95/0/0**. It uses recorded provider outcomes; no provider behavior changed. The eight historical cases were rerun through the existing optional trace adapter with offline/saved evidence: 17504 and 30832 remained `CONFLICT`; 4373, 5684, 5997, 23839, 30142 and the historical dithiazole case remained `UNRESOLVED`. The new mutation probe was not used to alter those outcomes. See [safety results](nomenclature_semantic_integration/safety_results.json).

## Verification and reproducibility

| Check actually run | Result |
|---|---|
| Pinned unmodified OPSIN core suite | 680 passed, 0 failed, 2 skipped |
| Operation-instrumented OPSIN core suite | 680 passed, 0 failed, 2 skipped |
| Existing token trace controls | 14 passed |
| Graph and operation observation controls | 11 passed |
| Existing adapter tests, including concurrent processes | 8 passed |
| Full retained resolver suite | 201 passed |
| Public status, warning, message, SMILES and CML | 27/27 matched baseline and release |
| RDKit-generated Standard and FixedH InChI | 25 comparable pairs, 0 differences; 2 parse failures not applicable |

An initial build failed because the isolated runner directory had not been created; the build script was corrected and rerun. The failed setup did not produce a valid test run. Two subsequent clean operation-instrumented builds produced identical class-file hashes and identical event streams after excluding temporary fragment-object IDs; see [rebuild verification](operation_semantic_poc/rebuild_verification.json). Reproduce by first running the pinned prior `nomenclature_semantic_integration/reproduce_windows.py`, then [build_operation_probe.py](operation_semantic_poc/build_operation_probe.py), [analyze_controls.py](operation_semantic_poc/analyze_controls.py), and [check_public_outputs.py](operation_semantic_poc/check_public_outputs.py); the Windows build uses a disposable short temporary path. The prior reproduction verified the release digest and the 331-entry supplied bundle manifest.

[Integrity checks](operation_semantic_poc/operation_integrity.json) verify recorded ontology, framework, schema, installed OPSIN and provider-code hashes, frozen evaluation inputs and provider-cache hashes, and scan new outputs against the configured credential. No case-specific development identifiers or molecule names occur in runtime semantic rules. The experimental patch and graph utility are not wired to admission.

## Next capability

Capture source-token and parser-operation lineage at the actual substitution and suffix application sites, including effects on neighboring atoms and explicit atom replacement/merge handling. Prove event completeness for a small independently specified chemical class, validate same-result graph mapping under symmetry and bound all mobile-H sites. Only then add and test a default-off admission feature flag, including genuine independent `SUPPORTED` and contradictory `DIFFERENT` controls before replaying the 81 cases.

OPERATION_AWARE_SEMANTICS_PARTIAL
