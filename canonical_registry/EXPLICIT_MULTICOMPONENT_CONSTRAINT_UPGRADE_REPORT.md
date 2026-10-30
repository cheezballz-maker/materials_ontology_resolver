# Explicit multicomponent constraint upgrade

The source-only constraint layer is implemented and conservatively limits admission, but the cached development set does not validate broad multicomponent or hydrate admission. **No new identity was admitted in the replay.**

## Implementation and boundary

[`composition_constraints.py`](composition_constraints.py) extracts source claims before retrieval; [`resolver.py`](resolver.py) compares them with the intact candidate graph before the existing form, source-specificity, corroboration and admission gates. The five fields are `components`, `component_counts`, `component_ratios`, `formal_charges` and `fixed_water_count`, with `SPECIFIED`, `UNSPECIFIED`, `CONFLICTING` and `NOT_APPLICABLE` states. The temporary profile also records provenance and comparison diagnostics. A name-parser graph is a hypothesis, not a source assertion establishing the missing composition. A separately supplied typed source structure or explicitly supplied typed component claims can establish a graph; a provider candidate cannot.

The implemented name patterns recognize `di`–`tetra` sodium, potassium and hydrochloride equivalents and `mono`–`deca` hydrate suffixes. Clearly delimited `A / B (1:2)`-style ratios are recorded, but exact component checking requires separately source-stated typed structures for both named components. Unowned numeric ratios remain unspecified. Explicit numeric charge text such as `borate(1-)` is retained, but its ownership must be established before comparison. Broader named-ion recognition, including general imidazolium/sulfate or coordination nomenclature, is not implemented. The comparison diagnostic currently labels a graph check `typed_source_graph` even for a parser hypothesis; use the accompanying `source_graph_kind` to distinguish `SOURCE_NAME_PARSE` from `SOURCE_TYPED_STRUCTURE`. The former never establishes complete source composition.

Counts check preserved Na+, K+, or neutral HCl/chloride equivalents. That equivalence is **only a count check**: neutral base·HCl and protonated base·Cl− remain distinct under the unchanged graph comparator, even where their Standard InChIKeys coincide. No proton transfer, fragment removal, parent selection, charge balancing or replacement of source evidence by a provider is performed. Disconnected candidates with incomplete source composition remain unresolved. Fractional hydrates are not compared using unscaled per-formula-unit counts and remain unresolved.

A numeric hydrate suffix records an equivalent count, but does not alone establish disconnected water: the source must additionally establish water-of-addition meaning, such as an explicit source form assertion, an independently supplied source graph with water, or an appropriately attached source water ratio. Where established, the checker requires exactly the stated number of `O` components. This deliberately does not decide polymorphism, crystal structure or water binding. Generic, fractional and variable hydrates remain held.

The comparator, form characterizer, source-name and source-form interpreters, evidence providers, policy, schema, ontology and reference framework are unchanged; only resolver integration and the new module changed. Hash checks against the prior freeze confirm the other 16 common runtime artifacts, ontology and framework are unchanged. The prior candidate and registry databases retain their scored hashes. The replay uses a separate workspace.

## Tests

**129 tests passed**, including 22 added constraint tests. These cover sodium and potassium counts, two hydrochloride equivalents without proton transfer, owned and unowned ratios, source-stated ionic components and charges, one/two/three waters and wrong counts, unknown and fractional hydration, neutral versus ionic forms, unsupported extra components, source/candidate contradictions and provider attempts to fill missing source semantics. A regression explicitly prevents a name parser from supplying unasserted salt stoichiometry. The earlier sodium-acetate test expectation was updated from acceptance to abstention for a name-only source, reflecting this additional source-constraint gate; its parent-substitution check remains. Test log: [tests.log](explicit_multicomponent_upgrade_release2/tests.log).

## Frozen 400-record development replay

This is an **offline development replay of the previously adjudicated 400**, not a fresh blinded holdout. It used the same frozen source records, independent reference labels and cached evidence, with zero external requests. Freeze, scoring and full case-level evidence: [implementation freeze](explicit_multicomponent_upgrade_release2/IMPLEMENTATION_FROZEN.json), [metrics](explicit_multicomponent_upgrade_release2/metrics.json), [comparison](explicit_multicomponent_upgrade_release2/comparison.json), [constraint audit](explicit_multicomponent_upgrade_release2/audit.json).

| Measure | Result |
| --- | --- |
| Source profiles | 400; 7 have explicit integer sodium/potassium/hydrochloride counts; 7 have numeric charge text |
| Component ratios | 0 owned/specified; 7 numeric ratios with ownership unspecified |
| Hydrate suffixes | 21 numeric suffix counts recorded; 0 source-established discrete water-of-addition counts |
| Candidate comparisons | 215 supported, 119 unresolved, 0 conflict, 66 not reached |
| Final statuses | 152 EXACT, 206 UNRESOLVED, 20 CONFLICT, 22 OUT_OF_SCOPE; unchanged from baseline |
| New admissions / newly recovered reference-confirmed identities | **0 / 0; complete list: none** |
| Newly rejected candidates for composition mismatch | **0; complete list: none** |
| Previously correct admissions lost | 0 of 151 |
| Automatic EXACT | 151 reference-confirmed correct, 0 known false positives, 1 unverified; 151/151 among assessable admissions |
| False merges | 0 among 3 independently assessable coassigned pairs |
| Alias promotion | 179/179 assessable promotions correct; 0 incorrect, 0 unverified; unchanged |

Every EXACT row had a supported composition comparison. The 119 unresolved comparisons left final outcomes unchanged and provide additional source-composition diagnostics; they do not imply that composition alone caused the final abstention. The historical false-positive cases remain non-EXACT: 5684 is CONFLICT; 5997, 23839 and 30142 are UNRESOLVED. Registry verification passed for 152 exact reconciliations and 149 graphs, with zero checked duplicates or orphan rows: [verification](explicit_multicomponent_upgrade_release2/run/verification.json).

## Hydrate and representative case review

The development sample contains **zero source-established fixed water-of-addition constraints**, so there are **0/0 evaluable correct fixed-water matches and 0 wrong-count rejections** in this replay. Synthetic tests exercise matching mono-, di- and trihydrates and a dihydrate/monohydrate mismatch; they are not evidence of real-world coverage. Of 15 records without numeric suffix counts, 12 were generic hydrate names and 3 were hemihydrates; all were non-EXACT. Five hydrate-named records ended in CONFLICT: 1049 and 41224 had invalid provider structures; 9604, 24624 and 53006 had identity-dimension conflicts. These are not claimed to be water-count conflicts. [All hydrate cases and diagnostics](explicit_multicomponent_upgrade_release2/audit.json).

| Case | Source constraint and outcome |
| --- | --- |
| 30203, dihydrochloride | Two hydrochloride equivalents recorded; UNRESOLVED because complete multicomponent semantics are missing. |
| 31381, disodium tartrate dihydrate | Two sodium equivalents and numeric hydrate suffix recorded; UNRESOLVED, including unspecified stereo and an InChI warning. |
| 53438, disodium nucleotide | Two sodium equivalents recorded; UNRESOLVED for source stereo. |
| 41891, 1:2 acid/substituted alcohol | Ratio ownership is not established by the supported delimiter grammar; UNRESOLVED. |
| 50220, imidazolium ethylsulfate | Full named-ion composition/ratio is not independently established; UNRESOLVED. |
| 11038, ampicillin trihydrate | Three suffix equivalents recorded, but discrete water meaning and source stereo are not established; UNRESOLVED. |
| 11279, hydrochloride hydrate | Water amount is unspecified; UNRESOLVED. |
| 35841, dihydrochloride hemihydrate | Two equivalents recorded; fractional formula-unit scaling is unsupported and the result remains UNRESOLVED. |
| 30142, `disodiumsalt dihydrate` | Glued `disodiumsalt` is not recognized by the bounded count grammar; sugar form/stereo remain unspecified, so UNRESOLVED. |

## Remaining work

This is a narrow constraint checker, not a general component-name interpreter. Standalone named ions, many source syntaxes, ownership of charge and ratios, complexation, fractional hydration, protonation sites and solvate identity remain unsupported. An explicit typed source assertion must still pass all existing identity and evidence checks. The replay has no positive real-world fixed-water comparisons or new admissions, and its limited three assessed merge pairs cannot establish performance at scale. The next capability should be source-grounded component and formula-unit ownership with independently validated examples, followed by a fresh blinded evaluation; broader salt admission is not justified by these results.

EXPLICIT_MULTICOMPONENT_CONSTRAINTS_PARTIAL
