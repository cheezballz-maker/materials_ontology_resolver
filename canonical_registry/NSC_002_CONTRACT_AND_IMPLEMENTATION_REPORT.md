# NSC-002 contract and implementation

## Executive conclusion

NSC-002 is an isolated, provisional Architecture B extension for **multiple explicitly locanted halo and nitro substitutions on a benzene parent**. It demonstrates reusable composition of source claims and ring-substitution operations. The implementation matched all **11 development** and **5 public held-out** expected outcomes, with no false `SUPPORTED` or `DIFFERENT` in those controls. Chemical review remains pending, the held-out controls were public, and this is not production validation.

Two of the 81 previously withheld records have complete preferred names in the frozen grammar, and both yielded provisional operation-level `SUPPORTED` against their saved candidates. An isolated replay of the existing local eligibility rules still withheld both: one for a source-constitution conflict and the other for protonation specificity. **No Substance recovery is claimed.**

## Candidate scopes and practical selection

Before reviewing record-level applicability, [three provisional scopes](nsc002_experiment/NSC-002/provisional_candidate_scopes.json) were fixed and [hashed](nsc002_experiment/NSC-002/provisional_scope_freeze.json). The [81-record comparison](nsc002_experiment/NSC-002/candidate_scope_comparison.json) then examined complete preferred names and saved aliases, with lexical near-matches reported only as opportunities. It did not use candidate structure to infer source meaning or local eligibility.

| Candidate | Independent provisional scope | Full-name opportunity | Potential with extension | Main constraint |
|---|---|---:|---:|---|
| A: lactam/lactim | Explicit indicated-H pyrimidinone with fixed H and carbonyl locants | 0 | 3 | Suffix composition, H placement and mobile-site completeness need stronger closure. |
| B: protonation | Explicit pyridinium cation, no counterion or other groups | 0 | 0 | A broader class requires ion ownership and component semantics; `-ate` is not a universal charge rule. |
| C: substitutive | Explicit halo/nitro prefixes and locants on complete benzene names | 2 | 8 | Broader named fragments, suffixes, and partial ownership remain unsupported. |

The remaining records were outside the respective provisional scopes: 78 for A, 81 for B and 71 for C. These counts are lexical triage, not proven chemical interpretation or recoveries. No partial operation was treated as supported. Candidate C was selected because the naming rules are independently grounded, the graph operation composes naturally, and its frozen scope has a measurable opportunity beyond NSC-001's zero whole-name matches. Its reach is still small relative to the 81 and it does not directly solve the most prevalent tautomer, charge or alias blockers. The selected grammar was not expanded after the corpus assessment.

## Grammar and chemical meaning

The frozen [grammar](nsc002_experiment/NSC-002/grammar.ebnf) accepts an entire ASCII, case-insensitive name consisting of one to three explicitly locanted prefix groups, followed by `benzene`. Each group uses positions 1–6 and `bromo`, `chloro`, `fluoro`, `iodo` or `nitro`; `di` and `tri` require the corresponding number of locants. Positions must be distinct, each substituent type has one group, and there can be at most six substituted sites. No whitespace, extra source tokens, suffixes, stereodescriptors, isotopes, charge descriptors, salts or additional components are accepted. Unsupported inputs are `OUT_OF_CONTRACT`, without a chemical-ambiguity judgment.

The [selected contract](nsc002_experiment/NSC-002/selected_contract.json) and [rule catalog](nsc002_experiment/NSC-002/nomenclature_rules.json) separate source-explicit locants, multiplicity, prefixes and parent from nomenclature-established H replacement and attachment. The governing sources are [IUPAC Blue Book P-13.1](https://iupac.qmul.ac.uk/BlueBook/P1.html#P-13.1) on substitution, [P-14.2](https://iupac.qmul.ac.uk/BlueBook/P1.html#P-14.2) on multiplicative prefixes, [P-14.3](https://iupac.qmul.ac.uk/BlueBook/P1.html#P-14.3) on locants, and [P-5 characteristic-group prefixes](https://iupac.qmul.ac.uk/BlueBook/P5.html). The [IUPAC Gold Book nitro definition](https://old.goldbook.iupac.org/plain/N04158-plain.html) specifies attachment via nitrogen. Example structures are corroborated by independently accessible records for [1-bromo-3-chlorobenzene](https://pubchem.ncbi.nlm.nih.gov/compound/7928), [1,3-dibromobenzene](https://pubchem.ncbi.nlm.nih.gov/compound/1_3-dibromobenzene) and [1-chloro-2-nitrobenzene](https://pubchem.ncbi.nlm.nih.gov/compound/6945); those records do not replace nomenclature authority.

Each named ring position replaces a benzene H with its specified group. A nitro group is N-attached; the accepted `[N+](=O)[O-]` graph has internal formal charges but net neutral group composition. The implementation does not infer a separately protonated species from these formal charges. It compares complete ring substitution patterns over the 12 benzene rotations and reflections, so symmetry-equivalent locant arrangements and valid aromatic/Kekulé depictions are not false differences. A valid `DIFFERENT` records either a different supported substituent composition or a different ring pattern after all 12 transformations fail. Candidate structures outside the closed graph class yield `UNKNOWN`, including unsupported charges, extra components, isotopes, radicals, stereo and unrecognized substituents. It does not canonicalize tautomers or strip salts.

Partial interpretation is deliberately **not implemented**. A recognized-looking substring in a larger name does not establish its owner or that later operations leave it valid. A complete-name operation result is also not a complete molecular identity: the common interface continues to report identity `NOT_ESTABLISHED` and the tautomer dimension `UNKNOWN`.

## Schema, implementation and closure

The [schema extension record](nsc002_experiment/NSC-002/semantic_constraint_extensions.json) documents reuse of NSC-001 v2's typed interpretation and validation models, source spans, rule/claim/operation/constraint IDs, dependency links and result taxonomy. The NSC-002 schema changes the contract ID and version; the existing NSC-001 schema and shared source are unchanged. NSC-002 validates its schema and invokes the existing referential-integrity checks using a compatibility projection. It records separate source claims and operations per prefix, and reports a **joint ring-pattern result** rather than incorrectly assigning a whole-pattern contradiction to every individual group.

The entry gate was met provisionally: the grammar and exclusions are explicit, IUPAC provides the rule basis, complete graph comparison is bounded, the two full-name cohort opportunities and multi-operation reuse provide value beyond the eight NSC-001 names, and positive, negative and abstention controls were specified before code. Qualified human review is still required before any production-level chemical conclusion.

The [independent interpreter](nsc002_experiment/architecture_B/nsc002_interpreter/interpreter.py) separates whole-name grammar, source-claim/constraint generation, schema validation and candidate comparison. It does not use OPSIN to determine source meaning and contains no CUMA-specific exceptions or name-to-product lookup. The earlier shared structural comparator rejects any charged atom; it was **not weakened** to accommodate nitro. The new narrow comparator implements explicit neutral nitro recognition and the same symmetry-aware graph principle. It is a separate diagnostic component, not a general resonance or protonation engine. [Extensibility details](nsc002_experiment/evaluation/extensibility_assessment.json) distinguish reused interfaces from new chemistry and comparator work.

## Benchmark and results

The [contract, rules, schema and controls](nsc002_experiment/NSC-002/benchmark_freeze.json) were frozen before implementation; the implementation was frozen after development and before the held-out run. [Chemical review](nsc002_experiment/NSC-002/chemical_review.json) is `CHEMICAL_REVIEW_PENDING`: IUPAC and structure-database cross-checks are not independent qualified human review. The held-out controls were public and are not blinded. No genuinely blinded set was run. Individual source claims, constraints, candidate evidence, unresolved dependencies and reasons are in [semantic results](nsc002_experiment/evaluation/nsc002_semantic_results.json).

| Case | Source / challenge | Expected | Actual | Reason |
|---|---|---|---|---|
| D01 | 1-bromo-3-chlorobenzene, matching structure | `SUPPORTED` | `SUPPORTED` | Ring pattern corresponds. |
| D02 | Same source, para rather than meta candidate | `DIFFERENT` | `DIFFERENT` | Substitution positions differ. |
| D03 | 1,3-dibromobenzene | `SUPPORTED` | `SUPPORTED` | Multiplicity and pattern correspond. |
| D04 | 1-chloro-2-nitrobenzene | `SUPPORTED` | `SUPPORTED` | N-attached neutral nitro pattern corresponds. |
| D05 | Same source, nitroso candidate | `UNKNOWN` | `UNKNOWN` | Candidate substituent unsupported. |
| D06 | Valid SMILES followed by arbitrary text | `UNKNOWN` | `UNKNOWN` | Invalid candidate. |
| D07 | Unlocanted bromochlorobenzene | `OUT_OF_CONTRACT` | `OUT_OF_CONTRACT` | Whole-name grammar. |
| D08 | Source with hydrochloride | `OUT_OF_CONTRACT` | `OUT_OF_CONTRACT` | Whole-name grammar. |
| D09 | Isotope-labelled candidate | `UNKNOWN` | `UNKNOWN` | Isotope unsupported. |
| D10 | Equivalent Kekulé/traversal depiction | `SUPPORTED` | `SUPPORTED` | Ring pattern corresponds. |
| D11 | Correspondence deliberately unavailable | `UNKNOWN` | `UNKNOWN` | No mapping evidence. |
| H01 | 1,2-dibromobenzene | `SUPPORTED` | `SUPPORTED` | Ring pattern corresponds. |
| H02 | 1,2-dibromobenzene, meta candidate | `DIFFERENT` | `DIFFERENT` | Substitution positions differ. |
| H03 | Equivalent nitro oxygen ordering | `SUPPORTED` | `SUPPORTED` | Ring pattern corresponds. |
| H04 | Additional candidate component | `UNKNOWN` | `UNKNOWN` | Multicomponent unsupported. |
| H05 | Source with an unsupported `-ol` suffix | `OUT_OF_CONTRACT` | `OUT_OF_CONTRACT` | Whole-name grammar. |

There were **0 false `SUPPORTED` and 0 false `DIFFERENT`** among these provisional controls. The tests also exercise source-span/reference integrity, strict trailing-text rejection, nitro internal charges, unsupported external charge, all ring transformations, equivalent source locants and permuted atom order. Passing a small fixture set does not establish general nomenclature correctness.

## NSC-001 regression and 81-record analysis

All **18** previous NSC-001 Architecture B controls were replayed without OPSIN, preserving scope, result, constraints and source spans; [regression results](nsc002_experiment/evaluation/nsc001_regression.json) pass. The NSC-001 benchmark, grammar and shared implementation remain unchanged.

The [selected 81-case diagnostic](nsc002_experiment/evaluation/nsc002_81_case_applicability.json) records 2 `FULL_NAME_APPLICABLE`, 8 `POTENTIALLY_APPLICABLE_REQUIRES_EXTENSION`, 71 `OUT_OF_SCOPE`, and zero partial-operation or insufficient-evidence classifications. The two full names produced provisional joint-operation `SUPPORTED` against saved candidates. No full identity dimension was asserted and no partial substring was promoted.

The [isolated existing-rule replay](nsc002_experiment/evaluation/local_eligibility_comparison.json) reran the saved-claim local helper across 224 records without provider calls and compared the two diagnostic observations alongside the unchanged rules. It retained the historical **102 eligible / 81 withheld among 183 confirmed-correct**. CUMA 11807 remained withheld for `SOURCE_CONSTITUTION_CONFLICT`; 26870 remained withheld for `SOURCE_PROTONATION_SPECIFICITY_UNKNOWN`. NSC-002 was not injected into those eligibility rules, so this does not measure a proposed admission policy or demonstrate recovery. Broader lexical potential must not be extrapolated into future recoveries.

## Safety, tests and reproducibility

Executed: NSC-002 grammar/semantic/comparison tests **8 passed**; frozen development **11/11** and public held-out **5/5** matched expected outcomes; existing NSC-001 B/interface/comparator tests **11 passed**; NSC-001 B control regression **18/18** unchanged; retained resolver tests **201 passed**. No tests were skipped in these sets. The historical offline safety helper kept 17504 and 30832 as `CONFLICT`, and 4373, 5684, 5997, 23839, 30142 and the historical dithiazole case as `UNRESOLVED`. NSC-002 did not affect those decisions. No OPSIN-specific suite was run for the NSC-002 implementation; no OPSIN artifacts were changed. Exact Python and RDKit versions and case outputs are in [test results](nsc002_experiment/evaluation/test_results.json).

To reproduce from the experiment folder with the repository's Python environment, run `python run_benchmark.py development`, then `python run_benchmark.py heldout`; the runner checks the frozen benchmark and freezes implementation hashes before heldout. `python run_nsc001_regression.py` replays NSC-001 B controls, and `python assess_selected_81.py` repeats the bounded diagnostic. Tests require RDKit and `jsonschema`, and the isolated eligibility replay additionally uses the existing resolver dependencies and saved local evidence. These scripts read the existing frozen data and write only experiment-local outputs.

[Integrity checks](nsc002_experiment/evaluation/integrity_report.json) pass for selected production files, both frozen benchmark sets and the NSC-002 implementation freeze. No registry write was issued; a full registry before/after digest was not taken. No provider adapter, budget, production admission, ontology or external-corroboration policy was changed. Public IUPAC and PubChem references were consulted for grounding; no new resolver provider calls were made.

## Limitations and next stage

This extension shows that multiple source operations can reuse the existing typed semantic interface, while the separate ring comparator demonstrates a genuine chemistry-specific addition. It does not establish a universal, economical nomenclature interpreter: the grammar is narrow, partial ownership is unresolved, and nitro handling covers a limited neutral graph pattern. All benchmark labels remain provisional and the public holdout is not an independent blinded chemical evaluation.

Before integration, obtain qualified chemical review and a freshly prepared blinded set, including adversarial ring symmetry, source conflicts, charge and resonance cases. A next contract should target **explicit charge/protonation nomenclature with independently defined component and source-claim scope**, or a carefully bounded indicated-H/suffix class; select between them using a new independently frozen opportunity assessment. Alias adjudication remains separate: one supported systematic name does not validate the other names in its record.

NSC002_IMPLEMENTATION_VALIDATED_PROVISIONAL
