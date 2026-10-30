# Resolver grounding remediation

**Result: partial.** The name-specific evidence fixture, sulfate/sulfite shortcut, duplicate-locant ownership exception and unsupported lexical transformations were removed or quarantined. A historical tautomer probe then exposed a general safety bug: a failed source-provider lookup could be ignored when another provider returned a hit. The new general guard holds that case as incomplete evidence. The remaining element and organic/inorganic scope heuristics are still admission-relevant, so the grounding success criterion is not yet met. **Do not resume feature development.**

The changed-rule matrix is [resolver_grounding_matrix.json](resolver_grounding_matrix.json); the prior [grounding audit](RESOLVER_GROUNDING_AUDIT.md) contains independent sources and implementation-risk analysis. This task did not modify ontology, persistent schema, prior registry snapshots, or add providers, a CAS/carbohydrate parser, OPSIN ownership adapter, salt semantics, or ontology relationships. The runtime retains the old `reviewed_evidence` constructor argument only as an ignored compatibility argument; the historical file remains an audit/test artifact and is never read by the resolver.

## Removed, quarantined and retained

- **Removed:** sulfur-token/oxygen-neighbor source conflict; the hard-coded reviewed-evidence injection; ethanol inversion and alphabetic hyphen rewrite; sugar-root, ring-proxy and alditol recognition; salt-name-word admission; name-based solvate inference.
- **Quarantined:** duplicate locants now return `LOCANT_SCOPE_UNRESOLVED`; unowned colon or solidus ratios are recorded as unspecified and block admission; alternative parse input cannot establish the preferred source claim; D/L alone cannot establish generic absolute stereo. Source and curated-provider name matches preserve descriptor case and punctuation. A case-only provider hit is retained as *incomplete evidence*, not silently discarded or declared equivalent.
- **Retained:** strict structures, explicit numeric sodium/potassium/hydrochloride and hydrate constraints, explicit charge capture, exact graph/form comparison, original evidence checks and abstention. A water suffix alone cannot establish disconnected water. Explicit source hydration semantics can support a count; non-water solvates remain held. The old element allowlist, organic-carbon and some coordination/material-scope guards remain active: removing them without a defensible replacement could admit unsupported structures. This unresolved conflict with the requested quarantine is why the result is partial.
- **General source conflict:** when the preferred claim and an alias both parse and their constitutional graphs differ, `source_form.assess` records `SOURCE_CONSTITUTION_CONFLICT`. A failed source parse cannot infer a sulfate/sulfite conflict. These source conflicts require review; they do not establish that the preferred structure itself is wrong.
- **General provider-safety correction:** source-claim `ERROR` or `NOT_QUERIED` is now incomplete evidence even if another provider succeeds. The original provider failure is retained; no new source or case mapping is introduced.

## Test changes and independent examples

The final frozen run passed **139 tests**, including ten new tests in [test_grounding_remediation.py](test_grounding_remediation.py). The retained suite still exercises R/S, E/Z, cis/trans, isotope locants, and exact-form comparisons. Independent source examples added include IUPAC disodium carbonate and addition-compound notation ([Blue Book salts](https://iupac.qmul.ac.uk/BlueBook/P6.html), [addition compounds](https://iupac.qmul.ac.uk/BlueBook/P1.html)); WHO dehydroemetine dihydrochloride and sodium phosphate monohydrate ([monograph](https://cdn.who.int/media/docs/default-source/medicines/pharmacopoeia/omitted-monographs/dehydroemetine_dihydrochloride.pdf), [pharmacopoeial comparison](https://cdn.who.int/media/docs/default-source/essential-medicines/2023-eml-expert-committee/applications-for-addition-of-new-medicines/a33_phosphorus.pdf?sfvrsn=9f401afc_2)); and chloral hydrate ([IUPAC Gold Book](https://goldbook.iupac.org/terms/view/15195)). IUPAC [P-9](https://iupac.qmul.ac.uk/BlueBook/P9.html), [P-82](https://iupac.qmul.ac.uk/BlueBook/P8.html), and [carbohydrate recommendations](https://iupac.qmul.ac.uk/2carb/06n07.html) independently ground the distinctions, not complete implementation coverage. Tests also cover case-preserving provider matching, unsupported CAS-style inversion, alias structure conflict, fixture isolation and unavailable source providers. [Test log](grounding_remediation_final_scored/tests.log).

| Changed test(s) | Why the prior expectation changed |
| --- | --- |
| `test_salts`, `test_hydrate_and_solvate` | A salt word or numeric hydrate suffix did not independently establish the disconnected graph; named solvate vocabulary is held. |
| `test_parser_failure_recovered_by_validated_original_alias`, `test_lexical_link_never_collapses_numeric_locants` | A hyphen/space or case-only variant was not proof of source-name identity. |
| `test_unknown_source_claim_conflict`, `test_sulfate_sulfite_conflict_without_name_dictionary`, `test_alias_retrieval_cannot_override_sulfate_claim` | Sulfur-name tokens cannot establish a parsed constitutional contradiction; unparsed preferred claims now remain unknown. |
| `test_wrong_alias_alone_is_not_a_record_veto` | The requested general mechanism compares two independently parsed source claims; a constitutional disagreement is now a source conflict. |
| `test_named_alditol_is_not_assumed_to_be_a_cyclic_sugar`, `test_explicit_cyclic_name_cannot_use_open_chain`, `test_broad_sugar_cannot_inherit_open_chain_or_anomer`, `test_expanded_key_cannot_make_generic_sugar_exact` | Root, ring and alditol shortcuts did not establish carbohydrate structure; D/L-only examples remain unresolved without a verified mapping. |
| `test_bounded_registry_inversion` | The specific ethanol transformation was not a grounded general index-name grammar. |
| `test_unique_stereogenic_duplicate_locant` | Only one topologically eligible atom does not prove name-fragment ownership. |
| `test_ratio_requires_typed_original_component_claims`, `test_ionic_pair_preserves_explicit_graph_and_charges`, `test_added_component_rejected_when_source_component_set_complete` | The slash/colon ratio was not a documented general grammar; graph/charge and added-component comparisons now use an independently supplied typed source structure. |
| `test_provider_cannot_upgrade_hydrochloride_protonation` | The earlier multicomponent guard can now produce a different conservative reason; the no-admission assertion remains. |

## Frozen 400-record development replay

The same frozen input and reference labels were replayed against copied cached evidence, **offline and without new provider requests**. This is a development replay, not an independent holdout. [Freeze](grounding_remediation_final_scored/IMPLEMENTATION_FROZEN.json), [metrics](grounding_remediation_final_scored/metrics.json), [case evidence](grounding_remediation_final_scored/change_analysis.json), and [all case comparisons](grounding_remediation_final_scored/comparison.json).

| Measure | Before | After |
| --- | ---: | ---: |
| EXACT | 152 | 11 |
| UNRESOLVED | 206 | 353 |
| CONFLICT | 20 | 14 |
| OUT_OF_SCOPE | 22 | 22 |
| Confirmed exact / known false / unverified | 151 / 0 / 1 | 11 / 0 / 0 |
| Assessed false merges / pairs | 0 / 3 | 0 / 0 |
| Correct / incorrect / unverified promoted aliases | 179 / 0 / 0 | 15 / 0 / 0 |

Of the prior EXACT records, 121 now show a failed or unqueried source-provider lookup and 13 show a case-only provider-name hold; these recorded cause groups can overlap with other changed gates. The offline cache therefore limits the meaning of the coverage drop. No merged pair remained assessable, so the zero false-merge count is not an estimate of merge safety.

**11 prior EXACT admissions remain admitted**, classified `PRIOR_ADMISSION_REMAINED_SUPPORTED` by the current gates; that is not independent proof of every underlying rule. **141 previous EXACT admissions were withheld**. **10 prior conflicts became unresolved**; this does not mean the underlying evidence was reconciled. Previously UNRESOLVED → EXACT: 0; UNRESOLVED → CONFLICT: 0. New EXACT admissions from any prior state: 0. Alias claims removed: 164; added: 0. 38 unchanged-status records acquired different reason text; these are available in the case evidence, not counted as changed outcomes.

The loss classification is evidence-based but not an independent chemical adjudication: `PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL` is used for the recorded D/L/case, locant, source-name and case-only-provider holds. `OTHER` includes new general parsed-alias conflicts and cases where multiple changed gates make causality uncertain. Changed outcomes: 151. Category counts: {'OTHER': 126, 'PRIOR_CONFLICT_REMOVED': 10, 'PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL': 15}. Recorded cause groups: {'OTHER; inspect evidence': 1, 'SOURCE_PROVIDER_FAILURE_HOLD': 122, 'CASE_ONLY_PROVIDER_HOLD': 19, 'CASE_SENSITIVE_OR_DL_SCOPE_HOLD': 2, 'HYDRATE_SEMANTICS_HOLD': 3, 'GENERAL_PARSED_SOURCE_ALIAS_CONFLICT': 4}. No prior admission was restored merely because the frozen reference supported it.

| CUMA | Name | Before → after | Classification | Recorded cause and new reason |
| ---: | --- | --- | --- | --- |
| 230 | boc-d-3-iodophenylalanine | EXACT → UNRESOLVED | OTHER | OTHER; inspect evidence: STEREO_SOURCE_INTENT_UNSPECIFIED |
| 467 | 4-Bromo-2,3-difluorobenzeneboronic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 1023 | DIETHYL ALLYLPHOSPHONATE | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 1049 | Ammonium molybdate tetrahydrate | CONFLICT → UNRESOLVED | PRIOR_CONFLICT_REMOVED | CASE_ONLY_PROVIDER_HOLD: NO_VALIDATED_CANDIDATE |
| 1545 | 1H-pyrrolo[2,3-b]pyridin-4-amine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 2305 | D-arabinitol | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_SENSITIVE_OR_DL_SCOPE_HOLD: SOURCE_STEREO_PARTIALLY_SPECIFIED |
| 2637 | Benzoic acid, 5-chloro-2-fluoro-4-hydroxy- | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 2847 | 5-[ethyl(2-hydroxyethyl)amino]pentan-2-one | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 2852 | 7-Fluoro-4-Trifluoromethoxy-1H-Indole | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 4125 | 3-Fluoro-4-methylbenzoic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 4363 | 2,2-Dibromo-3-Nitrilopropionamide | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 4503 | tert-Butyl cumyl peroxide | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 4722 | 1-(2-chloropyridin-4-yl)piperazine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 5044 | 5-(1,1-dimethylheptyl)resorcinol | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 5304 | 2,2',4,4',6,6'-hexamethylbenzophenon | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 5589 | Ethyl 2-methylthiazole-5-carboxylate | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 5684 | 1,1-Cyclopropane dimethanol cyclic sulphate | CONFLICT → UNRESOLVED | PRIOR_CONFLICT_REMOVED | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 5783 | 2-Fluoro-4-nitrophenylacetic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 5920 | Methyl 6-fluoro-1H-indole-4-carboxylate | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 5958 | Imidazo[1,2-a]pyridine-3-carboxylic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 6594 | 3-BROMO-5-IODOTOLUENE | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 7084 | 2,3,5,6-Tetrafluoro-4-methylbenzylchloride | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 7504 | 7-(4-Chlorobutoxy)-1H-quinolin-2-one | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 7855 | (R)-(4-Fluorophenyl) oxirane | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 7888 | 2-Chloro-5,6,7,8-tetrahydro-1,6-naphthyridine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 7994 | 5,6-Dihydro-3-(4-morpholinyl)-1-(4-nitrophenyl)-2(1H)-pyridinone | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 8309 | 3-Phenylpyridine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 8675 | 3-Methylbenzylamine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 9373 | TERT-BUTYL 4-FORMYLPYRIDIN-3-YLCARBAMATE | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 9444 | (4-nitrophenyl)methanesulfonyl chloride | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 9543 | 6-[2-(2-methyl-1H-imidazol-1-yl)ethyl]-1,3,5-triazine-2,4-diamine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 9604 | BOC-D-Leucine monohydrate | CONFLICT → UNRESOLVED | PRIOR_CONFLICT_REMOVED | HYDRATE_SEMANTICS_HOLD: HYDRATION_STOICHIOMETRY_UNKNOWN;MULTICOMPONENT_SEMANTICS_UNKNOWN |
| 10707 | 3-Methyl-5-(phenylmethoxy)-2-[4-(phenylmethoxy)phenyl]-1H-indole | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 11168 | diethyl methylphosphonate | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 11423 | 5-Bromo-3-chloropyridine-2-carboxylic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 11763 | 2H-1-Benzopyran-2-one, 7-fluoro-4-hydroxy- | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 12002 | 2,3,5-Trichloropyridine-4-carboxaldehyde | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 12060 | 6-Bromo-2,3-difluorophenylacetonitrile | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 12196 | Thiourea, (5-chloro-2-pyridinyl)- | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 12316 | 3,5-difluoro-2-nitroanisole | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 13055 | Pyridine-d5 | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 13084 | (R)-(4-Fluorophenyl)oxirane | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 13468 | Benzene-d6 | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 13698 | 1,4-diiodotetrafluorobenzene | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 13730 | 2-Fluoroterephthalic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 14095 | 5-fluoro-2-methoxy-pyridine-3-carbaldehyde | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 14492 | (R)-3-Aminotetrahydrofuran | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 14854 | Methyl 4-(trifluoromethyl)pyridine-2-carboxylate | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 15467 | 2,8-diazaspiro[4.5]decan-3-one | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 16593 | 4-Nitrophenylhydrazine | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 17117 | Tetraethylene glycol dimethyl ether | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 17356 | (R)-2-Amino-N-butyl-4-methylpentanamide | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 17917 | N-vinylformamide | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 17971 | 6-bromo-3-fluoropicolinonitrile | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 18390 | 3,6-Diiodopyridazine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 18428 | triethoxy(2-pyridyl)silane | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 18723 | 2-chloro-4-fluoro-pyridine-3-carboxylic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 19218 | 2,3,4,5-Tetrafluorobenzoyl Chloride | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 19408 | (4-Methoxycarbonyl-2-nitrophenyl)boronic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 20015 | 4-chloro-2-(trifluoromethyl)benzoyl chloride | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 20450 | 5-Chloro-1,3-benzodioxole | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 20495 | 4-Bromo-3-methyl-1H-indole | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 20511 | N,N-dimethylformamide diisopropyl acetal | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 20866 | 9H-Fluorene-9-ethanol | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 21069 | 2-Piperidinecarboxylic acid, 1-methyl-, (2R)- | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 22566 | 3,3,3-trifluoro-2,2-dimethylpropanoic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 22616 | 2,3-Difluoro-6-nitroanisole | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 22797 | N-Boc-4-iodopiperidine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 23002 | (2S)-amino[2-(trifluoromethyl)phenyl]ethanoic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 23253 | Butanal, 4-(heptyloxy)- | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 23470 | ROSE BENGAL | CONFLICT → UNRESOLVED | PRIOR_CONFLICT_REMOVED | CASE_ONLY_PROVIDER_HOLD: MULTICOMPONENT_SEMANTICS_UNKNOWN |
| 23547 | 3-BROMO-5-FORMYLPHENYLBORONIC ACID | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 23571 | 5-Bromo-2-chlorophenol | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 24235 | 1-benzothiophen-5-amine | EXACT → CONFLICT | OTHER | GENERAL_PARSED_SOURCE_ALIAS_CONFLICT: SOURCE_CONSTITUTION_CONFLICT |
| 24295 | 2-ANTHRACENEBORONIC ACID | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 24624 | Hexaketocyclohexane octahydrate | CONFLICT → UNRESOLVED | PRIOR_CONFLICT_REMOVED | HYDRATE_SEMANTICS_HOLD: HYDRATION_STOICHIOMETRY_UNKNOWN;MULTICOMPONENT_SEMANTICS_UNKNOWN |
| 24875 | 3-Bromo-6-chloroimidazo[1,2-a]pyrimidine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 25579 | 4-(hydroxymethyl)-2,6-dimethylphenol | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 26534 | (R)-2-acetaMido-2-(2-fluorophenyl)propanoic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 26687 | 2-fluoro-3-methylpyridine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 27043 | 2,3-heptanedione | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 27138 | Fmoc-D-3-Trifluoromethylphenylalanine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 27187 | Nitromethane-d3 | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 28810 | Sulfanilylurea | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 29667 | Methyl ethyl disulfide | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 30006 | methyl phenethyl ether | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 31892 | 3-Bromoaniline | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 33400 | Pyrazinoic acid hydrazide | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 35012 | (S)-3-chlorostyrene oxide | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 35068 | 2,3,5,6-Tetrafluorobenzoyl chloride | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 35283 | Isopropylamine | CONFLICT → UNRESOLVED | PRIOR_CONFLICT_REMOVED | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 35465 | Methylcyclohexane | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 36042 | 2-Chloro-4-fluoro-5-methylaniline | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 36282 | Ethyl 2-hydroxyethyl sulfide | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 36528 | 2-Iodothiophene | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 37000 | 3-Chloro-4,5-difluorobenzoic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 37251 | 3,4,5,6-tetrachloro-N-[2-(4,5,6,7-tetrachloro-2,3-dihydro-1,3-dioxo-1H-inden-2-yl)-8-quinolyl]phthalimide | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 37617 | 2-fluoro-4-methylpyridine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 38180 | L-arabinitol | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_SENSITIVE_OR_DL_SCOPE_HOLD: SOURCE_STEREO_PARTIALLY_SPECIFIED |
| 38628 | (R)-2-acetamido-2-(2-fluorophenyl)propanoicacid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 39652 | 4-(Trifluoroacetyl)morpholine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 40082 | 2-AMINOTEREPHTHALIC ACID | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 40367 | 3-HYDROXY-4-IODOBENZALDEHYDE | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 41197 | Diethylene glycol methyl ethyl ether | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 41224 | Entecavir hydrate | CONFLICT → UNRESOLVED | PRIOR_CONFLICT_REMOVED | CASE_ONLY_PROVIDER_HOLD: HYDRATION_STOICHIOMETRY_UNKNOWN;MULTICOMPONENT_SEMANTICS_UNKNOWN;STEREO_SOURCE_INTENT_UNSPECIFIED |
| 41332 | Alpha-Methylstyrene | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 41411 | 1,1,2-Trichloroethane | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 41551 | 5-(4-cyclopropyl-1H-imidazol-1-yl)-2-fluoro-4-methylbenzoic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 41871 | 3,3,3-Triphenylpropionic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 41897 | 2-bromo-6-chloro-4-fluorotoluene | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 41950 | Methyl 4-(butyrylamino)-5-methyl-3-aminobenzoate | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 42266 | 2,2'-Oxybis(N,N-dioctylacetamide) | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 42822 | 2,6-Dimethoxypyrazine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 43020 | Diphenhydramine hydrochloride | CONFLICT → UNRESOLVED | PRIOR_CONFLICT_REMOVED | CASE_ONLY_PROVIDER_HOLD: MULTICOMPONENT_SEMANTICS_UNKNOWN |
| 43207 | (R)-2-(2,5-DIFLUOROPHENYL)PYRROLIDINE | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 43284 | 4-chloro-3-(trifluoromethoxy)benzoic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 43434 | 2-fluoro-4-iodopyridine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 43546 | Diphenylacetonitrile | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 43668 | Diclofenac epolamine | CONFLICT → UNRESOLVED | PRIOR_CONFLICT_REMOVED | CASE_ONLY_PROVIDER_HOLD: MULTICOMPONENT_SEMANTICS_UNKNOWN |
| 44046 | 1-Naphthylacetyl chloride | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 44347 | Trifluoroacetyl chloride | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 44490 | (1S)-1-Phenyl-1,2,3,4-tetrahydroisoquinoline | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 44847 | 1,3,5-Trifluoro-2,4,6-triiodobenzene | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 45383 | Dichloromethane | EXACT → CONFLICT | OTHER | GENERAL_PARSED_SOURCE_ALIAS_CONFLICT: SOURCE_CONSTITUTION_CONFLICT |
| 45459 | 2-isopropoxyethanol | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 46123 | 4-Chloro-3-methylpyridine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 46392 | 1H-Indole, 5-chloro-2-phenyl- | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 46400 | 4,4'-Dihydroxybenzophenone | EXACT → CONFLICT | OTHER | GENERAL_PARSED_SOURCE_ALIAS_CONFLICT: SOURCE_CONSTITUTION_CONFLICT |
| 46533 | (3-Methoxyphenyl)acetonitrile | EXACT → CONFLICT | OTHER | GENERAL_PARSED_SOURCE_ALIAS_CONFLICT: SOURCE_CONSTITUTION_CONFLICT |
| 47096 | 6-Chloropyrimidine-4-carboxylic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 47622 | 4,6-Dichloro-5-fluoropyrimidine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 47828 | 4-Chloro-1H-imidazo[4,5-c]pyridine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 48466 | 2-chloro-6-isopropylphenol | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 48542 | N-Acetyl-L-citrulline | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 48668 | 4-chlorotoluene-2-sulphonyl chloride | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 49244 | Triethylbromosilane | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 49294 | 2-Chlorobenzyl bromide | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 50054 | 1-deuterioisoquinolin-6-amine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 50080 | 2-Bromobenzotrifluoride | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 50198 | 1,1'-sulfinyldidecane | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 50359 | 2-Methoxy-5-methylpyridine | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 50802 | 5-Hydroxypentanal | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 51083 | Dichloromethane-d2 | EXACT → UNRESOLVED | PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL | CASE_ONLY_PROVIDER_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 51142 | 3-iodo-5-methylbenzonitrile | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 51624 | methyl 3-chloro-5-methylbenzoate | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 52026 | Diphenylacetonitrile | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 52208 | 2,2-Difluoropentanedioic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 52446 | 9H-Fluorene-9-methanol | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 53006 | 5-Bromoisatin monohydrate | CONFLICT → UNRESOLVED | PRIOR_CONFLICT_REMOVED | HYDRATE_SEMANTICS_HOLD: HYDRATION_STOICHIOMETRY_UNKNOWN;MULTICOMPONENT_SEMANTICS_UNKNOWN |
| 53293 | 9-Anthraceneboronic acid | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |
| 53659 | Methyl 2-hydroxyisobutyrate | EXACT → UNRESOLVED | OTHER | SOURCE_PROVIDER_FAILURE_HOLD: EXTERNAL_EVIDENCE_INCOMPLETE |

## Historical unsafe admissions and runtime integrity

The four historical cases remain non-EXACT: 5684 sulfate/sulfite is **UNRESOLVED**; relative-stereo cases 5997 and 23839 are **UNRESOLVED** and **UNRESOLVED**; glucose-form case 30142 is **UNRESOLVED**. They are blocked by general unavailable-source, form or stereo checks, not index rules.

The separately probed historical dithiazole case 5 is **UNRESOLVED**, reason `EXTERNAL_EVIDENCE_INCOMPLETE`, using the old form-aware cache, without injected reviewed fixture or network access. A preliminary probe before the general provider-failure fix returned AUTO_ACCEPT while ChEBI had errored; this is why that general guard was added. The final result is an incomplete-evidence abstention, not proof that the tautomer conflict has been resolved or that future complete source results cannot miss it. [Probe](grounding_remediation_final_scored/historical_case5_probe.json).

Registry verification: **PASS**, 11 exact reconciliations checked, 11 canonical graphs, zero checked duplicates and orphans. The previous explicit-multicomponent, stereo and second-holdout scored registry/candidate snapshots match their frozen hashes; schema, ontology and framework hashes are unchanged. [Verification](grounding_remediation_final_scored/run/verification.json). The production OPSIN jar hash and live class-loading check match the original artifact; neither diagnostic instrumentation nor a shadow OPSIN class was loaded. [Classpath evidence](grounding_remediation/classpath.json).

## Remaining weak grounding and capability gaps

The existing element allowlist, carbon-based organic/inorganic test and coordination heuristics still gate admission and are not independently justified as complete chemical classification. Some bounded stereo/token, protonation, isotope, tautomer and source-claim mechanisms retain the limitations in the audit. Parser-generated names, external lookup status and source aliases can remain dependent; missing or contradictory information now produces more holds, not proof of correctness. No grounded carbohydrate form interpreter, source grammar for general component ratios, general fragment ownership, general solvate classifier, or broader salt/protonation semantics was added. The fresh independent examples are small and the reused 400-case sample cannot demonstrate scale safety. Resolve the scope-guard grounding and review the conservative provider-failure policy and evidence provenance in a separate remediation; **feature development should not resume yet**.

RESOLVER_GROUNDING_REMEDIATION_PARTIAL
