# Deterministic source-form safety remediation

## Decision and limits

The local layer now blocks the observed charge error and the two tautomer/source-conflict probes before the external gate. In a replay of saved evidence, 102 of 102 adjudicable locally eligible candidates were correct; however, 81 of 183 previously confirmed correct candidates were withheld, and another 15 eligible candidates lack an adjudicable reference. The present name-to-charge and name-to-tautomer checks are deliberately broad, and the available evidence does not establish for each withheld case whether the source was genuinely ambiguous or the implementation was overbroad. Further local form remediation and independent assessment are required before recommending a deterministic-primary change. The existing provider requirement has not been removed.

## Audit and implementation

The pre-change [audit](deterministic_form_remediation/source_form_aggregation_audit.json) traces the pipeline and was recorded before code changes. Previously, the alias comparator recorded `PROTONATION_DIFFERENT` for 17504, but source-form aggregation only promoted an alias difference to a conflict when constitution differed. In addition, successful parsing supplied a generic `SUPPORTED` state for charge and tautomer dimensions, and the comprehensive alias evaluation occurred only after provider admission. The result could therefore be `SUPPORTED` despite the recorded protonation difference; the discrepancy was an ignored dimension combined with ordering and unjustified source specificity, not proof that the candidate was correct.

Now the conjunction of applicable source dimensions is checked explicitly: `DIFFERENT`/`CONFLICTING` yields conflict, `UNKNOWN` or unspecified applicable source support prevents full support, and equivalent or non-applicable dimensions do not block. Specific, parseable preferred-name/alias differences are propagated into their respective dimensions; broad or unparseable aliases do not automatically override the preferred claim. Alias comparisons, source identifiers and local form checks precede the provider gate. The diagnostic `DETERMINISTIC_LOCAL_EXACT_ELIGIBLE` is not itself final admission.

No neutral parent, salt stripping, charge normalization or tautomer parent is substituted. A name-only charged structure is held when source-supported charge placement is not established. The existing chemistry-general tautomer enumeration signal holds a name-only tautomer-sensitive candidate unless source specificity is established; parser success and Standard InChI agreement do not establish it. An explicit typed structure can establish an exact tautomer, subject to the other checks. The current implementation does **not** map explicit chemical-name locants or ionic wording to all affected atoms; therefore its broad `UNKNOWN` is a capability limit, not evidence that every held name is genuinely vague. Existing provider qualification, budgets, admission policy, schema and OPSIN were not changed.

## Regression probes

These full-resolver probes use the saved source claims and a stub that fails on any parser or provider call; see [probe results](deterministic_form_remediation/regression_probes.json). They are examples, not runtime exceptions.

| CUMA index | Local result | Evidence and limitation |
|---|---|---|
| 17504 | CONFLICT; not eligible | Candidate is an anion, while a specific parsed acid alias and the frozen independent reference are neutral. `PROTONATION_DIFFERENT` is now a conflicting dimension; charge and tautomer support are also unknown. |
| 4373 | UNRESOLVED; not eligible | `SOURCE_TAUTOMER_SPECIFICITY_UNKNOWN`; the preferred name and a more specific 1H alias are present. This rule does not yet prove whether the name or alias unambiguously establishes the candidate tautomer. |
| 30832 | CONFLICT; not eligible | `SOURCE_CONSTITUTION_CONFLICT` and `SOURCE_TAUTOMER_SPECIFICITY_UNKNOWN`. The saved parse of the 2-oxo alias has different connectivity from the 3-oxo candidate; that diagnostic is independent of tautomer standardization. The current layer does not independently settle the source-name tautomer semantics. |

## Frozen-cohort replay

The 224 previously complete deterministic interpretations were replayed with the saved preferred and alias claims, source profiles, official InChI outcomes, frozen adjudications and previously recorded provider evidence. No new provider queries were made. This is a replay of the current local helpers, **not** a fresh blinded evaluation or a full end-to-end replay of every row. Provider outcomes play no role in the local eligibility and precision calculation.

| Measure | Result |
|---|---:|
| Locally eligible / withheld | 117 / 107 |
| Previously confirmed correct retained / newly withheld | 102 / 81 of 183 |
| Previously confirmed incorrect locally eligible | 0 of 1 |
| Eligible without adjudicable correctness reference | 15 |
| Local precision, adjudicable eligible | 102/102 = 100%; exact binomial 95% CI 96.45%–100% |
| Local recall, all reference-confirmed identities | 102/225 = 45.33%; exact binomial 95% CI 38.71%–52.08% |

These intervals describe binomial uncertainty and do not correct for cohort selection, non-random sampling or missing adjudications. The precision denominator excludes the 15 unadjudicable eligible cases. The recall denominator is the 225 frozen reference-confirmed identities, including cases outside the 224 complete-interpretation cohort.

Each held candidate, including each of the 81 previously correct cases, has its identity, reason codes, primary blocker and case-specific saved dimension evidence in [newly_blocked_cases.json](deterministic_form_remediation/newly_blocked_cases.json); the complete classifications are in [deterministic_form_replay.json](deterministic_form_remediation/deterministic_form_replay.json). Primary categories use precedence when multiple reasons apply:

| Primary blocker | All 107 held | Of 81 previously correct |
|---|---:|---:|
| Tautomer specificity | 56 | 41 |
| Alias conflict | 26 | 18 |
| Charge / protonation | 25 | 22 |
| Stereo, components, stoichiometry, other as primary blocker | 0 | 0 |

The reason attached to each row identifies the implemented rule; it does not establish whether that hold is chemically necessary. The 41 tautomer-primary correct cases have a potentially overbroad structural signal with no general name-to-tautomer mapping. The charge-primary cases include unverified named charge placement and/or a parsed alias disagreement; alias-primary cases include parser-supported source conflicts whose semantics require individual review. The frozen records do **not** justify classifying all 81 individually as genuinely unresolved or as false holds. That requested case-by-case distinction remains incomplete and is a material limitation, not a reason to relax the guard automatically.

## Recorded external gate comparison

Among the 102 adjudicable, locally eligible candidates, compare the already recorded qualifying external-corroboration decision:

| Category | Count |
|---|---:|
| A: correct and corroborated | 7 |
| B: correct without qualifying corroboration | 95 |
| C: incorrect and blocked only by the gate | 0 |
| D: incorrect and corroborated | 0 |

The saved evidence shows no confirmed locally eligible error that the gate alone prevented in this cohort. This does not prove that external corroboration can never distinguish errors, and it does not establish correctness for the 15 unadjudicable eligible candidates. See [gate comparison](deterministic_form_remediation/post_remediation_gate_value.json). No deterministic-primary or secondary alias-enrichment policy was implemented. Any later enrichment must first establish an exact provider-record structural/form match, then validate aliases and retain their provider-record provenance; an alias cache hit proposes a candidate, not an identity.

## Tests and integrity

The complete retained root test suite plus the new source-form tests ran **195 tests: 195 passed, 0 failed**; see [test log](deterministic_form_remediation/suite.log). New tests cover the dimension invariant, specific and broad aliases, charge, unspecified and explicitly typed tautomers, ordering before providers and preservation of the existing gate.

The first suite run had three failures and three errors from older assumptions. The retrieval tests for identifier discovery, GSRS corroboration and stereo alternatives used tautomer-sensitive fixtures, so they now use non-tautomer-sensitive fixtures while retaining their original retrieval assertions. The Standard-InChI tautomer test now asserts the earlier local hold and absence of provider queries, instead of expecting a later provider-comparison trace. The protected-diamine stereo test still checks supported stereo but expects the separate tautomer hold. These changes reflect the requested ordering and form policy, rather than accepting an incorrect provider result.

All five historical cases remain non-EXACT in an offline rerun: 5684 sulfate/sulfite, 5997 and 23839 relative stereo, 30142 glucose form, and index 5 dithiazole all returned `UNRESOLVED`; details are in [historical_regressions.json](deterministic_form_remediation/historical_regressions.json).

[Integrity checks](deterministic_form_remediation/integrity_results.json) pass: ontology, identity framework, persistent schema, OPSIN artifact, provider adapters and capability profiles, provider-budget code, frozen reference files, input snapshots and frozen provider caches retain their recorded hashes. Only `source_form.py`, `resolver.py` and the two explained test files changed among frozen implementation files. The new workspace and report were scanned against the configured CompTox key without disclosing it; no occurrence was found. No registry data was altered. The affected runtime files contain none of the three example indices or molecule-specific strings.

FURTHER_LOCAL_FORM_REMEDIATION_REQUIRED
