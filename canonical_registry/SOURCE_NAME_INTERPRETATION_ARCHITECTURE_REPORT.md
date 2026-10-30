# Source-name interpretation architecture

**Result: partial.** The resolver now records source-name interpretation before retrieval and never lets a provider response establish an unknown preferred name. The frozen 400-record development replay retained all 151 previously confirmed admissions and blocked the four earlier false positives. The interpreter is deliberately bounded: its state is not a general proof of source meaning, and it cannot yet establish common-name identities from trusted external name-to-form evidence. This is not a fresh blinded evaluation.

## Architecture and states

[The interpreter](name_interpretation.py) receives the original preferred source name, its deterministic source parse, and original alias texts; it does not receive provider records or candidate structures. It returns the interpretation and a [source-only feature profile](source_form.py) before acquisition. The resolver then performs the existing retrieval, form-aware comparison, source-specificity gate and admission checks. `ESTABLISHED` here means the supported parser has supplied a provisional source-form interpretation without an identified missing dimension; it is **not** canonical identity proof. Existing chemical validation, corroboration, and the source-form gate remain mandatory. `PARTIAL` identifies recognized underspecification such as relative-only stereo, a recognized broad sugar form, or unassigned stereogenic elements. `UNKNOWN` means the interpreter lacks an adequate reading; `CONFLICTING` currently detects a bounded sulfate/sulfite source-claim contradiction when the preferred claim cannot otherwise be parsed, or a parsed preferred name conflicting with an explicitly supplied source structure. Conflict detection is not comprehensive.

The four diagnostics are `NAME_INTERPRETATION_UNKNOWN`, `NAME_UNDERSPECIFIED`, `NAME_CONFLICT`, and `NAME_NOTATION_UNSUPPORTED`. The last recognizes some locant-style notation and is a bounded implementation heuristic; other unsupported nomenclature can receive the generic unknown diagnostic. In particular, the runtime does not assert that every unparsed name is inherently ambiguous. If the interpretation is UNKNOWN or CONFLICTING, a result that otherwise passes the unchanged source-form gate is blocked. PARTIAL remains subject to that gate, which decides whether the actual source and candidate support an exact form. An original preferred name may also be parsed after a source-only alphabetic hyphen-to-space normalization; numeric locants remain intact and the existing gate remains mandatory.

The minimal `NameInterpretationEvidence` interface carries name, interpreted form, interpretation status and reference. No external input to it is currently trusted or applied. A retrieved stereodefined structure cannot turn Sitagliptin from UNKNOWN into ESTABLISHED. Original aliases remain separate claims and may help retrieval or be independently checked, but unrelated aliases cannot establish an unknown preferred referent. A conflicting alias does not veto an independently established preferred parse. The narrow conflicting-source check operates only when the preferred name has not been parsed and recognizes explicit opposing oxyanion terms; it is not a synonym inference.

## Tests and development replay

The retained suite and eight new tests passed: **89 tests**. The new tests cover relative stereo, uninterpreted common names with provider hits, conflicting source claims, a bad alias alongside a parsed preferred name, unsupported notation, untrusted future evidence, typed-structure/name conflict, and alias non-establishment. [Test log](name_interpretation_architecture/tests.log).

The same 400 frozen inputs and labels were replayed offline with copied caches: zero provider requests and zero missing cached queries. The previous and current predictions have identical status and assessed verdicts. Exactly 152 records were admitted: **151/151 assessable EXACT admissions correct**, plus one unverified; zero assessed false positives. All 151 previously confirmed admissions retained their exact structures. Alias precision remained **179/179 assessable**, false merges **0/3 assessable coassigned pairs**, and non-EXACT outcomes **248/400 (62%)**. Status agreement with frozen judgments remained 239/400. Such small, enriched development samples do not establish deployment precision.

| Prior false positive CUMA | Interpretation state | Current resolution |
| --- | --- | --- |
| 5684 | CONFLICTING / NAME_CONFLICT | CONFLICT; sulfate/sulfite source conflict |
| 5997 | PARTIAL / NAME_UNDERSPECIFIED | UNRESOLVED; relative stereo |
| 23839 | PARTIAL / NAME_UNDERSPECIFIED | UNRESOLVED; relative stereo |
| 30142 | PARTIAL / NAME_UNDERSPECIFIED | UNRESOLVED; sugar form and stereo |

Across all 400 records, the new states were ESTABLISHED 216, PARTIAL 40, UNKNOWN 143 and CONFLICTING 1. These are source-interpretation states, not admission counts. Of the 18 prior cases whose final reason included `SOURCE_PREFERRED_INTERPRETATION_UNKNOWN`, 15 are UNKNOWN, two relative-stereo cases are PARTIAL, and the sulfate/sulfite case is CONFLICTING; no case was re-admitted. [Complete case review](name_interpretation_architecture/unknown_review.json).

## Fifteen previously confirmed admissions withheld

All 15 remain UNKNOWN and UNRESOLVED. The frozen references support their earlier assessed identities, but a retrieved or reference structure alone is not loaded as a trusted runtime interpretation of the preferred source name. The classification below is a bounded review, not a claim that each name is inherently unambiguous.

| CUMA | Preferred name | Runtime interpretation / diagnostic | Review |
| --- | --- | --- | --- |
| 642 | (2E)-7-{(1R,2R,3R)-3-hydroxy-2-[(1E,3S,5S)-3-hydroxy-5-methylnon-1-en-1-yl]-5-oxocyclopentyl}hept-2-enoic acid (non-preferred name) | UNKNOWN / NAME_NOTATION_UNSUPPORTED | Complex systematic notation and appended annotation; parser does not establish the referent. |
| 4183 | cyclobutanemethanesulfonyl chloride | UNKNOWN / NAME_INTERPRETATION_UNKNOWN | Systematic-name parsing limitation; no reliable preferred-name interpretation. |
| 7164 | 5-(4-Chlorobuty)-1-Cyclohexyl Tetrazol | UNKNOWN / NAME_NOTATION_UNSUPPORTED | Possibly truncated spelling in a systematic name; cannot determine intended referent. |
| 9636 | ibandronic acid | UNKNOWN / NAME_INTERPRETATION_UNKNOWN | Common drug name; trusted name-to-form interpretation absent. |
| 10141 | Ormetoprim | UNKNOWN / NAME_INTERPRETATION_UNKNOWN | Common drug name; trusted name-to-form interpretation absent. |
| 15409 | Borate(1-),trifluoro(1-methylethenyl)-, potassium (1:1), (T-4)- | UNKNOWN / NAME_NOTATION_UNSUPPORTED | Unsupported registry-style borate and coordination notation; component/form semantics also require work. |
| 15460 | 1,2-Pyrrolidinedicarboxylicacid, 4-cyano-, 1-(1,1-dimethylethyl) 2-methyl ester, (2S,4S)- | UNKNOWN / NAME_NOTATION_UNSUPPORTED | Unsupported inverted registry notation and stereo locants. |
| 18722 | tri(ethylene glycol) divinyl ether | UNKNOWN / NAME_INTERPRETATION_UNKNOWN | Polyether-style systematic notation; parser limitation, not proven semantic ambiguity. |
| 23774 | 2,3,3-Trimethyl-4,5-benzo-3H-Indole | UNKNOWN / NAME_NOTATION_UNSUPPORTED | Unsupported fused-ring systematic notation. |
| 27955 | benazolin | UNKNOWN / NAME_INTERPRETATION_UNKNOWN | Common pesticide name; trusted name-to-form interpretation absent. |
| 29365 | Diazogen | UNKNOWN / NAME_INTERPRETATION_UNKNOWN | Name resembles a trade/common name; intended mapping is not established by the interpreter. |
| 33770 | Metronidazole benzoate | UNKNOWN / NAME_INTERPRETATION_UNKNOWN | Drug/ester common-name interpretation unavailable; exact form also needs support. |
| 39419 | potassium trifluoro(prop-2-en-1-yl)borate(1-) | UNKNOWN / NAME_NOTATION_UNSUPPORTED | Borate and charge/component notation not interpreted; coordination and form semantics also require work. |
| 40845 | 2-naphthalene methanol | UNKNOWN / NAME_NOTATION_UNSUPPORTED | Naphthalene nomenclature parser limitation. |
| 48151 | Calcium Dobesilate | UNKNOWN / NAME_INTERPRETATION_UNKNOWN | Drug/salt common-name interpretation unavailable; component/form semantics also require work. |

Common or trade-name cases need reliable, form-specific name-to-identity evidence with provenance before their source meaning can be established. Systematic notation cases need better supported interpretation; malformed spelling may need source clarification. Nothing in this review changes a resolution.

## Remaining limitations and audit

The interpreter recognizes only bounded notation and conflict patterns; parsed names can contain subtleties not yet captured by its lexical features. Form-specific source evidence is not implemented, and a narrow punctuation reparse is not a general synonym rule. Separate gaps remain in complete stereo locant mapping, hydration and solvation stoichiometry, multicomponent and salt semantics, coordination, isotope-position handling, tautomer policy, and provider independence. A fresh blinded evaluation is required before drawing conclusions about scaling.

The existing read-only registry verification passed: 152 EXACT rows revalidated, 149 canonical graphs, no checked duplicates or orphan rows. The separate name-state audit found an interpretation on all 400 records and no admitted row with UNKNOWN/CONFLICTING interpretation or a failing source-form gate. These are consistency checks, not independent chemical validation. The ontology and framework hashes, frozen labels and baseline predictions were checked; the prior registry was not modified. The replay generated a separate snapshot. See [implementation freeze](name_interpretation_architecture/IMPLEMENTATION_FROZEN.json), [comparison](name_interpretation_architecture/comparison.json), [metrics](name_interpretation_architecture/metrics.json), [registry verification](name_interpretation_architecture/run/verification.json), [name-state verification](name_interpretation_architecture/name_verification.json), and [scoring freeze](name_interpretation_architecture/SCORING_FROZEN.json).

SOURCE_NAME_ARCHITECTURE_PARTIAL
