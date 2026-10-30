# Second fresh form-aware holdout evaluation

**Safety failures were detected in the retrieval-expanded resolver.** In this 400-record fresh blinded holdout, 171 records were admitted: 166 reference-confirmed, 4 false-positive and 1 unverified. Adjudicable EXACT precision is **166/170 (97.65%)**. All four false-positive records fall in the 26 admissions inferred to require expanded retrieval. The primary next capability is **source-form interpretation before retrieval-assisted admission**, with strict abstention when the source does not establish the candidate’s specificity.

## Sampling and leakage controls

The frozen sample contains **400 previously unused CUMA records**, seed **2026102802**, from 50,293 eligible records after excluding 3,374 of 53,667 source records. This deliberately enriched capability sample does not estimate population prevalence.

Exclusions cover the original 300 records, first 360-record holdout, development/manual-review/contradiction examples, regression literals, exact preferred-name and known alias overlaps, and obvious duplicate source names. Source-only lexical selection never read current predicted outcomes. Full eligible IDs, exclusion names/indices, source workbook hash, implementation hashes and original sample packets were saved before adjudication. All existing registries and protected files remain unchanged.

| Candidate sampling category | Selected records (overlapping) |
| --- | --- |
| difficult | 25 |
| hydrate | 36 |
| isotope | 30 |
| out_of_scope | 25 |
| protonation_charge | 27 |
| salt | 54 |
| solvate | 21 |
| stereo | 51 |
| straightforward | 164 |
| tautomer | 32 |

There are 32 frozen lexical pair groups. These hints are not reference chemistry: some name transformations identify ordinary duplicates or constitutional differences rather than the hinted form. Actual reference forms and pair outcomes are reported below. Eligibility and exclusions were computed before the seeded draw, but their files were serialized with the sample freeze rather than separately timestamped before sampling. This procedural deviation is disclosed; all artifacts were frozen before adjudication. A narrow solvate-name pool was empty, so a source-only solvent/ratio pattern was broadened before freezing. That did not yield established fixed-solvate identities. The reference set has 17 isotope-tagged cases and no INVALID outcome; neither positional-isotopologue nor invalid-input performance is well powered.

## Adjudication and evidence independence

Three fresh agents with no inherited project conversation received only original indices, preferred names, aliases, the unchanged molecular identity framework and independent-investigation instructions. They were not given strata, expected gaps, resolver candidates or predictions. Access isolation was procedural on a shared filesystem, not an operating-system barrier. Every original alias occurrence was adjudicated before promotion decisions were available. A separate supplemental packet was excluded from holdout metrics.

References preserve explicit molecular forms and track URLs, queries, provider records, available lineage and uncertainty. Shared database records/mirrors are one lineage; database synonym membership or a shared Standard InChIKey alone cannot establish SAME. Independent public retrieval and name interpretation were combined with standalone RDKit validation and focused authoritative-reference investigation. A parser result alone was not sufficient. Strong evidence with uncertain upstream independence is identified as such.

The references are agent-adjudicated evidence judgments, not experimental measurements or an expert-panel certification. Standalone RDKit, public OPSIN and independently retrieved PubChem evidence were combined with focused regulatory, manufacturer and primary-literature checks. OPSIN/PubChem computational ancestry can overlap with the evaluated engine; upstream independence is often unknown. Some sources were available only as indexed excerpts, and reference-side transport retry histories are incomplete. These limitations and per-record lineage are preserved in each packet’s methodology and evidence cache.

Every reference packet was frozen and hashed before the single resolver execution. Independent QA checked record/alias coverage, strict full structures, generated InChI/InChIKey and required identity dimensions. No label was revised after unblinding to improve agreement. Reference UNRESOLVED due to insufficient evidence remains unverified; documented inherent ambiguity is assessed as nonadmissible.

## Overall results

| Metric | Result |
| --- | --- |
| Automatic EXACT | 171 |
| Adjudicable EXACT precision | 166/170 (97.65%) |
| Confirmed false-positive EXACT | 4 |
| Unverified EXACT admissions | 1 |
| Confirmed EXACT recall | 166/276 (60.14%) |
| Reference-EXACT records withheld | 110 |
| Correct-abstention precision | 101/211 (47.87%) |
| Correct-abstention recall | 101/105 (96.19%) |
| False merges / assessable coassigned pairs | 0/3 (0.00%) |
| Unassessed coassigned pairs | 1 |
| Abstention (all non-EXACT) | 229/400 (57.25%) |
| Five-status agreement | 250/400 (62.50%) |

| Status | Reference | Resolver |
| --- | --- | --- |
| EXACT | 276 | 171 |
| UNRESOLVED | 72 | 188 |
| CONFLICT | 4 | 19 |
| OUT_OF_SCOPE | 48 | 22 |
| INVALID | 0 | 0 |

Among non-admissions, 101 are supported abstentions, 110 withhold reference-confirmed identities, and 18 remain unassessable. Adjudicable precision excludes 1 inconclusive admissions; it is not a claim that all admissions were independently confirmed. The four failures represent three chemical patterns because 5997 and 23839 are duplicate source records. None is a mismatch against a frozen reference-EXACT graph: each is an unjustified choice from a conflicting or underspecified referent. All 48 reference out-of-scope records were withheld, although only 22 received the same OUT_OF_SCOPE status. The single unverified admission, 17356, found a full-key PubChem candidate unavailable to the blinded name-based investigation; it was not relabelled after unblinding.

Descriptive Wilson 95% intervals: admission precision 94.11%–99.08%; alias precision 98.16%–100.00%. These do not correct for enriched sampling, duplicate concepts or correlated reference evidence.

## Capability-specific results

| Frozen reference-form group | N | EXACT admissions | Admission precision | Confirmed recall | Abstention | Alias precision |
| --- | --- | --- | --- | --- | --- | --- |
| straightforward | 141 | 127 | 126/126 (100.00%) | 126/138 (91.30%) | 9.93% | 167/167 (100.00%) |
| stereo | 126 | 20 | 17/20 (85.00%) | 17/64 (26.56%) | 84.13% | 19/19 (100.00%) |
| isotope | 17 | 6 | 6/6 (100.00%) | 6/14 (42.86%) | 64.71% | 1/1 (100.00%) |
| protonation_charge | 90 | 7 | 5/7 (71.43%) | 5/54 (9.26%) | 92.22% | 7/7 (100.00%) |
| salt | 106 | 5 | 3/5 (60.00%) | 3/59 (5.08%) | 95.28% | 3/3 (100.00%) |
| hydrate | 37 | 1 | 0/1 (0.00%) | 0/15 (0.00%) | 97.30% | 0/0 (not assessable) |
| solvate | 1 | 0 | 0/0 (not assessable) | 0/0 (not assessable) | 100.00% | 0/0 (not assessable) |
| tautomer | 28 | 12 | 12/12 (100.00%) | 12/19 (63.16%) | 57.14% | 11/11 (100.00%) |
| multicomponent | 134 | 5 | 3/5 (60.00%) | 3/67 (4.48%) | 96.27% | 3/3 (100.00%) |
| out_of_scope | 48 | 0 | 0/0 (not assessable) | 0/0 (not assessable) | 100.00% | 0/0 (not assessable) |

Categories are nonexclusive blinded-adjudicator classifications, not sampling strata. Empty or small positive denominators cannot support broad conclusions. Ordinary molecules performed well (126/126 assessed admissions; 126/138 recall), while stereo-tagged admissions include three unsafe specificity choices. The sole hydrate admission is the glucose-form failure, so 0/1 is not evidence that hydration coefficients were lost. Fixed solvates have no established positive cases. Two frozen category annotations require caution: 5684 is a neutral cyclic sulfate/sulfite conflict, not an ionic salt/multicomponent case; 2219 is a solution. Raw grouped results are retained below; a separate post-unblinding sensitivity view and all methodological issues are explicitly documented, without changing reference labels or primary scores.

Diagnostic category-membership sensitivity, excluding the misclassified neutral cyclic compound 5684 only from the three affected form groups (all primary scores and labels above remain frozen):

| Form group | N | Admissions | Assessed precision | Confirmed recall | Abstention |
| --- | --- | --- | --- | --- | --- |
| protonation_charge | 89 | 6 | 5/6 (83.33%) | 5/54 (9.26%) | 83/89 (93.26%) |
| salt | 105 | 4 | 3/4 (75.00%) | 3/59 (5.08%) | 101/105 (96.19%) |
| multicomponent | 133 | 4 | 3/4 (75.00%) | 3/67 (4.48%) | 129/133 (96.99%) |

## Alias evaluation

All **1622 original alias occurrences** were labelled before predictions: 505 SAME, 269 DIFFERENT and 848 UNRESOLVED. The resolver promoted **212** claims: **205 confirmed correct, 0 confirmed incorrect, 7 unverified**. Adjudicable alias precision is **205/205 (100.00%)**. Preferred names stored as aliases are excluded from this promotion metric.

The assessable denominator increased to 205 from 24 in the first fresh holdout (29 in its later upgraded-resolver re-evaluation). However, all seven unverified promotions belong to false-positive subjects: one sulphite alias for 5684 and three relative-stereo aliases on each of 5997 and 23839. The frozen subject-conditional metric excludes them; 100% assessed precision therefore does not establish safety of all promoted aliases. There were 1,410 held alias occurrences, with no automatic promotion from source co-occurrence.

## Merge and near-form safety

| Frozen source-pair outcome | Count |
| --- | --- |
| BOTH_ADMITTED_DISTINCT | 8 |
| BOTH_WITHHELD | 14 |
| CORRECT_EXACT_CLUSTER | 3 |
| ONE_WITHHELD | 6 |
| UNASSESSED_COASSIGNMENT | 1 |

All coassignments were assessed separately: 4 pairs, 3 assessable and 1 unassessed. Independent reference graphs identify 6 exact-equivalent source pairs across the whole sample. Coassignment precision and exact-duplicate recovery are different questions; withholding both sides does not demonstrate successful exact matching.

| Reference-exact pair recovery across the whole sample | Count |
| --- | --- |
| BOTH_WITHHELD | 2 |
| CORRECT_EXACT_CLUSTER | 3 |
| ONE_WITHHELD | 1 |

Only 3 of 4 coassigned pairs have exact reference identities. The fourth, 5997/23839, repeats the unsafe assignment of one enantiomer to a relative-stereo referent; it is an unassessed merge pair, not evidence of correct clustering or a proven merge of different molecules. The six independently exact-equivalent pairs yielded three correct clusters, two both-withheld pairs and one one-withheld pair. Distinct admissions include D/L-arabinitol, dichloromethane/dichloromethane-d2 and five positional-isomer pairs. Specified/unspecified stereo pairs preserved abstention on the unspecified side. Parent/salt and meropenem/hydrate comparisons mainly withheld a member or both. No tested positive pairs establish safety for positional isotopologues, isolated charge-state variants, different fixed hydration numbers, fixed solvates/different solvents or explicit tautomer pairs. The frozen isotope-pair relation label is overly broad because of explicit-H handling; the molecular graphs and separate IDs correctly retain the isotope distinction.

| CUMA pair | Reference relation | Resolver outcome |
| --- | --- | --- |
| 32833 / 19423 | REFERENCE_NOT_FULLY_ASSESSABLE | BOTH_WITHHELD |
| 29645 / 12793 | EXACT_REFERENCE_IDENTITY | BOTH_WITHHELD |
| 52026 / 43546 | EXACT_REFERENCE_IDENTITY | CORRECT_EXACT_CLUSTER |
| 44168 / 14531 | REFERENCE_NOT_FULLY_ASSESSABLE | BOTH_WITHHELD |
| 5997 / 23839 | REFERENCE_NOT_FULLY_ASSESSABLE | UNASSESSED_COASSIGNMENT |
| 21069 / 559 | REFERENCE_NOT_FULLY_ASSESSABLE | ONE_WITHHELD |
| 48406 / 14492 | REFERENCE_NOT_FULLY_ASSESSABLE | ONE_WITHHELD |
| 30822 / 35012 | STEREOCHEMICAL_DIFFERENCE | ONE_WITHHELD |
| 38629 / 30226 | STEREOCHEMICAL_DIFFERENCE | BOTH_WITHHELD |
| 2305 / 38180 | STEREOCHEMICAL_DIFFERENCE | BOTH_ADMITTED_DISTINCT |
| 36042 / 19388 | EXACT_REFERENCE_IDENTITY | ONE_WITHHELD |
| 7855 / 13084 | EXACT_REFERENCE_IDENTITY | CORRECT_EXACT_CLUSTER |
| 26534 / 38628 | EXACT_REFERENCE_IDENTITY | CORRECT_EXACT_CLUSTER |
| 51083 / 45383 | CONSTITUTIONAL_OR_OTHER_FORM_DIFFERENCE | BOTH_ADMITTED_DISTINCT |
| 32058 / 44775 | REFERENCE_NOT_FULLY_ASSESSABLE | BOTH_WITHHELD |
| 7888 / 12258 | COMPONENT_OR_CHARGE_DIFFERENCE | ONE_WITHHELD |
| 4808 / 43207 | COMPONENT_OR_CHARGE_DIFFERENCE | ONE_WITHHELD |
| 406 / 40612 | REFERENCE_NOT_FULLY_ASSESSABLE | BOTH_WITHHELD |
| 52557 / 17341 | REFERENCE_NOT_FULLY_ASSESSABLE | BOTH_WITHHELD |
| 20308 / 11300 | COMPONENT_OR_CHARGE_DIFFERENCE | BOTH_WITHHELD |
| 45188 / 7839 | REFERENCE_NOT_FULLY_ASSESSABLE | BOTH_WITHHELD |
| 37169 / 41478 | REFERENCE_NOT_FULLY_ASSESSABLE | BOTH_WITHHELD |
| 37726 / 53087 | REFERENCE_NOT_FULLY_ASSESSABLE | BOTH_WITHHELD |
| 36781 / 30421 | REFERENCE_NOT_FULLY_ASSESSABLE | BOTH_WITHHELD |
| 52577 / 7464 | HYDRATION_NUMBER_DIFFERENCE | BOTH_WITHHELD |
| 44417 / 46190 | REFERENCE_NOT_FULLY_ASSESSABLE | BOTH_WITHHELD |
| 52446 / 20866 | DISTINCT_REFERENCE_IDENTITIES | BOTH_ADMITTED_DISTINCT |
| 26687 / 37617 | CONSTITUTIONAL_OR_OTHER_FORM_DIFFERENCE | BOTH_ADMITTED_DISTINCT |
| 19218 / 35068 | CONSTITUTIONAL_OR_OTHER_FORM_DIFFERENCE | BOTH_ADMITTED_DISTINCT |
| 15467 / 8482 | CONSTITUTIONAL_OR_OTHER_FORM_DIFFERENCE | BOTH_ADMITTED_DISTINCT |
| 12316 / 22616 | CONSTITUTIONAL_OR_OTHER_FORM_DIFFERENCE | BOTH_ADMITTED_DISTINCT |
| 24295 / 53293 | CONSTITUTIONAL_OR_OTHER_FORM_DIFFERENCE | BOTH_ADMITTED_DISTINCT |

## Evidence-retrieval generalization

Route use is distinguished from necessity. Older-path attribution uses saved original-name evidence and the documented old sufficiency conditions; it is a counterfactual inference, not a second resolver run. Ambiguous causal attribution is UNKNOWN. Different providers or multiple queries are not automatically independent evidence. The [per-admission retrieval appendix](second_form_aware_holdout/retrieval_admissions.md) records every admission, route, lineage, reference verdict and older-path inference.

| Supporting admission route | Used | Confirmed | Incorrect | Unverified | Older path inferred unresolved |
| --- | --- | --- | --- | --- | --- |
| full InChIKey | 14 | 12 | 1 | 1 | 14 |
| InChI/complete structure | 5 | 5 | 0 | 0 | 5 |
| validated original alias | 18 | 15 | 3 | 0 | 16 |
| GSRS | 11 | 11 | 0 | 0 | 9 |
| supplied identifier | 0 | 0 | 0 | 0 | 0 |
| validated provider name | 0 | 0 | 0 | 0 | 0 |

The trace-based older path was sufficient for 145 admissions, all reference-confirmed. The 26 inferred increment-dependent admissions comprise **21 correct, 4 incorrect and 1 unverified**: **21/25 (84.00%) adjudicable precision**. This shows useful generalization and a safety regression in the expanded admission routes; the counterfactual was not verified by another resolver run. Full-key retrieval supported the glucose-form error; validated-original-alias recovery supported the sulphate/sulphite and two relative-stereo errors. GSRS-supported admissions were 11/11 correct and complete-structure-supported admissions 5/5, with overlapping small denominators. Supplied-identifier lookup was not exercised; alternative validated provider names were queried 30 times but supported no admission. Three correct admissions (9636, 23002, 48151) explicitly rejected distinct full-key discoveries as noncorroborating; these demonstrate safe related-form filtering, not source-intent validation. Nineteen records ended CONFLICT, but none of the four unsafe admissions exposed its source-level problem as a blocking contradiction.

| Provider | HTTP requests / budget | Observed cache hits | Cached request failures |
| --- | --- | --- | --- |
| PubChem | 555 / 2400 | 17 | 96 |
| ChEBI | 527 / 4000 | 20 | 256 |
| GSRS | 106 / 800 | 3 | 0 |

Runtime caches started empty and remained separate from adjudicator caches. Cache hits are reconstructed from repeated recorded URLs, excluding in-memory query deduplication; detailed HTTP failures, request utilization and query modes are preserved in `provider_usage.json`. No budgets, routes, adapters or retries were changed after outcomes. The single run completed successfully in about 28 minutes 25 seconds. Requests used 23.13% of the PubChem budget, 13.18% of ChEBI and 13.25% of GSRS; no budget was exhausted. All 352 cached HTTP failures were 404/not-found responses, with no recorded transport failures. Successful HTTP responses can still contain no candidate or rejected evidence. The new evaluation snapshot contains 167 Substance identities for 171 EXACT reconciliations, four multi-record clusters and 372 stored aliases including preferred names. Existing verify.py revalidated all 171 admissions and found zero duplicate/orphan violations; this tests internal consistency, not chemical correctness.

## Complete disagreement taxonomy

| Dominant cause | Substantive disagreements | Confirmed identities withheld |
| --- | --- | --- |
| salt semantics | 25 | 25 |
| stereo source intent | 23 | 21 |
| parser failure and retrieval incomplete | 22 | 17 |
| unresolved identity dimension | 21 | 7 |
| provider disagreement | 15 | 9 |
| coordination/electronic-state unsupported | 9 | 7 |
| stereo interpretation | 9 | 8 |
| parser warning | 5 | 3 |
| evidence dependence/provenance | 4 | 3 |
| extended material unsupported | 4 | 4 |
| unsafe admission | 4 | 0 |
| hydration stoichiometry | 3 | 3 |
| tautomer conflict | 3 | 1 |
| isotope position unknown | 2 | 2 |
| reference uncertainty | 1 | 0 |

Every disagreement has a case-level classification, expected/predicted result, resolver reason and reference evidence in [the complete disagreement appendix](second_form_aware_holdout/disagreements.md). Attribution records dominant observed gates; a gate can conceal a second limitation. Confirmed errors, unverified predictions, conservative abstentions and reference uncertainty remain separate. The 150 classified items comprise 110 withheld reference-EXACT records, 31 non-admission status disagreements, four reference-uncertainty disagreements, four false-positive admissions and one unverified admission. The table preserves the frozen dominant-gate taxonomy. Detailed safety attribution appears separately below: relative/absolute stereo (2 records), source constitutional conflict (1), sugar-form source intent (1). At least two of the eight stereo-gate losses, 15032 and 44468, have documented topology-related false potential-stereo flags. A no-candidate result does not imply that the reference identity is invalid. Counts are records, not guaranteed recoverable identities or independent chemical examples.

### Confirmed unsafe admissions

| CUMA / preferred name | Blinded reference → resolver | Retrieval route | Specific cause |
| --- | --- | --- | --- |
| 5684 / 1,1-Cyclopropane dimethanol cyclic sulphate | CONFLICT → EXACT | validated original alias | Source-name constitutional conflict during alias-assisted recovery. The preferred sulphate claim requires two S=O groups. The accepted sulphite graph has one. A misleading PubChem/supplier name hit and a valid sulphite alias corroborated that different candidate, without resolving which source referent was intended. |
| 5997 / 1-N-BOC-1,2-TRANS-CYCLOHEXYLDIAMINE | UNRESOLVED → EXACT | validated original alias | Relative stereochemistry treated as absolute configuration. The trans-1,2 preferred name and the alias used for local support specify relative configuration, not the RR/SS choice. The record also contains an RR alias, but its association with the broad preferred referent was not independently established; the engine itself did not promote that RR alias. Frozen reference remains inherently ambiguous. |
| 23839 / 1-N-BOC-1,2-TRANS-CYCLOHEXYLDIAMINE | UNRESOLVED → EXACT | validated original alias | Relative stereochemistry treated as absolute configuration. Duplicate source concept of 5997, assigned the same RR graph and Substance ID through the same relative-name alias route. It is a second erroneous record, not a second independent chemical failure pattern. |
| 30142 / D-glucose 6-phosphate disodiumsalt dihydrate | UNRESOLVED → EXACT | full InChIKey | Source sugar-form ambiguity hidden by a fully specified candidate graph. OPSIN selected the open-chain D-glucose-6-phosphate graph. A full-key lookup corroborated that graph but did not establish open-chain rather than cyclic/anomeric source intent. Sodium and water counts were preserved; this is not salt stripping or loss of hydration. |

### Evaluation limitations found during review

These are separate annotations, not changes to reference outcomes, original form tags, comparison logic or frozen metrics.

| Case(s) | Issue | Effect on interpretation |
| --- | --- | --- |
| 24920 | Pre-identified sulfinate resonance-enumeration limitation | No effect on admission precision or merges in this run: the record was UNRESOLVED with NO_VALIDATED_CANDIDATE. All 166 reference-EXACT admissions match their frozen full graphs; no graph mismatch was counted as an error. |
| 5684 | Frozen form-category metadata incorrectly tags a neutral cyclic sulfate/sulfite conflict as salt, protonation_charge and multicomponent | Overall verdict and primary metrics are unchanged. Raw grouped precision contains this category error. A clearly labelled sensitivity view excluding this membership gives salt 3/4, protonation_charge 5/6 and multicomponent 3/4; it is not a reference relabeling. |
| 2219 | The sole frozen solvate tag is a solution/mixture, not a fixed molecular solvate | There is no established fixed-solvate positive denominator. The frozen OUT_OF_SCOPE reference and CONFLICT prediction remain unchanged. |
| [51083, 45383] | Pair diagnostic calls dichloromethane-d2 versus dichloromethane CONSTITUTIONAL_OR_OTHER_FORM_DIFFERENCE | Explicit deuterium becomes explicit hydrogen in the diagnostic isotope-removal view, while the other graph uses implicit hydrogen. Frozen graphs directly establish an isotope difference. Exact comparison correctly kept both admitted forms distinct; no merge or outcome metric changes. |
| [5684, 5997, 23839] | Alias precision is conditional on an assessable exact subject | All seven unverified promoted aliases belong to false-positive subjects. One is DIFFERENT from the literal preferred sulphate claim; six are relative-stereo names. The 205/205 assessed result must not be presented as validation of all 212 promotions. |

## Supplemental independent review — excluded from holdout metrics

| CUMA | Independent review | Reason / key evidence |
| --- | --- | --- |
| 9152 | confirmed correct | The ACS primary synthesis identifies the resolved (2S) Cbz-protected azetidine/Boc-protected piperidine alcohol as compound 29 (SI pages 11–12), separately from its (2R) enantiomer. The intact OPSIN graph has both carbamates, the 3-hydroxyazetidine linkage and one S piperidine stereocentre. PubChem name miss is not a chemical ambiguity. [ACS Medicinal Chemistry Letters supporting information](https://pstorage-acs-6854636.s3.amazonaws.com/4166524/ml300049d_si_001.pdf) |
| 46724 | confirmed correct | The original (3S) descriptor belongs to the benzodiazepine stereocentre, as established by the primary patent preparation of compound D. Both independently parsed complete systematic names produce the same S lactam methyl propionate graph. A PubChem alias hit lacks stereochemistry and is retained only as a related unspecified candidate, not used to erase S. [WIPO patent via Google Patents](https://patents.google.com/patent/WO2019020790A1/en); [Japan MHLW chemical announcement](https://anzeninfo.mhlw.go.jp/kag_det/kag_116130.html) |
| 52217 | contradicted | Conflicting chemical intent: the literal preferred name parses to an unlabeled N-phenyl nitrosotosylamide (C13 framework), while every substantive alias specifies N-methyl-d3 Diazald (C8 framework). Manufacturer isotope-reference material confirms the latter structure. The public marketplace hit for the preferred name itself mixes the N-phenyl heading with methyl-d3 CAS/details. No authoritative evidence resolves which referent this source intended; do not silently substitute methyl-d3 or admit parser-only phenyl structure. [CDN Isotopes / Fisher product record](https://www.fishersci.co.uk/shop/products/n-methyl-d3-n-nitroso-p-toluenesulfonamide-cdn-2/30310445); [Guidechem marketplace](https://www.guidechem.com/trade/n-phenyl-n-nitroso-p-toluenesu-id4487198.html) |

9152 and 46724 match independently established stereodefined structures supported by primary synthetic/patent evidence. 52217 is contradicted as an admissible source-to-identity assignment: the literal N-phenyl preferred name conflicts with substantive N-methyl-d3 aliases and inconsistent marketplace metadata. This does not prove that the literal N-phenyl graph itself is chemically impossible. No supplemental result enters the 400-record metrics, and no earlier reference file was changed.

## Ranked remaining capabilities and ontology disposition

This ranking was made only after metrics and disagreements were frozen. Confirmed identity losses inform it alongside safety, deterministic feasibility, cross-source applicability, scope and policy implications.

| Rank / capability | Confirmed losses | Safety and feasibility; policy boundary |
| --- | --- | --- |
| 1. Source-form interpretation before retrieval-assisted admission | 21 at the source-intent gate; 4 unsafe admissions (3 chemical patterns) | Safety first: all four new errors and supplemental 52217 concern source intent that a valid retrieved graph cannot settle. The 21 withheld source-intent cases show the opposite, conservative failure mode; they are opportunities, not a recovery promise. Deterministic relative/absolute-stereo, sugar-form and conflicting-name checks can improve this within the existing molecular scope. Reusable for CUMA, CosIng and future sources; implementation change, not relaxed identity policy. |
| 2. Defined salt and multicomponent semantics, including fixed hydration ratios | 25 salt-gate losses + 3 hydration-gate losses | Frequent across unseen names and useful across sources, but an admission expansion would amplify the source-intent risk unless the first capability is addressed. Complete ionic components, proton state and integer ratios offer bounded deterministic checks. Limit to established molecular/composition scope; no automatic acid/base transfer, parent selection or ontology change. |
| 3. Reliable interpretation of potential stereogenic elements | 8 stereo-gate losses; at least 2 documented cage false flags | CUMA 15032 and 44468 establish topology-constrained cage flags; the other six require individual analysis. High risk if a blanket stereo exemption is used. Topology-aware, separately validated treatment is deterministic and source-independent. Identity policy already distinguishes real configuration from representation; no ontology change. |
| 4. Strict handling of difficult nomenclature and parser warnings | 17 no-candidate losses + 3 warning-gate losses | Common across index-style names, markup and malformed spacing; broadly reusable. Conservative typed preprocessing and bounded warning interpretation are implementable, but parser success still cannot prove source intent. No generated aliases or semantic rewriting; within current scope and policy. |
| 5. Provider-conflict and evidence-lineage attribution | 9 provider-conflict losses + 3 lineage-gate losses | False locants, proton states, covalent hydration and correlated sources require discrimination. Provenance and structured contradiction checks are reusable, but a provider majority or more URLs is not evidence independence. Preserve abstention until conflict is explained; no scope or ontology change. |
| 6. Interpret unresolved identity-dimension diagnostics | 7 dominant UNKNOWN-dimension losses | A heterogeneous group including stereo and tautomer issues. Frequency alone does not identify a safe general repair. Improve evidence-level diagnosis before expanding admissions; broadly useful but implementability depends on the specific dimension. Existing semantics can represent the distinctions. |
| 7. Isotope notation and position interpretation | 2 records of the same carbon-13 dioxide concept | A small, duplicated denominator rather than two independent chemical failures. A bounded notation fix is deterministic and within policy; useful for isotope reagents across sources but less central to typical CosIng inputs. Six isotope admissions were correct; positional-isotopologue pair coverage remains absent. |
| 8. Explicit tautomer evidence reconciliation | 1 dominant tautomer-conflict loss | Preserve hydrogen/bond placement when a provider standardizes to another tautomer. Generalizable and within policy, but no paired-tautomer positive denominator here. Twelve adjudicable tautomer-tagged admissions were correct; avoid key-only or parent-tautomer equivalence. |
| 9. Coordination and inorganic validator scope | 7 coordination/electronic-state + 4 extended-material gate losses | Some references establish composition rather than a discrete molecular graph. These losses do not authorize crossing the bounded validator scope. Deterministic support needs domain-specific coordination/electronic-state validation and explicit scope review; applicable to some future material sources, less broadly to molecular CosIng. Parser/provider limitations are not ontology deficiencies. |

**One primary next capability: Source-form interpretation before retrieval-assisted admission.** Require evidence that the original referent supports the chosen constitution and form specificity, separately from proving that a candidate graph exists and parses. In particular, relative stereo must not become absolute through parser defaults, sugar ring/anomer scope must not be inferred from a retrieved open-chain graph, and a validated alias must not repair an unresolved preferred-name conflict. Implement bounded deterministic checks and preserve abstention outside their support. Do not treat every bad alias as a record-level veto; the question is whether the preferred referent itself is established. This is the next development recommendation only; no resolver change was made in this evaluation.

**No ontology modification is justified by this holdout.** Existing Substance/MolecularSubstance, Alias, Identifier and Structure semantics already distinguish real chemical forms, representational equivalence and unsupported source claims. The failures concern implementation of source intent and evidence scope. Unsupported salt, coordination or solid-state validation does not establish an unrepresentable recurring semantic distinction. No relationship schema or full-CUMA canonicalization is recommended.

## Reproducibility and integrity

The audit package contains [sample/exclusion hashes](second_form_aware_holdout/SAMPLE_FROZEN.json), [frozen adjudication](second_form_aware_holdout/ADJUDICATION_FROZEN.json), [frozen metrics](second_form_aware_holdout/METRICS_FROZEN.json), [retrieval attribution](second_form_aware_holdout/retrieval_routes.json), [provider usage](second_form_aware_holdout/provider_usage.json), [alias comparison](second_form_aware_holdout/alias_comparison.json), [supplemental evidence](second_form_aware_holdout/supplemental_review.json), [post-unblinding methodological review](second_form_aware_holdout/POST_UNBLINDING_REVIEW.json), [ranked assessment](second_form_aware_holdout/ASSESSMENT.json) and [final verification](second_form_aware_holdout/FINAL_VERIFICATION.json). Registry output is a separate evaluation snapshot. No full CUMA canonicalization was performed or recommended.

**RESOLVER_SAFETY_REGRESSION_DETECTED**
