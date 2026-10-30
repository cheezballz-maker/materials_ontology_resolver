# Nomenclature semantics refinement

## Outcome

No admission-changing nomenclature rule was sufficiently grounded and mapped to the candidate structure in this phase. The new [indicated-hydrogen diagnostic](nomenclature_refinement/semantic_diagnostics.py) records possible numbered-H tokens and spans, with fragment ownership and candidate atom explicitly **unverified**. It is not connected to resolver admission. Consequently **0 of the 81 previously confirmed-correct candidates were recovered; all 81 remain withheld**. This does not satisfy the requested goal of refining the broad admission behavior; the limitation is deliberate rather than evidence that those source names are all ambiguous.

The 81 cases are a diagnostic development set, not a fresh validation set. “Confirmed correct” means the saved candidate matched the independently assessed reference; it does **not** independently establish that every preferred name and alias in that source record uniquely asserts that form. No CUMA name or index was encoded in the diagnostic rule, and no provider lookup was made for the replay.

## Taxonomy and evidence

The [81-row taxonomy](NOMENCLATURE_FALSE_HOLD_TAXONOMY.json) was created before implementation. Every record includes its original preferred name, aliases and saved parse comparisons, blocker and other reasons, candidate, reference structure, suspected patterns, and any recorded source-claim conflicts. Alias strength labels describe the saved parser observations, not adjudicated source semantics. Each record retains an explicit uncertainty about source specificity and the independent mapping or review needed; the requested case-by-case determination of genuinely ambiguous versus overly broad holds is **not complete**.

| Primary blocker | Cases | Diagnostic interpretation |
|---|---:|---|
| Tautomer specificity | 41 | Alternative tautomer graphs triggered a global hold. A source may specify a particular graph; the existing implementation does not map all of the relevant name grammar and atoms. |
| Charge / protonation | 22 | Includes charged atom representations of otherwise neutral nitro-containing graphs, and conflicts with acid/base aliases. Formal atom charge alone is not a source-supported protonation statement. |
| Alias conflict | 18 | The saved parser frequently reports constitutional differences. Each requires a claim-scope assessment; a matching preferred-name reference does not automatically disprove a specific contradictory alias. |

Exploratory name-pattern tags overlap and do not prove nomenclature semantics: 29 heterocycle contexts, 19 carbonyl/oxo contexts, 17 acid/derivative contexts, 17 nitro contexts, 8 possible indicated-H tokens, 11 hydroxy contexts and 6 amide/imide contexts. The exact tag predicates and record-level evidence are in the taxonomy generator. These counts are not estimates of how many cases can safely be admitted.

## Grounding and capability decisions

The full [capability assessment](nomenclature_capability_assessment.json) records the construct, authoritative reference, observable, independent examples, result and limitations. The only implemented capability is lexical observation; it produces no `SPECIFIED` tautomer state or eligibility. The [implemented-rule record](implemented_semantic_rules.json) is explicit about that boundary.

| Capability | Assessment | Evidence and boundary |
|---|---|---|
| Possible indicated-H token observation | READY_TO_IMPLEMENT, diagnostic only | [IUPAC Blue Book P-14.7](https://iupac.qmul.ac.uk/BlueBook/P1.html) distinguishes indicated H from added indicated H. Non-development examples `1H-pyrrole` and `3H-pyrrole` show different positions. A token does not by itself prove fragment ownership, atom mapping, isotope meaning, or that all mobile-H sites are fixed. |
| Name-to-atom indicated-H and complete tautomer support | TOO_COMPLEX_FOR_CURRENT_RESOLVER | The same Blue Book section and [IUPAC indicated hydrogen definition](https://goldbook.iupac.org/terms/view/I03004) support the semantics; the current locant mapping does not generally establish grammatical fragment ownership. Multiple tautomerizable sites remain possible. |
| Functional-group / keto–enol specificity | NEEDS_MORE_GROUNDING | [IUPAC tautomerism](https://goldbook.iupac.org/terms/view/T06252) distinguishes interconvertible structures. Independent examples `propan-2-one` and `prop-1-en-2-ol` demonstrate a keto/enol distinction, but simple suffix matching cannot establish complete source scope and hydrogen mapping. |
| Ionic suffixes and counterions | NEEDS_MORE_GROUNDING | [Blue Book P-7](https://iupac.qmul.ac.uk/BlueBook/P7.html) defines ionic nomenclature in grammatical context. `tetramethylammonium chloride` and `sodium ethanoate` illustrate different ionic forms; suffix substring matching alone does not prove center, components or stoichiometry. |
| Nitro resonance versus protonation | NEEDS_MORE_GROUNDING | [IUPAC nitro compounds](https://goldbook.iupac.org/terms/view/N04158) defines the group. `nitrobenzene` and `1-nitropropane` illustrate its use. Identifying one nitro group does not prove that the rest of a named molecule contains no separate ionic or protonation claim. |
| Dimension-specific alias dominance | NEEDS_MORE_GROUNDING | [IUPAC stereoisomers](https://goldbook.iupac.org/terms/view/S05984) distinguishes spatial configurations. `butan-2-ol` versus `(R)-butan-2-ol` illustrates a potentially less-specific alias; `(R)-butan-2-ol` versus `(S)-butan-2-ol` illustrates a specific difference. The existing coarse broad-alias handling remains in force; this phase did not infer alias scope solely from a parsed graph. |

The diagnostic recognizes numbered uppercase `H` tokens with source spans; it does not validate whether a token is ordinary indicated H, added H, an isotope, or belongs to a particular fragment. Its independent tests include `1H-pyrrole`, `3H-pyrrole`, a parenthesized token, missing notation and multiple unmapped tokens. A positive observation cannot establish candidate agreement; a conflict requires an independently mapped source constraint and remains unimplemented.

## Replay and safety

The [81-case replay](false_hold_replay.json) records each old blocker, unchanged outcome and reasons, candidate, reference comparison, and token observations. There are **0 newly eligible**, **81 still withheld**, **0 changed blockers**, and **0 new conflicts**. No recovery is asserted. A fresh replay of the 224 saved claims used the existing local helper and saved official InChI results, not providers; it is not an end-to-end rerun or a new independent holdout. The 183 confirmed-correct candidates remain **102 eligible / 81 withheld**.

| Local measure | Result |
|---|---:|
| Adjudicable eligible precision | 102/102 = 100%; exact 95% CI 96.45%–100% |
| Local recall against all frozen reference-confirmed identities | 102/225 = 45.33%; exact 95% CI 38.71%–52.08% |
| Eligible without an adjudicable reference | 15 |

The intervals do not correct for cohort selection or missing adjudications. The [metrics](refined_local_metrics.json) are unchanged because admission was unchanged.

Saved-claim full-resolver probes still withhold 17504 as `CONFLICT`, 4373 as `UNRESOLVED`, and 30832 as `CONFLICT`; the 17504 charge disagreement remains explicit. The offline historical rerun still withholds 5684, 5997, 23839, 30142 and the historical dithiazole case, all `UNRESOLVED`. See [probe](deterministic_form_remediation/regression_probes.json) and [historical](deterministic_form_remediation/historical_regressions.json) outputs.

## External gate and recommendation

Among adjudicable locally eligible cases, the unchanged [A/B/C/D comparison](post_refinement_gate_value.json) is **7 / 95 / 0 / 0** respectively. Thus the saved cohort contains no confirmed incorrect locally eligible candidate blocked only by the gate, and no provider actively detected such an error. In the earlier analysis, the gate withheld the known 17504 error because no qualifying provider result was available; it did **not** identify the chemical error. The remediated local checks now withhold that case. These observations do not prove that a provider can never detect another error or establish correctness for the 15 unadjudicable eligible cases.

There is no demonstrated chemical-error-detection benefit from mandatory corroboration **in this remediated cohort**. However, zero recoveries, unresolved source-to-atom semantics and the limited conditional reference evidence do not justify implementing deterministic-primary resolution yet. Prioritize general source/fragment ownership and atom mapping, complete tautomer-site reasoning, and independently reviewed alias claim strength; validate on a separate holdout before changing the gate.

## Tests and integrity

The full retained suite plus four diagnostic tests ran **199 tests: 199 passed, 0 failed**; see [test log](nomenclature_refinement/suite.log). There were no test-expectation changes in this phase. [Integrity checks](nomenclature_refinement/integrity_results.json) verify the original ontology, schema, OPSIN artifact, provider adapters and capability profiles, budget-related implementation, frozen evaluation inputs and provider caches against the earlier freeze. Resolver admission code was unchanged during this phase. The new outputs were scanned against the configured credential without disclosing it, and no occurrence was found. No registry or external alias-enrichment table was changed.

FURTHER_NOMENCLATURE_CAPABILITY_REQUIRED
