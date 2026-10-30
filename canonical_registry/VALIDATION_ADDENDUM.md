# Validation addendum

Verified 27 October 2026 against the existing SQLite databases, current implementation, saved `evaluation/results.json`, and fresh test/verification runs. No pipeline or registry data changes were made.

## 1. Actual persistent schema

Extracted from `sqlite_master` and `PRAGMA table_info`, `foreign_key_list`, `index_list` and `index_info`. `NN` means explicitly declared `NOT NULL`; all columns have no declared default.

| Table | Actual columns and declared types | Primary key / uniqueness | Foreign key |
|---|---|---|---|
| `substance_identity` | `substance_id TEXT`; `preferred_name TEXT NN`; `identity_status TEXT NN` | `substance_id` | None |
| `substance_alias` | `substance_id TEXT NN`; `alias TEXT NN` | `(substance_id, alias)` | `substance_id → substance_identity(substance_id)` |
| `substance_identifier` | `substance_id TEXT NN`; `identifier_type TEXT NN`; `identifier_value TEXT NN` | `(substance_id, identifier_type, identifier_value)` | Same |
| `substance_structure` | `substance_id TEXT NN`; `structure_type TEXT NN`; `structure_value TEXT NN` | `(substance_id, structure_type, structure_value)` | Same |
| `substance_reconciliation` | `cuma_index INTEGER`; `substance_id TEXT` nullable; `resolution_status TEXT NN`; `reason TEXT NN` | `cuma_index INTEGER PRIMARY KEY` (rowid alias) | Same |
| Temporary/local `candidate` | `cuma_index INTEGER`; `name TEXT`; `aliases TEXT`; `status TEXT`; `diagnostic TEXT`; `evidence_json TEXT` | `cuma_index INTEGER PRIMARY KEY` (rowid alias) | None |

The first four tables each have one unique primary-key index, named `sqlite_autoindex_<table_name>_1`, on the key columns in the order above. Reconciliation and candidate use the rowid key and have no separate indexes. **No secondary indexes or additional UNIQUE constraints exist**: neither aliases nor identifier type/value pairs are globally unique across Substances, and reconciliation has no index on `substance_id`.

Actual CHECK constraints:

- Identity: `identity_status='ACCEPTED'`.
- Reconciliation: status in `('EXACT','UNRESOLVED','CONFLICT','OUT_OF_SCOPE','INVALID')` and `(resolution_status='EXACT')=(substance_id IS NOT NULL)`.
- No other CHECK constraints; candidate JSON is stored as nullable TEXT without database JSON validation.

All foreign keys use `NO ACTION` on update/delete. SQLite foreign-key enforcement is connection-specific; the build enables it. These are ordinary, non-STRICT rowid tables. In particular, `substance_identity.substance_id TEXT PRIMARY KEY` does **not** explicitly enforce non-nullness under SQLite's rowid-table semantics; the current data contain zero null IDs. Integer primary keys uniquely identify stored rows but can auto-assign a rowid when inserted as NULL.

## 2. Implemented identity decision matrix

`exact_key` is `(canonical isomeric SMILES, full Standard InChIKey)`. Pairwise inequality prevents merging; it is not itself a record status. The table distinguishes a comparison between separate identities from contradictory evidence for one claim. `AUTO_ACCEPT` is the actual internal spelling; persistence converts it to `EXACT`.

The implementation has literal reason strings, **not separate reason codes**. Abbreviations below are only document references:

| Ref | Actual reason string |
|---|---|
| A | `Warning-free OPSIN, RDKit, official InChI and unique PubChem graph agree` |
| F | `Form, stereo, isotope, size or element boundary held for review` |
| D | `Local and provider molecular graphs differ or lookup is ambiguous` |
| N | `No validated local molecular candidate` |
| O | `Explicit excluded material family` |

| Identity situation | Current decision and actual rule/reason |
|---|---|
| Exact validated same structure | **AUTO_ACCEPT / EXACT (A)** only after the admission/evidence gates pass; accepted records with the same exact key cluster together. Equality alone is insufficient. |
| Constitutional isomer | Different keys, never merged. Each can independently become **EXACT (A)**; local/provider disagreement within one claim is **CONFLICT (D)**. |
| Specified vs unspecified stereochemistry | Any RDKit potential-stereo entry fails eligibility: **UNRESOLVED (F)** for both forms. Keys remain distinct. |
| Stereoisomer | **UNRESOLVED (F)**; distinct stereo graphs are not merged. |
| Isotope/isotopologue difference | Isotope-bearing candidate: **UNRESOLVED (F)**; no local parse: **UNRESOLVED (N)**. Isotope-free counterpart is assessed separately. |
| Protonation/charge difference | Nonzero total formal charge: **UNRESOLVED (F)**. No charge-parent merge; neutral counterpart assessed separately. Zwitterions are not explicitly detected as a separate class: other gates, including InChI warnings, apply. |
| Salt vs parent | Multiple components or a matched form keyword: **UNRESOLVED (F)**. Parent assessed separately; no stripping. |
| Hydrate/solvate | Parsed multiple components or matched form keyword: **UNRESOLVED (F)**; parse failure: **UNRESOLVED (N)**. |
| Tautomer | No blanket tautomer exclusion. Different preserved graphs never merge, even with the same Standard InChIKey. Each may independently be **EXACT (A)**; cross-provider tautomer disagreement is **CONFLICT (D)**. |
| Disconnected/multicomponent structure | `components != 1`: **UNRESOLVED (F)**; component multiplicity retained. |
| Conflicting provider structure | **CONFLICT (D)**; inconsistent supplied identifiers: `Provider structure and InChI/InChIKey disagree`; malformed provider representation: `Provider structure is malformed or unsupported`. |
| Insufficient evidence | **UNRESOLVED**: N; `Official InChI disagreement or unavailable`; `Official InChI validation required`; `External corroboration not queried (request budget/offline)`; `External provider error; no corroboration`; or `Exactly one corroborating provider record required`, depending on the failing gate. |
| Excluded material family | Scope-regex match: **OUT_OF_SCOPE (O)**. This is lexical screening, not exhaustive classification: `polyethylene` currently remains **UNRESOLVED (N)**. |
| Invalid source record | **INVALID**: `Malformed CUMA alias list` or `Missing preferred name`. Strict structure parsing raises `ValueError`; a failed local claim can be marked INVALID in evidence while the final named record is **UNRESOLVED (N)**. |

Order matters: source validity/scope precede reconciliation; official disagreement precedes provider comparison; provider conflict precedes the eligibility gate. In the production build, external queries are made only for eligible local candidates. A discordant **alias** is held back rather than automatically changing an accepted preferred-name record to CONFLICT; its reason is `Unvalidated, conflicting, ambiguous, or parent record not accepted`.

## 3. Evaluation and regression cases

All **37 saved labels** are listed below. Name-case negative labels mean only “do not admit,” not a required choice between UNRESOLVED and OUT_OF_SCOPE. Pair labels test equality, not admission. Saved external evaluation evidence was inspected, not refreshed; the existing unit/integration suite was rerun.

| Input/case | Important identity issue | Expected | Actual | Pass/fail |
|---|---|---|---|---|
| ethanol | Straightforward molecule | Admit `CCO` | AUTO_ACCEPT, matching graph | PASS |
| ethyl alcohol | Common alias | Admit `CCO` | AUTO_ACCEPT, matching graph | PASS |
| acetone | Carbonyl identity | Admit `CC(C)=O` | AUTO_ACCEPT, matching graph | PASS |
| benzene | Aromatic identity | Admit `c1ccccc1` | AUTO_ACCEPT, matching graph | PASS |
| acetic acid | Neutral acid form | Admit `CC(=O)O` | AUTO_ACCEPT, matching graph | PASS |
| dimethyl ether | Same formula as ethanol | Admit `COC` | AUTO_ACCEPT, matching graph | PASS |
| methylamine hydrochloride | Salt | Do not admit | UNRESOLVED | PASS |
| methylammonium | Charged form | Do not admit | UNRESOLVED | PASS |
| (S)-alanine | Specified stereo | Do not admit | UNRESOLVED | PASS |
| alanine | Unspecified stereo | Do not admit | UNRESOLVED | PASS |
| ethanol monohydrate | Hydration | Do not admit | UNRESOLVED | PASS |
| deuterium oxide | Isotope; no local candidate | Do not admit | UNRESOLVED | PASS |
| polyethylene | Polymer name missed by scope regex | Do not admit | UNRESOLVED | PASS |
| poly(ethylene) | Recognized polymer syntax | Do not admit | OUT_OF_SCOPE | PASS |
| silicon bronze | Alloy | Do not admit | OUT_OF_SCOPE | PASS |
| ethanol mixture | Mixture | Do not admit | OUT_OF_SCOPE | PASS |
| arbitrary_invalid_chemical_zzzz | Invalid name | Do not admit | UNRESOLVED | PASS |
| CN hydrochloride | SMILES-prefix trap as a name | Do not admit | UNRESOLVED | PASS |
| `CCO` / `OCC` | Traversal | Same key | Same key | PASS |
| `c1ccccc1` / `C1=CC=CC=C1` | Kekulé representation | Same key | Same key | PASS |
| `CCO` / `COC` | Constitutional isomers | Different keys | Different keys | PASS |
| `N[C@@H](C)C(=O)O` / `N[C@H](C)C(=O)O` | Enantiomers | Different keys | Different keys | PASS |
| `NC(C)C(=O)O` / `N[C@H](C)C(=O)O` | Unspecified/specified stereo | Different keys | Different keys | PASS |
| `F/C=C/F` / `F/C=C\F` | Geometric stereo | Different keys | Different keys | PASS |
| `CN` / `C[NH3+].[Cl-]` | Salt/parent | Different keys | Different keys | PASS |
| `CN` / `C[NH3+]` | Protonation | Different keys | Different keys | PASS |
| `CCO` / `CCO.O` | Hydrate | Different keys | Different keys | PASS |
| `CCO` / `CCO.CO` | Solvate | Different keys | Different keys | PASS |
| `O=c1cccc[nH]1` / `Oc1ccccn1` | Tautomers sharing Standard InChIKey | Different exact keys | Different exact keys | PASS |
| `CCO` / `[13CH3]CO` | Isotopologues | Different keys | Different keys | PASS |
| `C` / `[CH3]` | Radical | Different keys | Different keys | PASS |
| `NCC(=O)O` / `[NH3+]CC(=O)[O-]` | Zwitterion | Different keys | Different keys | PASS |
| `CO.O` / `CO.O.O` | Component multiplicity | Different keys | Different keys | PASS |
| ethyl alcohol → ethanol alias | Exact name correspondence | Promote | Promoted | PASS |
| acetone → ethanol alias | Misleading alias | Hold | Held | PASS |
| methylamine hydrochloride → ethanol alias | Different substance/form | Hold | Held | PASS |
| arbitrary_invalid_chemical_zzzz → ethanol alias | Unvalidated name | Hold | Held | PASS |

Explicit legacy regressions in the latest test run:

| Regression | Tested input/assertion | Actual result |
|---|---|---|
| Trailing arbitrary text | `CCO arbitrary text`, `CCO` + tab + `ethanol`, `CCO \|foo\|`; ethanol InChI plus ` arbitrary`, `/garbage`, or `garbage` | All raise `ValueError`; PASS |
| Slash/backslash corruption | The geometric-stereo pair above remains distinct | PASS; no structure-string name normalization |
| Parent/salt collapse | `CN hydrochloride` rejected as typed SMILES; named input remains unresolved; OPSIN `methylamine hydrochloride` gives `CN.Cl`; charged salt remains distinct from `CN` | PASS |
| Invalid name as canonical text | `arbitrary_invalid_chemical_zzzz`: OPSIN FAILURE; missing local evidence yields UNRESOLVED | PASS; no canonical text fallback |
| Inconsistent supplied structure/identifier | Ethanol fixture with methane InChIKey | CONFLICT; PASS. An InChI-only mismatch is checked by the same code branch but has no separate dedicated test assertion. |

**Latest unit/integration run: PASS, 13/13 test methods** (`python -m unittest test_registry -v`). This does not establish representative population precision; in particular, negative name labels do not validate the completeness of scope classification.

## 4. Registry integrity verification

`python verify.py` passed: 114 EXACT reconciliations revalidated, 112 unique canonical graphs, all stored aliases supported, SQLite integrity `ok`, and no foreign-key violations. Additional SQL used read-only connections; duplicate counts below are violating key groups, and orphan counts are rows. No data were repaired.

| Check | Count | Result |
|---|---:|---|
| Duplicate `substance_identity.substance_id` | 0 | PASS |
| Null canonical `substance_id` | 0 | PASS |
| Orphan alias rows | 0 | PASS |
| Orphan identifier rows | 0 | PASS |
| Orphan structure rows | 0 | PASS |
| Non-null reconciliation references to nonexistent Substances | 0 | PASS |
| Duplicate `(substance_id, identifier_type, identifier_value)` assertions | 0 | PASS |
| Duplicate `(substance_id, alias)` rows | 0 | PASS |
| Duplicate `cuma_index` reconciliation rows | 0 | PASS |

Duplicate checks used `GROUP BY <declared key> HAVING count(*)>1`; orphan checks used a left join to `substance_identity` with a missing parent. Cross-Substance reuse of an identifier value is not prohibited by this schema and is not counted as a duplicate assertion. **Overall registry integrity: PASS.**

## 5. Implemented evidence providers

| Provider/tool | Current status | Implemented role |
|---|---|---|
| RDKit | IMPLEMENTED_AND_USED | Strict structural validation, graph serialization, descriptors and generated InChI/key consistency checks |
| RDKit MolStandardize | IMPLEMENTED_AND_USED | Diagnostic comparison views only; no canonical parent replacement |
| Official/reference InChI | IMPLEMENTED_AND_USED | JNA reference library 1.07.2 generates InChI/key from RDKit molfile; structural/serialization cross-check, not independent source corroboration |
| OPSIN | IMPLEMENTED_AND_USED | Deterministic name-to-structure candidate generation with status/message capture |
| PubChem | IMPLEMENTED_AND_USED | Bounded name-based external corroboration; returned structures and identifiers validated locally |
| ChEBI | DEFERRED | No adapter in this POC |
| UniChem | DEFERRED | No adapter in this POC |
| CompTox/DSSTox | DEFERRED | No adapter in this POC |

None of the listed providers is IMPLEMENTED_BUT_NOT_USED_IN_THIS_RUN.

## 6. Final self-assessment

1. The POC implementation is complete within its current bounded admission scope and external-query budget.
2. The full CUMA dataset has not been canonicalized; full local analysis produced only the accepted subset documented in the existing reports.
3. The most important remaining limitation before increasing the external-query budget is the absence of a representative, independently adjudicated CUMA validation set establishing admission, alias-promotion and false-merge precision beyond the small engineering evaluation.
