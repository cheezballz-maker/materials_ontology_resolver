# Stereo propagation and locant scoping upgrade

**Result: partial.** Verified source stereo now reaches the downstream form check and source gate. The frozen development replay restored both previously correct admissions lost to duplicate locants, with no new assessed false positives. OPSIN's returned CML does not expose reliable name-fragment ownership, so only a narrow source-syntax and source-graph case is recovered; general fragment-local scoping remains unresolved. This is not a fresh blinded validation.

## Propagation

The existing source-name interpretation profile is the single carrier of mapped source stereo. Each mapping retains the descriptor, locant, atom or bond type and source-graph index, scope, and `VERIFIED` status. The mapping also records the source-derived isomeric SMILES. [form_characterizer.py](form_characterizer.py) consumes the profile only when the structure is the same canonical source graph, the graph has fully specified supported stereo, and the verified mappings cover every specified stereogenic element. Missing, partial, mismatched or duplicated mappings do not establish full stereo. The profile is passed through the existing [resolver](resolver.py), [policy](policy.py), and [source-form gate](source_form.py); the gate uses the verified mapping directly instead of re-deriving R/S or E/Z from the raw name. The read-only verifier receives the same profile.

No provider result is an input to name interpretation or locant selection. A later structure must match the complete source graph before the verified profile can support its source-specificity check. Relative-only stereo, broad sugars and all other existing gates remain in force. Unmapped source descriptors remain visible in the source notation profile and do not become verified.

## Duplicate locants

The existing OPSIN CML is flat: it contains locants and the source structure, but not dependable descriptor-to-parent/substituent fragment ownership. [systematic_notation.py](systematic_notation.py) therefore uses a deliberately limited structural scope: a descriptor must occur in a leading whole-name stereo block, the source graph must have one connected component, and exactly one atom or bond carrying that locant must be *potentially* stereogenic in the source graph. Eligibility uses topology, including specified and unspecified stereo; it does not use the desired CIP value, assigned stereo as a tiebreaker, atom ordering, or provider candidates. The already-selected unique source element must then pass the existing independent R/S or E/Z verification and graph-isomorphism checks. Ambiguous source-graph mappings, multiple eligible elements, local or nested descriptor scope, and disconnected components abstain. `LOCANT_SCOPE_UNRESOLVED` or the existing `GRAPH_MAPPING_AMBIGUOUS` is retained as diagnostic.

This is a unique-source-element rule, not general fragment identity reconstruction. It cannot recover cases where two fragments both contain potentially stereogenic elements bearing the same locant, even if a more complete name parser could establish which fragment owns the descriptor.

## Tests

All **107 tests** passed: the retained 99 plus eight focused tests. The new tests cover bridgehead descriptors through the full resolver path, complete multiple-centre and E/Z propagation, duplicate locants with one eligible source element, two eligible elements, an unestablished local scope, disconnected components, incomplete descriptor mappings, and a candidate that differs from the source graph. [Test log](stereo_locant_upgrade_complete/tests.log). The four prior false-positive cases are checked in the replay below. No ontology or provider changes were made.

## Frozen development replay

The same 400 source records, judgments and copied caches were replayed offline against the systematic-nomenclature baseline. No labels or prior registry snapshots were modified. No new provider requests were made. **Eight queries were not available in the cache**, all newly reached for CUMA 14541; this affects that case's ability to pass external corroboration and limits the replay comparison. The final implementation and tests were frozen before the scored run; earlier development preparations and replays are separate artifacts.

| Measure | Before | After |
| --- | ---: | ---: |
| Name interpretation: ESTABLISHED / PARTIAL / UNKNOWN / CONFLICTING | 212 / 40 / 147 / 1 | 214 / 40 / 145 / 1 |
| Verified source mappings | 3 | 5 |
| Mapped records whose downstream form check recorded and independently rechecked consumption | — | 5/5 |
| Mapped records reaching and recording consumption by the source gate | — | 3/5 |
| `LOCANT_NOT_UNIQUE` mapping failures | 4 | 0 |
| Bounded unique-source-element duplicate-locant mappings | — | 2 |
| Remaining ambiguous source graph mappings among those four | — | 2 |
| EXACT / UNRESOLVED / CONFLICT / OUT_OF_SCOPE | 150 / 208 / 20 / 22 | 152 / 206 / 20 / 22 |
| Correct / assessable EXACT | 149/149 | 151/151 |
| Unverified EXACT | 1 | 1 |
| Newly recovered reference-confirmed identities | — | 2 |
| Previously correct admissions restored / newly lost | — | 2 / 0 |
| Assessed false-positive EXACT | 0 | 0 |
| Assessed false merges | 0/3 pairs | 0/3 pairs |
| Assessed alias precision | 177/177 | 179/179 |

The two recovered identities are the same two reference-confirmed admissions lost in the previous upgrade; they are not additional identities beyond that earlier baseline. The two mappings that do not reach the source gate are blocked earlier by missing offline external evidence and multicomponent semantics, respectively. `source_stereo_used` is recorded in the downstream form for all five and rechecked from the saved source profile; the gate's own consumption flag is recorded for the three that reached it.

| CUMA | Before → after | Disposition |
| --- | --- | --- |
| 23002 | UNRESOLVED → EXACT | Global locant 2 duplicated; one eligible source stereocentre in the bounded leading-name scope. Frozen reference supports the restored exact structure. |
| 44490 | UNRESOLVED → EXACT | Global locant 1 duplicated; one eligible source stereocentre in the bounded leading-name scope. Frozen reference supports the restored exact structure. |
| 14541 | UNRESOLVED → UNRESOLVED | 3aR, 4S, 5R and 6aS mapped and consumed; the former `STEREO_SOURCE_INTENT_UNSPECIFIED` is gone. Final reason is `EXTERNAL_EVIDENCE_INCOMPLETE`, with eight newly reached provider queries missing from the offline cache. This does not establish whether the record would be admitted with fresh corroboration. |
| 41891 | UNRESOLVED → UNRESOLVED | Source graph mapping remains ambiguous; multicomponent semantics independently block the form. |
| 48695 | CONFLICT → CONFLICT | Source graph mapping remains ambiguous; tautomer conflict remains the downstream outcome. |
| 50787 | UNRESOLVED → UNRESOLVED | Source stereo was mapped and consumed; multicomponent semantics remain unsupported. |

The four earlier false-positive cases remain non-EXACT: 5684 is CONFLICT, 5997 and 23839 are UNRESOLVED, and 30142 is UNRESOLVED. There were no new assessed false-positive admissions or false merges. One admitted case remains unverified; three assessable clustered pairs and an enriched development set are insufficient to establish real-world precision.

## Remaining stereo-related cases

Report-only triage of non-EXACT records with detectable explicit stereo markers yields `LOCANT_SCOPE_UNRESOLVED` 2, `SOURCE_NOTATION_UNSUPPORTED` 15, `SOURCE_STEREO_PARTIAL` 12 and `OTHER_DOWNSTREAM_GAP` 9. The classifier groups both locant-scope and graph-isomorphism ambiguity in the first category. It is a coarse lexical and outcome-based review, not an exhaustive count of stereo-specific names, especially when a common name has no explicit stereo marker. [Per-case triage](stereo_locant_upgrade_complete/stereo_triage.json).

Remaining gaps include source-fragment ownership in nested and multicomponent names, ambiguous graph automorphisms, incomplete mappings and the unchanged adapter limitation: injected bridges without `opsin_cml` do not provide this additional mapping audit. External corroboration, salt proton transfer, multicomponent and hydrate semantics, tautomer policy and coordination remain separate capabilities. The next focused capability is trustworthy source-derived fragment ownership metadata; fresh blinded evaluation should follow before scaling.

## Audit

The existing read-only verifier passed on the new snapshot: 152 EXACT reconciliations revalidated, 149 canonical graphs, and no checked duplicate or orphan rows. Prior scored outputs, registry and candidate snapshot hashes were checked unchanged. These are integrity checks, not independent chemical adjudication. See [implementation freeze](stereo_locant_upgrade_complete/IMPLEMENTATION_FROZEN.json), [tests](stereo_locant_upgrade_complete/tests.log), [mapping and propagation analysis](stereo_locant_upgrade_complete/stereo_analysis.json), [comparison](stereo_locant_upgrade_complete/comparison.json), [metrics](stereo_locant_upgrade_complete/metrics.json), [verification](stereo_locant_upgrade_complete/run/verification.json), and [scoring freeze](stereo_locant_upgrade_complete/SCORING_FROZEN.json).

STEREO_LOCANT_UPGRADE_PARTIAL
