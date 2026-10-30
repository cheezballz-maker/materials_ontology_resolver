# Source-form interpretation upgrade

**SOURCE_FORM_GATE_PARTIAL.** The final development replay blocks all four previously identified false-positive admissions. Adjudicable EXACT precision changed from 166/170 (97.65%) to 151/151 (100.00%), while 15 previously reference-confirmed admissions were withheld. This is a replay of the development set, not a new blinded validation. The remaining recall cost and bounded interpretation rules prevent a claim that the source-specificity invariant has been proven generally.

## Architecture and source-specificity representation

The new [source_form.py](source_form.py) separates source claims from candidate structures. [resolver.py](resolver.py) records a preferred claim before retrieval and, for a candidate that otherwise passes the existing policy, evaluates that claim and individually parsed source aliases before final admission. A candidate must pass the source gate as well as the unchanged form, official-InChI, external-evidence and identity-comparison checks. Every promoted alias also passes its own source-specificity check. The gate does not allocate IDs, query providers, alter structures or change the five-table schema.

The audit representation stores original claim text, claim type, parse status and parsed structure, lexical source features, comparisons with substantive aliases, source states and candidate compatibility for constitution, stereochemistry, isotope, protonation/charge, tautomer, components, stoichiometry, hydration/solvation and molecular-form scope. States include SPECIFIED, PARTIALLY_SPECIFIED, UNSPECIFIED, ENSEMBLE, CONFLICTING and NOT_APPLICABLE; compatibility is SUPPORTED, OVER_SPECIFIED, CONFLICTING, UNKNOWN or NOT_APPLICABLE. An otherwise admissible candidate is blocked if a dimension is OVER_SPECIFIED, CONFLICTING or identity-significant UNKNOWN. The initial pre-candidate record can be NOT_YET_ASSESSED.

| Dimension | Current implementation and limits |
| --- | --- |
| Constitution | A preferred name must parse as a source claim, a typed source structure must be supplied, or an independently attested original alias must be a narrow alphabetic-hyphen/whitespace variant of the preferred claim. Locant punctuation is retained. Sulfate/sulphate and sulfite/sulphite claims are checked against sulfur–oxygen connectivity; a mismatch is a conflict. |
| Stereochemistry | Recognizes relative cis/trans/syn/anti, absolute R/S, D/L and ensemble terms. A relative-only claim cannot select a non-identical mirror image; a single explicit R/S or E/Z descriptor is checked against a single candidate stereogenic element. Multiple absolute descriptors are counted conservatively, but general locant-to-atom mapping and all relative-descriptor semantics are not implemented. |
| Sugar form | Recognized sugar-root names must specify open-chain scope or a ring and anomer; an explicitly cyclic claim is checked for a sugar-like ring. Named alditols are not treated as anomeric cyclic sugars. This is bounded lexical/structural recognition, not a complete carbohydrate grammar. |
| Isotopes, protonation, tautomers and components | The gate carries source support and the existing form checks forward; it does not strip isotopes, change protonation, select a parent, normalize tautomers or replace components. Existing rules still decide admissibility. Complex isotope positions, tautomer/source-name semantics and unmodeled forms are not comprehensively interpreted by this increment. |
| Typed source structure | A valid structure explicitly supplied by the source can establish form specificity; a candidate generated or retrieved from a database cannot. Explicit recognizable contrary source claims, such as a single opposite R/S descriptor or sulfate/sulfite mismatch, still block admission. |

A parsed preferred claim does not make every alias a synonym. A separately parsed alias that conflicts with a clear preferred candidate is recorded and withheld without automatically vetoing the source concept. If the preferred claim itself cannot be interpreted, the new gate does not let an unrelated specific alias silently define it. This deliberately narrow link is a major source of the observed recall loss.

## Tests and evaluation method

The complete retained suite plus new source-form regressions passed: **81 tests**. New tests exercise relative versus absolute stereo, unspecified and collective stereo, R/S and E/Z contradictions, harmless alias disagreement, sulfate/sulfite conflict, broad sugar and anomer handling, explicit ring/chain conflict, alditols, typed structures, valid retrieval and safe punctuation variants. Existing tests continue to cover isotope, salt/counterion, hydrate/solvate, tautomer, protonation, constitutional isomers, strict parser prefix rejection, InChI disagreement and provider conflicts. One existing alias-recovery test was retained but its previously unsupported preferred-name fixture was replaced with a narrow spelling variant; a separate new regression requires the old ambiguous fixture to abstain.

The 400 source inputs and frozen labels from the second holdout were replayed in a separate snapshot. Provider responses were copied byte-for-byte from the original run; offline mode made **zero new requests** and recorded **zero missing/not-queried acquisition queries**. The baseline and final scorer use the same frozen labels and comparison functions. No reference was revised. The source is an enriched capability sample, and this re-evaluation is informed by prior results: precision, Wilson intervals and recall are descriptive, not fresh generalization estimates.

An initial preparation stopped before resolver execution because its ontology path was wrong; that attempt was retained. A first completed replay blocked the four errors but withheld 17 correct identities. A general alditol-classification fix, single R/S check and explicit ring/chain check were then added; a second replay withheld 15 correct identities. A further single E/Z configuration check and regression were added before this final replay. The superseded pre-run freeze and both completed earlier snapshots remain available for audit; the final implementation and tests were frozen before its replay.

## Before and after

| Measure | Original holdout | Final development replay |
| --- | --- | --- |
| Automatic EXACT | 171 | 152 |
| Confirmed correct EXACT | 166 | 151 |
| Confirmed false-positive EXACT | 4 | 0 |
| Unverified EXACT | 1 | 1 |
| Adjudicable EXACT precision | 166/170 (97.65%) | 151/151 (100.00%) |
| Confirmed EXACT recall | 166/276 (60.14%) | 151/276 (54.71%) |
| Previously correct admissions withheld | — | 15 |
| New source-gate abstentions among previous EXACT | — | 19 |
| Alias-promotion precision | 205/205 (100.00%) | 179/179 (100.00%) |
| Alias promotions: correct / incorrect / unverified | 205 / 0 / 7 | 179 / 0 / 0 |
| False merges | 0/3 assessed; 1 unassessed | 0/3 assessed; 0 unassessed |
| All non-EXACT abstentions | 229/400 (57.25%) | 248/400 (62.00%) |
| Five-status agreement | 250/400 (62.50%) | 239/400 (59.75%) |

Of the 19 newly withheld previous EXACT records, four were the identified false positives and 15 were reference-confirmed identities. There were 0 new reference-confirmed admissions. The one unverified admission remains outside the precision denominator. Reference EXACT withholding is not itself proof that the new abstention is unsafe: the resolver may lack the independently corroborated source interpretation available to the blinded reviewers.

All 151 retained correct admissions preserve the reference-matching molecular graph. 149 have a different `SUB_` value in the separately rebuilt evaluation snapshot because allocation was performed afresh relative to the historical base registry. This is not an ID migration or evidence of graph changes; no existing registry was modified.

There were 3 assessable coassigned pairs and no false merge. The old unassessed coassignment of the two relative-stereo records disappeared when both were withheld. Of six reference-equivalent pairs, all three previous correct clusters remain clustered, two remain both withheld and one remains partly withheld. These denominators are small.

## Four previous false-positive admissions

| CUMA | Preferred name | Before → after | Final reason |
| --- | --- | --- | --- |
| 5684 | 1,1-Cyclopropane dimethanol cyclic sulphate | EXACT → CONFLICT | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN;SOURCE_CONSTITUTION_CONFLICT |
| 5997 | 1-N-BOC-1,2-TRANS-CYCLOHEXYLDIAMINE | EXACT → UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN;SOURCE_STEREO_RELATIVE_ONLY;SOURCE_FORM_OVERSPECIFIED_BY_CANDIDATE |
| 23839 | 1-N-BOC-1,2-TRANS-CYCLOHEXYLDIAMINE | EXACT → UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN;SOURCE_STEREO_RELATIVE_ONLY;SOURCE_FORM_OVERSPECIFIED_BY_CANDIDATE |
| 30142 | D-glucose 6-phosphate disodiumsalt dihydrate | EXACT → UNRESOLVED | SOURCE_STEREO_PARTIALLY_SPECIFIED;SOURCE_SUGAR_FORM_UNSPECIFIED |

The two trans-cyclohexanediamine rows are duplicate source concepts and represent one stereo failure pattern. The sulfate/sulfite case concerns contradictory preferred versus alias constitution; the glucose case concerns unjustified open-chain/anomer specificity. A substantive bad alias by itself remains insufficient to veto a fully supported preferred identity.

## Previously confirmed admissions lost

| CUMA | Preferred name | Final outcome | Reason |
| --- | --- | --- | --- |
| 642 | (2E)-7-{(1R,2R,3R)-3-hydroxy-2-[(1E,3S,5S)-3-hydroxy-5-methylnon-1-en-1-yl]-5-oxocyclopentyl}hept-2-enoic acid (non-preferred name) | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN;SOURCE_FORM_OVERSPECIFIED_BY_CANDIDATE |
| 4183 | cyclobutanemethanesulfonyl chloride | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN |
| 7164 | 5-(4-Chlorobuty)-1-Cyclohexyl Tetrazol | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN |
| 9636 | ibandronic acid | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN |
| 10141 | Ormetoprim | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN;SOURCE_FORM_OVERSPECIFIED_BY_CANDIDATE |
| 15409 | Borate(1-),trifluoro(1-methylethenyl)-, potassium (1:1), (T-4)- | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN;SOURCE_FORM_OVERSPECIFIED_BY_CANDIDATE |
| 15460 | 1,2-Pyrrolidinedicarboxylicacid, 4-cyano-, 1-(1,1-dimethylethyl) 2-methyl ester, (2S,4S)- | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN;SOURCE_FORM_OVERSPECIFIED_BY_CANDIDATE |
| 18722 | tri(ethylene glycol) divinyl ether | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN |
| 23774 | 2,3,3-Trimethyl-4,5-benzo-3H-Indole | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN;SOURCE_FORM_OVERSPECIFIED_BY_CANDIDATE |
| 27955 | benazolin | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN;SOURCE_FORM_OVERSPECIFIED_BY_CANDIDATE |
| 29365 | Diazogen | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN |
| 33770 | Metronidazole benzoate | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN;SOURCE_FORM_OVERSPECIFIED_BY_CANDIDATE |
| 39419 | potassium trifluoro(prop-2-en-1-yl)borate(1-) | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN;SOURCE_FORM_OVERSPECIFIED_BY_CANDIDATE |
| 40845 | 2-naphthalene methanol | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN |
| 48151 | Calcium Dobesilate | UNRESOLVED | SOURCE_PREFERRED_INTERPRETATION_UNKNOWN;SOURCE_FORM_OVERSPECIFIED_BY_CANDIDATE |

These losses are not silently counted as correct abstentions in the recall calculation. Each has a frozen EXACT reference. All were withheld because the gate could not establish the unparsed preferred claim; a narrowly equivalent, independently attested source alias is one supported path, but authoritative source-name evidence is not yet represented by this interface. Some source names are malformed, while others are established common names or structurally explicit nomenclature. The separate reference evidence can support manual review; it is not loaded into the runtime.

## Review of the 21 prior source-intent losses

Of the 21 frozen reference-EXACT records, 0 are now safely recoverable, 0 were classified as correctly conservative, 15 still require source-name interpretation not implemented here, and 6 have an additional or earlier capability gap. The classification is a post-score review, not a reference-label change. The two notation cases were reclassified after checking the unchanged earlier stereo-token matcher.

| CUMA | Preferred name | Classification | Final reason / review |
| --- | --- | --- | --- |
| 1357 | Vitamin D2, 1a-Hydroxy- | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 4743 | Grazoprevir | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 6984 | Lysine clonixinate | different underlying capability gap | MULTICOMPONENT_SEMANTICS_UNKNOWN;STEREO_SOURCE_INTENT_UNSPECIFIED; The saved reason also identifies multicomponent or hydration semantics; resolving stereo alone would not establish admission. |
| 7464 | Meropenem trihydrate | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 8969 | timolol maleate | different underlying capability gap | MULTICOMPONENT_SEMANTICS_UNKNOWN;STEREO_SOURCE_INTENT_UNSPECIFIED; The saved reason also identifies multicomponent or hydration semantics; resolving stereo alone would not establish admission. |
| 9361 | docetaxel trihydrate | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 11038 | Ampicillin trihydrate | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 14541 | (3aR,4S,5R,6aS)-4-(tert-Butyldimethylsilyloxy)methyl-5-hydroxy-hexahydro-2H-cyclopenta[b]furan-2-one | different underlying capability gap | STEREO_SOURCE_INTENT_UNSPECIFIED; The existing form characterizer does not recognize bridgehead locants such as 3aR in its stereo-token expression; the new gate is not reached. |
| 18761 | Abacavir | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 25769 | pleuromulin | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 26725 | Cetrorelix diacetate | different underlying capability gap | MULTICOMPONENT_SEMANTICS_UNKNOWN;STEREO_SOURCE_INTENT_UNSPECIFIED; The saved reason also identifies multicomponent or hydration semantics; resolving stereo alone would not establish admission. |
| 26798 | L(+)-Tartaric acid | different underlying capability gap | STEREO_SOURCE_INTENT_UNSPECIFIED; The existing form characterizer does not recognize L(+)- notation; the new gate is not reached. |
| 29227 | Geranyl Bromide | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 33781 | Clascoterone | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 36998 | cortisone | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 38882 | Hydrocortisone hemisuccinate hydrate | different underlying capability gap | HYDRATION_STOICHIOMETRY_UNKNOWN;MULTICOMPONENT_SEMANTICS_UNKNOWN;STEREO_SOURCE_INTENT_UNSPECIFIED; The saved reason also identifies multicomponent or hydration semantics; resolving stereo alone would not establish admission. |
| 41478 | Sitagliptin | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 46125 | Desogestrel | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 52171 | Isoacteoside | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 52577 | Meropenem | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |
| 53438 | xanthosine 5'-monophosphate disodium salt | still requires unsupported interpretation | STEREO_SOURCE_INTENT_UNSPECIFIED; The old admission gate has no source-supported mapping from this name to its fully specified stereochemical form; the new gate does not invent one. |

## Remaining gaps and next capability

The source gate is not a complete semantic interpreter. Its sugar and sulfur-name recognition is bounded; it does not map every multi-locant stereo descriptor to the correct candidate atom/bond or fully interpret all isotope-position and tautomer naming. A parser’s successful output can still reflect a default in an unrecognized naming family. Unrecognized or weakly supported distinctions require further conservative review. The untouched earlier form characterizer can also return before the new gate, as the two notation cases show. No claims of universal zero-error behavior follow from a development replay or three assessable cluster pairs.

**Primary next capability: evidence-backed interpretation of the original preferred name.** Represent reliable source-name-to-form evidence, including recognized common names and explicit stereo nomenclature, with its provenance and identity scope. It must establish the name’s intended form, not merely prove that a retrieved graph exists or repeat a copied provider record. This addresses the 15 new losses and the still-uninterpreted cohort while retaining abstention for genuinely broad or conflicting names. Validate it on a fresh blinded set after development. Salt proton transfer, multicomponent/hydrate rules, advanced tautomer policy, coordination handling, provider selection and the ontology remain separate work.

## Integrity and audit

The existing verifier passed with 152 EXACT reconciliations revalidated, zero duplicate/orphan violations and five persistent tables. A separate read-only source-gate replay checked 152 admitted source claims and 179 promoted aliases. These are consistency checks, not independent chemical validation. The framework, ontology, prior registry snapshots and frozen labels retain their original hashes. No full CUMA run was performed.

Artifacts: [frozen implementation and cache manifest](source_form_upgrade/IMPLEMENTATION_FROZEN.json), [tests](source_form_upgrade/tests.log), [final metrics and four cases](source_form_upgrade/metrics.json), [all changed outcomes](source_form_upgrade/changes.json), [all lost admissions](source_form_upgrade/previously_correct_lost.json), [cohort review](source_form_upgrade/cohort_review.json), [gate verification](source_form_upgrade/gate_verification.json), [registry verification](source_form_upgrade/run/verification.json), [scoring freeze](source_form_upgrade/SCORING_FROZEN.json), [first replay](source_form_upgrade_attempt_1/metrics.json), [second replay](source_form_upgrade_attempt_2/metrics.json), and [final audit](source_form_upgrade/FINAL_VERIFICATION.json).

**SOURCE_FORM_GATE_PARTIAL**
