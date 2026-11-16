# Stage C v5 evidence coverage and monitored expansion

The bounded stereo pathway corrected the nonadienol false rejection and passed the retained safety suite. Across the first 800 fresh CosIng concepts, the two isolated fixtures recorded 106 exact assignments. Review exposed one unsupported whole-referent mapping and alias, for Benzylhemiformal. Both were quarantined. The remaining 1,200 records were frozen and their authority queues completed. Canonical processing stopped at the phase 2 safety gate.

## Baseline and correction

Stage C v4 processed 300 fresh CosIng revisions, mapped 22, and found a probable missed stereochemically defined alcohol. Its fresh sample was stratified and yielded no independent specialist adjudication. The v5 change is an opt-in Stage C qualification adapter. It uses the existing evidence sufficiency evaluator, form and scope checks, exact matching, canonical creation, alias transaction and journal. [Stage C v4 report](STAGE_C_V4_CHEMICAL_FORM_CORRECTION_AND_CONTROLLED_RESUMPTION_REPORT.md), [shared contract](CHEMICAL_IDENTITY_EVIDENCE_SUFFICIENCY_CONTRACT_V1.md).

CosIng revision `80fd286ffecc2008ffbde46c7aeda9761973157ff6b849cde6eed11416b6d2b5` of `CIC_00006353` reports 2-trans, 6-cis-nonadienol, CAS 28069-72-9 and EC 248-816-8. The source has no separate structural definition. Stage B retained no graph. OPSIN could not assign the cis locant to the legacy name, and the v4 warehouse candidate was retrieved only by CAS. Its projected graph and the independently retrieved NIST species structure specify the same (2E,6Z) isomer. The NIST receipt was in the v4 review capture, outside operational acquisition. The warehouse projection had no qualified whole-referent receipt, and v4 returned `NO_SUFFICIENT_EVIDENCE_PATH`. PubChem has CID 5362833 for the specific isomer. The GSRS UNII was in the projection but absent from the v4 native capture. [NIST species](https://webbook.nist.gov/cgi/cbook.cgi?ID=C28069729), [JECFA](https://apps.who.int/food-additives-contaminants-jecfa-database/Home/Chemical/5151), [ECHA](https://echa.europa.eu/substance-information/-/substanceinfo/100.044.364), [PubChem](https://pubchem.ncbi.nlm.nih.gov/compound/5362833).

The new adapter recognizes a bounded full-name grammar for linear primary dienols whose two internal double bonds each bear one hydrogen per alkene carbon. It transfers both explicit cis/trans locants to E/Z before calling OPSIN. It requires a revision-bound source designation and an agreeing singleton CAS from a pinned NIST species receipt, compares the full graph against both the species and relevant retrieved candidates, and checks for conflicting or incomplete evidence. The existing evaluator validates official InChI. The same-evidence control held under v4 and qualified under v5 with key `AMXYRHBJZOVHOL-ODYTWBPASA-N`. With the NIST reference withheld, v5 also held. The added tests cover opposite stereo, unsupported or incomplete nomenclature, modified competing candidate and incomplete search. No generic cis/trans substitution, name-only route, or arbitrary stereo assignment was added. [Adapter](stage_c/evaluation/stereo_binding.py), [comparison tests](stage_c/evaluation/test_v5_stereo.py).

### Previously unresolved case review

| Source | Evidence and disposition |
|---|---|
| Palmitamine | NIST CAS and the parser graph indicate hexadecanamine. The available authority name did not establish the typed whole-referent binding. The hold remains defensible pending source-bound corroboration. |
| Adenosine cyclic phosphate | The CAS species is the 3′,5′-cyclic form. The designation omits linkage locants and no exact source-bound relationship was qualified. |
| Cytidine | The NIST graph specifies sugar stereochemistry. The saved decision has conflicting dimensions and an unestablished OPSIN name. The available evidence does not support a correction to the general policy. |
| Nitrofurazone | The NIST reference leaves the imine geometry open and v4 reported conflicting dimensions. It does not select an exact stereoisomer. |
| Amylvinylcarbinyl acetate | The reference supports the ester constitution. Neither the designation nor the reference establishes the configuration of its stereogenic centre. |
| Ethylhexyl acrylate | The reference leaves the branch-centre stereochemistry open. The saved description refers to a formula absent from the text. |
| Retinyl palmitate | The SCCS opinion describes the defined all-trans material it assessed. That supports a targeted source review. The opinion alone does not select a form for every CosIng revision using the ingredient name. [SCCS opinion](https://health.ec.europa.eu/system/files/2023-08/sccs_o_261.pdf) |
| Methylchloroisothiazolinone | NIST identifies the discrete active. The SCCS opinion distinguishes the active from the two-ingredient preservative preparation. Current source-revision scope still needs verification. [NIST](https://webbook.nist.gov/cgi/cbook.cgi?ID=C26172554), [SCCS](https://health.ec.europa.eu/system/files/2016-11/sccs_o_009_0.pdf) |
| Tridecyl neopentanoate | The frozen revision specifies linear n-tridecyl ester. A historical EU inventory entry describes a branched material under the same designation. This is a revision-specific distinction. [Restricted-expansion analysis](STAGE_C_RESTRICTED_MONITORED_COSING_EXPANSION_V1_REPORT.md) |

Three other packets labelled as having discrete references in v4 already had exact mappings. Tribenzoin, niacin and allyl propionate were kept as positive diagnostic controls. [Case records and original diagnostics](stage_c/data/v5/false_rejection_investigation.json), [JECFA allyl propionate](https://apps.who.int/food-additives-contaminants-jecfa-database/Home/Chemical/2914).

## Sampling and acquisition

The SHA-256 selection froze 2,000 fresh revisions and 271 stratified review packets before canonicalization. The fresh IDs are disjoint from 4,287 IDs from earlier Stage C and shared evidence cohorts. The six strata contain 910 defined graphs with identifiers, 40 other graphs, 350 form-sensitive records, 300 identifier-led records, 150 potential conflicts and 250 broad materials. Only 46 unseen records were available in the other-graph stratum under the frozen definition. Forty preserved an exact proportional split over the 200/600/1,200 stages. The other 210 target slots moved to the defined-graph stratum. These are engineering samples. [Cohort seal](stage_c/data/v5/freeze.json), [exclusions](stage_c/data/v5/exclusions.json), [blinded source packets](stage_c/data/v5/blind_source_packets.json).

The 34 bounded, read-only warehouse queries returned candidates for 1,265 concepts (123/200, 371/600 and 771/1,200). The first sandbox authority attempt failed DNS. Its receipts remain available. The first scheduling pass included historical inputs with a `fresh` label from another manifest. It was replaced before registry execution by phase queues built directly from the frozen v5 membership. Successful immutable receipts were reusable. Public acquisition budgets are 100, 220 and 360 per identifier queue, with original misses preserved. [Acquisition implementation](stage_c/evaluation/v5.py), [warehouse query example](stage_c/data/v5/lookup_01_executed.sql).

## Calibration results

The isolated calibration processed 200 fresh revisions and 30 historical controls, including nine native GSRS checks and the nonadienol development control. It admitted 34 fresh identities and asserted 34 fresh aliases. The 35 fresh form-stratum records remained unresolved. The fresh cohort contained no designations within the new linear dienol grammar, so the controlled gain is one historical false rejection corrected and zero fresh mappings attributable to the new adapter in calibration. The raw difference between the v4 and v5 stratified mapping rates cannot isolate a policy effect. [Same-evidence comparison](stage_c/data/v5/nonadienol_v4_v5_comparison.json), [calibration outcomes](stage_c/data/pilot-v5-phase-1/v5_metrics.json).

| Calibration measure | Count or result |
|---|---:|
| Fresh records processed | 200 |
| With warehouse candidates | 123 |
| Linked to submitted or cached authority requests | 129 |
| Authority responses | 128 |
| Useful authority structure evidence | 94 |
| Source-binding receipts before the final sufficiency disposition | 38 |
| Qualified and mapped exactly | 34 |
| Fresh new Substance IDs and distinct targets | 34 |
| Fresh reuse operations | 0 |
| Fresh unresolved | 166 |
| No usable authority structure evidence | 106 |
| Whole-referent binding unestablished | 49 |
| Identity conflict diagnostics | 20 |
| Exact form unsupported by source | 2 |
| Source-scope withholds supported by the provisional screen | 15 |
| ChemicalConcept mappings | 0 |
| Exact alias assertions | 34 |
| Duplicate canonical identities created | 0 |

The full calibration fixture has 47 exact mappings to 43 distinct Substance identities, including 42 new identities and five reuse operations. Three native GSRS controls reused the CosIng water, glycerol and ethanol targets. The integrity verifier checked source revision and target consistency, qualified exact aliases, audit recovery, SQLite foreign keys and registry uniqueness. Checkpoint replay recovered 230/230 decisions in 217.2 seconds with unchanged decisions, aliases, both fixture file digests and the dedicated index. It verified 69 protected path entries and 194 historical evidence and cache entries. [Integrity and full fixture counts](stage_c/data/pilot-v5-phase-1/metrics.json), [alias assertions](stage_c/data/pilot-v5-phase-1/alias_associations.json), [replay](stage_c/data/pilot-v5-phase-1/replay_results.json).

The calibration review covered all 34 fresh exact assignments and their aliases provisionally. Nineteen have agreeing full NIST graph comparisons. Fifteen lacked an available NIST structural comparison and rely on the retained authority binding or targeted references. Some references were already consumed by the resolver. The review recorded zero incorrect exact assignments or aliases and zero independent specialist judgments. [Case-level provisional review](stage_c/data/pilot-v5-phase-1/provisional_positive_review.json).

Calibration acquisition took 378.4 seconds after the corrected queue was prepared. PubChem returned 97 of 100 queries as JSON, ChEBI 43 of 100 searches, and GSRS returned 92 search receipts and 92 native receipts. NIST provided 42 structural references from 100 CAS lookups. The isolated canonicalization took 636.8 seconds including input validation, fixture setup and compaction. Peak working set was 544.2 MiB. The fresh transaction median was 2.418 s and P95 was 3.032 s over 34 transactions. Qualification median was 0.305 ms and form/scope median was 0.031 ms. These timings include a different authority inventory and host workload from v4. The fixture ended at 254,341,120 bytes with 604 Substances. Its compressed audit payloads grew from 74,047,027 to 75,511,403 bytes, and the dedicated derived index reached 31,297,536 bytes. [Run profile](stage_c/data/pilot-v5-phase-1/run.json), [acquisition profile](stage_c/data/v5/phase-1-frozen/acquisition_performance.json).

## Controlled expansion

The second fixture processed all 600 fresh records. It qualified 73, created 72 exact Substance identities with 72 revision-bound aliases, and withheld one qualified candidate at canonical creation. There were 528 unresolved records, including 175 without established whole-referent binding, three with an unsupported proposed form and one with competing forms. Seventy received the identity-conflict diagnostic. Authority evidence provided 326 responses and useful structure for 208 records. The 600-record fixture took 508.5 seconds, with 548.7 MiB peak working set. Fresh transactions had a median of 1.965 s and a P95 of 2.526 s. The separate index reached 59,441,152 bytes and compressed audit payloads reached 76,611,220 bytes. [Phase 2 outcomes](stage_c/data/pilot-v5-phase-2/v5_metrics.json), [performance](stage_c/data/pilot-v5-phase-2/run.json).

The second-phase provisional screen covered all 72 exact results. Thirty-four had agreeing NIST graph comparisons. Targeted source checks distinguished glyoxylic acid from its separately registered monohydrate and established the linear diester for ditridecyl adipate under the source CAS. Benzylhemiformal was the critical exception. [Case findings](stage_c/data/pilot-v5-phase-2/reference_findings.json), [phase 2 provisional review](stage_c/data/pilot-v5-phase-2/provisional_positive_review.json).

### Benzylhemiformal quarantine and stop

For `CIC_00004069`, the frozen source supplies the designation and CAS 14548-60-8. Its text refers to a formula absent from the captured record. Native GSRS corroborated the monomer and the Stage B parser graph. The `NATIVE_PREFERRED_NAME_AND_SOURCE_GRAPH` pathway treated that corroboration as sufficient for the entire ingredient. The transaction created fixture target `SUB_00000622` with key `PETXWIMJICIQTQ-UHFFFAOYSA-N` and asserted an exact alias. The SCCNFP cosmetic-use opinion specifies a formal repeat count averaging 1.5 under the same designation and CAS. An ECHA document assigns the same designation and CAS to benzyloxymethanol. The molecular graph is credible, and the source revision leaves its correspondence to the whole ingredient unresolved. The provisional exports exclude both assertions and the isolated journal preserves the original decision. [SCCNFP, section 5.4](https://ec.europa.eu/health/archive/ph_risk/committees/sccp/documents/out188_en.pdf), [ECHA record comparison](https://echa.europa.eu/documents/10162/536e4e59-936c-496f-9ecb-eddeed40b228), [quarantine](stage_c/data/pilot-v5-phase-2/quarantine.json), [filtered export](stage_c/data/pilot-v5-phase-2/provisional_reviewed_exports.json).

This is a shared scope qualification failure on a native-authority route. It warrants a targeted revision-bound composition safeguard for cases where the same designation and identifier cover both a defined molecule and a variable product. The correction needs its own development controls and an untouched retest. The phase 3 fixture was blocked. [Gate decision](stage_c/data/v5/phase-2-frozen/blocked.json), [sealed phase 3 acquisition](stage_c/data/v5/phase-3-frozen/seal.json).

## Combined results and gates

| Measure | Processed fresh cohorts |
|---|---:|
| Selected / processed | 2,000 / 800 |
| Historical controls | 30 distinct, 60 executions |
| Warehouse candidate coverage | 494/800 |
| Linked to submitted or cached authority requests | 455/800 |
| Successful authority responses | 454/800 |
| Useful authority structure evidence | 302/800 |
| Source-binding receipts | 115/800 |
| Qualified source referents | 107/800 |
| Exact Substance mappings before / after quarantine | 106 / 105 |
| Fresh new fixture identities / fresh reuse operations | 106 / 0 |
| Distinct fresh molecular signatures across fixtures | 106 before quarantine, 105 after |
| ChemicalConcept mappings | 0 |
| Exact aliases asserted / provisionally exported | 106 / 105 |
| Confirmed unsupported mapping / alias | 1 / 1 |
| Unresolved | 694 |
| Without usable authority structure evidence | 498 |
| Whole-referent binding unestablished | 224 |
| Identity conflict diagnostic | 90 |
| Provisional source-scope withholds | 30 |
| Software-induced false rejections corrected | 1 historical control |
| Fresh mappings attributed to the new pathway | 0 |
| Independent specialist judgments | 0 |
| New duplicate identities detected within the fixtures | 0 |

The fixtures start from the same pinned registry and have independent ID namespaces. A repeated fixture ID across phases does not denote the same Substance. Chemical precision remains unestablished. The provisional review yielded 136 judgments across the two executed cohorts, comprising 106 exact assertions reviewed and 30 source-scope withholds. This falls short of the 150-judgment target. NIST agreed structurally in 53/53 of the available positive comparisons. The remaining 53 exact assertions had no NIST graph comparison, and one failed the whole-referent review despite a plausible monomer. The 271-packet source-only screen spans all three planned stages. It marked 46 scope withholds and left 225 inconclusive before comparison with predictions or targeted reviews. [Source-only review packets](stage_c/data/v5/provisional_blind_reference_packets.json), [calibration review](stage_c/data/pilot-v5-phase-1/provisional_positive_review.json), [expansion review](stage_c/data/pilot-v5-phase-2/provisional_positive_review.json).

Phases 2 and 3 used their own authority queues. Phase 2 acquired 212/220 PubChem JSON responses, 91/220 ChEBI search responses, 220/220 GSRS searches and 73/220 NIST species structures. Phase 3 acquired 348/360 PubChem JSON responses, 169/360 ChEBI search responses, 360/360 GSRS searches and 116/360 NIST species structures in 1,551.7 seconds. A same-evidence qualification comparison was executed for the historical stereochemical control. A second complete v4 registry run over the 800 fresh records was not executed. No fresh designation was within the new dienol grammar, so the fresh exact mappings cannot be credited to that code change.

| Gate | Result |
|---|---|
| A. Evidence coverage | Pass on the bounded historical control. Fresh generalization remains unmeasured. |
| B. Chemical identity safety | Fail. Shared whole-referent qualification admitted an unsupported Benzylhemiformal association. |
| C. Chemical validation | Conditional. Review identified a material scope failure, and the independent review and judgment targets remain open. |
| D. Integrated canonicalization | SQLite, transactions, provenance and matching integrity passed within the completed fixtures. Exact semantic acceptance failed for the quarantined case. |
| E. Operational scaling | Conditional. The first two phases executed in isolation. The final stage stopped at the semantic gate. |

The retained suite passed 136 tests and 49 subtests. Across both phases, 860/860 checkpoints replayed, including 630 in phase 2 in 191.9 seconds. Both fixture pairs, their decisions and aliases, canonical digests and dedicated derived caches matched on restart. The ontology, authoritative registries, original CosIng revisions, Stage B and historical quarantines were protected. The saved restricted-expansion fixture retained all 2,970 verified historical events. Broader automatic expansion requires correction of the shared whole-referent failure and an untouched validation cohort with stronger independent adjudication. [Phase 2 replay](stage_c/data/pilot-v5-phase-2/replay_results.json), [preservation checks](stage_c/data/v5/preservation_checks.json), [regression results](stage_c/data/v5/tests.xml).

## Reproduction

```powershell
python -B -m canonical_registry.stage_c.evaluation.v5 1 --verify canonical_registry/stage_c/data/pilot-v5-phase-1
python -B -m canonical_registry.stage_c.evaluation.v5 2 --verify canonical_registry/stage_c/data/pilot-v5-phase-2
python -B -c "from canonical_registry.stage_c.evaluation.v5 import compare_v4_control; compare_v4_control()"
```

**STAGE_C_V5_FAILED**
