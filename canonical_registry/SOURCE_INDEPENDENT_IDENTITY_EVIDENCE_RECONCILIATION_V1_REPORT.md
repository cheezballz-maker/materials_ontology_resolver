# Source-independent identity evidence and reconciliation v1

## Executive conclusion

The isolated v1 evidence-comparison and reconciliation core is implemented. It passed **21 development and 8 public held-out controls**, including **36/36 expected claim relationships**, with zero false exact-compatible or exact-incompatible results in those controls. It handles per-dimension broadness, specific contradictions, unknown active claims, documented non-binding metadata and dependent evidence. Exact source/source contradictions persist even when the candidate is broader than both claims.

The result is **provisional validation of the implemented annotated-evidence scope**, not a validated general name interpreter or production integration. The transfer adapters cannot establish enough source-specific evidence to reconcile complete identities: all 224 CUMA records and all 20 sampled cached PubChem records remain record-level unresolved. The enabled diagnostic gate would conservatively withhold all 117 previously eligible records; it produces **zero gains**. Production defaults are unchanged. Independent qualified chemical review and genuinely blind evaluation remain pending.

## Architecture, scientific basis and scope

The implementation reuses the existing molecular parser/descriptor, form characterizer, identity comparator, the isolated charge-attribution correction and an optional NSC-001 Architecture B source interpreter. It does not replace their chemical normalization with a universal identity key. NSC-002, ChargeDimensionEvidence and the production source-form/aggregation code are retained unchanged and regression-tested. A direct NSC-002-to-IdentityEvidence adapter is **not implemented in v1**; transfer coverage therefore does not represent all source semantics potentially available from earlier experiments.

The ontology and identity framework distinguish canonical Substance identity from source concepts. Broad source referents cannot select a narrower candidate as exact. [IUPAC configuration specification](https://iupac.qmul.ac.uk/BlueBook/P9.html#P-93.1) grounds the distinction between specified configurations and unspecified stereo; [P-8](https://iupac.qmul.ac.uk/BlueBook/P8.html) distinguishes isotopically modified forms; [P-7](https://iupac.qmul.ac.uk/BlueBook/P7.html) distinguishes ionic/protonation and zwitterionic representations; [P-14.7](https://iupac.qmul.ac.uk/BlueBook/P1.html#P-14.7) addresses indicated-H naming. These sources justify chemical boundaries, not the correctness of every adapter assertion.

The core consumes **already established dimension assertions** from explicit source graphs or validated interpretation modules. It does not derive broadness from arbitrary name strings, failed parsing, or candidate features. Development name-to-graph meanings are explicitly annotated, provisional rule-grounded inputs. Thus the benchmark principally tests evidence semantics, graph comparisons and aggregation with those inputs; it is not a test of a new comprehensive nomenclature parser.

## Evidence contract and provenance

[IdentityEvidence](identity_reconciliation/identity_evidence_models.py) and its [JSON Schema](identity_reconciliation/identity_evidence_schema.json) preserve:

- Evidence, source, source-record, claim and explicit shared-referent IDs.
- Claim role, evidence type, original value and source provenance.
- Source-provided, source-derived, candidate-derived and external-reference origins.
- Documented role status and interpretation basis, including unverified evidence.
- Per-dimension assertions, derivation dependencies and unresolved obligations.

Every asserted feature has a rule/basis link. Adapters distinguish an explicit source structure from a parser-generated candidate. A candidate-derived InChIKey or graph cannot confirm itself. Missing dependencies, cycles or candidate-derived dependency roots make derived evidence unusable. The schema checks data shape; runtime code checks references and scope. Provenance assertions are trusted adapter inputs, not cryptographic attestations or automatic proof that a source name was interpreted correctly.

The output retains all claim comparisons and pairwise source comparisons. `unique_source_lineages` records distinct **derivation roots**, not a count of independently authoritative databases or providers; separate roots in one source record are not independent corroboration. No vote, confidence score or majority rule is used.

## Dimensions and specificity relationships

The model accommodates constitution, stereochemistry, tautomer, protonation/charge, isotope, components, component stoichiometry, hydration/solvation and electronic state. Assertions can be an exact singleton, a supported finite set, explicitly unspecified within a justified framework, unknown, or demonstrably inapplicable. A finite set that still contains distinct possible identities does not become exact merely because both sides describe the same set.

| Relationship | Implemented interpretation |
|---|---|
| `EXACT_COMPATIBLE` | Established dimension assertions identify equivalent features. |
| `EXACT_INCOMPATIBLE` | Established assertions demonstrably exclude one another for that dimension. |
| `BROADER_THAN_CANDIDATE` | Explicitly supported set/scope includes the candidate without selecting it uniquely. |
| `NARROWER_THAN_CANDIDATE` | Source evidence is more specific than the candidate representation. |
| `UNKNOWN` | Meaning, applicability, comparison or specificity relationship is unproven. |
| `NOT_APPLICABLE` | V1 demonstrates no potential stereo distinction on the matching framework; missing evidence does not qualify. |

For open stereo scope, framework comparison removes stereo while retaining constitution and other graph attributes. For open isotope scope, it removes isotope labels within the explicitly declared scope. Ordinary unlabelled ethanol is **not** automatically asserted to cover all isotopologues; the broad-isotope control explicitly declares an open isotope scope. General broad tautomer families are not implemented and remain unknown.

The existing comparator supplies valid molecular comparisons. The charge-attribution wrapper avoids calling ethanol/dimethyl ether a protonation difference. Explicit acid/base and neutral/zwitterionic graph distinctions remain. The hydration control compares **explicit molecular component composition**, not crystal structure or a claim that any dot-water graph establishes a solid hydrate. Unsupported correspondence stays unknown.

## Source roles and reconciliation rules

Claim roles distinguish identity assertions, partial identity evidence, explicit structure claims, identifiers, unverified aliases and search metadata. Only an independently documented non-binding search role is ignored. An unknown role or unparseable potentially binding alias remains an active unresolved obligation. An unmapped identifier does not become a structure assertion.

[The reconciler](identity_reconciliation/source_claim_reconciler.py) checks each claim against the candidate and established source claims against one another. It returns:

- `RECONCILED_COMPATIBLE` when all **requested** dimension obligations are supported and no active unresolved or contradictory claim remains.
- `RECONCILIATION_CONFLICT` when an established dimension contradiction exists.
- `RECONCILIATION_UNRESOLVED` when coverage, interpretation, role or dependencies are insufficient.

The requested-dimension scope is explicit. A constitution-only compatible result is not proof of complete canonical identity. A broad stereo claim can coexist with an exact compatible stereo claim; it does not independently establish that exact configuration. An unknown stereo dimension never makes a contradictory constitution globally broad. Exact R and S assertions conflict even if the proposed candidate omits stereo. Partial claims about distinct dimensions can combine only under an explicitly established shared referent; no implicit cross-record join is made.

Unknown active claims block reconciliation, whereas documented search metadata does not. Dependency roots are retained and dependent interpretations are not counted as independent confirmation. Broader aliases are not persisted or promoted to exact aliases.

## Independent benchmark and implementation results

[The benchmark](identity_reconciliation/controls/benchmark_freeze.json) was frozen before implementation independently of CUMA. Every item includes source roles, candidate graph, asserted dimensions, expected claim relationships, expected reconciliation, justification and references. Review is `CHEMICAL_REVIEW_PENDING`. The held-out controls were public and frozen, not genuinely blind.

The development cases cover ethanol/ethyl alcohol; explicit and unspecified stereo; opposite enantiomers; constitutional isomers; acid/conjugate-base forms; equivalent nitro representations; neutral/zwitterionic glycine **graphs** without claiming that the bare name selects a form; explicit hydration and salt composition; uninterpreted aliases; documented versus unknown search roles; unvalidated identifiers; explicit tautomer graphs; open isotope scope; and candidate-derived observations. Held-out cases add positional isomers, another acid/base pair, another stereo framework, component multiplicity, dependent interpretation and a missing dependency.

| Measure | Development | Public held-out |
|---|---:|---:|
| Cases matching all expected relationships and record result | 21/21 | 8/8 |
| False record-compatible results | 0 | 0 |
| False record-conflict results | 0 | 0 |

Across both suites, **36/36 claim relationships** matched, including **4/4 broader-than-candidate** relationships, with zero false exact-compatible or exact-incompatible claim results. Complete outputs and provenance appear in [development results](identity_reconciliation/evaluation/development_results.json) and [held-out results](identity_reconciliation/evaluation/heldout_results.json).

Development found and corrected three limitations: an explicit component-composition contrast, missing consumer record/candidate binding, and exact source/source contradictions when the candidate is broader. Benchmark expectations did not change. Earlier implementation freezes were retained, and the final controls and transfer evaluation were rerun after these corrections; see [revision history](identity_reconciliation/evaluation/implementation_revision_history.json). These are development fixes, not independent blinded discoveries.

## Diagnostic consumer and actual eligibility impact

The [default-off consumer](identity_reconciliation/diagnostic_reconciliation_consumer.py) checks the source-record referent and candidate graph binding before applying results. It preserves existing conflicts and specific reason codes. Enabled unresolved active claims add an unresolved obligation; enabled established contradictions add a conflict. Compatible evidence can contribute proved dimensions, but v1 does not generally retract pre-existing specific source-form reasons. It cannot write registry rows, allocate IDs or call providers.

The saved-evidence 224-record local baseline was freshly reproduced. Production behavior remains at **102 reference-correct eligible, 81 correct withheld, 0 incorrect eligible and 15 unadjudicable eligible**. The older 225-reference-exact population is not substituted for the 224 deterministic-cohort denominator.

| Diagnostic outcome | Default off | Enabled additional gate |
|---|---:|---:|
| Correct eligible | 102 | 0 |
| Correct withheld | 81 | 183 |
| Incorrect eligible | 0 | 0 |
| Unadjudicable eligible | 15 | 0 |
| Source form supported | 117 | 0 |
| Source form unresolved | 71 | 188 |
| Existing source-form conflicts | 36 | 36 |
| Eligibility gains | — | 0 |

This substantial conservative reduction is an **evidence-adapter coverage failure**, not evidence that those chemical identities or historical reference labels are wrong. Current CUMA name/alias adapters do not establish the source semantics and roles required by the new contract. The consumer is connected, but is **not suitable as a production replacement**. Existing specific reasons are not deleted and the 36 legacy conflicts remain. Changed records, claim evidence, rules and before/after source forms are preserved in [local_eligibility_before_after.json](identity_reconciliation/evaluation/local_eligibility_before_after.json). No final canonical decision or external-gate bypass was performed.

## Transfer across real source types

After final implementation freeze, the module was evaluated on the original 224 CUMA records and 20 actual cached PubChem records. The latter were the first 20 unique CIDs in numerical order among 44 available unique saved CIDs, extracted from the existing candidate-evidence database. No records were manufactured. PubChem's own supplied structure, supplied name and CID were kept as distinct claims with original cached row provenance. This is self-consistency assessment of reference-record fields, **not independent corroboration of CUMA**.

| Transfer measure | CUMA terminology | Cached PubChem reference records |
|---|---:|---:|
| Records evaluated | 224 | 20 |
| Records with multiple claims | 224 | 20 |
| Claims with at least one comparable established dimension | 0 | 20 |
| Exact-compatible dimension relationships | 0 | 180 |
| Unknown dimension relationships | 7,326 | 360 |
| Records unresolved for all requested-dimension completion | 224 | 20 |
| Complete reconciled identity-evidence records | 0 | 0 |
| Evaluation errors | 0 | 0 |

CUMA parser-derived candidates remained observations rather than source structures. Its unverified aliases remained active. In PubChem, the explicitly supplied graph provides structural evidence about that record, while names not mapped by the optional interpreter and identifiers without validated identity correspondence remain unresolved. No validated broader claims or new exact source conflicts were established in this transfer; that is limited evidence coverage, not proof that none exist. The 180 compatible comparisons are nine self-consistency dimensions for 20 explicit record graphs, not 180 independent confirmations. [Cross-source results](identity_reconciliation/evaluation/cross_source_results.json) preserve both datasets separately.

## Regression, integrity and reproducibility

Executed: **11** new reconciliation unit tests; **11** existing NSC-001/interface/comparator tests; **8** NSC-002 tests; **7** ChargeDimensionEvidence tests; **34** unchanged frozen NSC controls; and **201** retained resolver tests, all passing. New tests include finite-set uncertainty, missing/cyclic dependencies, candidate-derived lineage, cross-record linkage, source/candidate binding, per-dimension evidence combination and exact contradictions against an underspecified candidate.

The eight historical safety cases were rerun: 17504 and 30832 remained `CONFLICT`; 4373, 5684, 5997, 23839, 30142 and the historical dithiazole case remained `UNRESOLVED`. [Test results](identity_reconciliation/evaluation/test_results.json) record actual counts and versions (Python 3.14.3, RDKit 2025.09.6). No qualified human review or blinded chemical evaluation is claimed.

[Integrity verification](identity_reconciliation/evaluation/integrity_report.json) confirms selected production modules, provider-policy code, main registry/database digest, frozen evaluation inputs and previous NSC/charge artifacts match the pre-implementation snapshot. Historical ontology/framework/schema contract hashes also match. New benchmark expectations and the final runtime freeze are unchanged. No production admission, provider budget, external-corroboration policy, persistent alias or registry schema/data was changed. No new resolver-provider request was made.

Reproduce from `identity_reconciliation` using the repository environment: `python -m unittest -v test_reconciliation`; `python run_benchmark.py development`; `python run_benchmark.py heldout`; `python evaluate_transfer.py`; `python run_legacy_regressions.py`; and `python finalize.py`. Benchmark and runtime hashes are checked. The adapters reuse repository modules; they require the saved local evidence for transfer, not live provider access. All diagnostic outputs are experiment-local.

## Remaining limitations and next improvement

V1 validates reconciliation under an explicit, provisional evidence contract. It does not independently certify arbitrary upstream `RULE_ESTABLISHED` annotations, infer metadata roles, resolve bare identifiers, parse general conventional names, interpret broad tautomer families, establish physical hydrate phases or provide a general electronic-state comparison. Existing comparator limitations remain conservative unknowns where exposed. Source-link authority and all-dimension coverage are obligations of adapters and subsequent scientific validation.

The next task should implement **auditable source-role and semantic-evidence adapters**, beginning with documented structural fields and already validated NSC-002/ChargeDimensionEvidence outputs, then validated identifier-to-structure correspondence. Define what source metadata establishes each role and which semantic module establishes each dimension; retain unverified synonyms as active obligations. Freeze independent adapter controls before evaluating dataset coverage. The next checkpoint must show trustworthy evidence coverage and a defensible isolated eligibility delta without suppressing exact conflicts. Further grammar expansion should follow that checkpoint rather than conceal adapter gaps.

IDENTITY_RECONCILIATION_V1_VALIDATED_PROVISIONAL
