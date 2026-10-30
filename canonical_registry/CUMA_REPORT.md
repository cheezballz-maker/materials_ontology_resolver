# CUMA registry POC results

Run date: 27 October 2026 (Asia/Singapore). Input: CUMA v1 (ENG Only). Ontology: unchanged Substance Ontology 0.2.0.

This is a deliberately bounded seed registry. Every source record and name/alias was locally analyzed; only the first 120 eligible unique preferred-name requests were budgeted for external corroboration. Low coverage is intentional.

| Measure | Count |
|---|---:|
| Total CUMA records | 53,667 |
| Preferred names with validated local molecular candidate graphs | 39,006 |
| Local candidates within narrow admission envelope, before corroboration | 22,285 |
| EXACT | 114 |
| UNRESOLVED | 53,098 |
| CONFLICT | 5 |
| OUT_OF_SCOPE | 450 |
| INVALID | 0 |
| Canonical Substances created | 112 |
| Multi-CUMA exact clusters | 2 |
| CUMA alias occurrences accepted | 196 |
| CUMA alias occurrences held/rejected | 202,295 |
| Distinct stored aliases including validated preferred names | 300 |

The local molecular-candidate count is not a confirmed in-scope count. A parsable graph does not establish that a material is a discrete molecule. EXACT records are confirmed admissions under the narrow v1 envelope; other molecular and form claims remain unadjudicated. Alias occurrence counts include repeated source strings; stored aliases are deduplicated within each Substance.

## Principal decision reasons

| Reason | Records |
|---|---:|
| External corroboration not queried (request budget/offline) | 22,163 |
| Form, stereo, isotope, size or element boundary held for review | 16,721 |
| No validated local molecular candidate | 14,211 |
| Explicit excluded material family | 450 |
| Warning-free OPSIN, RDKit, official InChI and unique PubChem graph agree | 114 |
| Local and provider molecular graphs differ or lookup is ambiguous | 5 |
| External provider error; no corroboration | 3 |

## Evaluation

13 unit/integration test methods passed before the full run. The explicit name gold set contains 18 cases and 6 automatic admissions. Admission precision: 100%; alias promotion precision: 100%; false-merge rate: 0%; abstention: 66.7%; coverage: 33.3%.

These metrics describe only the small engineering gold set, including 15 graph pairs (13 negative pairs) and four alias claims (one promoted). They are not statistically representative CUMA precision measurements and have not received independent expert adjudication. The test labels are never used as production identity evidence.

## Representative difficult cases

| CUMA index | Name | Result / diagnostic |
|---|---|
| 1 | 4-(4-Chlorophenoxy)piperidine | EXACT: Warning-free OPSIN, RDKit, official InChI and unique PubChem graph agree |
| 3 | 2,5-Diphenyloxazole | EXACT: Warning-free OPSIN, RDKit, official InChI and unique PubChem graph agree |
| 5 | 5-Amino-3H-1,2,4-dithiazole-3-thione | EXACT: Warning-free OPSIN, RDKit, official InChI and unique PubChem graph agree |
| 43 | tert-Amyl peroxyneodecanoate | CONFLICT: Local and provider molecular graphs differ or lookup is ambiguous |
| 116 | O-Chlorophenol | CONFLICT: Local and provider molecular graphs differ or lookup is ambiguous |
| 176 | 4-Methyl-1H-imidazole-2-carboxylic acid | CONFLICT: Local and provider molecular graphs differ or lookup is ambiguous |
| 6 | Silicon bronze | OUT_OF_SCOPE: Explicit excluded material family |
| 67 | Poly(ethylene glycol) diglycidyl ether | OUT_OF_SCOPE: Explicit excluded material family |
| 171 | Chromium bronze | OUT_OF_SCOPE: Explicit excluded material family |
| 2 | Amiodarone | UNRESOLVED: No validated local molecular candidate |
| 4 | (2-hydroxypropyl)trimethylammonium 2-ethylhexanoate | UNRESOLVED: Form, stereo, isotope, size or element boundary held for review |
| 7 | 5-chloro-2-fluoro-3-(4,4,5,5-tetramethyl-1,3,2-dioxaborolan-2-yl)-Benzenamine | UNRESOLVED: Form, stereo, isotope, size or element boundary held for review |

### Held aliases on accepted records

- CUMA 5, 5-Amino-3H-1,2,4-dithiazole-3-thione: `5-Imino-1,2,4-Dithiazolidine-3-Thione` → TAUTOMER_RELATED
- CUMA 14, 2-Bromobenzonitrile: `o-Bromobenzonitrile 2-Bromobenzonitrile` → SHARED_FRAGMENT_PARENT
- CUMA 35, Di-n-butylamine: `2-n-butylamine` → DIFFERENT_STRUCTURE; `N-butylbutan-1-aminium` → CHARGE_PARENT_RELATED
- CUMA 41, 1-cyclopropyl-6,7-difluoro-1,4-dihydro-4-oxoquinoline-3-carboxylic acid: `3-Quinolinecarboxylicacid` → DIFFERENT_STRUCTURE
- CUMA 48, myristyl acetate: `1-Tetradecanol` → DIFFERENT_STRUCTURE
- CUMA 56, 2'-Chloroacetophenone: `o-Chlorophenylmethylketone` → DIFFERENT_STRUCTURE
- CUMA 60, 4-(trifluoromethyl)thiobenzamide: `4-[(Trifluoromethyl)-thio]-benzamide` → DIFFERENT_STRUCTURE
- CUMA 96, 3-ethoxy-4-methoxybenzaldehyde: `3-ethyl-4-methoxybenzaldehyde` → DIFFERENT_STRUCTURE

## Limits and safeguards

- Canonical IDs are fresh, snapshot-local SUB numbers. No CUMA index or external identifier is used as the Substance ID.
- Automatic admissions exclude stereo, isotope, charge, multicomponent and complex-form cases. Their original graphs remain in audit evidence; no salt stripping or parent selection occurs.
- Only PubChem is queried externally. CAS/EC/ChEBI identifiers are not fabricated or extracted from unvalidated alias strings.
- Alias promotion uses separate OPSIN interpretation plus equality to the externally corroborated graph. Each alias does not receive its own external lookup.
- Unknown material families remain unresolved; regex scope screening is not a comprehensive materials classifier.
- Reference InChI via JNA checks RDKit molfile serialization. It is not an independent source attestation.
- Exact keys combine graph and full InChIKey; no formula, name-overlap, parent-view or transitive ambiguous merge is used.
- MolStandardize parent views exist only in development diagnostics. No ontology or relationship table was changed.
- Full candidate evidence and provider responses are local audit data. The registry itself contains exactly five tables.
