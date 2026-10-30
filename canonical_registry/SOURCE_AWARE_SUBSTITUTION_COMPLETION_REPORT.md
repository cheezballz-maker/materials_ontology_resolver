# Source-aware substitution completion assessment

## Result and decision

**Milestone A: FAIL. Milestone B: FAIL / not established.** The existing source-aware trace remains useful, and a new diagnostic can compare traced attachment sites on a common restored parent. Neither establishes a complete source-associated operation lineage or proves that an independently supplied resolver candidate has the required attachment provenance. Thus the implementation produces `OPERATION_UNKNOWN` for the positive and negative development controls and `UNKNOWN` for the tautomer dimension. It produces no validated `OPERATION_SUPPORTED`, `OPERATION_DIFFERENT`, dimension `SUPPORTED`, or dimension `DIFFERENT`. These are missing capabilities, not evidence that the names are chemically ambiguous.

Do not integrate or use the diagnostic for admission. Change the architecture of the experiment: define a small, explicit operation contract and a source-aware provenance API or independent semantic component, then prove its closure before further corpus testing. The source inspection identifies a limitation of the **current OPSIN result and sidecar instrumentation**, not proof that OPSIN cannot be modified to provide the missing information.

## Operation lineage and root cause

The existing isolated OPSIN 2.9.0 probe, pinned at `b91b610af5ab07560fedb20730d7aef46bb2bca0`, still carries the written locant into `performLocantedSubstitutiveOperations`, records the target and attachment atoms at `joinFragmentsSubstitutively`, and ties the indicated-H claim to the same parent atom. For the three prior positive controls, the observed parent H claim precedes the join and the joining bond survives in the final CML. This correctly avoids requiring a final H on the substituted atom.

The inspected execution path is wider than that event: `StructureBuildingMethods.resolveWordOrBracket` follows recursive locanted processing with unlocanted processing, including feature resolution and further substitutions. `StructureBuilder.buildFragment` subsequently runs special cases, oxidation handling, spare-valency conversion, stoichiometry, explicit H generation, fragment unification and stereochemistry. `FragmentManager.incorporateFragment` transfers atoms and bonds across fragment ownership, while `replaceAtomWithAnotherAtomPreservingConnectivity` creates new bonds, copies locants and removes the original atom. These methods occur in several nomenclature application paths. A surviving target and bond cannot prove that no relevant later operation changed another parent atom, attachment semantics or mobile-H state. The current low-level probe records only selected mutations involving the H-mapped atom, lacks complete source attribution, and does not follow replacement or clone identity. Its final output does not contain a complete operation log or a proof that uninstrumented paths were inapplicable.

A prospective bounded patch would have to retain the selected source parse and fragment atom sets before attachment; track source-associated operations and old-to-new atom/bond identities at each applicable feature, replacement, incorporation and cloning application; record closure through the finalization stages; and reject every outside grammar branch or unsupported transformation. It must prove those restrictions cover all paths admitted by the contract. A few additional mutation hooks would not establish that proof. Supporting general OPSIN nomenclature, all replacements, suffixes, clone propagation and version upgrades would instead be a substantial maintained fork. No new OPSIN patch was made in this task; the pinned existing probe and process isolation remain unchanged.

## Common parent and symmetry

The isolated [common-parent probe](source_aware_substitution_poc/common_parent_probe.py) takes two same-result trace records, cuts only their recorded attachment bonds, and restores one hydrogen at each endpoint as a **comparison construction**, not as a historical intermediate. It requires a single non-ring single bond, one connected input, one reliable traced event per result, successful parsing, and no warnings or clone activity. It separately compares the two restored parent fragments and substituent fragments, using bounded all-isomorphism enumeration with atom element, isotope, formal charge, aromaticity, hydrogen counts and bond structure. It abstains for unsupported stereo, radicals, isotope-labelled hydrogen, mapping overflow, incompatible fragments or malformed evidence. It is separate from full-graph identity comparison and never produces a semantic `SUPPORTED` or `DIFFERENT`.

The three self-comparisons return `ALL_TARGETS_AGREE` as graph observations. The `1-methyl-1H-pyrazole` versus `3-methyl-1H-pyrazole` development pair returns `ALL_TARGETS_DIFFER` after restoring matching parent and substituent graphs; this is stronger than an unexplained full-graph mismatch. However, both cuts came from their own OPSIN name traces. The diagnostic has not established complete lineage for either trace or an equivalent source-grounded partition of an arbitrary resolver candidate, so it is **not** a validated nomenclature contradiction. A synthetic symmetric-parent test yields `SYMMETRY_AMBIGUOUS`, and an enumeration cap yields `UNKNOWN`; no mapping is selected to obtain a desired answer. Clone activity remains an unconditional abstention. The graph observations are not proof of chemical identity or a replacement for independent chemical adjudication.

## Mobile-H completeness and result levels

The candidate experimental subdomain is a single-component, non-stereogenic, non-isotope-labelled, explicitly locanted simple alkyl substitution on one indicated-H heterocyclic parent, without clones, suffix transformations or additional source modifications. Even within it, the current trace does not enumerate and classify all identity-relevant mobile-H sites or show how every permitted subsequent valence and hydrogen transformation constrains them. It also does not independently establish which generated defaults carry source meaning. No closed, chemically validated mobile-H subdomain was established; RDKit tautomer enumeration was not treated as an exhaustive proof.

Therefore `OPERATION_UNKNOWN` and dimension `UNKNOWN` are recorded separately. If a future operation is validated while other mobile-H sites remain unresolved, it may legitimately return `OPERATION_SUPPORTED` and tautomer `UNKNOWN`. Nothing in this experiment promotes a source constraint, relaxes an existing contradiction check, or changes external corroboration.

## Controls and evaluation gates

| Control | Observation | Operation / dimension | Acceptance |
|---|---|---|---|
| `1-methyl-1H-pyrazole` | Trace connects the written locant, methyl and H-parent atom; self parent mapping agrees. | `OPERATION_UNKNOWN` / `UNKNOWN` | Positive not met: lineage incomplete. |
| `1-ethyl-1H-pyrazole` | Same bounded trace with another substituent; self parent mapping agrees. | `OPERATION_UNKNOWN` / `UNKNOWN` | Positive not met. |
| `1-methyl-1H-imidazole` | Same bounded trace on another parent; self parent mapping agrees. | `OPERATION_UNKNOWN` / `UNKNOWN` | Positive not met. |
| `1-methyl-1H-pyrazole` vs `3-methyl-1H-pyrazole` | Restored traced parent/substituent graphs match; all parent mappings place attachments at different sites. | `OPERATION_UNKNOWN` / `UNKNOWN` | Negative not met: independent candidate provenance and lineage not proven. |
| Warning, Unicode-normalized span, clone and repeated-word controls | Existing trace/adapter rejects or does not attribute evidence. | `OPERATION_UNKNOWN` / `UNKNOWN` | Conservative abstention observed. |
| Symmetric synthetic parent and mapping limit | Conflicting possible mapped sites or exceeded cap. | `OPERATION_UNKNOWN` / `UNKNOWN` | Conservative abstention observed. |
| Incompatible substituent, isotope or component | No reliable exact restored fragment pair. | `OPERATION_UNKNOWN` / `UNKNOWN` | Conservative abstention observed. |

The separate [new holdout](source_aware_substitution_poc/completion_holdout_frozen.json) was frozen before implementation-result inspection (SHA-256 `3a59387f34ef57fe6d44f496553a6c6a1e14892c0ba99355b0212cb68e094f11`) and **not run**: development acceptance is not met. The earlier frozen holdout also remains unrun. Its labels are hypotheses, not adjudicated evidence. No 81-case or 183-case post-change replay was performed because the acceptance gates failed; applicability, recovery, precision and recall for a completed capability are unknown. Prior cohort figures are historical and are not post-change results.

## Safety, tests and integrity

The historical eight-case offline safety run under the existing resolver and diagnostic adapter returned `CONFLICT` for 17504 and 30832, and `UNRESOLVED` for 4373, 5684, 5997, 23839, 30142 and the historical dithiazole case. No case was admitted; the new graph probe was not connected to the resolver. Detailed reason codes are in [safety results](source_aware_substitution_poc/safety_results.json).

| Check rerun | Result |
|---|---|
| Pinned baseline OPSIN and existing source-aware instrumented core | Each 680 passed, 2 skipped, 0 failed. |
| Existing indicated-H trace | 14 passed. |
| Common-parent diagnostic and source-aware development, including process isolation | 11 passed. |
| Existing graph correspondence and operation observations | 11 passed. |
| Semantic adapter, including concurrent process isolation | 8 passed. |
| Top-level retained resolver suite | 201 passed. |
| Seven development public outputs | Status, warning, message, SMILES and CML match; seven RDKit Standard and FixedH InChI pairs match. |

An initial unrestricted recursive pytest collection was interrupted; the scoped suites listed above were run successfully. The earlier [rebuild check](source_aware_substitution_poc/rebuild.json) found matching class hashes and event streams across two builds, excluding temporary IDs; no new independent rebuild was performed in this task. The [integrity check](source_aware_substitution_poc/completion_integrity.json) rechecked historical frozen contracts, frozen inputs and provider-cache hashes; all checked values pass. Its four documented historical code exceptions are not verified by that older freeze, so this is not a complete before/after hash proof of every production file. This task edited experimental files and this report only; it did not modify production admission, provider code, registry data, ontology or pinned OPSIN source. No new provider queries were made.

## Architecture recommendation

For an OPSIN continuation, specify and test a narrowly closed grammar and add source-associated operation records and atom lineage at the nomenclature application sites and finalization boundaries listed above. A provenance-aware API with explicit unsupported-path failures is preferable to repeatedly adding diagnostic mutation hooks. For a different approach, evaluate an independently validated semantic parser or a separate constrained source-to-parent interpretation component against the same frozen controls. Prior research found that OpenEye documents atom locants from name parsing, but it did not establish original token ownership, clone lineage or mobile-H semantics, and no licensed alternative was tested. RDKit and FixedH InChI can compare candidate structures; they cannot by themselves supply the source-operation provenance. Neither alternative is assumed to solve the gap without evidence.

OPSIN_ARCHITECTURAL_LIMITATION_IDENTIFIED
