# ChargeDimensionEvidence v1

## Executive conclusion

The isolated implementation now separates candidate charge observations from source-supported assertions, enforces complete source/alias context for neutral-nitro evidence, and has a functioning default-off consumer. A closed independent control changes the actual source-form charge dimension from `UNKNOWN` to `SUPPORTED` and becomes locally eligible in the isolated test. An additional tautomer obligation or established source conflict survives consumption.

The frozen 224-record replay shows **zero cohort dimension or eligibility gains**. One record gains neutral-nitro operation support; its unsupported alias claims prevent whole-charge closure. Correct eligible/withheld counts remain **102/81**, incorrect eligible remains zero and unadjudicable eligible remains 15. No canonical admission was performed.

The verdict is **partial**. Source-derived v1 charge evidence produces `SUPPORTED` or `UNKNOWN`; source-level ionic contradiction semantics and `NOT_APPLICABLE` proof are not implemented. The separate attribution comparator demonstrates valid structural `DIFFERENT` results, but that must not be represented as source-derived negative evidence. The controls and all changes remain provisional pending qualified chemical review.

## Root cause and conceptual model

`form_characterizer` records formal charges, net charge, H distribution and supported resonance views as candidate properties. In production `source_form.assess`, a nonempty `charge_distribution` makes charge/protonation relevant; when the source is not an explicitly typed structure, the guard sets `SOURCE_PROTONATION_SPECIFICITY_UNKNOWN`. It does not consume the independently scoped NSC-002 operation result. That explains why a neutral nitro representation can trigger a whole-source protonation hold.

The production identity comparator also defines charge equality through net charge, total H and graph-dependent charge views. For ethanol versus dimethyl ether, those views differ because constitution differs; the old comparator therefore emits `PROTONATION_DIFFERENT` despite there being no demonstrated protonation relationship. Its global `DISTINCT` is correct.

Formal charge belongs to individual atoms in a representation; net charge belongs to a defined component; resonance equivalence preserves the chemically defined species; protonation concerns H/proton attachment and location; source specificity concerns what the original claims establish. Neither formal atom charges nor net zero supply the last two. [IUPAC Blue Book P-7](https://iupac.qmul.ac.uk/BlueBook/P7.html) distinguishes ionic and zwitterionic nomenclature, and [P-74.2.2.1.10](https://iupac.qmul.ac.uk/BlueBook/P7.html#P-74.2.2.1.10) specifically names nitro compounds using the traditional R–NO2 structure. The [characteristic-group prefix table](https://iupac.qmul.ac.uk/BlueBook/P5.html) provides the naming basis; NSC-002 supplies the already frozen source grammar and structural boundary. These authorities establish rules, not expert approval of this implementation.

## Typed evidence and provenance

[ChargeDimensionEvidence](charge_dimension_evidence/charge_evidence_models.py) and its [JSON Schema](charge_dimension_evidence/charge_evidence_schema.json) contain evidence/version IDs, source claim and rule links, semantic owner, original text/spans, source scope, candidate correspondence, structural observations, relevant sites, site coverage, unresolved dependencies, source assertions, operation/dimension results and reason codes. The model validates schema shape, source text spans, assertion references and the proof prerequisites for `SUPPORTED`. The consumer also binds evidence to the original source-name/alias list and canonical candidate graph. This is an internally produced diagnostic evidence object, not a cryptographic attestation or a parser-independent proof verifier.

Candidate observations include formal atomic charges, net component charges, H distribution, N-attached nitro motifs and the complete candidate-envelope check. They are labelled structurally derived. Source assertions come from complete NSC-002 interpretations with typed claim links; they are labelled nomenclature-established. No observation is promoted into a missing source claim.

The schema allows `SUPPORTED`, `DIFFERENT`, `UNKNOWN` and `NOT_APPLICABLE`. The current bounded evidence producer only establishes the first and third. The other values are reserved for separately validated source semantics. In particular, net neutrality never causes `NOT_APPLICABLE`.

## Neutral-nitro scope and site closure

[Source-context closure](charge_dimension_evidence/source_context_closure.py) reuses the unchanged NSC-002 full-name grammar: explicitly locanted halo/nitro substitutions on one neutral benzene parent, with supported multiplicities, no additional functional groups or source operations, and at least one nitro substituent. Each supplied alias must independently fit that grammar and agree with the same complete candidate pattern. Failed, incomplete, differently scoped or incompatible aliases create unresolved dependencies. Their parser failure is not treated as evidence that they are broad.

[Candidate observations](charge_dimension_evidence/neutral_nitro_semantics.py) reuse NSC-002's structural envelope, requiring N attachment, the two-O nitro connectivity, the validated charge/bond pattern, neutral group composition, a single component and full structure consumption. Nitro oxygen ordering and valid Kekulé/aromatic depictions correspond under the existing graph comparison. Nitroso, nitrite/nitrate ester, extra components, independent protonated sites and unrecognized surrounding chemistry abstain. No general salt, acid/base or zwitterion interpreter was added.

Group operation support requires the preferred source operation and candidate pattern to agree. Whole charge-dimension support additionally requires closure of every supplied source claim, all relevant sites and candidate context. Thus a supported nitro operation with an incomplete alias remains charge `UNKNOWN`. Nitrobenzoic acid and nitroaniline are outside the complete source grammar; their other acid/base sites are not silently excluded. These are conservative implementation boundaries, not findings that those names are chemically ambiguous.

## Attribution correction

The [diagnostic comparator wrapper](charge_dimension_evidence/charge_comparison_attribution.py) leaves production comparison unchanged. It checks a common heavy-atom framework, enumerated framework correspondences and the relationship between total H and net-charge changes before retaining a protonation attribution. With incompatible framework, or a hydrogenation change without a proton-charge basis, it reports `UNKNOWN`/`PROTONATION_NOT_COMPARABLE` while retaining the original global constitutional distinction. No source specificity is asserted by this structural comparator.

Seven frozen structural controls passed: ethanol/dimethyl ether yields constitutionally `DISTINCT` with protonation `UNKNOWN`; benzoic acid/benzoate, nitroaniline/protonated nitroaniline and nitrobenzoic acid/nitrobenzoate retain `DIFFERENT`; neutral/zwitterionic glycine retains distinct charge/H-site structure without claiming that the name “glycine” selects either source form; nitro representation equivalents remain `EQUIVALENT`; benzene/cyclohexane is not called a pure protonation difference. This is a bounded dependency/attribution correction, not a general validated proton-transfer mechanism detector. It is evaluated separately and is **not substituted into the cohort's production alias comparisons**, so no existing source conflict is cleared by this experiment.

## Frozen controls and results

[Controls and chemical scope](charge_dimension_evidence/controls/benchmark_freeze.json) were frozen before implementation. They are independently rule-based specifications, not generated from the cohort reference candidates. Review is `CHEMICAL_REVIEW_PENDING`; automated checks are not qualified human adjudication. The public held-out set is frozen but not blind. No independently adjudicated blinded set was available.

| Layer | Cases | Result |
|---|---:|---|
| Source/evidence development controls | 11 | 11 expected operation and dimension outcomes matched |
| Public frozen held-out controls | 3 | 3 matched |
| Structural attribution/contradiction controls | 7 | 7 matched |

The development source cases include two fully closed neutral-nitro positives; acid-containing and amino-containing unknown contexts; glycine; an unresolved alias; extra components; nitroso, nitrite and nitrate functionality; and a specifically incompatible alias. The held-out cases use another ring-substitution pattern, an incomplete alias and an extra charged component. Detailed evidence and expected/actual outcomes are retained in [development results](charge_dimension_evidence/evaluation/development_results.json), [held-out results](charge_dimension_evidence/evaluation/heldout_results.json) and [attribution results](charge_dimension_evidence/evaluation/comparator_attribution_results.json). Source-level negative charge proof remains a declared v1 limitation, rather than relabelling an outside-envelope structure as a proven protonation contradiction.

## Functioning default-off consumer

[The consumer](charge_dimension_evidence/diagnostic_evidence_consumer.py) is separately executable, defaults to disabled and cannot create IDs or call providers. When enabled it can replace only `SOURCE_PROTONATION_SPECIFICITY_UNKNOWN`, and only when the evidence proves `SUPPORTED` with source/candidate binding and closure. It changes the one charge dimension and recomputes the existing dimension conjunction; every unrelated reason and dimension remains. Established charge `DIFFERENT`, constitution conflict, alias conflict and tautomer uncertainty cannot be overwritten.

[Consumer-control evidence](charge_dimension_evidence/evaluation/consumer_control_results.json) demonstrates an actual current-source-form transition, not a mocked eligibility flag: `1-chloro-2-nitrobenzene` with a matching structure and no additional claims is initially held by the charge guard. The disabled consumer retains it; the enabled consumer satisfies that dimension and yields isolated local eligibility. Further tests retain an independent tautomer blocker, a real meta/ortho alias constitution conflict and an established charge contradiction. These are independent controls, not CUMA recoveries or final Substance admission.

## Frozen cohort before and after

The saved-evidence local helper reproduced the same 224-record population and historical reference labels. The older 225-reference-exact denominator is retained only in the original helper output and is not used as this cohort denominator.

| Measure | Before | Enabled diagnostic consumer |
|---|---:|---:|
| Correct locally eligible | 102 | 102 |
| Correct withheld | 81 | 81 |
| Incorrect locally eligible | 0 | 0 |
| Unadjudicable locally eligible | 15 | 15 |
| Source-form `SUPPORTED` | 117 | 117 |
| Source-form `UNRESOLVED` | 71 | 71 |
| Source-form `CONFLICT` | 36 | 36 |
| Newly created/suppressed conflicts | — | 0 / 0 |

The evaluation **is connected**: all 224 records were assessed with flag off and on, evidence binding and the real consumer. There were no consumed cohort proofs and therefore no dimension or local-eligibility changes. Final canonical admission was not performed. All source claims, evidence, remaining blockers, reference status and before/after dimensions are in [local_eligibility_before_after.json](charge_dimension_evidence/evaluation/local_eligibility_before_after.json).

## The sixteen neutral-nitro opportunities

There are 16 structural opportunities, 12 with only the source-protonation reason and four with additional current obligations. Complete record/source-context support: **0**. Group operation `SUPPORTED`: **1**. Whole charge dimension `SUPPORTED`: **0**. Local eligibility gained: **0**. All sixteen remain unresolved for source specificity or additional reasons.

| CUMA index | Operation | Whole charge dimension | Principal v1 boundary |
|---:|---|---|---|
| 8165 | `UNKNOWN` | `UNKNOWN` | Amino-containing source outside grammar |
| 8982 | `UNKNOWN` | `UNKNOWN` | Sulfonic-acid context outside grammar |
| 14396 | `UNKNOWN` | `UNKNOWN` | Heterocyclic/methoxy context |
| 17165 | `UNKNOWN` | `UNKNOWN` | Benzoyl-chloride context |
| 18984 | `UNKNOWN` | `UNKNOWN` | Isatin/tautomer context |
| 20787 | `UNKNOWN` | `UNKNOWN` | Thiophene parent and incomplete aliases |
| 26846 | `UNKNOWN` | `UNKNOWN` | Cyano-substituted heterocycle |
| 26870 | `SUPPORTED` | `UNKNOWN` | Two aliases outside closed grammar |
| 28529 | `UNKNOWN` | `UNKNOWN` | Heterocyclic/methoxy context |
| 34227 | `UNKNOWN` | `UNKNOWN` | Acid/carboxylate claims and heterocycle |
| 36149 | `UNKNOWN` | `UNKNOWN` | Pyrrole/H/tautomer context |
| 36180 | `UNKNOWN` | `UNKNOWN` | Amino-containing source and unlocanted alias |
| 40839 | `UNKNOWN` | `UNKNOWN` | Benzyl/methyl source outside grammar |
| 42982 | `UNKNOWN` | `UNKNOWN` | Benzophenone context |
| 44101 | `UNKNOWN` | `UNKNOWN` | Hydroxy/ester/phenolate and tautomer obligations |
| 53068 | `UNKNOWN` | `UNKNOWN` | Benzyl and trifluoromethyl context |

For 26870 the preferred name `1,3-dibromo-5-nitrobenzene` and its case variant are supported, but `1,3-dibromo-5-nitro-` and `3,5-DIBROMONITRO BENZENE` are not fully interpreted by NSC-002. They were retained as unresolved source claims. No reference-correctness label was used to fill their meaning. [The sixteen-case artifact](charge_dimension_evidence/evaluation/nitro_16_case_analysis.json) retains all names, structures, exact dependencies and current reasons. No record ID or exception occurs in runtime chemical rules.

## Regressions, integrity and reproducibility

Executed: **7** new unit tests; **11** existing NSC-001 B/interface/comparator tests; **8** existing NSC-002 tests; **34** unchanged frozen NSC controls (18 + 16); and **201** retained resolver tests, all passing. The eight historical safety cases were rerun: 17504 and 30832 remained `CONFLICT`; 4373, 5684, 5997, 23839, 30142 and the historical dithiazole case remained `UNRESOLVED`. No unsupported local-eligibility or final-EXACT gain was produced. Detailed counts, Python/RDKit versions and logs are in [test results](charge_dimension_evidence/evaluation/test_results.json).

[Integrity verification](charge_dimension_evidence/evaluation/integrity_report.json) confirms the snapshotted production source, provider policies, registry/schema, main registry digest, frozen candidate database and NSC artifacts are unchanged. Frozen source controls and the listed runtime files also match recorded digests. No resolver-provider query was made. IUPAC pages were consulted for semantic grounding. Production defaults and the original source-form/comparator implementations remain unchanged; the attribution correction and consumer are isolated diagnostic modules.

Reproduce from `charge_dimension_evidence` using the existing repository environment: `python run_evaluation.py development`, then `python run_evaluation.py heldout`, `python evaluate_cohort.py`, `python -m unittest -v test_charge_evidence`, and `python run_regressions.py`. The benchmark runner checks control hashes and records an implementation freeze before held-out execution. These modules reuse repository NSC-002 and shared NSC-001 interfaces; no new dependency or OPSIN instrumentation was introduced.

## Recommendation and remaining acceptance gap

The evidence representation and functioning consumer establish a useful foundation. Zero cohort recovery is explained by the deliberately closed source grammar and incomplete claim closure, not by non-execution. Next prioritize **dimension-specific source-claim scope and limited validated naming variants**, with independent adjudication of compatible, exact incompatible and incomplete aliases. Reassess actual eligibility gains at that checkpoint before expanding to general charged nomenclature. Acids/bases, independent basic sites, zwitterions and multicomponent interpretation remain separate work.

The full v1 acceptance claim remains incomplete because source-derived charge `DIFFERENT` and `NOT_APPLICABLE` are not demonstrated by the evidence producer, and independent scientific review is pending. Structural contradiction controls are valuable but cannot substitute for that source-level proof. All outside-envelope structures remain conservative `UNKNOWN`.

CHARGE_EVIDENCE_V1_PARTIAL
