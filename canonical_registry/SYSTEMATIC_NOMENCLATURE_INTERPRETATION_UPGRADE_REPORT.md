# Systematic nomenclature interpretation upgrade

**Result: partial.** The implementation now records literal nomenclature features and verifies some locant-to-structure mappings using OPSIN's source-derived CML. In the frozen 400-record development replay, no UNKNOWN name became ESTABLISHED or PARTIAL, and no reference-confirmed identity was newly recovered. Two previously correct admissions were withheld because locants were not unique in the OPSIN output. The four prior false positives remain blocked. This is a development replay, not a new blinded validation.

## Changes and limits

[systematic_notation.py](systematic_notation.py) extracts source-only, parenthetical numbered R/S and E/Z blocks including bridgehead locants. The existing OPSIN bridge can return its own CML with atom locants. Before retrieval, the mapper reconstructs its heavy-atom graph, matches it to the **same source parse's** SMILES without using stereochemical ordering, requires an unambiguous full graph mapping and a unique locant, and verifies RDKit-assigned CIP or bond geometry. It records mapped source-structure indices, not a mapping to an external candidate. Multiple graph matches, duplicate locants, missing labels, differing CIP, unsupported CML and unavailable CML cause an UNKNOWN mapping; an otherwise established interpretation becomes UNKNOWN. The existing source-form gate and admission policy remain unchanged. The mapper is conservative: it cannot yet determine the scope of duplicate locants in different name fragments.

The source profile preserves explicit relative `cis`/`trans`, D/L series, optical `(+)`/`(-)`, numbered ionic charges, explicit component ratios, and counterion terms as separate literal features. It does not infer R/S from D/L or optical rotation, absolute configuration from relative notation, or molecular stoichiometry from a retrieved candidate. Recognition of literal features does not itself establish complete molecular identity. Unlocanted stereo, complex nested locant scopes, and arbitrary registry notation are not comprehensively mapped. Existing single and multiple stereo parsing remains dependent on OPSIN's successful source parse and on the unchanged downstream form checks.

The bounded source-only preprocessing adds equivalent Unicode hyphen handling and one narrowly specified registry inversion: `ethanol, 2-chloro-` to `2-chloroethanol`, generalized to a numbered single halogen on ethanol. It neither invents locants nor rewrites higher unnumbered alkanols; existing whitespace and alphabetic hyphen normalization remains. It is tried only when the original preferred-name parse fails, preserves the original name, and does not bypass the source gate. The broader inverted borate and fused-ring examples remain unsupported rather than being guessed. OPSIN already parses some inverted forms directly; this rule is not a general CAS nomenclature converter.

A current interface limitation matters: if an injected nonstandard bridge does not implement `opsin_cml`, the additional mapping audit is skipped and prior interpretation behavior remains. The normal production `Bridge` provides it, and the replay used that bridge. Enforcing this requirement for every injected adapter, without discarding the existing mock-based tests, remains work; this is one reason for the partial result.

## Tests

All **99 tests** passed: the retained 89 and ten new tests. The new tests exercise real OPSIN CML for bridgehead stereocentres, multiple R/S centres, multiple E/Z bonds, graph symmetry abstention and an incorrect descriptor; they also cover source-only inversion, literal charge/counterion/ratio capture, D/L and optical rotation versus relative stereo, unsupported mapping, and trans-only underspecification. [Test log](systematic_nomenclature_upgrade_final/tests.log). The original four false-positive cases were checked in the replay below. No new external provider or ontology modification was introduced.

## Replay and interpretation changes

The 400 inputs, frozen judgments and provider caches were reused offline. There were **zero external requests and zero missing cached acquisition queries**. The preceding development replay is the baseline; no labels were revised. The final code and tests were frozen before the replay. A preliminary run preceded a safety correction that restricted the inversion rule to ethanol; it is retained separately and is not the final run.

| Interpretation state | Before | After |
| --- | ---: | ---: |
| ESTABLISHED | 216 | 212 |
| PARTIAL | 40 | 40 |
| UNKNOWN | 143 | 147 |
| CONFLICTING | 1 | 1 |

UNKNOWN → ESTABLISHED: **0**; UNKNOWN → PARTIAL: **0**; UNKNOWN → UNKNOWN: **143**. Four formerly ESTABLISHED names became UNKNOWN because a locant was not unique in the source graph. Three source parses had complete verified locant mappings; four had UNKNOWN mappings. These counts describe names in the replay, not the entire nomenclature domain.

| CUMA | Mapping result | Final outcome and relevance |
| --- | --- | --- |
| 14541 | MAPPED: 3aR, 4S, 5R, 6aS | UNRESOLVED: existing downstream stereo-token recognition still reports `STEREO_SOURCE_INTENT_UNSPECIFIED`. |
| 21069 | MAPPED: 2R | EXACT, unchanged. |
| 50787 | MAPPED: 2S | UNRESOLVED: existing multicomponent semantics. |
| 23002 | UNKNOWN: `LOCANT_NOT_UNIQUE` | EXACT → UNRESOLVED; frozen reference confirms the previous structure. |
| 41891 | UNKNOWN: `LOCANT_NOT_UNIQUE` | UNRESOLVED, unchanged; multicomponent semantics also block admission. |
| 44490 | UNKNOWN: `LOCANT_NOT_UNIQUE` | EXACT → UNRESOLVED; frozen reference confirms the previous structure. |
| 48695 | UNKNOWN: `LOCANT_NOT_UNIQUE` | CONFLICT, unchanged; tautomer conflict. |

| Measure | Before | After |
| --- | ---: | ---: |
| EXACT | 152 | 150 |
| Correct / assessable EXACT | 151/151 | 149/149 |
| Unverified EXACT | 1 | 1 |
| Assessed false-positive EXACT | 0 | 0 |
| Newly recovered reference-confirmed identities | — | 0 |
| Previously correct admissions lost | — | 2 |
| UNRESOLVED / CONFLICT / OUT_OF_SCOPE | 206 / 20 / 22 | 208 / 20 / 22 |
| Assessed alias precision | 179/179 | 177/177 |
| Assessed false merges | 0/3 pairs | 0/3 pairs |
| Non-EXACT | 248/400 | 250/400 |

The earlier false-positive cases remain non-EXACT: 5684 CONFLICT; 5997 and 23839 UNRESOLVED; 30142 UNRESOLVED. No new assessed false-positive admission or false merge was observed; one EXACT admission remains unverified. Neither zero-error count proves general safety on this small, enriched set. The two losses are limitations of locant scoping, not evidence that the frozen chemical judgments were wrong.

## Remaining UNKNOWN triage

A report-only lexical triage assigns all 147 UNKNOWN cases as follows: `COMMON_NAME_EVIDENCE_REQUIRED` **49**, `SYSTEMATIC_NOTATION_STILL_UNSUPPORTED` **58**, `MALFORMED_OR_INCOMPLETE_NAME` **0**, and `OTHER_EXISTING_CAPABILITY_GAP` **40**. These labels are coarse string and outcome heuristics, not expert nomenclature judgments: in particular a name resembling a common name may actually be systematic, and a malformed name may be counted as unsupported or other. CUMA 7164's apparent truncated spelling remains a manual-review concern, not a corrected name. [Per-case triage and transitions](systematic_nomenclature_upgrade_final/interpretation_analysis.json).

The previously withheld Bucket B examples remain unresolved where OPSIN cannot interpret the original source or the narrow punctuation rule does not apply: fused rings, registry-style inversion, borate charge/coordination notation, polyether notation and naphthalene positional naming. Common-name identities, including Sitagliptin, remain outside this upgrade and are not inferred from providers.

## Next work and audit

The most relevant next capability is **source-derived locant scoping across fragments**, validated on independently adjudicated names, so a descriptor can be tied to the correct OPSIN atom without choosing among duplicate locants by order. The downstream bridgehead stereo-token limitation and adapter-capability enforcement also need attention. Separate gaps remain in salt proton transfer, multicomponent and hydrate/solvate semantics, advanced tautomers and coordination; this task did not expand them or recommend relaxing admission.

The read-only registry verification passed for the new replay: 150 EXACT rows revalidated, 147 canonical graphs, and zero checked duplicate or orphan rows. Frozen reference hashes and the prior scored registry and candidate snapshots were checked; the prior registry was not changed. [Frozen implementation](systematic_nomenclature_upgrade_final/IMPLEMENTATION_FROZEN.json), [replay comparison](systematic_nomenclature_upgrade_final/comparison.json), [metrics](systematic_nomenclature_upgrade_final/metrics.json), [registry verification](systematic_nomenclature_upgrade_final/run/verification.json), [scoring freeze](systematic_nomenclature_upgrade_final/SCORING_FROZEN.json), and [preliminary run](systematic_nomenclature_upgrade/run.log).

SYSTEMATIC_NOMENCLATURE_UPGRADE_PARTIAL
