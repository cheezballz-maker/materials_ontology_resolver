# Chemical Correspondence Hardening and Independent Validation v1

Date: 2026-10-30. Isolated, default-off diagnostic; original production behavior and frozen results remain unchanged.

## 1. Executive conclusion

The general partial-stereochemistry correction resolves RW30. Agreement with the original 30 documentary graph labels improves from 29/30 to 30/30, with zero false equivalences or false differences. RW29 remains reference-pending and unscored. This purposive, non-blind, small corpus is not an estimate of population-level accuracy.

Recommend **PROCEED_TO_READ_ONLY_REGISTRY_MATCHING** within the validated chemical scope, with unresolved dimensions and provenance visible. Existing ID reuse and new ID creation are not ready on this evidence. Five real positive corroboration opportunities were investigated; **zero** have independently established upstream structural provenance. Qualified expert review remains pending. All 31 actual diagnostic admission recommendations are withheld.

## 2. Comparator defect, correction and applicability

The old dimension comparator first returned `UNKNOWN` when either graph had any partial/unspecified stereochemistry. Its assertion adapter also handled `UNSPECIFIED` as broad scope before comparing specified constraints. Consequently, a known C1 contradiction was suppressed by the unrelated unknown C2 configuration in RW30.

The new adapter reuses strict parsing, the existing isotope correction, evidence qualification, reconciliation and assessment interfaces. It injects function-local copies with a corrected stereo assertion comparison. It never monkeypatches a module or changes a production comparator/default.

1. Parse the original graphs. Reject unsupported enhanced/relative, non-tetrahedral or other unvalidated stereo classes as unknown.
2. Remove stereo only in temporary mapping views. Require identical constitution, isotope placement, charges, hydrogen counts, bond types, aromaticity and radical attributes. No salt, tautomer, charge or isotope normalization is used to establish a stereo correspondence.
3. Enumerate all full-graph atom correspondences, including symmetry alternatives; validate atom/bond attributes under each mapping. The bound is 4,096 mappings; overflow returns `UNKNOWN` before any contradiction conclusion.
4. Transport ordinary tetrahedral orientation using neighbour-order permutation parity. For ordinary E/Z bonds, transport endpoint and stereo-defining substituent choices. CIP labels alone are not comparison keys.
5. Establish a difference only if **every valid correspondence** violates at least one constraint specified in both graphs. A compatible alternative mapping prevents a difference conclusion. Unspecified elements never supply positive evidence.

| Conditions | Stereo result / rule | Assertion result |
|---|---|---|
| Unavoidable specified contradiction across all mappings | `DIFFERENT` / `ESTABLISHED_STEREO_DIFFERENCE` | `EXACT_INCOMPATIBLE` |
| At least one compatible mapping; some potential stereo unspecified | `UNKNOWN` / `STEREO_SPECIFICITY_UNKNOWN` | `UNKNOWN` |
| Complete compatible ordinary stereo | `EQUIVALENT` / `ALL_RELEVANT_STEREO_SUPPORTED` | `EXACT_COMPATIBLE` |
| Same framework with no potential stereo | `NOT_APPLICABLE` / `STEREO_NOT_APPLICABLE` | `NOT_APPLICABLE` |
| Different framework, invalid input, unsupported class or enumeration overflow | `UNKNOWN`, with explicit reason | `UNKNOWN` |

Explicitly broad/set source assertions are never promoted to exact identity by a compatible graph. Different constitution remains a separate dimension; stereo does not fabricate a positional correspondence across unlike frameworks. Other dimensions can still establish a difference independently.

RW30 has one valid correspondence and one shared specified center: source atom 2 (zero-based; nomenclature C1) is incompatible with the reference. C2 remains unspecified. Represented graph and source-identity correspondence therefore become different. RW23 and RW24 remain unresolved. **No other original corpus outcome changes.**

Implementation: [stereo_comparison.py](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/stereo_comparison.py>); integration: [assessment.py](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/assessment.py>); per-case before/after and full mapping: [evaluation/stereo_before_after.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/evaluation/stereo_before_after.json>).

## 3. Independent controls and limits of independence

The 18 explicit graph controls cover partial incompatible/compatible centers, complete matching/different centers, different traversals, symmetric meso/enantiomeric examples, unspecified stereo, achiral graphs, unlike constitution, relative/enhanced stereo rejection, E/Z, isotope-environment differences and combined bond/center constraints. Supplemental tests cover square-planar rejection and a partial symmetric example where an alternative mapping avoids contradiction.

All controls pass, together with 204 deterministic randomized atom-order assertions and 105 pairwise checks over complete stereoisomer enumerations in four frameworks. These check the parity implementation against RDKit chirality/canonicalization behavior; they are not a second independent chemistry implementation or expert adjudication. All 55 previous correspondence controls also pass through the corrected interface, including source conflict, ambiguity, duplicate-candidate and specificity controls.

Control expectations were declared in the initializer before implementation. The JSON freeze completed after preliminary smoke checks because the first broad snapshot attempt was interrupted. Its original metadata overstates freeze timing; the explicit [controls/provenance_note.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/controls/provenance_note.json>) records this without changing any frozen expectation. No new blind or expert-reviewed benchmark is claimed.

## 4. NIST stereochemical investigation: RW12 and RW17

Both cases are classified **`SOURCE_FIELDS_CONTRADICT`**.

| Case / NIST name | Original molfile interpretation | Reference InChI 1.07.2 from original bytes | Published NIST key |
|---|---|---|---|
| RW12 / R-butan-2-ol, C14898794 | `CC[C@@H](C)O`, R | `/t4-/m1/s1`; `BTANRVKWQNVYAZ-SCSAIBSYSA-N` | `BTANRVKWQNVYAZ-BYPYZUCNSA-N` (opposite) |
| RW17 / S-butan-2-ol, C4221992 | `CC[C@H](C)O`, S | `/t4-/m0/s1`; `BTANRVKWQNVYAZ-BYPYZUCNSA-N` | `BTANRVKWQNVYAZ-SCSAIBSYSA-N` (opposite) |

The preserved molecular-file atoms, coordinates and stereo bond lines are included in the investigation. The narrow-end center is atom 2, with wedge bond 2→3 (one-based). Priorities are O > ethyl > methyl > H. RDKit decoding, direct reference-library interpretation of the unmodified original file, and reference-library interpretation after RDKit serialization agree. This is stronger than merely recomputing descriptors from one decoded SMILES; the two library routes may nevertheless share InChI algorithm ancestry.

JST Nikkaji publishes coherent R and S name/SMILES/InChI triplets consistent with these decoded graphs. This supports the documentary interpretation but does not establish upstream independence. See [JST R](https://jglobal.jst.go.jp/en/detail?JGLOBAL_ID=200907042961101098) and [JST S](https://jglobal.jst.go.jp/detail?JGLOBAL_ID=200907081209460874).

The [InChI Trust conventions](https://www.inchi-trust.org/technical-faq/) use narrow-end wedge interpretation and absolute stereo by default; a zero molfile chiral flag does not itself invert the default absolute configuration. These conventions do not reconcile the observed opposite descriptors. **The internal NIST cause, export history and authoritative curator correction remain unavailable.** No field or frozen label is replaced. Graph-only labels remain scored as originally frozen; full reference-record/source-identity assertions remain unresolved and are excluded from complete-identity claims. An attempted CAS Common Chemistry lookup did not yield accessible usable records and was not used as evidence.

Original bytes, hashes, atom/bond details and actual interpreter outputs: [reference_review/stereochemistry_discrepancies.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/reference_review/stereochemistry_discrepancies.json>).

## 5. Sodium acetate: RW29

Classification: **`REFERENCE_INTERPRETATION_UNRESOLVED`**; graph result remains `CHEMICALLY_UNRESOLVED`; original label remains null/unscored.

The original file explicitly encodes neutral `CC(=O)O[Na]` with an O–Na single bond; the incoming graph is `CC(=O)[O-].[Na+]`. Direct reference InChI produces the published ionic projection and explicitly warns: “Salt was disconnected; Proton(s) added/removed”. Its key is `VMHLLURERBWHNL-UHFFFAOYSA-M`.

The [InChI Trust documentation](https://www.inchi-trust.org/technical-faq/) explains metal disconnection and optional nonstandard reconnection. Thus Standard InChI normalization explains why these explicit graphs can share a descriptor. It does not prove exact identity of their represented bonding or physical form under this project's contract. No general metal-bond equivalence rule was added. Missing evidence is a documented curator depiction convention for this export, a validated applicability boundary with negative controls, and any form/phase evidence needed for a full Substance claim. Metal stripping and universal salt normalization remain prohibited.

Actual original-file/reference-library outputs and missing evidence: [reference_review/sodium_acetate_representation.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/reference_review/sodium_acetate_representation.json>).

## 6. Review-ready package and reference status

[reference_review/REVIEW_QUEUE.md](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/reference_review/REVIEW_QUEUE.md>) prioritizes RW12/RW17/RW29/RW30. [reference_review/chemical_review_package.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/reference_review/chemical_review_package.json>) contains **all 31** original source/reference records, structures and identifiers, original material paths/hashes, frozen expected labels, old and corrected outputs, unresolved dimensions, provenance and proposed reviewer decisions. Sixty-one derived molecular files support inspection where graphs exist; each passes a graph round-trip check and is hashed and labelled as a visualization derivative, never an original deposit or independent evidence. Original NIST molecular-file links are retained separately. RW25 has no source molecular graph and no invented file.

**Qualified chemical expert adjudication: NOT PERFORMED / PENDING.** There are no approved expert labels and no expert-reviewed accuracy population. Automated/documentary findings remain distinct from proposed reviewer decisions.

## 7. Evidence-independence audit and actual positive opportunities

| Status | Required evidential basis |
|---|---|
| `INDEPENDENTLY_ESTABLISHED` | Both original graph assertions and referents, original contributor/deposit or curation, revision/import/standardization chains, traceable upstream roots and a documented audit excluding shared structural ancestry |
| `KNOWN_DEPENDENT` | Shared documented upstream structural origin or explicit derivation/import from the other assertion; candidate-derived descriptors cannot corroborate their originating graph |
| `INDEPENDENCE_UNESTABLISHED` | Missing structure-level ancestry/transform evidence; database names, curator names, downloads, matching graphs and keys cannot fill it |

The audit is a documented evidence procedure, not an automated certification of truth from caller-supplied flags. Synthetic fixtures exercise its required-field/shared-root behavior only. It neither changes provider qualification nor hides valid graph comparisons.

| Real positive opportunity | Chemical scope | Graph result | Upstream independence |
|---|---|---|---|
| PubChem 11838 / ChEBI 38703 | Isopropyl salicylate, ester | Equivalent | Unestablished |
| PubChem 24965990 / ChEBI 82698 | Suvorexant, specified stereo drug | Equivalent | Unestablished |
| PubChem 30231 / ChEBI 83535 | Neohesperidin dihydrochalcone, glycoside | Equivalent | Unestablished |
| PubChem 472335 / ChEBI 90225 | Rubitecan, heterocyclic lactone | Equivalent | Unestablished |
| PubChem 79617 / ChEBI 747036 | Methylsulfonylaniline, sulfone | Equivalent | Unestablished |

Each audit preserves both exact current graph assertions, field referents, source URLs/cache hashes, ChEBI structure ID, available record creators, modification date, compound origins, citations, name attributions and accessions. PubChem property responses lack original contributor SID structures and their CID standardization/revision chains. ChEBI's saved current records lack the structure-level deposit/import/revision chain tying citations to that exact graph. A record creator or record modification date does not establish the origin/version of the structure. No graph-specific common ancestor can be excluded for these pairs.

These gaps are consistent with [PubChem's compound standardization model](https://pubchem.ncbi.nlm.nih.gov/docs/compounds) and [ChEBI's mix of imported, submitted and curated data](https://www.ebi.ac.uk/training/online/courses/chebi-the-online-chemical-dictionary-for-small-molecules/what-is-chebi/where-does-the-data-come-from/). [ChEBI is also a PubChem contributor](https://pubchem.ncbi.nlm.nih.gov/source/ChEBI); that is an import opportunity, not proof of the specific ancestry of an audited CID.

**Five available-provenance investigations; zero independently established positive pairs.** The two actual registry hits instead have known shared PubChem roots. Full receipts and exact gaps: [evaluation/provenance_audit_results.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/evaluation/provenance_audit_results.json>). No new production provider requests were issued. Public documentary observations, including inaccessible lookups, are separately recorded in [reference_review/public_document_observations.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/reference_review/public_document_observations.json>); they are not resolver-provider corroboration.

## 8. Unchanged admission policy: actual evidence versus fixtures

All actual corpus, ten saved-pair and two registry-match assessments remain withheld. No real independently established evidence pair satisfies a demonstrated positive end-to-end corroboration path in this task. Missing official/qualifying-provider inputs are not fabricated to make admission pass.

Ten explicitly **synthetic** fixtures call the unmodified `policy.decision`: qualifying external source routes (unknown and declared independent lineage); no external evidence; known dependence; missing official validation; incomplete source; verified stereo contradiction; existing typed-structure exemption; unqualified NIST; and candidate-derived key lookup. All expected statuses/reasons pass. Synthetic official-validation flags, identifiers and provider rows are labelled synthetic and count as **zero real corroborations**.

Two existing behaviors require care before scaling: (1) explicitly typed structural sources already have a corroboration exemption after required official validation/specificity checks; (2) non-typed qualifying routes accept `SOURCE_DEPENDENCE_UNKNOWN` as well as `SOURCE_INDEPENDENT`. The policy reason `INDEPENDENT_EXACT_FORM_CORROBORATION` therefore does **not** establish audited upstream independence. These are measured existing behaviors, not new exceptions or removed requirements. NIST remains unqualified; all budgets and qualification profiles are unchanged.

Actual and synthetic inputs/results: [evaluation/admission_policy_results.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/evaluation/admission_policy_results.json>).

## 9. Documentary accuracy before and after

| Metric | Original documentary corpus | Post-correction documentary corpus |
|---|---:|---:|
| Scored / total references | 30 / 31 | 30 / 31 |
| Equivalence precision / recall / F1 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 |
| Difference precision / recall / F1 | 1.000 / 0.923 / 0.960 | 1.000 / 1.000 / 1.000 |
| False equivalences / false differences | 0 / 0 | 0 / 0 |
| Necessary / unnecessary abstentions | 3 / 1 | 3 / 0 |
| Agreement | 29/30 (96.67%) | 30/30 (100%) |
| Scored abstention rate | 4/30 (13.33%) | 3/30 (10.00%) |
| Reference coverage | 30/31 (96.77%) | 30/31 (96.77%) |

Original confusion: E→E 14, D→D 12, D→U 1, U→U 3. Corrected: E→E 14, D→D 13, U→U 3. RW29 is excluded from both denominators. No reference label changes. RW12/RW17 remain graph-only documentary labels despite full-record contradictions. Expert-reviewed subset: 0, metrics not evaluated. Independently provenance-established accuracy subset: 0, metrics not evaluated; five provenance-gap investigations must not be mistaken for five independent ground-truth labels. Full machine-readable populations: [evaluation/documentary_accuracy_before_after.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/evaluation/documentary_accuracy_before_after.json>).

Original corpus source-identity results after correction: supported 12, different 12, unresolved 7. All 31 upstream independence assessments remain unestablished. Graph support is not independently corroborated identity or admission.

## 10. Ten saved PubChem–ChEBI pairs

E/D/U below denote represented-graph equivalence/difference/unresolved; S/D/U in source identity are supported/different/unresolved. Every row has independence **unestablished**, independent corroboration **not established**, and admission **withheld**.

| PubChem CID | ChEBI | Identity | Graph | Source identity |
|---|---|---|---|---|
| 11838 | CHEBI:38703 | isopropyl salicylate | E | S |
| 135491830 | CHEBI:81815 | Sethoxydim | U | U |
| 23688465 | CHEBI:87819 | sodium glycodeoxycholate | E | U |
| 24965990 | CHEBI:82698 | suvorexant | E | S |
| 30231 | CHEBI:83535 | neohesperidin dihydrochalcone | E | S |
| 417391 | CHEBI:231274 | N,N-Dimethyl-N-(4-piperidinyl)amine | E | S |
| 472335 | CHEBI:90225 | rubitecan | E | S |
| 593414 | CHEBI:194652 | 1-(3-Chloro-2-hydroxyphenyl)ethan-1-one | E | S |
| 636405 | CHEBI:59213 | cefpiramide | D | D |
| 79617 | CHEBI:747036 | 4-(methylsulfonyl)aniline | E | S |

Totals remain 8 E / 1 D / 1 U; source identity 7 supported / 1 different / 2 unresolved. Sethoxydim retains stereo uncertainty; sodium glycodeoxycholate retains source-scope uncertainty despite graph equivalence.

CID 636405 / ChEBI 59213 remains **different**: the PubChem graph has an N–H/carbonyl pyridone form, while ChEBI specifies a pyridine/O–H form. Their Standard InChI/key coincide through a mobile-H projection; fixed-H InChIs and explicit graphs differ. The original deposition-versus-standardization cause cannot be assigned from available metadata. No special-case override is used. All five judgments and original payloads: [evaluation/pubchem_chebi_pair_results.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/evaluation/pubchem_chebi_pair_results.json>).

## 11. Read-only registry matching

The actual registry contains 112 Substances. Thirty of 31 inputs supplied a graph-derived full-key lookup, spanning 19 distinct keys and 21 distinct source records. Two candidates were retrieved: pyridine (PubChem 1049) → `SUB_00000112`; bromomethane (PubChem 6323) → `SUB_00000006`. Both represented graphs are equivalent; full source identity is **consistency only** because their PubChem ancestry is shared. Both are `KNOWN_DEPENDENT`, have no independent corroboration, and remain withheld for diagnostic admission.

All queries use SQLite `mode=ro`. The remaining 29 case lookups lack candidates in this narrow channel; they do not establish global absence or `NO_MATCH`. No existing ID was assigned to a new record. Actual query parameters/results: [evaluation/registry_candidate_results.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/evaluation/registry_candidate_results.json>); preserved SQL: [evaluation/registry_lookup.sql](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/evaluation/registry_lookup.sql>).

## 12. Safety regressions

**357 unit/integration tests pass:** the 324 retained tests plus 11 stereo tests, 16 corrected-interface tests and 6 policy/audit tests. The 55 frozen correspondence controls pass both original and corrected diagnostic interfaces, alongside 34 NSC frozen controls and 8 unchanged historical safety cases. These are separate denominators, not an inflated unit-test count. All 10 synthetic policy fixtures pass within the policy tests.

Historical CUMA 17504 and 30832 remain conflicts. CUMA 4373, 5684, 5997, 23839, 30142 and the saved dithiazole case remain unresolved. Retained suites cover source-form aggregation, charge, isotopes, acid/base, tautomer, components/stoichiometry, broad referents, candidate ambiguity, source conflicts, circular/derived evidence and existing resolver parsing failures. No false supported result or false difference appears in either frozen 55-control replay. RW23/RW24 abstention and cefpiramide tautomer difference are preserved.

Actual suite counts, logs and assertion denominators: [evaluation/test_results.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/evaluation/test_results.json>); historical results: [evaluation/historical_safety_results.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/evaluation/historical_safety_results.json>).

## 13. Readiness and recommended next milestone

| Requirement | Read-only matching | Existing ID reuse | New ID creation |
|---|---|---|---|
| Chemical comparison | R | P | P |
| Source specificity | R | P | P |
| Source reconciliation | R | P | P |
| Candidate identification | R | P | N |
| Identity uniqueness | R | P | N |
| Evidence independence | P | B | B |
| Admission safety | R | P | B |
| Scientific validation | P | P | P |
| Registry integrity | R | N | N |

Codes: R = `READY_WITHIN_VALIDATED_SCOPE`; P = `PARTIALLY_VALIDATED`; B = `BLOCKED`; N = `NOT_EVALUATED`. Full requirement-specific evidence: [evaluation/readiness_assessment.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/evaluation/readiness_assessment.json>).

Proceed with read-only proposals and explicit uncertainty within the validated graph scope. Before controlled ID reuse, obtain traceable original structural provenance and demonstrate a genuine positive corroboration path under unchanged provider qualification, review the priority reference conflicts, and assess the current typed-source/unknown-dependence admission semantics. ID creation requires further validation and transaction/uniqueness work; it was not implemented. Read-only readiness does not authorize identity reuse or creation.

Remaining scientific limits are ordinary tetrahedral/E-Z scope, bounded symmetry enumeration, unvalidated advanced/relative stereo and metal-bond depiction correspondence, unresolved physical-form scope where graphs alone cannot establish it, a small non-blind documentary corpus and no qualified expert sign-off. The principal evidence limitation is unavailable structure-level upstream ancestry, not a shortage of matching identifiers.

## 14. Reproducibility and integrity

From the workspace root, run `python canonical_registry/chemical_correspondence_hardening/run_all.py`. This replays saved source records, local official InChI, strict RDKit and existing offline suites. Browser documentary observations are preserved as observations from 2026-10-30; the runner makes no new provider/document network calls. Initial protected/control snapshots refuse overwrite. Original production and benchmark files are not execution outputs.

Environment: Python 3.14.3; RDKit 2025.09.6; reference InChI 1.07.2 through the existing JNA bridge. Protected-file SHA-256 verification: **1026 files, zero changes**. Registry digest is unchanged: `57d0d8143c22c89e0a8dcbdb66f06b7c9e61b4081ec0432d739cf9d26cccb15e`. SQLite integrity is `ok`; foreign-key errors, duplicate identity/alias/identifier/structure/reconciliation assertions and orphan rows are all zero. Registry schema, IDs, aliases, ontology, original benchmarks, provider qualification, admission functions and query budgets remain unchanged. New canonical IDs: 0; registry writes: 0; production resolver-provider requests: 0.

[evaluation/integrity_report.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/evaluation/integrity_report.json>); final implementation manifest: [evaluation/implementation_manifest.json](<C:/Users/IT PatsnapSG/OneDrive - Patsnap/13. PatSnap/12. Normalization/main/canonical_registry/chemical_correspondence_hardening/evaluation/implementation_manifest.json>). Public validation evidence is separate from qualifying provider evidence, and generated display files are separate from original molecular files. All outcomes above are documentary/automated findings pending qualified review.

CORRESPONDENCE_HARDENING_V1_VALIDATED_PROVISIONAL
