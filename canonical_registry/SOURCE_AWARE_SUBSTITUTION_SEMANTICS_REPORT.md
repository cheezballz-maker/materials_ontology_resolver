# Source-aware substitution semantics

## Result

An isolated OPSIN trace now connects source-written locant and substituent tokens to the **actual locanted substitution application**, its selected parent atom, substituent attachment atom and resulting same-result CML bond. In three independent development controls, that target is the same OPSIN atom as the indicated-H parent claim. This is a meaningful provenance improvement over the prior low-level bond trace.

The requested admission capability is **not validated**. Later-operation completeness and mobile-H coverage are not established, and a candidate with different connectivity does not yet have a validated common-parent correspondence proving which source constraint it violates. Accordingly the three expected positive controls and one expected contradiction control still return operation and dimension `UNKNOWN`; none is presented as `SUPPORTED` or `DIFFERENT`. No feature flag or admission change was added. The independently frozen holdout and the 81-case corpus were **not run**, as required by the task's ordering when both acceptance states are not demonstrated.

## Source-aware instrumentation

The experiment uses pinned OPSIN 2.9.0 commit `b91b610af5ab07560fedb20730d7aef46bb2bca0`, with official artifact SHA-256 `627ee5da4af551f9c4d1d766f545eb7cf519a344776e0bb677247a47abac0252`. The [substitution patch](source_aware_substitution_poc/substitution-instrumentation.patch) is layered on the previously reproduced indicated-H and low-level operation patches, in a disposable build; the installed parser and resolver policy are unchanged.

At `ComponentProcessor.assignLocantsAndMultipliers`, the probe carries the original locant-token provenance onto the substituent node before the token is detached. At `StructureBuildingMethods.performLocantedSubstitutiveOperations`, it records the source parse node and surviving group tokens, parent fragment, resolved locant, selected parent atom and substituent attachment atom at the `joinFragmentsSubstitutively` call. It verifies the join and both same-result atom objects in the final CML. This is the actual locanted application path described by the [pinned OPSIN source](https://github.com/dan2097/opsin/blob/b91b610af5ab07560fedb20730d7aef46bb2bca0/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/StructureBuildingMethods.java), not a later inference from a generic bond mutation. Additive, multiplied, unlocanted and unsupported paths are not claimed.

The [trace schema](source_aware_substitution_poc/substitution_trace_schema.json) records the source locant span, substituent token spans, parse XML, target and attachment atoms, same-object indicated-H relation, structural bond and mapping status. For the three simple alkyl controls, the parser's contiguous stem and `yl` token spans reconstruct the written substituent; the locant and H token retain separate original spans. One successful selected parse and no clone activity are required. Temporary atom IDs are scoped to that result. Missing spans, normalized text, repeated words, warnings, failed parses and unsupported clones do not become source evidence.

The source-written indicated-H parent operation must be composed with substitution rather than treated as a literal final hydrogen count; [IUPAC Blue Book P-14.7](https://iupac.qmul.ac.uk/BlueBook/P1.html#P-14.7) distinguishes indicated hydrogen from added hydrogen. The trace observes the H-claim application before the substitution event and verifies a bond in the final CML. It does not yet prove every later atom replacement, merge, source-associated operation or mobile-H site. It therefore does not certify the entire operation or tautomer dimension.

## Independent controls

The [control definitions](source_aware_substitution_poc/frozen_controls.json), including a separate held-out group, were saved before inspecting this instrumentation's results. The [positive evidence](source_aware_substitution_poc/substitution_positive_controls.json) includes:

| Source | Observed source trace | Required semantic result |
|---|---|---|
| `1-methyl-1H-pyrazole` | Written locant and contiguous substituent tokens; same indicated-H atom; ordered application; final bond and snapshot-candidate graph mapping. | `UNKNOWN`; complete operation and mobile-H proof missing. |
| `1-ethyl-1H-pyrazole` | Same bounded chain with an independently named substituent. | `UNKNOWN` for the same missing gates. |
| `1-methyl-1H-imidazole` | Same bounded chain on a different parent ring. | `UNKNOWN` for the same missing gates. |

The [negative control](source_aware_substitution_poc/substitution_negative_controls.json) compares the first source with an independently specified differently substituted candidate. OPSIN's source trace targets the indicated-H atom, while the candidate's own parsed substitution targets another atom. The existing full-graph correspondence correctly returns `UNKNOWN` for non-isomorphic graphs; it does **not** establish the common-parent, source-atom correspondence needed to declare a semantic `DIFFERENT`. No expected contradiction is counted as passed.

[Unknown controls](source_aware_substitution_poc/substitution_unknown_controls.json) cover a warning-producing name, clone activity and a Unicode-normalized input; all abstain. Existing indicated-H tests also cover repeated words and missing explicit tokens. A symmetry case with divergent semantic conclusions, arbitrary transformed atoms and complete mobile-H coverage have not been independently validated for this substitution layer. The [held-out controls](source_aware_substitution_poc/substitution_holdout_controls.json) remain frozen and unexecuted; their results are not claimed.

## Integration and evaluation boundaries

The existing bounded graph utility enumerates full-graph isomorphisms without atom-order assumptions, checking element, isotope, charge, bonds, components and H counts. It abstains for unsupported stereo, radicals, isotopic H, mapping-limit exhaustion and non-isomorphic graphs. Symmetric matches cannot establish an operation conclusion unless all mappings agree. Clone activity continues to invalidate provenance unless original-to-clone lineage is proven. A correctly observed substitution operation would remain distinct from the overall tautomer dimension even after operation support is established.

No `SUPPORTED` or `DIFFERENT` acceptance control passed, so a default-off admission feature flag was **not justified or added**. External corroboration and provider behavior remain unchanged. The [81-case replay](source_aware_substitution_poc/substitution_81_case_replay.json) is marked `NOT_RUN`; applicability, complete provenance and recoveries are not estimated. The [cohort metrics](source_aware_substitution_poc/substitution_cohort_metrics.json) and [gate values](source_aware_substitution_poc/substitution_gate_value.json) show only the prior saved-evidence baseline: 102/183 confirmed-correct eligible, 81 held, 0/1 confirmed-incorrect eligible, and A/B/C/D 7/95/0/0. They are not a new substitution-aware evaluation. Practical coverage upside remains unknown.

The eight historical controls were independently rerun under the existing resolver with the older diagnostic adapter enabled and offline/saved evidence: 17504 and 30832 remained `CONFLICT`; 4373, 5684, 5997, 23839, 30142 and the historical dithiazole case remained `UNRESOLVED`. The new experimental substitution trace was not used to change these decisions. See [safety results](source_aware_substitution_poc/safety_results.json).

## Tests, reproduction and integrity

| Check actually run | Result |
|---|---|
| Pinned unmodified OPSIN core suite | 680 passed, 0 failed, 2 skipped |
| Source-aware instrumented OPSIN core suite | 680 passed, 0 failed, 2 skipped |
| Existing indicated-H trace suite | 14 passed |
| Source-aware development observation and concurrent-process tests | 5 passed; these test evidence and abstention, not `SUPPORTED`/`DIFFERENT` admission |
| Existing graph and operation observation suite | 11 passed |
| Existing adapter suite, including concurrency | 8 passed |
| Full retained resolver suite | 201 passed |
| Seven development public outputs | Status, warning, message, SMILES and CML all equal; 7/7 RDKit-generated Standard and FixedH InChI pairs equal |
| Existing 27 indicated-H controls | Released, baseline and instrumented ordinary public outputs matched; their trace suite passed |

The first build failed because its baseline classpath omitted the runner; the build script was corrected and rerun. A second isolated build reproduced class-file hashes and trace events after excluding temporary object IDs; see [rebuild verification](source_aware_substitution_poc/rebuild.json). The [build manifest](source_aware_substitution_poc/substitution_build_manifest.json) records the pinned artifact, successive patch and frozen-control hashes. Reproduce the previous pinned token and operation POCs first, then run [build_probe.py](source_aware_substitution_poc/build_probe.py), [analyze_development.py](source_aware_substitution_poc/analyze_development.py), and [check_public_outputs.py](source_aware_substitution_poc/check_public_outputs.py) from this folder. Builds use isolated short Windows temporary paths.

[Integrity checks](source_aware_substitution_poc/substitution_integrity.json) verify the ontology, framework, schema, installed OPSIN artifact, provider-related frozen code, frozen evaluation input and provider-cache hashes. New output was scanned against the configured credential without disclosing it. No development record IDs or molecule-name whitelist appears in the runtime instrumentation patch; names appear only in control definitions and evidence. No production resolver or provider code was modified in this task.

## Next step

Finish a general source-associated operation lineage through atom replacement and merging, then implement a bounded common-parent correspondence for genuinely different candidate graphs and prove mobile-H completeness for the supported class. Re-run independent `SUPPORTED` and `DIFFERENT` controls before the frozen holdout or 81-case corpus. Once this substitution class is validated, suffix-related operations are the next distinct capability.

SOURCE_AWARE_SUBSTITUTION_SEMANTICS_PARTIAL
