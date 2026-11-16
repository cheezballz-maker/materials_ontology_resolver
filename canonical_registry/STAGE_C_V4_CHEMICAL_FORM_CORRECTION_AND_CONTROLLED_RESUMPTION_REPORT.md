# Stage C v4 chemical form correction and controlled resumption

Stage C v4 withheld the unsupported Pyridoxine Salicylate assignment and admitted qualified isopropyl alcohol after a complete registry search proved it distinct from acetone. The monitored run mapped 22 of 300 fresh CosIng concepts to new identities in an isolated fixture. All 329 checkpoints replayed consistently. Provisional review found no incorrect exact mapping and identified one plausible missed exact assignment. Independent chemical accuracy remains unestablished, so broader automatic admission remains conditional.

## Baseline and failure analysis

The restricted expansion processed 2,000 fresh CosIng revisions and 33 controls. It recorded 61 fresh exact mappings before provisional review found an unsupported form assignment. Repository cleanup preserved the failed fixture and its journals. Its old shared cache could only be replayed under the documented cache exception. The v4 runner uses separate caches for safety controls and the monitored run. [Restricted expansion](STAGE_C_RESTRICTED_MONITORED_COSING_EXPANSION_V1_REPORT.md), [v3 safety closure](STAGE_C_V3_SAFETY_CLOSURE_REPORT.md), [authority coverage](STAGE_C_V3_AUTHORITY_COVERAGE_AND_SCALABLE_CANONICALIZATION_REPORT.md), [cleanup](REPOSITORY_HYGIENE_AND_LEGACY_CLEANUP_V1_REPORT.md), [implementation map](maintenance/IMPLEMENTATION_INDEX.md).

The saved CosIng revision `8e15ab4af3bf75385dc65214ca442d2e0cf9edc74cdeec3db28cd30169bf563f` of Pyridoxine Salicylate, `CIC_00019582`, contains a designation and no definition, CAS or EC. Stage B retained an OPSIN-derived ester graph as a candidate-only assertion. PubChem CID 187064 returned the same graph, and the provider's computed systematic name parsed to that graph. The earlier lookup promoted the agreement to `AUTHORITY_PREFERRED_NAME_AND_SOURCE_GRAPH` and issued a whole-referent nomenclature claim. The evaluator validated the proposed graph, the source-scope gate found no explicit contradiction, and the creation transaction assigned `SUB_00000621` and recorded the designation as an exact alias. The published patent uses the same designation for an ion pair. The original evidence leaves the CosIng form unresolved. The old fixture retains the assignment as quarantined evidence. [Saved assignment and authority receipt](stage_c/data/pilot-expansion/quarantined_findings.json), [US patent application, claims 18–19](https://patents.google.com/patent/US20060147508A1/en).

Isopropyl alcohol and acetone share the coarse heavy-atom adjacency used for candidate retrieval. The full structures have formulas C3H8O and C3H6O. The full comparator called them distinct. Charge attribution left the protonation dimension unknown because two hydrogen atoms differ without a net charge change. The registry aggregator used only the reconciled dimensions and lost the global distinction. The matcher now preserves a full-graph composition distinction for sufficiently qualified, supported single-component molecular graphs with the same charge, no radical ambiguity, and a demonstrated non-protonation hydrogen-count difference. Incomplete structures and conflicting registry evidence still block this proof. [Isopropyl alcohol](https://webbook.nist.gov/cgi/cbook.cgi?ID=C67630), [acetone](https://webbook.nist.gov/cgi/cbook.cgi?ID=C67641), [historic matcher trace](stage_c/data/pilot-expansion/isopropyl_duplicate_diagnostic.json).

## Form qualification

The Stage C safety layer records one of five diagnostics. Canonical statuses and the shared evidence contract remain in use. [Evidence sufficiency contract](CHEMICAL_IDENTITY_EVIDENCE_SUFFICIENCY_CONTRACT_V1.md), [form qualification implementation](stage_c/source_identity_safety.py), [matcher aggregation](canonical_registry_matching/registry_matcher.py).

| Diagnostic | Meaning |
|---|---|
| `EXACT_FORM_ESTABLISHED` | A whole structure, qualified exact-form identifier, exact systematic source definition, or an existing applicable qualified pathway establishes the form. |
| `EXACT_FORM_UNSUPPORTED_BY_SOURCE` | A valid candidate exists. The source lacks affirmative evidence to select the form. The receipt is withheld before matching. |
| `MULTIPLE_FORMS_PLAUSIBLE` | Source or applicable authority evidence presents alternatives without selecting one. |
| `IDENTITY_CONFLICT` | Applicable identity evidence contradicts the candidate form. |
| `FORM_SCOPE_UNESTABLISHED` | The available evidence does not support exact molecular scope. |

The proof obligation applies to parser–computed-name corroboration, covalent ester graphs with a basic site, charged or multicomponent graphs, and association designations. It can be discharged by exact evidence for the source revision. Scope observations for distributions, preparations and representative structures continue to block exact whole-ingredient mappings. The matcher preserves the existing distinct-form and complete-search semantics for tautomers, resonance, salts, stereoisomers and isotopologues.

## Frozen evaluation and acquisition

The fresh cohort contains 300 CosIng concepts selected by a stable hash after excluding the previous Stage C cohorts and the historical authority and evidence-sufficiency cohorts. The six strata contain 105 defined graphs, 30 other graphs, 65 form-sensitive records, 30 conflicts, 40 broad or preparation records and 30 identifier-led records. Five read-only Trino shards returned candidates for 182 records. The provider queues used public full InChIKeys, UNIIs and CAS numbers and retained the preceding capture receipts.

| Evidence | New receipts | Outcome | First-to-last receipt span |
|---|---:|---|---:|
| PubChem | 92 | 91 JSON, 1 HTTP error | 126.5 s |
| ChEBI | 132 | 78 JSON, 54 HTTP errors | 255.1 s |
| GSRS | 104 | 104 JSON, including accession lookups and native records | 180.4 s |
| Operational NIST CAS | 114 | 49 structural references, 65 without reference fields | 146.6 s |
| Separate NIST review CAS | 61 | 14 structural references, 47 without reference fields | 77.6 s |

The provider requests ran concurrently and their spans overlap. The warehouse receipts reported 13.9 s total query execution across the five shards. The review plan froze 18 cases per stratum. Reference packets keep graph comparisons and whole-source judgments separate and flag CAS overlap with operational evidence. [Frozen cohort](stage_c/data/v4/freeze.json), [sealed inputs](stage_c/data/v4/acquisition_freeze.json), [reference plan](stage_c/data/v4/reference_plan.json), [provisional source screen](stage_c/data/v4/provisional_reference_screen.json).

## Measured gates and results

### Phase 1 safety closure

All ten historical negative controls were retested in the isolated lifecycle. The fixture recorded no exact association or alias for any of them. Pyridoxine Salicylate received `EXACT_FORM_UNSUPPORTED_BY_SOURCE`. Ethylcyclohexene-1-carboxylate and 2-tert-butylhydroquinone methyl ether received identity conflicts. Tridecyl isononanoate and butylene glycol diisononanoate retained whole-scope holds. Citric acid, magnesium sulfate, glutamic acid and sodium chloride remained unresolved. Alcohol Denat. was identified as non-discrete. The current run supplied no source-specific hold overrides.

Nine CosIng positives resolved, including WATER and AQUA to the same baseline ID, verified ethanol, glycerol, acetone, hydrogen peroxide, isopropyl alcohol, tripalmitin and phenylparaben. Three native GSRS controls reused the water, ethanol and glycerol IDs. The 29 checkpoints contain 12 exact mappings, five reuse operations, seven new fixture Substances and 12 alias assertions. Sodium acetate remained unresolved for the original designation. The new form test suite exercised a separately specified molecular salt and other whole-form evidence paths. No positive claim is made for a fresh CosIng salt association solely from that synthetic qualification exercise.

Isopropyl alcohol was matched against a fixture snapshot of 566 identities. The constitution index excluded 565 by necessary condition, and the full graph comparison excluded the one remaining candidate, acetone. The matcher established complete no-match with zero unresolved possible duplicates. The transaction admitted fixture identity `SUB_00000567` and completed its live self-match. The compound's resolved form had qualified authority evidence and the reported 67-63-0 CAS matched the NIST reference. [Phase 1 gate and complete match proof](stage_c/data/v4/phase_1_gate.json), [control integrity](stage_c/data/pilot-v4-controls/metrics.json).

The regression run passed 127 tests and 49 subtests, including 24 new form and matching controls. It exercised matched constitutional isomers, isotopes, stereochemistry, salts, tautomers, resonance, intentionally incomplete graphs, duplicate prevention and rollback. The 29-record control run took 538.1 s including provider decoding and fixture setup. Peak process working set was 416.0 MiB. The 12 combined matching/admission transactions had a median of 2.078 s. A separate read-only profile of the nine CosIng positives on the populated control snapshot measured 0.953 s median and 52.119 s P95 for matching and its admission validation, with the cold candidate-index load included. This profile differs from transaction timing. [Test output](stage_c/data/v4/tests.log), [matching profile](stage_c/data/v4/control_matching_profile.json).

The old failed fixture and 2,970 compressed historical events were verified read-only against their prior digests. The v4 runtime protects the source inputs and separately seals its own derived cache. A read-only matcher profile used the shared development cache before the fresh fixture opened. That cache's digest changed. The new run checks 69 original path and sidecar entries and keeps the shared cache outside v4's replay dependency. The old cleanup report and Stage C manifests retain their original checksums. The historical cache bytes remain unavailable. [Historical evidence integrity](stage_c/data/v4/historical_replay_integrity.json).

### Phase 2 controlled execution

| Metric | 300 fresh CosIng revisions | Full fixture with 29 controls |
|---|---:|---:|
| Chemically qualified for matching | 23 | 35 |
| Exact mappings to Substance | 22 | 34 |
| Reuse operations | 0 | 5 |
| New fixture Substance IDs | 22 | 29 |
| Distinct canonical IDs represented | 22 | 30 |
| ChemicalConcept mappings | 0 | 0 |
| Exact alias assertions | 22 | 34 |
| Unresolved | 278 | 295 |
| Unsupported proposed form | 4 | 5 |
| Competing forms | 1 | 1 |
| Identity conflict diagnostic | 33 | 35 |
| Explicit source–authority disagreement | 4 | 6 |
| Strict `SOURCE_IDENTIFIER_STRUCTURE_CONFLICT` disposition | 0 | 0 |
| Duplicate identities created | 0 | 0 |

All 22 exact fresh mappings came from the defined-graph stratum, which contained 105 records. The 65 form-sensitive records remained unresolved. Lauramidopropylamine Oxide had competing authority forms. The four unsupported-form holds include Butylene Glycol Stearate and Stearyl Gallate. The two historical positional-isomer cases stopped earlier with `SOURCE_AND_AUTHORITY_CLAIMS_DISAGREE`. One qualified record, Gold, was withheld at admission under the existing element and completeness limitations. The fixture reused one baseline ID and two IDs created earlier in the run. There were 31 distinct Substance–alias pairs. SQLite, foreign keys, uniqueness, mapping revision, graph correspondence, receipt digests and alias provenance passed the automated checks. [Verified results](stage_c/data/pilot-v4/metrics.json), [fresh strata and performance](stage_c/data/pilot-v4/v4_metrics.json), [fixture mappings](stage_c/data/pilot-v4/resolved.json), [alias receipts](stage_c/data/pilot-v4/alias_associations.json).

### Chemical review

The 108-case frozen source screen and all additional exact assignments yielded 125 case packets. Provisional review supported 22/22 inspected exact mappings and their revision-bound aliases. Fifteen exact candidates had a full graph comparison against NIST and all 15 agreed. All 15 references were accessible to the operational run. Twelve positives rely on shared-reference review for their external graph or name support. Ten positives have targeted supplemental sources, including records whose upstream independence remains unestablished. Allyl Caproate was linked explicitly to allyl hexanoate by JECFA, and an SCC opinion distinguished the 4-ethoxy-m-phenylenediamine free base from its broader regulatory context. [Positive review and references](stage_c/data/pilot-v4/positive_reference_review.json), [JECFA allyl hexanoate](https://www.fao.org/food/food-safety-quality/scientific-advice/jecfa/jecfa-flav/details/en/c/329/), [SCC free-base definition](https://ec.europa.eu/health/scientific_committees/consumer_safety/docs/scc_o_9.pdf).

The 103 abstention packets contain 59 source-scope withholds and 12 form or capability withholds supported provisionally. Seven had discrete species references, and 25 lacked enough review evidence to reach a judgment. One of the seven is a provisional false rejection. The source name and reported CAS for 2-trans, 6-cis-nonadienol identify the same stereoisomer as NIST, while the resolver found no sufficient path. Six other discrete-reference cases require more correspondence review. No incorrect fresh exact mapping, invalid alias, or structural/source-scope disagreement was identified in these assessments. There were zero independent specialist adjudications. The 125 case packets comprise 94 supported or counterexample judgments and 31 inconclusive cases. This falls short of 100 conclusive assessments. The review cannot estimate production precision or recall. [Review packets](stage_c/data/pilot-v4/reference_packets.json), [missed exact review](stage_c/data/pilot-v4/missed_exact_review.json), [NIST stereochemical reference](https://webbook.nist.gov/cgi/cbook.cgi?ID=C28069729), [provisional fixture exports](stage_c/data/pilot-v4/reviewed_exports.json).

### Performance, replay and protection

The 329-record run took 420.4 s including authority validation and fixture creation, or 0.78 checkpoints/s. Peak process working set was 434.4 MiB. The form and source-scope gate measured 0.0295 ms median and 3.924 ms P95. Total qualification measured 0.271 ms median and 13.752 ms P95. Combined matching/admission transactions measured 2.157 s median and 3.073 s P95 over 35 attempts. The separate matching profile includes a cold index build, and the cohorts differ from v3. These measurements do not isolate a causal change in latency from the new rule alone. The Substance fixture ended at 255,213,568 bytes with 591 canonical identities. Compacted audit storage grew by 1,343,096 bytes to 75,390,123 compressed bytes. The dedicated v4 index ended at 22,040,576 bytes. [Run timing](stage_c/data/pilot-v4/run.json), [derived-index seal](stage_c/data/v4/derived_index_seal.json).

Restart recovered all 329 checkpoints in 200.0 s from the v4 evidence seal and its dedicated cache. Both fixture file digests, the canonical digest, all decisions and aliases, and the derived-index digest matched across replay. The run and replay verified 69 original source and registry paths or sidecars and 176 historical evidence and cleanup paths. No authoritative identity, ontology, source history or historical fixture changed. The run did not execute ingredient equivalence. [Replay proof](stage_c/data/pilot-v4/restart_results.json), [historical checksum manifest](stage_c/data/v4/historical_protection.json).

| Acceptance gate | Result |
|---|---|
| A. Chemical-form safety | Pass for exercised controls and the provisional fresh review. The quarantined Pyridoxine association and alias were withheld in the new fixture. |
| B. Canonical matching | Pass. Complete matching excluded acetone, admitted qualified isopropyl alcohol and kept unknown cases conservative. |
| C. Fresh validation | Conditional. Independent specialist review and conclusive scope judgments remain incomplete. |
| D. Operational integration | Pass in the isolated fixture. Exact reuse, new identity creation, alias provenance, audit recovery, sealed-cache replay and source protection verified. |

Continue with isolated, monitored runs for discrete molecular records with affirmative form evidence. Keep unresolved ester/salt and adduct designations, variable compositions, uncertain stereo or hydration and unsupported inorganic materials on review. Prioritize the reference gap for exactly named stereochemical cases such as 2-trans, 6-cis-nonadienol and obtain independent specialist assessment before wider automatic admission.

## Reproduction

```powershell
python -B -m canonical_registry.stage_c.evaluation.verify --run pilot-v4-controls
python -B -m canonical_registry.stage_c.evaluation.verify --run pilot-v4
python -B -m canonical_registry.stage_c.evaluation.v4 replay
```

The input seal, controls-only runner and Phase 1 gate are recorded under `stage_c/data/v4`. The monitored fixture and review packets are under `stage_c/data/pilot-v4`. [Isolated Substance fixture](controlled_identity_reuse/fixtures/stage_c_b57c1edfe66248748555a0884a4dac92.sqlite), [isolated ChemicalConcept fixture](chemical_concept_registry/fixtures/stage_c_b57c1edfe66248748555a0884a4dac92.sqlite).

**STAGE_C_V4_CONDITIONAL**
