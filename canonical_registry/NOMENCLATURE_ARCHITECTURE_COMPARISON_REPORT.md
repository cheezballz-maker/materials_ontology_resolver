# NSC-001 nomenclature architecture comparison

## Executive conclusion

Two isolated diagnostic implementations now use the same frozen NSC-001 v2 grammar, semantic interface and public controls. Architecture B, an independent constrained interpreter, matched **12/12 development** and **6/6 public held-out** expected operation results. Architecture A, the source-aware OPSIN adapter, matched **7/12** and **3/6** respectively; it conservatively returned `UNKNOWN` for all eight cases where B returned `SUPPORTED` or `DIFFERENT`. Neither produced a false `SUPPORTED` or false `DIFFERENT` in these controls.

These are **provisional engineering results**, not chemical validation or evidence of production readiness. A qualified human has not reviewed the benchmark, the held-out cases were visible to the implementation process, and no genuinely blinded set was run. The pilot covers only eight complete names and has zero whole-name matches in the previous 81-record diagnostic set. The appropriate decision is **benchmark not ready for an architectural winner**. B is the more useful *candidate for a subsequent experiment*; A's inability to prove closure is a substantive, observable limitation.

## Contract corrections, chemistry and review

[NSC-001 v2](nsc_architecture_experiment/NSC-001/contract_v2.json) preserves the exact [v1 grammar](nsc_architecture_experiment/NSC-001/grammar_v2.ebnf): a locant `1`, one normal C1–C4 alkyl prefix, `1H`, and a pyrazole or imidazole parent, with full-input consumption. It adds typed evidence references and comparator-level symmetry fixtures. The earlier 12 development and six public held-out expected labels were retained; no chemical label was changed in response to an architecture result. `D09`, `D12` and `H04` are explicitly injected comparison-unavailability scenarios, not claims of chemical ambiguity. `D11` scores the record-level conflict separately from the first source's operation.

The chemical basis remains [IUPAC Blue Book P-13.1](https://iupac.qmul.ac.uk/BlueBook/P1.html#P-13.1) for replacing a parent H with a substituent; [P-14.3.2](https://iupac.qmul.ac.uk/BlueBook/P1.html#P-14.3.2) for locant placement; [P-14.7.1–2](https://iupac.qmul.ac.uk/BlueBook/P1.html#P-14.7) for indicated versus added H; [P-22, Table 2.2](https://iupac.qmul.ac.uk/BlueBook/P2.html) for the two retained parent hydrides and numbering; and [P-29.3.2.1](https://iupac.qmul.ac.uk/BlueBook/P2.html#P-29.3.2.1) for terminal alkyl attachment. PubChem's independently documented [N-methylpyrazole](https://pubchem.ncbi.nlm.nih.gov/compound/70255), [3-methylpyrazole](https://pubchem.ncbi.nlm.nih.gov/compound/1453-58-3), and [N-methylimidazole](https://pubchem.ncbi.nlm.nih.gov/compound/MCTWTZJPVLRJOU-UHFFFAOYSA-N) support the example graphs; they are not naming-rule authorities. Replacing the parent N1 hydrogen gives a substituted N1 without requiring a final N1 H. Kekulé and aromatic depictions are compared as equivalent representations where chemistry permits.

[Benchmark review](nsc_architecture_experiment/NSC-001/benchmark_review.json) marks every fixture **provisional, `CHEMICAL_REVIEW_PENDING`**. No qualified human review or approval is claimed. The [freeze](nsc_architecture_experiment/NSC-001/benchmark_freeze.json) hashes the v2 contract, rules, schema and both public control sets plus comparator fixtures. This freeze was written before either architecture's implementation. The implementation itself was frozen after development and before public held-out execution.

## Common representation and shared comparison

The [v2 JSON Schema](nsc_architecture_experiment/NSC-001/semantic_constraint_schema_v2.json) explicitly types claim IDs, half-open original Unicode-code-point source spans, source text, claim type, semantic owner and rule. Operations and constraints carry IDs, source-claim IDs, rule IDs, owners, dependencies and assertions. The [semantic interface](nsc_architecture_experiment/shared/semantic_interface.py) additionally checks unique IDs, exact original text spans, existing claim and operation references, and permitted rule IDs; JSON Schema alone cannot enforce cross-object references. These IDs are contract-local and are not OPSIN atom objects.

The [shared comparator](nsc_architecture_experiment/shared/structural_comparator.py) strictly parses the complete candidate SMILES, rejects unsupported components, charged states, isotope labels, stereochemistry and radicals, and enumerates bounded full-graph correspondences with atom and hydrogen attributes. It accepts alternative traversal and aromatic/Kekulé serializations. For a non-isomorphic candidate, it can give a bounded structural reason only when a unique ring-to-sidechain cut, capped parent/substituent fragments and all relevant parent mappings establish an incompatible attachment, a different alkyl fragment, or a different parent connectivity. Otherwise it returns `UNKNOWN`; graph mismatch alone does not assert a specific operation violation. This diagnostic method and its chemical assumptions still need independent review.

A comparator-level benzene control exercises 12 graph automorphisms: a graph-identity predicate is invariant and supports equivalence; an unlabeled site-specific predicate has both true and false outcomes and therefore returns `UNKNOWN`. This is a comparator test, not an assertion that a nontrivial symmetry ambiguity exists within NSC-001. Mapping-limit exhaustion, malformed input and unsupported form attributes abstain.

An operation `SUPPORTED` never establishes the full tautomer dimension or canonical identity. The common results explicitly return tautomer `UNKNOWN` and identity `NOT_ESTABLISHED`. There is no production admission integration.

## Architecture implementations

**A — source-aware OPSIN.** The [adapter](nsc_architecture_experiment/architecture_A/implementation/interpreter.py) invokes the existing isolated OPSIN 2.9.0 instrumentation, checks the official dependency digest and stored patch digest, and inspects original locant and indicated-H source spans, selected parse, event, same-target relation, final atoms and clone status. It retains the existing observation rather than adding broad instrumentation. For a recognized and traced input it exposes source claims but returns `UNKNOWN`, because the trace does not prove the relevant final-operation closure. In particular, OPSIN feature resolution, fragment incorporation/replacement and later finalization can affect state after the observed join; the existing sidecar does not certify all relevant source-associated transformations or excluded paths. Full global operation logging is not required by the contract, but a bounded, independently validated final-state proof or a provenance API with reliable closure is still missing. A minimum patch would need selected-parse/source fragment boundaries and explicit supported-path/transform status; extending it across general OPSIN nomenclature would entail version-sensitive maintained source changes.

**B — independent interpreter.** The [implementation](nsc_architecture_experiment/architecture_B/implementation/interpreter.py) recognizes the frozen grammar independently, preserves source spans, chooses separately defined numbered parent templates, and composes a generic normal-alkyl chain by replacing the parent N1 H. Parent definitions, grammar, operations, constraint generation and validation are separate modules; there is no eight-name-to-SMILES lookup. RDKit constructs and compares graphs, but does not establish the naming rule. B's supported and contradiction results are experimental outcomes relative to the provisional benchmark; complete tautomer and identity dimensions remain unresolved.

Both use the same candidate inputs and result semantics. A does not use B's name interpretation or output as evidence. The existing source-aware OPSIN build is held in a machine-specific temporary directory referenced by `source_aware_substitution_poc/build.json`; the A adapter fails closed if it is absent. The dependency jar and patch are checked, but the adapter does not verify every compiled class against a complete reproducible class manifest at invocation. Thus the current A experiment is **not yet self-contained for clean-environment reproduction**: reproduce the pinned earlier POCs and build first, and verify their class artifacts. B requires Python, RDKit and `jsonschema`; precise versions from this run appear in [test results](nsc_architecture_experiment/evaluation/test_results.json).

## Development and public held-out outcomes

Every fixture, expected result, both outputs, claims, reason codes and agreement appears in [development results](nsc_architecture_experiment/evaluation/development_results.json) and [held-out results](nsc_architecture_experiment/evaluation/heldout_results.json). The expected grammar classification was matched for all 18 cases by both adapters.

| Suite | Architecture | Expected results matched | False `SUPPORTED` | False `DIFFERENT` | Record-conflict case |
|---|---|---:|---:|---:|---|
| Development, 12 | A | 7 | 0 | 0 | Not established |
| Development, 12 | B | 12 | 0 | 0 | Correctly detected, 1/1 |
| Public held-out, 6 | A | 3 | 0 | 0 | Not applicable |
| Public held-out, 6 | B | 6 | 0 | 0 | Not applicable |

B's development results comprised four `SUPPORTED`, one `DIFFERENT`, four `UNKNOWN` and three `OUT_OF_CONTRACT`; its held-out results comprised two, one, two and one respectively. A produced nine `UNKNOWN` and three `OUT_OF_CONTRACT` in development, and five and one in held-out. These aggregate counts are conditional on provisional labels and do not establish general nomenclature accuracy.

All eight A/B disagreements are enumerated in [disagreements.json](nsc_architecture_experiment/evaluation/disagreements.json):

| Fixture | Source | Expected | A | B | Cause |
|---|---|---|---|---|---|
| D01 | `1-methyl-1H-pyrazole` | `SUPPORTED` | `UNKNOWN` | `SUPPORTED` | A lacks final-operation closure; B finds exact graph correspondence. |
| D02 | `1-methyl-1H-imidazole` | `SUPPORTED` | `UNKNOWN` | `SUPPORTED` | Same closure difference. |
| D03 | `1-methyl-1H-pyrazole` | `DIFFERENT` | `UNKNOWN` | `DIFFERENT` | A abstains; B's capped common parent and substituent place the attachment at a different atom. |
| D10 | `1-methyl-1H-pyrazole` | `SUPPORTED` | `UNKNOWN` | `SUPPORTED` | A abstains; B accepts equivalent graph representations. |
| D11 | `1-methyl-1H-pyrazole` | `SUPPORTED` | `UNKNOWN` | `SUPPORTED` | A abstains; B also detects the separate incompatible imidazole source claim. |
| H01 | `1-ethyl-1H-imidazole` | `SUPPORTED` | `UNKNOWN` | `SUPPORTED` | A abstains; B finds exact graph correspondence. |
| H02 | `1-ethyl-1H-imidazole` | `DIFFERENT` | `UNKNOWN` | `DIFFERENT` | A abstains; B identifies methyl versus ethyl on a matched capped parent. |
| H06 | `1-ethyl-1H-imidazole` | `SUPPORTED` | `UNKNOWN` | `SUPPORTED` | A abstains; B accepts equivalent traversals. |

The public held-out data were frozen but visible and are not blind. No separately adjudicated blind evaluation was available or run. The reference expectations and comparison rules should be independently reviewed before interpreting the result as semantic correctness.

## Engineering, closure and extension

B has a small explicit grammar and reviewed-by-inspection parent templates; all eight grammatical combinations were generated in tests, but the semantic meaning and complete candidate-space behavior are not yet independently certified. A reuses more of OPSIN's parser and can expose valuable source provenance; its closure limitation means its demonstrated *semantic* coverage here is narrower than its parsing coverage. B's modules are easier to inspect within this tiny class, while broad nomenclature would require significant independently maintained grammar, parent templates and operation semantics. A would need source provenance and boundary support maintained against OPSIN changes. Both need rigorous handling of source normalization, symmetry, formal charge, isotope and unsupported operations before wider use.

The [extension assessment](nsc_architecture_experiment/evaluation/extensibility_assessment.json) distinguishes reusable interfaces and comparator machinery from new semantics required for additional parents, branched/multiple substituents, suffixes and added H, protonation, components, stereo and isotopes. These are estimates. A reasonable next contract is a separately grounded, tightly scoped **monocyclic lactam/lactim suffix and added-H construction**, with multiple parent examples and an explicit mobile-H boundary. First freeze its grammar and quantify coverage independently; do not retrofit this pilot around particular CUMA records.

## Tests, safety and integrity

Executed in this task: pinned baseline OPSIN core **680 passed, 2 skipped**; instrumented core **680 passed, 2 skipped**; indicated-H trace **14 passed**; prior graph/operation tests **11 passed**; prior common-parent/source-aware tests **11 passed**; adapter/concurrency **8 passed**; new shared/interface/A/B tests **13 passed**; retained resolver tests **201 passed**. The first development test run exposed an explicit-H valence handling error in B; it was corrected before final development evaluation and implementation freeze, and the tests were rerun successfully. Seven prior development structures again produced equal baseline/instrumented public outputs and equal RDKit-generated Standard and FixedH InChI pairs. This is bounded output equivalence, not a general equivalence proof.

The existing offline historical safety run returned `CONFLICT` for 17504 and 30832, and `UNRESOLVED` for 4373, 5684, 5997, 23839, 30142 and the historical dithiazole case. The experimental implementations were not connected to that resolver. [Integrity results](nsc_architecture_experiment/evaluation/integrity_report.json) confirm selected production-file hashes, contract/control hashes and post-development implementation hashes match their recorded snapshots. The older ontology, framework and provider-cache checks also pass, subject to their documented historical exceptions. No before/after digest of the entire registry was taken; no registry write was issued. No resolver provider queries or admission-policy changes were made. Public chemistry references were consulted through the web; this is not a new resolver evidence-provider run.

## Recommendation

Obtain qualified chemical review of the frozen rules, parent templates, candidate partitions and all provisional fixtures, then freeze an independently prepared blind control set and make A reproducible without an ephemeral build path. B can be carried forward as the leading *experimental* candidate for the next contract, provided its source semantics and contradiction classifier pass that review. Preserve A's fail-closed status until its bounded closure can be demonstrated. Neither result supports a production admission change.

BENCHMARK_NOT_READY_FOR_DECISION
