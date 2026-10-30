# Exact-form evidence upgrade — development re-evaluation

2026-10-28. The reusable acquisition increment recovered **8 reference-confirmed identities** on the frozen 360-record set. Automatic EXACT admissions increased from 90 to 101: **8 confirmed recoveries and 3 new unverified admissions**. No confirmed false-positive EXACT, false merge, revoked admission or changed retained molecular identity was observed. This is **development re-evaluation**, not a fresh independent holdout: the existing benchmark informed failure analysis.

## Architecture and retrieval

The new `evidence_retrieval.py` coordinates bounded retrieval and evidence classification. `providers.py` adds identifier/structure retrieval and one new provider, GSRS. `resolver.py` consumes this evidence through the existing form characterizer, comparator and admission-policy module. `pipeline.py` supplies budgets/caches; `verify.py` replays acquisition evidence; `registry_builder.py` adds only generic UNII identifier mapping.

`chemistry.py`, `form_characterizer.py`, `identity_comparator.py`, `policy.py`, `schema.sql`, the ontology, authoritative identity framework and original tests are unchanged. Public lookup outcomes remain EXACT / NO_MATCH / UNRESOLVED; internal registry diagnostics retain CONFLICT and other existing statuses. Five persistent tables, SUB identifiers and allocation remain unchanged. Earlier registries and frozen references were preserved; the new 100-Substance registry is an evaluation snapshot in `evidence_upgrade/run/`. No full CUMA run was performed.

The acquisition sequence is:

1. Preserve and query original source claims; validate returned structures and identifiers. Supplied typed identifiers are retrieval claims, not automatic canonical assertions.
2. For an otherwise eligible hypothesis with insufficient evidence, use regenerated full InChIKey, complete SMILES/InChI, or an already validated provider name. No parent transformation generates a key.
3. Compare every retrieved structure. Related/unknown **discovery** forms remain diagnostics and cannot corroborate. Contradictions returned against an **original source claim** remain blocking evidence; no provider takes precedence. Invalid provider structures/keys are never repaired.
4. For parser failure, an original source alias can supply local nomenclature support only after warning-free OPSIN parsing, exact graph agreement, its own eligibility check and separate exact-alias external attestation. It cannot supply missing preferred-name stereo/form intent. A provider-generated name cannot become independent local source evidence.
5. Reapply existing form, dimension, reference-InChI and admission checks. Validate aliases individually; allocate IDs separately.

The runtime does not import frozen judgments or add CUMA-specific name/index exceptions. The pre-existing reviewed contradiction fixture remains unchanged and veto-only. See [implementation details](EVIDENCE_RETRIEVAL.md) and [evaluation protocol](evidence_upgrade/PROTOCOL.md).

## Providers, modes and provenance

| Provider/tool | Used in this development run | Role and boundary |
|---|---|---|
| OPSIN | Preferred names and original aliases | Deterministic candidate/local nomenclature support; never admission by parser success alone |
| RDKit | Full structures and generated identifiers | Strict structural validation and preserved molecular graph |
| MolStandardize | Existing comparison views | Diagnostic comparison only; no parent merge/retrieval key |
| Reference InChI | Existing agreement check | Validation; disagreement remains blocking |
| PubChem | 216 original-name, 152 alias-validation, 18 full-key queries | Candidate evidence and complete-form corroboration |
| ChEBI | 216 original-name, 18 full-key, 16 validated-provider-name queries | Curated corroboration, subject to full-graph comparison |
| GSRS, NCATS public deployment | 59 exact-name and 14 complete-SMILES queries | New structured chemical registration evidence, including full structures and moieties |

These are logical operations, including cache hits and empty/error results, not independent observations. Actual new HTTP requests were **45 PubChem + 34 ChEBI + 89 GSRS = 168**; GSRS full-record fetches explain its larger HTTP count. No budget was exhausted (caps 1,800 / 3,000 / 500). Original name-query caches were copied into the separate run. Cached errors were retained; for example, 185 ChEBI logical operations returned 404, not corroboration.

PubChem InChI and complete-SMILES modes are implemented and passed live ethanol smoke checks, but were unnecessary in the 360-record run after full-key retrieval. Typed CID, ChEBI ID, CAS, EC and UNII input paths are implemented; these packets contained names/aliases, so supplied-identifier paths were not exercised by this benchmark. Source identifier lookup does not automatically promote the identifier.

GSRS was selected for reusable structured chemical registrations, explicit moieties and structure-linked references. Only approved PRIMARY/COMPLETE chemical records within supported stereo scope qualify. Molfile, SMILES, InChI/key and positive integer component ratios must agree; mixtures, fractional-ratio assembly and unsupported forms are withheld. Its adapter has caching, bounded results, timeouts and error handling. GSRS corroborated **5 admitted records, including 4 new admissions**, but **none of the 11 gains depended exclusively on GSRS**. Its incremental admission benefit has therefore not been isolated. NIST/supplier adapters were not added. [GSRS API documentation](https://gsrs.ncats.nih.gov/api-documentation) and saved [live smoke results](evidence_upgrade/provider_smoke/results.json) document the interface used.

Each result retains provider, record ID, query and origin, timestamp, URL, structure/identifiers and available lineage. Repeated record/structure evidence is deduplicated; conflicting graphs remain. FDA/NCATS mirrors share a family. Unknown lineage is UNDETERMINED, not independent corroboration. Two external-only provider hits require documented nondependent lineages; current adapters do not assert such independence merely from provider names. Original-alias recovery supplies local nomenclature plus external corroboration; two PubChem queries do **not** count as two independent external sources. This conservative evidence-sufficiency gate does not change chemical equivalence.

## Tests and integrity

**62/62 tests passed:** all 32 original tests, unchanged, plus 30 retrieval tests. Added coverage includes identifier recovery after name failure; exact stereo/isotope retention; salt versus parent; hydrate/solvate versus unsolvated form; fixed tautomers sharing a Standard InChIKey; dependent/mirrored sources; conflicting structures/keys; validated original-alias parser recovery; arbitrary/incomplete name rejection; GSRS structure/ratio consistency; query limits, caching and offline behavior. These are controlled regression cases, not independent accuracy estimates.

The verifier returned **PASS**: 101 EXACT reconciliations, 100 canonical graphs, five tables, SQLite/FK integrity intact; zero duplicate identities, identifier assertions, aliases or CUMA reconciliations; zero orphan alias, identifier, structure or reconciliation rows. Alias evidence replay confirms internal support, not independent chemical truth. See [test log](evidence_upgrade/tests.log) and [verification result](evidence_upgrade/run/verification.json).

## Before/after metrics

Both snapshots use the same 360 inputs, unchanged frozen labels and unchanged scoring definitions.

| Metric | Before | After |
|---|---:|---:|
| Automatic EXACT | 90 | 101 |
| Confirmed correct / false-positive / unverified EXACT | 74 / 0 / 16 | 82 / 0 / 19 |
| Adjudicable EXACT precision | 74/74 = 100% | 82/82 = 100% |
| Confirmed EXACT recall | 74/167 = 44.31% | 82/167 = 49.10% |
| False merges / assessable merged pairs | 0/1 | 0/1 |
| Non-EXACT abstention | 270/360 = 75.00% | 259/360 = 71.94% |
| UNRESOLVED / CONFLICT / OUT_OF_SCOPE / INVALID | 237 / 14 / 19 / 0 | 225 / 15 / 19 / 0 |
| Promoted source alias claims | 114 | 133 |
| Correct / incorrect / unverified promoted aliases | 24 / 0 / 90 | 29 / 0 / 104 |
| Adjudicable alias precision | 24/24 = 100% | 29/29 = 100% |
| Status agreement | 219/360 = 60.83% | 223/360 = 61.94% |

Recall increased **4.79 percentage points**. All 90 reference-established nonadmissible cases remained withheld. All prior admissions and alias promotions were retained; no retained admitted graph changed. The 19 added alias promotions comprise 5 confirmed and 14 unverified claims. Alias metrics count source claims, not the 231 deduplicated stored alias strings (which also include accepted preferred names).

The precision denominators exclude inconclusive references: only **82/101 admissions** and **29/133 promoted alias claims** are confirmed. Descriptive Wilson 95% intervals are 95.52–100% for adjudicable EXACT precision and 88.30–100% for adjudicable alias precision; these do not correct for benchmark reuse or unverified cases. One assessable merged pair is inadequate to establish a general false-merge rate. Detailed metrics and case comparisons are in [after_metrics.json](evidence_upgrade/after_metrics.json) and [comparison.json](evidence_upgrade/comparison.json).

## Every new admission: recovery and safety review

All 11 new admissions passed internal safety review: the original referent was classified SPECIFIED; every used comparison dimension was EQUIVALENT or NOT_APPLICABLE; reference InChI agreed; the admitted graph matched its original validated local support. No parent stripping, stereo invention, isotope removal, inferred proton transfer, solvent removal or forced tautomer normalization was used. Internal consistency does not settle an inconclusive frozen reference.

| CUMA | Preferred name (long names abbreviated here) | Enabling capability and form review | Frozen-reference verdict |
|---|---|---|---|
| 1114 | N-Boc-L-phenyl alanine | Full-key PubChem corroboration; original L configuration retained | Confirmed |
| 23559 | 2-thiophenecarboxylic acid, sodium salt | Full-key PubChem and complete-structure GSRS; explicit anion plus Na+, no neutral-parent substitution | Confirmed |
| 33262 | dipropetryn | Original systematic alias parsed and externally attested; same graph as preferred-name candidate | Confirmed |
| 34916 | Boc-D-Ser-OBzl | Original benzyl N-Boc-D-serinate alias validated; D configuration and protecting groups retained | Confirmed |
| 36647 | N-benzyloxycarbonyl-β-alanine | Full-key PubChem and complete-structure GSRS; unchanged neutral protected β-alanine | Confirmed |
| 37542 | (R)-baclofen | Original R systematic alias validated; PubChem/GSRS agree on the same enantiomer | Confirmed |
| 42996 | FMOC-L-2-Chlorophe | Original Fmoc-2-chloro-L-phenylalanine alias validated; L configuration and hydrogen/bond graph retained | Confirmed |
| 45305 | 7-(β-D-glucopyranosyloxy)-5-hydroxy-2-(4-hydroxyphenyl)-4H-1-benzopyran-4-one | Full-key PubChem/ChEBI; β-D sugar stereochemistry and complete glycoside retained | Confirmed |
| 9152 | (2S) protected azetidinyl-piperidine systematic name | Full-key PubChem agrees with original explicit 2S parse; frozen evidence lacked sufficient corroboration | Unverified |
| 46724 | (3S) bromopyridyl-benzodiazepinone propionic acid methyl ester | Full-key PubChem retains source 3S; frozen research established only an unspecified alternative | Unverified |
| 52217 | N-Phenyl-N-nitroso-p-toluenesulfonamide | Full-key PubChem supports preferred N-phenyl graph; all seven misleading isotope/N-methyl aliases remain rejected | Unverified |

The **8 confirmed gains** divide into **4 full-key corroboration recoveries and 4 original-alias parser recoveries**. All eight belonged to the previous 32 evidence-blocked reference-EXACT cases: **8/32 recovered**, 24 still withheld. They are not new chemical identity exceptions.

The three unverified cases retain their frozen UNRESOLVED references and are neither confirmed successes nor established false positives. No newly admitted hydrate, solvate or isotopically labelled case demonstrates improvement in those categories; the relevant regression tests provide only controlled boundary checks. Sodium salt 23559 is the only new metal-containing admission and retains the explicit counterion. Full original names, SMILES, InChIKeys, form features and query traces for every new admission are in [new_admission_safety.json](evidence_upgrade/new_admission_safety.json); individual review notes are in [MANUAL_SAFETY_REVIEW.json](evidence_upgrade/MANUAL_SAFETY_REVIEW.json).

## New conflict and remaining gaps

**CUMA 49210, Paroxetine HCl Hemihydrate:** UNRESOLVED → CONFLICT (`IDENTITY_DIMENSION_CONFLICT`). The original cached PubChem name result already contained CID 5282487 (2 drug : 2 HCl : 1 water), CID 43815 (parent) and CID 62878 (hydrochloride without water). Comparing all original-claim structures before the external-only sufficiency gate exposes their component/charge mismatch. This was not a GSRS discovery or a new HTTP result. No provider was selected as winner; the frozen UNRESOLVED reference was not revised, and the record remains unadmitted.

Of 167 reference-EXACT records, **85 remain withheld**. Retrieval cannot supply missing source intent or resolve excluded semantics. Both confirmed solvates—17854 Darunavir Ethanolate and 32795 ledipasvir compound with acetone—remain blocked by `MULTICOMPONENT_SEMANTICS_UNKNOWN;STEREO_SOURCE_INTENT_UNSPECIFIED`. Deucravacitinib 8093 remains blocked by `ISOTOPE_POSITION_UNKNOWN`; two reference-EXACT cases still lack documented evidence independence. Other limitations include missing validated candidates, hydrate stoichiometry, stereo interpretation and coordination/electronic-state support. None was repaired by a parent lookup or altered identity rule.

Runtime hashes were frozen before prediction; scoring followed the completed run. [SCORING_MANIFEST.json](evidence_upgrade/SCORING_MANIFEST.json) records reference/prediction hashes and protected-file checks. [FINAL_VERIFICATION.json](evidence_upgrade/FINAL_VERIFICATION.json) checks those hashes again after reporting. No reference relabeling or runtime tuning followed the results.

The bounded retrieval mechanism is validated by confirmed gains and preserved tested boundaries. Its general accuracy and GSRS-specific incremental benefit remain unestablished. **Recommended next step: another fresh blinded holdout**, with stronger alias adjudication and more exact/near-form pairs, plus independent review of the three new unverified admissions. Increased CUMA coverage does not justify a full CUMA run.

**EVIDENCE_RETRIEVAL_INCREMENT_VALIDATED**
