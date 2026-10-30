# Nomenclature semantic constraint integration

## Result

**Partial integration only.** A pinned, process-isolated OPSIN trace adapter can be explicitly supplied to the resolver, which records its evidence before the provider gate. It always returns the identity constraint `UNKNOWN`; it does not change source-form status, local eligibility, the provider requirement, or default resolver behavior. Operation-aware composition, candidate-graph correspondence and complete mobile-H coverage are **not implemented**. Therefore this is not the requested admission-supporting semantic constraint layer and no case was recovered.

The verified source-token → parser node → fragment → CML-atom trace is a necessary starting point, but it cannot safely be treated as a final-H constraint or proof of the entire tautomer. The existing conservative decision remains authoritative whenever tracing is disabled, unavailable, ambiguous, or incomplete.

## Pinned OPSIN and reproducibility

The official 2.9.0 tag resolves to commit `b91b610af5ab07560fedb20730d7aef46bb2bca0`; the downloaded core dependency jar hashes to `627ee5da4af551f9c4d1d766f545eb7cf519a344776e0bb677247a47abac0252`, matching the publisher's release digest and the supplied POC report. The supplied bundle's 331 manifest entries all verified. The [build manifest](opsin_build_manifest.json) records source, artifact, bundle, patch and packaged diagnostic hashes. The released dependency and upstream source are isolated from the installed 3.0-SNAPSHOT parser; **the production parser was not replaced**.

The provided six-unit instrumentation patch was reproduced unchanged from the pinned clean source. The [Windows reproduction script](nomenclature_semantic_integration/reproduce_windows.py) adapts classpath separators and uses base64 argument transport to preserve Unicode; it retains the original patch. An initial run exposed Windows command-line encoding corruption in the Unicode control and failed one trace test; after the harness transport correction all controls passed. The independently reproduced outputs match released and source-baseline public outputs on 27 probe runs. Separately, 15 independent controls compared the installed 3.0-SNAPSHOT with 2.9.0: status, warning content, SMILES and CML were equal in all 15. This bounded comparison does not establish universal parser-version equivalence.

## Architecture and supported evidence

`Resolver(..., semantic_adapter=...)` optionally invokes the [experimental adapter](nomenclature_semantic_integration/semantic_adapter.py) during local validation, before the provider gate. A fresh Java process handles each request, isolating the POC's static state across threads and requests. Runtime digests are checked. Any exception, missing or mismatched artifact, parse failure, warning, ambiguity, unsupported alternative, or non-ASCII source is fail-closed to `UNKNOWN`; tracing failure cannot cause a resolver failure. The default adapter is `None`, and no provider module, profile, budget or policy was changed.

The [trace schema](semantic_trace_schema.json) records original source token/span, indicated versus added indicated H, fragment token and temporary ID, local locant, same-result CML atom, parent-feature stage, explicit/generated distinction, mapping status, and an abstention reason. The adapter requires an original ASCII span match, successful single selected parse, no warning, same-result atom, matching CML locant and no observed clone activity. Generated H nodes are not promoted to explicit source evidence. Unicode normalization and repeated-word ambiguity abstain; temporary fragment and atom IDs are not stable identifiers.

The trace does **not** establish which later substitutions or suffix operations modified the parent state. For `1-methyl-1H-pyrazole` the POC's mapped parent nitrogen has zero final H neighbors, while `3H-pyrrole` has two at the mapped carbon. Thus a rule requiring one final H would be wrong. Both `INDICATED_HYDROGEN` and `ADDED_INDICATED_HYDROGEN` are recorded, but operation sequence is `NOT_CAPTURED` and every semantic constraint remains `UNKNOWN`. A successful mapping also does not validate all mobile-H sites, other identity dimensions, or a graph match to the resolver's separate 3.0-SNAPSHOT candidate. Symmetry is left to the existing identity comparator; locant differences are not identity keys.

The minimum necessary production design still requires validated parent-state and subsequent operation events, a safe same-result-CML to resolver-graph correspondence, and a bounded completeness proof for *all* relevant mobile-H sites. Until then even a mapped explicit token cannot produce source-form `SUPPORTED` or `DIFFERENT`.

## Independent controls and safety

The [control results](semantic_control_results.json) preserve 27 reproduced POC runs. They include indicated H and added H, nested repeated locants, methyl-substituted parents, generated H, warning, invalid name, repeat-word, Unicode and fragment-copy abstentions. The experimental adapter's eight tests additionally cover process isolation under concurrent calls and missing-artifact fallback. The resolver-hook tests confirm the diagnostic runs before provider evaluation when supplied, does not promote eligibility, and fails safely.

All eight historical controls were rerun with the optional trace adapter enabled, using saved claims or offline providers: 17504 and 30832 returned `CONFLICT`; 4373, 5684, 5997, 23839, 30142 and the historical dithiazole case returned `UNRESOLVED`. See [safety results](nomenclature_semantic_integration/safety_results.json). No case became `EXACT` or `AUTO_ACCEPT`.

## Saved-evidence replay

The [81-case diagnostic replay](semantic_81_case_replay.json) records applicability, bounded mapping, source token, blockers and unchanged eligibility for every previously correct hold. Four cases have a bounded token/fragment/CML mapping; 77 do not. For the 41 tautomer-primary holds, three cases have an indicated-H mapping, one has an added-H mapping, and those groups overlap in one case; 35 have no traceable claim and three contain claims whose mapping is unresolved. All 41 lack an operation-composition and mobile-H completeness proof. A bounded source-token claim is not a complete identity claim. **Zero eligibility changes** occurred.

The 224-case local-helper replay uses saved claims and official InChI results with no provider calls. Since the experimental trace is not used for admission, this replay leaves the previous metrics unchanged; it is not a full end-to-end trace of all 224 cases. [Metrics](semantic_cohort_metrics.json):

| Measure | Result |
|---|---:|
| Previously confirmed correct eligible / withheld | 102 / 81 of 183 |
| Confirmed incorrect locally eligible | 0 of 1 |
| Precision among adjudicable eligible | 102/102 = 100%; exact 95% CI 96.45%–100% |
| Recall against all reference-confirmed identities | 102/225 = 45.33%; exact 95% CI 38.71%–52.08% |
| Eligible without adjudicable reference | 15 |

These intervals do not correct for the selected cohort or missing adjudications. The frozen [gate comparison](semantic_gate_value.json) remains A/B/C/D = **7/95/0/0**; it is analytical and does not change provider behavior.

## Tests and integrity

| Check | Result |
|---|---|
| Pinned OPSIN core suite, source baseline | 680 passed, 0 failed, 2 skipped |
| Pinned OPSIN core suite, instrumented | 680 passed, 0 failed, 2 skipped |
| Reproduced POC trace controls | 14 passed, 0 failed |
| Experimental adapter tests | 8 passed, 0 failed |
| Retained resolver suite including hook tests | 201 passed, 0 failed |
| Released/baseline/instrumented public-output probes | 27/27 matched |

The first resolver-hook test used a pyrrole fixture that was already locally eligible and incorrectly expected a hold. It was corrected to a tautomer-sensitive control; the final suite passed without weakening the assertion. The original offline Maven run could not find a test dependency; the pinned suite passed after retrieving that public dependency.

[Integrity verification](integration_integrity.json) checks the ontology, framework, persistent schema, provider modules and budgets, installed OPSIN artifact, frozen input and provider-cache hashes, and scans new outputs for the configured credential. It found no unexpected frozen-code changes, case-specific runtime rules or credential occurrence. The resolver change is limited to the opt-in, fail-closed diagnostic hook. No registry data or external alias-enrichment pipeline was modified.

## Next capability

Instrument and independently test the **operation lineage** from parent indicated-H state through substitution and suffix transformations, then establish symmetry-safe correspondence to the resolver graph and mobile-H completeness. Include independent positive, conflicting, underspecified, warning, cloned and multi-site controls. Only after those claims are demonstrated should a separate policy change allow a semantic constraint to affect eligibility; keeping a missing trace as `UNKNOWN` remains mandatory.

BOUNDED_INTEGRATION_PARTIAL
