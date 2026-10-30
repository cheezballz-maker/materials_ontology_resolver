# Form-aware molecular resolver upgrade

Validated 2026-10-27 against the unchanged 300-record CUMA reference set. The upgrade adds **25 reference-confirmed exact identities**, loses none of the previously confirmed exact records, and prevents the known dithiazole tautomer-conflict admission. The final snapshot contains 164 EXACT reconciliations and 162 canonical identities. No false-positive EXACT or false merge was detected in assessable cases; substantial reference uncertainty remains.

The implementation remains **source-independent**. CUMA ingestion and numbered-index reconciliation are retained in the adapter; molecular characterization, comparison, admission and public resolution accept generic names, structures and evidence. No CosIng integration, full CUMA run or legacy-table query was performed in this upgrade.

## Implementation and identity contract

Authority: `C:\Users\IT PatsnapSG\Downloads\Molecular_Substance_Identity_Framework_v1.md`. The ontology and `schema.sql` are unchanged. The original registry/candidate databases and frozen reference labels are unchanged, verified by SHA-256. The new registry is a separate evaluation snapshot, not an in-place migration.

| Component | Change |
|---|---|
| `chemistry.py` | Reused strict parsing/serialization and identifiers; retained original typed structure input. No name normalization is applied to structures. |
| `form_characterizer.py` | Added graph features, component multiplicity, potential/assigned stereo, isotope positions, charge/radicals, explicit H/bond placement, solvent counts and separate source-form interpretation. |
| `identity_comparator.py` | Added dimension-wise equivalence and related-form diagnostics; supported resonance equivalence without moving protons or stripping forms. |
| `policy.py`, `resolver.py` | Replaced the narrow neutral/stereo-free gate with sufficiently specified form admission. Preserved evidence reconciliation, independent alias checks and explicit abstention. |
| `providers.py`, `RegistryBridge.java` | Reused OPSIN/PubChem/reference InChI; preserved actual OPSIN version and added bounded ChEBI full-record corroboration. |
| `registry_builder.py`, `pipeline.py` | Retained CUMA adapter and five-table storage; added all-to-all exact clustering, reuse of exact existing IDs and fresh IDs above the base maximum. |
| Tests/evaluation/verification | Retained old regressions; added form boundaries, ChEBI granularity, ID continuity and complete-link clustering tests; added reproducible 300-case preparation/scoring and read-only verification. |

Every comparison reports EQUIVALENT, DIFFERENT, UNKNOWN or NOT_APPLICABLE for connectivity, stereochemistry, isotope specification, protonation/charge, electronic state, tautomeric form, components and component stoichiometry. EXACT requires supported equivalence in all applicable dimensions **and** a common preserved molecular graph across supported resonance representations. Any significant DIFFERENT or UNKNOWN blocks EXACT. Standard InChIKey, aliases, formula and standardized parents cannot independently establish identity.

Original inputs and validated structures are preserved. MolStandardize normalization/parent views, bounded tautomer enumeration and Fixed-H InChI are diagnostic comparisons. Distinct explicit hydrogen/bond placements can remain distinct despite equal Standard InChIKeys. Counterions, water/solvent components, isotopes, stereo and protonation are never removed to force equality.

Admission requires a supported and sufficiently specified source referent, strict RDKit validation, agreeing reference Standard InChI/key, coherent external corroboration and no unresolved identity dimension. A local candidate needs at least one qualifying corroborating molecular record. Candidate generation after local name parsing fails requires both PubChem and ChEBI evidence; all applicable retrieved records are compared. Provider errors are not chemical evidence. Applicable provider contradictions veto admission.

ChEBI corroboration requires an exact preferred-name/alias match to a released three-star full record. Wildcard residue/class records are excluded from discrete-molecule evidence even when their API `is_r_group` flag is false; their original responses and exclusion diagnostics remain available. Bounded fuzzy-search truncation is recorded, not represented as exhaustive coverage. Failed full-record retrieval blocks acceptance. PubChem and ChEBI are not assumed to have independent upstream sources.

Aliases require their own warning-free OPSIN interpretation, specified form, exact comparison, and either a qualifying ChEBI name attestation or a separate validated PubChem alias lookup. No bulk synonym import occurs. Clustering requires all-to-all exact comparison; ambiguous existing matches cannot allocate a new ID. Public outcomes remain EXACT/NO_MATCH/UNRESOLVED; NO_MATCH never writes an identity automatically. The CUMA tables retain their richer original reconciliation statuses.

## Tools actually used

| Tool | Actual role |
|---|---|
| RDKit 2025.09.6 | Strict parsing, graph/stereo/isotope/charge/component characterization, serialization and generated identifiers. |
| RDKit MolStandardize | Diagnostic parent views and bounded tautomer enumeration only. |
| Reference InChI 1.07.2 via existing JNA bridge | Independent molfile-to-Standard-InChI/key cross-check. Ordinary proton adjustment warnings require agreement. Fixed-H is generated by RDKit diagnostically, not separately reference-validated. |
| OPSIN 3.0-SNAPSHOT | Candidate name parsing with exact query, result, warnings/errors, timeout, library version and JAR hash. |
| PubChem | Existing cached name/property API for candidate retrieval, graph/identifier corroboration and alias queries. No new structure-search adapter was required. |
| ChEBI | New bounded search/full-record adapter for curated name, graph and identifier corroboration. |

No UniChem, CompTox/DSSTox, CAS Common Chemistry, ChEMBL, COD or pymatgen integration was added. No new package dependency was installed. The prior dithiazole source structures in `reviewed_evidence.json` are a transparent, veto-only evidence import, not a new live provider or positive acceptance rule.

Live development collection used 402 PubChem and 387 ChEBI HTTP requests (379/326 initial, 23/61 follow-up), plus existing cached responses. The final `validated` replay made **zero HTTP requests**. Initial budgets were 700 per provider; the follow-up was capped at 100 PubChem/200 ChEBI requests. Provider caches include failures and retrieval timestamps.

## Frozen-reference re-evaluation

All 300 original inputs and 1,220 alias occurrences were retained. Reference judgments and alias attestations were not changed. Engine execution reads source inputs, not expected labels; scoring occurs afterward using a separate graph scorer. Because the previously blinded cases and the known regression informed development, this is **development re-evaluation, not a fresh blinded holdout**.

The old run had a smaller query budget and no ChEBI adapter. These results measure the combined policy/provider/evidence upgrade; they do not isolate the causal effect of form handling from increased external coverage. Synthetic test provider rows are never used for actual CUMA admission.

| Metric | Before | After |
|---|---:|---:|
| Automatic EXACT records | 114 | 164 |
| Reference-confirmed correct EXACT | 58 | 83 |
| False-positive EXACT against frozen adjudication | 1 | 0 |
| EXACT admissions with inconclusive reference | 55 | 81 |
| EXACT precision among adjudicable admissions | 58/59 = 98.31% | 83/83 = 100% |
| Confirmed-correct fraction of all admissions, conservative lower bound | 58/114 = 50.88% | 83/164 = 50.61% |
| Detected false merges / assessed coassigned pairs | 0/2 = 0% | 0/2 = 0% |
| Promoted original alias occurrences | 196 | 244 |
| Reference-confirmed correct aliases | 56 | 81 |
| Confirmed incorrect aliases | 0 | 0 |
| Promoted aliases with inconclusive reference | 140 | 163 |
| Alias precision among adjudicable promotions | 56/56 = 100% | 81/81 = 100% |
| Confirmed-correct fraction of all alias promotions | 28.57% | 33.20% |
| Internal UNRESOLVED / all records | 162/300 = 54.00% | 102/300 = 34.00% |
| All non-admissions / all records | 186/300 = 62.00% | 136/300 = 45.33% |
| Five-status outcome agreement | 172/300 = 57.33% | 168/300 = 56.00% |
| Newly reference-confirmed exact identities | — | 25 |
| Previously confirmed exact records lost | — | 0 |

The old false positive is a **certainty/admission error from contradictory tautomer evidence**, not proof that the chosen amino-thione graph itself is wrong. An UNRESOLVED reference is counted as unverified, not automatically as an incorrect new admission. Two coassigned pairs provide very little evidence about population false-merge rates. Alias metrics count original alias occurrences, excluding the separately stored preferred names; they are not the count of unique stored alias rows.

| Status | Frozen expected | Before | After |
|---|---:|---:|---:|
| EXACT | 112 | 114 | 164 |
| UNRESOLVED | 152 | 162 | 102 |
| CONFLICT | 8 | 5 | 15 |
| OUT_OF_SCOPE | 27 | 19 | 19 |
| INVALID | 1 | 0 | 0 |

The new snapshot has 162 canonical identities: 111 reused exact IDs and 51 freshly allocated IDs. The known conflicted old identity is not included. There are two multi-CUMA exact clusters, 398 unique stored alias assertions (including preferred names), 244 promoted alias occurrences and 976 held occurrences. No production identity was deleted or replaced.

| Form category, non-exclusive | All newly allocated identities | Reference-confirmed newly gained identities |
|---|---:|---:|
| Stereo-defined | 10 | 4 |
| Isotope-labelled | 7 | 5 |
| Protonation/charge | 1 | 1 |
| Salt | 1 | 1 |
| Hydrate | 0 | 0 |
| Solvate | 0 | 0 |
| Tautomer-sensitive diagnostic | 20 | 10 |

Categories overlap and do not sum to total new identities. “Tautomer-sensitive” means the bounded diagnostic enumerator found multiple hydrogen/bond-placement views; it does not assert experimental tautomer populations, admission of multiple tautomers, or use of a tautomer parent. Common-name/provider coverage also contributes gains outside these categories.

## Representative results

All cases below were previously UNRESOLVED except CUMA 5, previously EXACT.

| CUMA index / preferred name | Frozen reference | New result | Evidence or remaining boundary |
|---|---|---|---|
| 4136 / L-Glutamic acid | EXACT | EXACT | Defined L graph agrees across OPSIN, PubChem and ChEBI; wildcard residue alias is not discrete-molecule evidence. |
| 2124 / Deuterium oxide | EXACT | EXACT | Both deuteriums retained; same graph as the frozen reference. |
| 15994 / Isopropanol-d8; 17148 / 1,1,2,2-Tetrachloroethane-d2; 34487 / Tetrahydrofuran-d8 | EXACT | EXACT | Explicit isotope placement and full graph agree; no isotope stripping. |
| 45452 / Phosphoric acid-d3 | EXACT | EXACT | Three deuteriums retained; solution aliases are not the discrete analyte. |
| 6643 / Acetic acid, potassium salt | EXACT | EXACT | Acetate anion plus potassium retained; not neutral acetic acid. |
| 13673 / (S)-3-Hydroxypiperidine; 27548 / (S)-1-N-Boc-2-methylpiperazine; 27611 / (S)-N-Boc-2-Hydroxymethylmorpholine | EXACT | EXACT | Specified stereochemical graphs agree with reference. |
| 1983 / 5-Aminouracil | EXACT | EXACT | Preserved keto graph agrees; tautomer-related name claims are compared separately. |
| 5 / 5-Amino-3H-1,2,4-dithiazole-3-thione | CONFLICT | CONFLICT | `TAUTOMER_CONFLICT`: reviewed amino-thione and imino-thiol evidence shares a Standard InChIKey but differs in H/bond placement. |
| 1264 / Pantoprazole Sodium | EXACT | UNRESOLVED | `IDENTITY_DIMENSION_UNKNOWN`: unspecified sulfoxide stereo. Frozen reference accepted this graph; the authoritative upgrade framework requires sufficiently defined stereo. Label unchanged. |
| 49685 / Ethoxyamine hydrochloride | EXACT | UNRESOLVED | `MULTICOMPONENT_SEMANTICS_UNKNOWN`: neutral base plus HCl depiction; no automatic proton transfer. |
| 6151 / (1R,3R)-3-aminocyclopentan-1-ol hydrochloride | UNRESOLVED | UNRESOLVED | Stereo recognized; neutral-component salt semantics remain unresolved. |
| 6978 / dipotassium 2,2'-biquinoline-4,4'-dicarboxylate trihydrate | EXACT | UNRESOLVED | Local fixed hydrate characterized; current exact-name requests lacked corroboration (`EXTERNAL_EVIDENCE_INCOMPLETE`). |
| 26261 / Phenylpyruvic acid, sodium salt monohydrate | UNRESOLVED | CONFLICT | `IDENTITY_DIMENSION_CONFLICT`: provider graph fails to preserve the named form. |
| 17105 / GSK1120212 (DMSO solvate) | EXACT | UNRESOLVED | `NO_INDEPENDENT_CANDIDATE_CORROBORATION` after local parsing failure; no inferred solvate ratio. |

All per-record outcomes, reasons, reference graphs, changes and category flags are in `form_aware_evaluation/comparison.json`; promoted-alias assessments are in `alias_comparison.json`. The frozen reference files retain their original source evidence.

## Verification and limits

**32 tests passed**, including the existing Java OPSIN/reference-InChI integration checks. Added tests cover equivalent ethanol/Kekule/resonance depictions, constitutional and stereo differences, generic/partial stereo abstention, isotope positions and symmetry, protonation/zwitterions, counterions/ratios, fixed and unspecified hydrates/solvates, same-key tautomers, dithiazole conflict, immutable comparison views, complete-link clustering, stable IDs and ChEBI residue granularity. Legacy protections still cover trailing arbitrary text, slash/backslash preservation, `CN hydrochloride`, invalid-name text fallback, inconsistent identifiers, formula matching and alias-only merging.

Fixed ionic hydrate and explicit DMSO-solvate fixtures pass the admission policy with controlled coherent evidence. These are algorithmic boundary tests, **not independently evidenced real-world admissions**. No hydrate or solvate in this sample obtained automatic EXACT; that part of real-source coverage remains limited.

`verify.py --output form_aware_evaluation/validated` returned **PASS**: five persistent tables, all 164 EXACT reconciliations revalidated, 162 canonical graphs, SQLite/foreign-key integrity valid, and zero duplicate Substance IDs, duplicate alias assertions, duplicate identifier assertions, duplicate CUMA reconciliations or orphan alias/identifier/structure/reconciliation rows. Stored aliases have engine evidence support; that does not replace independent alias precision measurement.

Remaining limits include advanced stereo/atropisomerism, radicals, broad material classes, coordination/extended solids, general mixtures/co-crystals, incomplete isotope placement, neutral base-plus-acid salt depictions and uncorroborated or unspecified solvent stoichiometry. Name-token interpretation is conservative. Reference agreement checks serialization, not source intent. ChEBI retrieval is bounded and evidence sources may overlap. Failed exact-name lookups and 81 unverified admissions/163 unverified alias promotions remain material scaling uncertainties.

The bounded upgrade is implemented and tested, with improved confirmed coverage and no detected degradation on assessable cases. It does **not** establish unrestricted readiness to scale: the next quality gate is independent adjudication of the new/unverified admissions and real fixed hydrate/solvate cases on an untouched holdout. Increased measured coverage must not be mistaken for established population precision.

Reproduction commands are in `README.md`. Final evidence is under `form_aware_evaluation/validated/`; `score_manifest.json` identifies its database/code hashes and confirms protected artifacts are unchanged. Intermediate snapshots are development audit artifacts, not the reported final result.
