# OPSIN indicated-H ownership mapping proof of concept

## Finding

**A bounded internal mapping trace is feasible and has now been demonstrated.** An isolated, pinned OPSIN 2.9.0 build connects an original indicated-H or added-H token occurrence, through a transformed parser node and its owning fragment, to the same atom object in the successful result and its CML atom ID. Nested names with two occurrences of `1H` map to their respective ring fragments without selecting atoms by a global locant-label search.

This supplies evidence previously missing from the public-output investigation. It does **not** establish a complete tautomer validator, a production adapter, or eligibility recovery in the 81 historical cases. Clone lineage, normalized source offsets, warning-result selection, complete mobile-H coverage, functional-group operations and other identity dimensions remain incomplete. Production admissions and external corroboration were not changed.

## Inputs and limits of this continuation

Available locally: `NOMENCLATURE_ENGINE_FEASIBILITY_REPORT.md` and the current project ontology. The earlier `OPSIN_OWNERSHIP_TRACE_FOLLOWUP_REPORT.md` was read from the saved report to avoid repeating its R/S experiment. Its previous narrow ownership finding and unresolved clone/version limitations informed this experiment.

The earlier source checkout, installed 3.0-SNAPSHOT jar, probe scripts, production resolver, registry, frozen evaluations, 81-case taxonomy and replay files are not present in this workspace. Exact-title searches did not retrieve the supporting JSON files or a canonical-registry bundle; this does not prove they do not exist elsewhere. Accordingly, this study uses independent controls. It cannot reproduce the historical 102/183 eligibility result, re-adjudicate the 81 cases, run the retained production resolver suite, or calculate updated precision, recall or external-gate contribution.

Historical safety IDs, including 17504, 4373, 30832, 5684, 5997, 23839 and 30142, were not reconstructed from IDs or aggregate reports. No new safety-case outcome or admission is asserted for them.

## Pinned implementation and provenance

- Official source: OPSIN tag `2.9.0`, commit `b91b610af5ab07560fedb20730d7aef46bb2bca0`.
- Compiler/runtime: OpenJDK 17.0.20; compilation uses `--release 8` and UTF-8.
- Dependency artifact: official `opsin-core-2.9.0-jar-with-dependencies.jar`.
- SHA-256: `627ee5da4af551f9c4d1d766f545eb7cf519a344776e0bb677247a47abac0252`, matching the official GitHub release asset digest.
- Every core Java source is compiled separately for the baseline and diagnostic, with source resources preceding the released jar on the classpath. The release jar supplies dependencies, rather than replacing selected baseline core classes.
- Independent recompilation reproduced the class-file hash maps for both builds. Six existing Java source units were instrumented; nine existing class files differ, including nested-class debug metadata, plus the diagnostic helper and runner.

This establishes a reproducible new experimental baseline. It does not identify or prove equivalence to the earlier 3.0-SNAPSHOT installation. Across the 27 controls, released-jar public outputs also match both new source builds, which is bounded behavioral evidence rather than universal equivalence.

See `build_identity.json`, the official [2.9.0 release](https://github.com/dan2097/opsin/releases/tag/2.9.0), and the [pinned source tree](https://github.com/dan2097/opsin/tree/b91b610af5ab07560fedb20730d7aef46bb2bca0).

## What was instrumented

The diagnostic uses sidecar object-identity maps. It does not insert provenance attributes into OPSIN XML or change atom-selection instructions.

| Stage | Observation and boundary |
|---|---|
| Parser token construction | Record cumulative token offsets only when concatenated tokens match the parsed word and that exact word occurs once in the original input. The substring at the recorded span must match the token. Unmappable normalization and repeated identical words receive no span. |
| Token copying | Carry a known origin through `TokenEl.copy`; this alone does not validate chemical clone multiplicity. |
| Component generation | Carry the original indicated-H token origin to its newly created locanted node. Separately carry a `2(1H)-` locant-token origin to the added-H node created from it. Other generated nodes do not automatically acquire an origin. |
| Locanted feature application | Record the node, its resolved owning `group` fragment, locant, selected atom object and pre-application spare-valency state inside `resolveLocantedFeatures`. OPSIN already requires exactly one group at that local scope. |
| Parse selection | Clear events at each attempt; expose atom events only for the successful selected result. Retain generated parse XML alternatives and their selected-attempt indicator. Warning results deliberately expose no selected mapping. |
| Final output | Require the recorded atom object to occur in the returned fragment; independently check its CML `a<ID>` and matching locant label. Count actual H neighbors from the final CML bonds. |
| Copying/transformation | Any observed fragment-copy activity conservatively invalidates the bounded mapping classification for the entire selected attempt. Original-to-clone atom lineage is not claimed. |

The source span covers the complete originating token, such as `1H-` or `2(1H)-`; it is not a fabricated minimal character span for the H alone. Application order need not equal textual order. Nested controls explicitly verify occurrence positions, fragment names and distinct atom IDs.

The trace proves **the observed internal ownership path**, not that OPSIN exhaustively considered all chemically plausible interpretations. All tested names generated one parse alternative. A later successful attempt after an actual abandoned attempt was not experimentally exercised. Sequential success/failure/warning isolation was exercised. The helper is sequential and uses static state; concurrent use would require isolation before any integration.

Relevant pinned source files:

- [Parser.java](https://github.com/dan2097/opsin/blob/b91b610af5ab07560fedb20730d7aef46bb2bca0/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/Parser.java): `writeWordXML`.
- [ComponentGenerator.java](https://github.com/dan2097/opsin/blob/b91b610af5ab07560fedb20730d7aef46bb2bca0/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/ComponentGenerator.java): `processIndicatedHydrogens`, `processLocants`, generated added-H conventions.
- [StructureBuildingMethods.java](https://github.com/dan2097/opsin/blob/b91b610af5ab07560fedb20730d7aef46bb2bca0/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/StructureBuildingMethods.java): `resolveLocantedFeatures`.
- [FragmentManager.java](https://github.com/dan2097/opsin/blob/b91b610af5ab07560fedb20730d7aef46bb2bca0/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/FragmentManager.java): fragment copying and `cloneElement`.

## Chemical grounding and a necessary correction

[IUPAC Blue Book P-14.7.1–2](https://iupac.qmul.ac.uk/BlueBook/P1.html#P-14.7) distinguishes indicated hydrogen in a parent ring system from added indicated hydrogen accompanying a structural modification. P-14.7.1 explicitly contrasts `1H-pyrrole` and `3H-pyrrole`; P-14.7.2 describes bracketed H associated with a suffix operation. These supply independent expectations for this bounded experiment. Substitutive operations are discussed in P-13.1 of the same chapter.

**A mapped indicated-H descriptor is not generally a final H-count constraint.** The observed `1-methyl-1H-pyrazole` and `1-methyl-1H-imidazole` traces map the explicit `1H` descriptor to nitrogen, but each final nitrogen has zero H neighbors after methyl substitution. Conversely, the indicated carbon of `3H-pyrrole` has two H neighbors. A shortcut imposing exactly one final H per H descriptor would therefore be wrong.

The future constraint layer must compose parent-state, suffix and substitutive operations. Also, absence of a written H token does not establish chemical ambiguity: P-14.7.1 permits omission in some general names. This experiment deliberately attributes only explicit token provenance; it does not adjudicate all recognized naming conventions.

Different atom labels also do not establish distinct substances under symmetry. The `1H-pyrazole`/`2H-pyrazole` controls demonstrate mapping to differently numbered atoms; no claim of distinct canonical identities follows.

## Probe results

There are **27 probe runs, representing 26 distinct inputs**; the final repeat checks state isolation.

| Result | Runs | Interpretation |
|---|---:|---|
| Bounded mapping trace | 13 | Includes one repeated input. All traced H nodes have attributable source spans, same-result atoms and matching CML locants, with no observed fragment copying. |
| Abstain after fragment-copy activity | 3 | Two stoichiometric water-adduct challenges and `3,4-dimethyl-1H-pyrazole`; the conservative check can reject benign copying too. |
| No complete trace | 11 | Missing explicit token, generated/default node, repeated word, normalized input, parse failure or warning. |

Public statuses: 24 SUCCESS, 2 FAILURE and 1 WARNING. **27/27** match across released jar, source baseline and diagnostic for status, message, warning type/text, ambiguity flag, SMILES and CML.

Selected controls:

| Input | Observed result |
|---|---|
| `1H-pyrrole`; `3H-pyrrole` | Explicit token → ring fragment → N at locant 1 / C at locant 3; final H counts 1 / 2. |
| `pyridin-2(1H)-one`; `quinolin-2(1H)-one` | Original `2(1H)-` token → added-H node → ring N at locant 1. This is not a complete suffix trace. |
| `3-(1H-imidazol-2-yl)-1H-pyrazole` | First written `1H` maps to the imidazole ring and second to pyrazole, with distinct same-result atoms. |
| `2-(1H-pyrazol-3-yl)-1H-imidazole` | Reversed ring arrangement likewise maps each occurrence to its owning ring. |
| `1-methyl-1H-pyrazole`; imidazole analogue | Parent-H descriptor mapping survives; final mapped N has zero H neighbors. |
| `anthrone` | Generated added-H node is observed with no explicit token attribution. It is not mislabeled source-explicit. |
| `1H-pyrazole - water (2:1)` | A surviving original-atom event does not establish evidence for all copied components; abstain. |
| `1H-pyrazole 1H-pyrazole` | Both words repeat; neither receives an invented original-word span. |
| `1H−pyrazole` using Unicode minus | Parser succeeds after normalization, but source-offset provenance is withheld. |
| `methyl-1H-pyrazole` | WARNING, `APPEARS_AMBIGUOUS`; no selected mapping is exposed. |
| `9H-pyrazole`; trailing garbage | FAILURE; no mapping evidence. |
| `pyrazole`, `pyrrole`, `triazine`, `pyridin-2-ol` | No explicitly attributed indicated/added-H event; no inference that the names are chemically underspecified. |

`1H-pyrazole hydrochloride` has a mapped H descriptor, but this says nothing about whether its charge, protonation and counterion interpretation is fully supported. Mapping status never represents aggregate source support.

## Verification actually executed

| Check | Executed | Passed | Failed | Skipped |
|---|---:|---:|---:|---:|
| Unmodified OPSIN core test suite | 680 | 680 | 0 | 2 |
| Instrumented OPSIN core test suite | 680 | 680 | 0 | 2 |
| Targeted trace tests | 14 | 14 | 0 | 0 |
| Public-output equivalence probes | 27 | 27 | 0 | 0 |

These test counts describe the pinned OPSIN **core** suite, not the absent project's complete retained suite or OPSIN's other Maven modules. The 14 targeted tests inspect independently selected chemical contrasts, nested ownership, non-invention of source spans, copy abstention, warnings, failures and sequential isolation. They do not independently adjudicate all candidate graphs.

Both core builds were independently recompiled with identical per-class hashes. `reproduce.py` was additionally run from a clean checkout into a new output directory, applying the retained patch and rebuilding/rerunning probes and both core suites. See `reproduction.log` and test logs. The reproduction path normalizes Java line endings before applying the textual patch; the original checkout remains unmodified.

## Acceptance assessment

**Met for the bounded experiment:** pinned source and released dependency digest; reproducible class files; token occurrence → transformed node → local owning fragment → final atom correspondence; nested repeated-locant controls; added-H controls; explicit/default distinction for tested paths; output preservation; warning/failure and copy abstention.

**Not met for a general source-form validator:** cloned descriptor/atom lineage; arbitrary original offsets after normalization, inversion or repeated words; exhaustive competing interpretation handling; warning-result ownership; complete mobile-H-site coverage; suffix/substitution operation composition; source-versus-convention reasoning for all names; independent charge/components/isotope/stereo/alias checks; resolver graph correspondence under symmetry; production concurrency.

No CUMA record IDs or molecule-name whitelist appears in the Java instrumentation. Named controls occur in investigative tests only. No provider queries, vendor contacts, license changes or external-gate changes were made.

## Recommendation and handoff

The earlier conclusion that public locant labels alone are insufficient remains valid. The stronger new finding is that **internal indicated-H ownership is recoverable for a useful bounded class**, including nested repeated locants. It is no longer merely a proposed experiment.

The smallest justified next task is an **isolated operation-aware constraint prototype for this demonstrated class**. Preserve the trace as evidence; represent parent-H/valence operations and subsequent substitution/suffix effects separately; reject contradictory final graphs, missing operations and incomplete site coverage. Start with these independent controls and add a withheld validation set before evaluating actual historical cases. Keep unsupported clones and normalization paths as abstentions. A commercial engine is optional additional evidence, not a prerequisite to that next bounded task.

Once the original workspace artifacts are accessible, apply that prototype to the real 81-case taxonomy and report every identity dimension separately. Do not infer recovery counts from the 12 distinct successfully mapped controls, or let a successful H mapping override a charge, alias, stereo or component contradiction. Removal of external corroboration is outside the evidence and scope of this study.

The ontology and source attachment were only read. Their current ontology SHA-256 is recorded in `build_identity.json`; there is no historical frozen file set here against which to verify project-wide byte identity. The untouched pinned checkout is clean. All investigative code and outputs are separate from the production resolver, which is absent.

## Reproduction bundle

The accompanying bundle contains the exact patch, runner, probe script, 14-test suite, rebuild script, raw TSV/CML output, JSON observations, build identity, test reports/logs and public dependency jars. It contains no project credentials or commercial-engine material. Source is obtained from the exact official commit; the Git repository itself is not embedded.

With a clean checkout at the pinned commit and a JDK exposing `com.sun.tools.javac.Main`, run:

```bash
python reproduce.py --source /absolute/path/to/pinned-opsin --out /absolute/path/to/new-output
```

The script refuses an existing output directory and a modified or differently pinned checkout. The bundled class files can also be inspected independently; reproducing the build requires the pinned source.

**BOUNDED_INDICATED_H_MAPPING_DEMONSTRATED — FULL_SOURCE_FORM_VALIDATION_NOT_ESTABLISHED**
