# Provider correspondence remediation report

## Source correspondence and route aggregation

A candidate-derived SMILES, InChI or InChIKey is discovery and comparison data, never independent evidence that the original source name denotes the candidate. An actual source-provided identifier can establish correspondence when the provider's exact route returns the same identifier and its structure passes the existing form and graph checks. Literal returned source preferred names or source aliases can establish correspondence under the same dimensional, completeness and source-dependence gates. There is no new casefold, fuzzy or punctuation equivalence.

Each result is grouped by provider, lookup type, query and query origin. Record evidence is retained separately; `CORROBORATES` plus `CONTRADICTS` on one source-linked route becomes `PROVIDER_RECORD_AMBIGUOUS`. The ambiguous route contributes no positive corroborator and no contradiction. Otherwise contradiction takes precedence, then corroboration, then non-discriminating evidence, then the query's neutral availability. Multiple compatible records count as one route, not votes. A separately source-provided exact identifier remains its own route and may corroborate even if a name route is ambiguous. Deduplication now preserves the same record when reached through different routes. Explicit sufficiently specified typed structures still need no external corroborator.

The implementation retains static profiles and does not score, rank or vote across providers. Query audit includes provider, route, query, record IDs, per-record states and aggregate state. An unknown direct dependence can qualify, but known direct source dependence cannot. See [evidence model](evidence_model.py), [retrieval](evidence_retrieval.py), and [policy](policy.py).

## Bounded authenticated CompTox check

Three independently chosen queries used five live requests. [Full record comparisons](provider_correspondence_remediation/live_smoke.json) contain no credentials.

| Route and query | Aggregate | Record states |
|---|---|---|
| name Toluene | CORROBORATES | DTXSID7021360: CORROBORATES |
| name Deuterium oxide | PROVIDER_RECORD_AMBIGUOUS | DTXSID4051243: CORROBORATES; DTXSID80159585: CONTRADICTS |
| DTXSID DTXSID4051243 | CORROBORATES | DTXSID4051243: CORROBORATES |

The deuterium-oxide result follows the generic aggregator; there is no name-specific runtime branch. The exact DTXSID result is shown separately and does not erase the ambiguous name route.

## Reconciliation of the 24 previously failing assertions

The previous failure log is preserved in [tests_latest.log](provider_qualification/tests_latest.log), and pre-remediation test sources are preserved in [baseline](provider_correspondence_remediation/baseline). Each row below identifies the prior assumption and the retained fix. The mocked GSRS fixture represents the adapter's post-validation output; it is not presented as a real GSRS observation. Unknown source dependence remains eligible under the stated one-corroborator policy; known dependence is now explicitly tested as ineligible. Archived test copies also caused generic `pytest` import-name collisions: those are `TEST_DISCOVERY_DUPLICATE`, separate from the 24 behavioral failures. The retained suite explicitly selects current modules.

| Previous failure | Classification | Resolution and retained check |
|---|---|---|
| `test_registry.test_ambiguous_provider` | OBSOLETE_EXPECTATION | Two incompatible records on one route now aggregate as ambiguous; mock now has a real route. |
| `test_registry.test_decisions` | TEST_FIXTURE_INVALID | The metadata-only anonymous fixture is replaced with a controlled complete-GSRS source-ID fixture; identifier mismatch still blocks. |
| `test_forms.test_charge_and_resonance` | TEST_FIXTURE_INVALID | A complete GSRS-form fixture replaces a metadata-only response; charge and resonance identity assertions remain. |
| `test_forms.test_conflicting_tautomer_is_not_admitted` | OBSOLETE_EXPECTATION | Unqualified PubChem tautomer responses are non-discriminating, not source contradictions; the result must abstain. |
| `test_forms.test_isotopes` | TEST_FIXTURE_INVALID | The positive form test now uses a complete GSRS source-ID fixture; isotope differences remain separately tested. |
| `test_forms.test_stereo` | TEST_FIXTURE_INVALID | The positive form test uses a complete GSRS source-ID fixture; stereo distinctions and source specificity remain asserted. |
| `test_forms.test_tautomers` | TEST_FIXTURE_INVALID | The form comparator test uses a controlled full-GSRS-graph fixture; normalized PubChem tautomer evidence still abstains. |
| `test_evidence_retrieval.test_gsrs_can_corroborate_validated_local_candidate` | TEST_FIXTURE_INVALID | Added exact returned GSRS name, record ID and adapter moiety-validation output to the synthetic response. |
| `test_evidence_retrieval.test_identifier_corroboration_after_name_failure` | OBSOLETE_EXPECTATION | A generated InChIKey is discovery only and no longer satisfies the source-name evidence requirement. |
| `test_evidence_retrieval.test_isotope_not_removed_by_retrieval` | OBSOLETE_EXPECTATION | Both candidate-key searches abstain; the separate assertion still checks that isotopes are preserved. |
| `test_evidence_retrieval.test_original_provider_disagreement_still_blocks` | TEST_FIXTURE_INVALID | The contrary provider fixture now has a record ID and literal returned source name; a genuine contradiction still blocks. |
| `test_evidence_retrieval.test_source_identifier_recovery_and_checksum` | TEST_FIXTURE_INVALID | The old PubChem CAS mock did not return an exact CAS assertion. Use an exact source-provided CID and retain CAS checksum rejection. |
| `test_evidence_retrieval.test_stereo_search_alternatives_are_not_exact_evidence` | OBSOLETE_EXPECTATION | A candidate-derived key cannot corroborate even when one returned stereo graph matches; related-record filtering remains asserted. |
| `test_source_form.test_specific_alias_is_not_promoted_when_it_is_broad_relative_name` | TEST_FIXTURE_INVALID | Add literal returned names and record IDs; the broad relative-stereo alias is still rejected. |
| `test_source_form.test_validated_key_and_absolute_source_still_resolve` | OBSOLETE_EXPECTATION | Candidate-derived key does not prove the source name; the test retains its separate source-stereo support check. |
| `test_source_form.test_wrong_alias_alone_is_not_a_record_veto` | TEST_FIXTURE_INVALID | Make the preferred-name response a valid exact-name record so the original source-claim conflict check is reached. |
| `test_grounding_remediation.test_failed_source_provider_cannot_be_repaired_by_one_hit [ERROR]` | TEST_FIXTURE_INVALID | Use a source-linked literal exact-name record; an unavailable other provider stays neutral. |
| `test_grounding_remediation.test_failed_source_provider_cannot_be_repaired_by_one_hit [NOT_QUERIED]` | TEST_FIXTURE_INVALID | Same fixture correction for the not-queried provider branch. |
| `test_grounding_remediation.test_fixture_path_is_not_loaded_or_used` | TEST_FIXTURE_INVALID | Use a literal exact-name provider record while retaining the assertion that reviewed fixtures are not loaded. |
| `test_evidence_model.test_complete_name_one_independent_and_no_match` | TEST_FIXTURE_INVALID | Replace anonymous TEST/manual qualification with an exact returned name and PubChem record ID. |
| `test_evidence_model.test_complete_name_one_independent_and_other_unavailable` | TEST_FIXTURE_INVALID | Same source-linked fixture; the other provider remains neutral. |
| `test_evidence_model.test_exact_independent_qualified_record` | TEST_FIXTURE_INVALID | Replace TEST/manual certification with recognized profile, source name, record ID and validated graph. |
| `test_evidence_model.test_genuine_vs_unproven_contradiction` | TEST_FIXTURE_INVALID | Contradiction requires literal source correspondence; query mismatch now tests unproven correspondence. |
| `test_evidence_model.test_verified_conflicting_same_source_blocks` | OBSOLETE_EXPECTATION | Same route corroboration plus contradiction is ambiguous and abstains rather than becoming a source conflict. |

All **182 retained tests passed** in the final run, including nine new correspondence/aggregation tests. [Test log](provider_correspondence_remediation/tests.log). No previous assertion was removed merely to obtain a passing total; fixtures or expected outcomes above were updated to reflect the documented source route and representation gates. The separate tests still cover typed source admission, malformed structures, form boundaries and neutral provider unavailability.

## Frozen offline development replay

The frozen 400 source records were replayed against copies of prior caches, with no online requests; this is reused development data, not fresh blinded validation. Results: **8 EXACT, 367 UNRESOLVED, 3 CONFLICT, 22 OUT_OF_SCOPE**. Eight canonical graphs and their exact reconciliations passed registry verification; all reported duplicate and orphan counts were zero. [Frozen implementation and test hashes](provider_correspondence_remediation/frozen.json), [replay log](provider_correspondence_remediation/replay.log), [verification](provider_correspondence_remediation/verify.log), [full audit](provider_correspondence_remediation/analysis.json).

Counts below are provider-route queries, not distinct CUMA records. Each query contributes one state; a record can issue multiple queries.

| Provider | CORROBORATES | CONTRADICTS | PROVIDER_RECORD_AMBIGUOUS | NON_DISCRIMINATING | NO_MATCH | UNAVAILABLE |
|---|---:|---:|---:|---:|---:|---:|
| PubChem | 9 | 0 | 0 | 245 | 0 | 191 |
| ChEBI | 2 | 0 | 0 | 54 | 22 | 474 |
| GSRS | 0 | 0 | 0 | 3 | 46 | 270 |
| CompTox | 0 | 0 | 0 | 0 | 0 | 284 |

## Revised admissions and prior candidate-key admissions

All eight EXACT decisions below use a CUMA preferred name, `ESTABLISHED` source interpretation and `SUPPORTED` source-form interpretation. Their qualifying route is a literal returned name, with the local graph comparison `EXACT`; the identifier origin column is `source name` because no identifier was used to establish correspondence. The final reason for each is `INDEPENDENT_EXACT_FORM_CORROBORATION`. These are audit observations, not independent accuracy judgments. [Machine-readable audit](provider_correspondence_remediation/analysis.json) includes all per-record comparisons, routes, provider identifiers and source-dependence classifications.

| CUMA index and name | Provider and record ID | Correspondence / identifier origin | Aggregate | Dimensions compared |
|---|---|---|---|---|
| 22566 3,3,3-trifluoro-2,2-dimethylpropanoic acid | PubChem 19867367 | EXACT_RETURNED_NAME / source name | CORROBORATES | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 26687 2-fluoro-3-methylpyridine | PubChem 242722 | EXACT_RETURNED_NAME / source name | CORROBORATES | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 37617 2-fluoro-4-methylpyridine | PubChem 2737403 | EXACT_RETURNED_NAME / source name | CORROBORATES | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 43284 4-chloro-3-(trifluoromethoxy)benzoic acid | PubChem 17750688 | EXACT_RETURNED_NAME / source name | CORROBORATES | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 43434 2-fluoro-4-iodopyridine | PubChem 7023570 | EXACT_RETURNED_NAME / source name | CORROBORATES | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 46926 Morpholine | ChEBI CHEBI:34856 | EXACT_RETURNED_NAME / source name | CORROBORATES | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 51142 3-iodo-5-methylbenzonitrile | PubChem 71125607 | EXACT_RETURNED_NAME / source name | CORROBORATES | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 51624 methyl 3-chloro-5-methylbenzoate | PubChem 19788161 | EXACT_RETURNED_NAME / source name | CORROBORATES | connectivity, electronic_state, protonation_charge, tautomeric_form |

Of the 11 previous EXACT admissions, three relied on candidate-derived PubChem InChIKeys and are now UNRESOLVED / `NO_QUALIFYING_CORROBORATION`: **7855** (CID 7023123), **18428** (CID 45117490), and **20866** (CID 10921761). The eight remaining admissions above had exact returned-name support and remain EXACT. No retained EXACT relies solely on a candidate-derived identifier. The per-case prior routes and new outcomes are in the [full audit](provider_correspondence_remediation/analysis.json).

One additional case, 50198, changed from CONFLICT to UNRESOLVED: the resolver only evaluates some source-alias conflicts after provisional admission, and the removed candidate-key corroboration means that check is not reached. No identity is admitted. This pre-existing ordering limits diagnostic specificity and should be reviewed separately; it was not expanded in this remediation.

## Historical safety and integrity

Sulfate/sulfite 5684, relative-stereo 5997 and 23839, and glucose-form 30142 are UNRESOLVED in the replay. The separate historical dithiazole probe is UNRESOLVED / `NO_QUALIFYING_CORROBORATION`. [Probe](provider_correspondence_remediation/case5_probe.json). No case-specific rule was added.

The OPSIN jar and bridge hashes match the prior freeze; runtime class-loading verifies the expected jar and no diagnostic shadow class or Java injection environment was found. Ontology and persistent schema hashes match the earlier freeze. The prior qualification registry and candidate snapshot match their pre-replay hashes. The configured key was absent from scanned new text, cache, log and report files. [Integrity checks](provider_correspondence_remediation/integrity.json). Verification of prior snapshots is limited to these recorded files and hashes, rather than every historical artifact.

Element, coordination, carbon-free multicomponent and other existing scope/capability guards remain unchanged and are technical debt. Normalization holds remain conservative, and the evidence classification depends on recorded source dependence; unrecorded circularity remains possible. The reused development set cannot estimate prospective admission precision.

The stated gates for a **fresh blinded evaluation** are met: retained tests pass, no replay admission relies solely on candidate-derived identifiers, route ambiguity is deterministic, and the historical unsafe cases remain non-EXACT. A fresh evaluation is recommended before any scale-up; this report does not claim readiness to scale.

PROVIDER_CORRESPONDENCE_REMEDIATION_VALIDATED
