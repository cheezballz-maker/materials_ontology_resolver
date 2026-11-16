# Stage C v3 safety closure

The safety gate evaluates whether a source referent is as specific as its candidate graph and whether identifier-linked structures conflict with that graph. It runs before the existing canonical matcher and admission transaction. The three original failures remain regression controls. The safety run does not load the earlier record-specific holds.

## Baseline and failure analysis

Stage C v3 resolved 46 of 628 records, including 600 fresh CosIng concepts, and created 41 fixture Substances with five reuse operations. Its paired median was 2.74 s, with 21 of 21 comparable NIST Standard InChIKeys agreeing after three targeted holds. No chemical specialist reviewed the cohort. [Stage C v3 baseline](STAGE_C_V3_AUTHORITY_COVERAGE_AND_SCALABLE_CANONICALIZATION_REPORT.md), [Stage C v2 baseline](STAGE_C_V2_AUTHORITY_ACCESS_AND_RESOLUTION_PERFORMANCE_REPORT.md).

| Historical case | Failure mechanism | Generalized check |
|---|---|---|
| Ethylcyclohexene-1-carboxylate | The source designation and OPSIN interpretation supported the double bond adjacent to the ester-bearing ring carbon, `HDKVSEUEUWKMFS-UHFFFAOYSA-N`, also returned by PubChem CID 74173. NIST identifies the reported CAS 15111-56-5 as ethyl cyclohex-3-ene-1-carboxylate, `BYNLHLLOIZDKIC-UHFFFAOYSA-N`. V3 did not reconcile this separately retrieved source identifier evidence with the name path. The source CAS is a reported claim, and the external species record supports a chemically distinct candidate. Neither claim selects the source referent on its own. | Resolve a typed identifier through a captured record with explicit identifier-to-structure provenance. If the verified Standard key differs from the proposed graph, withhold the assignment and keep both structures. [NIST CAS 15111-56-5](https://webbook.nist.gov/cgi/cbook.cgi?ID=C15111565). |
| Tridecyl isononanoate | PubChem CID 9884387 and OPSIN agreed on `NRLLZRJXDKUVHM-UHFFFAOYSA-N`. The source row lacks a detailed definition. The published definition encompasses branched-chain nonanoic acids and leaves branch placement open. The selected graph represents one possible molecular member. | A branch-class designation triggers a whole-referent specification requirement. The retained name parse and matching external molecule cannot satisfy it. [CIR ingredient definitions](https://cir-reports.cir-safety.org/view-attachment/?id=b34bc38f-8e74-ec11-8943-0022482f06a6). |
| Butylene glycol diisononanoate | OPSIN and PubChem CID 87250669 agreed on `AUKODEQPZHYYRB-UHFFFAOYSA-N`. The original definition describes a glycol diester with branched-chain nonanoic acids. Different acid residues and branch placements satisfy it. The CIR structure illustrates one arrangement. The previous authority match did not account for the broader source definition. | Source-attested distribution or representative scope blocks exact assignment. A source would need an explicit, revision-bound specification of the whole constitution and its form before exact assignment could be considered. [CIR final report, Table 1](https://www.cir-safety.org/sites/default/files/magdae092017final.pdf). |

## Implemented rules

- The adapter preserves original definitions and reports matched source spans for explicitly described mixtures, distributions, preparations, representative graphs and alternative forms. These diagnostics are evidence-level categories. A term in the designation alone can raise a proof requirement for a branch-class name. It never establishes variable composition by itself. A matching, revision-bound source graph with explicit whole-referent and specification grants can satisfy that requirement. An explicit incompatible definition still forces review.
- The identifier check requires a typed source value and a record that binds the same identifier to the structural entity. Valid native GSRS records are compared using complete signatures, including Fixed-H. A NIST species lookup validates the reported CAS, InChI and full key before a differing Standard key can force a hold. NIST Standard InChI agreement alone leaves Fixed-H and complete ingredient scope open. Multiple reported identifiers within the same namespace are an ambiguity signal. An unresolved identifier is retained as missing correspondence evidence. Other qualified pathways can still proceed.
- Positive mappings still require the existing whole-referent grant, complete form specificity and official structural validation. Explicit native evidence retains its existing pathway. PubChem and ChEBI continue to require the prior Stage C v3 source-binding rules. Safety decisions and their source revisions are retained in journal records and successful receipts. Holds return to the shared sufficiency evaluator before matching, creation, alias association or mapping. No ontology, matching policy, registry schema or historical canonical identity was changed. [Implementation](stage_c/source_identity_safety.py), [shared evidence contract](CHEMICAL_IDENTITY_EVIDENCE_SUFFICIENCY_CONTRACT_V1.md).

## Frozen cohort and reference evidence

The disjoint 280-record cohort has 90 defined-graph, 35 other-graph, 55 form-sensitive, 35 conflict, 40 broad and 25 identifier-led concepts. Historical v1, v2, v3, authority lookup and evidence sufficiency selections were excluded. Five bounded, read-only Trino queries returned candidates for 205 fresh records. The direct CLI route could not connect in the sandbox. All five warehouse queries completed through the read-only MCP route, with query IDs, original SQL and result rows retained.

Live acquisition captured 171 responses in the GSRS batch, including its fixed provider probes, 115 PubChem responses and 171 ChEBI responses. The operational NIST identifier queue independently selected 82 public CAS numbers, of which 34 returned a structured reference. The frozen reference plan sampled 120 cases across all strata and exposed source definitions, identifiers and candidate graphs while withholding final system outcomes. Its separate CAS retrieval returned 21 structural references from 80 CAS numbers. Thirty-three packets shared a CAS with the operational queue and are excluded from the separate structural comparison. The source-scope rubric was frozen before scoring and uses original definitions for narrow negative judgments. Supplemental review used published evidence for four named positives and withdrew the salicin label because NIST omits the stereo specified in FDA's record. Some supplemental cases were chosen after inspecting provisional outcomes. They are targeted, non-blind checks, with the frozen judgments and their denominators preserved separately. Independent specialist adjudication remains unavailable. [Frozen judgments](stage_c/data/safety_closure/reference_judgments.json), [supplemental review](stage_c/data/safety_closure/reference_review_notes.json), [cohort, query and capture artifacts](stage_c/data/safety_closure/).

The fresh 2-tert-butylhydroquinone methyl ether record exposed another positional-isomer conflict. Its proposed graph was 3-tert-butyl-4-methoxyphenol, `IMOYOUMVYICGCA-UHFFFAOYSA-N`. The reported CAS 121-00-6 and EC 204-442-7 point to 2-tert-butyl-4-methoxyphenol, `MRBKEAMVRSLQPH-UHFFFAOYSA-N`. The same operational identifier check that caught the historical carboxylate withheld this record. [NIST CAS 121-00-6](https://webbook.nist.gov/cgi/cbook.cgi?ID=121-00-6&Units=SI), [FDA structural record](https://precision.fda.gov/uniisearch/srs/unii/A03IJ8ROOP), [SCCS chemical identity discussion](https://health.ec.europa.eu/document/download/502956f3-471d-4e2d-899f-08aa4511bb90_en?filename=sccs_o_306.pdf).

## Integrated results

| Measure | Safety closure result |
|---|---:|
| Fresh CosIng concepts | 280 |
| Historical failures / other historical CosIng controls / GSRS controls | 3 / 19 / 9 |
| Exact source-to-Substance assignments | 30 / 311 |
| Fresh exact assignments | 15 / 280 |
| New Substance identities / reuse operations | 25 / 5 |
| Distinct target identities | 26 |
| ChemicalConcept mappings | 0 |
| Exact alias assertions / distinct Substance–alias pairs | 30 / 27 |
| Identifier–structure conflicts withheld | 2 source records |
| Historical unsupported assignments withheld without record-specific holds | 3 / 3 |
| Unresolved | 281 / 311 |

WATER and AQUA reused the existing water identity. The isolated run admitted exact ethanol, glycerol and hydrogen peroxide, and the three native GSRS controls reused water, ethanol and glycerol across source systems. Standalone public authority qualification still passes for two PubChem and three ChEBI controls. Isopropyl alcohol passed qualification. The existing canonical matcher withheld admission because it could not eliminate a possible duplicate, leaving one known defined chemical without an exact mapping. [EPA isopropanol record](https://cdxapps.epa.gov/oms-substance-registry-services/substance-details/4291), [standalone authority controls](stage_c/data/safety_closure/isolated_pathways.json).

The first execution reached 311 checkpoints and then rolled back a locked replay attempt. A profiling duration had been placed inside the hashed qualification packet. The corrected workflow keeps timing in journal diagnostics, and a regression checks that repeated calls produce the same admission evidence despite different timings. The exploratory fixture was kept out of the final measurement. The retained suite passed 143 tests and 49 subtests. The final focused suite passed eight tests, including the replay-evidence regression. [Initial replay failure](stage_c/data/safety_closure/initial_replay_failure.json), [retained tests](stage_c/data/safety_closure/tests.xml), [focused safety tests](stage_c/data/safety_closure/final_safety_tests.xml).

### Chemical correctness and abstention

The paired baseline produced 34 assignments. The four decisions changed by the safety gate were the three historical failures and the newly detected hydroquinone methyl ether conflict. None of those four produced a source mapping or alias in the safety fixture. In the 120-packet review subset, provisional source review supported 4 of 4 assessed exact assignments and 15 of 15 assessed abstentions for preparations or distributions. The remaining 101 records lacked a whole-referent judgment. The original frozen rubric supplied 14 of those negatives. Supplemental review supplied the isocetyl isostearate negative and the four positives. Isocetyl isostearate was already withheld at the existing whole-referent evidence gate. The four corresponding exact alias assertions agreed with the provisional positive judgments. The remaining alias assertions have internal receipt verification and lack independent case-level adjudication. [Case results](stage_c/data/pilot-safety-final/closure_results.json), [alias assertions](stage_c/data/pilot-safety-final/alias_associations.json).

Among the 87 packets outside the operational CAS queue, eight had NIST structural references and all eight were unresolved. The other 79 lacked a structural reference. Thus no resolved case supports a fully held-out NIST exact-match denominator in this subset. The four targeted positives use additional source references, with structural agreement partly shared with the operational evidence. No incorrect whole-referent, form or alias assignment was identified in the provisionally adjudicated cases after applying the safeguards. No specialist reviewed the assignments, so population precision and false-rejection rates remain unmeasured. Isopropyl alcohol is a known missed mapping. Retinyl palmitate illustrates an additional case for review because a defined external reference exists while the current source-to-form evidence remains insufficient. [NIST retinyl palmitate](https://webbook.nist.gov/cgi/cbook.cgi?ID=79-81-2).

The safety run recorded 60 review holds, 195 cases needing more evidence, 25 non-discrete exclusions and 31 candidates ready for canonical matching. The 60 holds include 16 added source-scope review reasons on previously unqualified cases. The identifier check recorded two verified conflicts, 14 exact native comparisons and 46 incomplete correspondence observations across qualified candidate evaluations. These are claim-level observations and may exceed the number of affected records.

### Performance and operational integrity

| Paired metric | V3 without new safeguards | Safety closure |
|---|---:|---:|
| Median end-to-end processing, same 30 exact assignments | 3.270 s | 3.283 s |
| Median canonical transaction, same 30 | 3.236 s | 3.243 s |
| Median new-identity transaction, mode-specific creation counts | 3.291 s | 3.262 s |
| Median qualification across 311 records | 0.330 ms | 0.382 ms |
| Median / total time of new scope and identifier gate | — | 0.018 ms / 0.119 s |
| Batch wall time including setup and two locked replays | 596.62 s | 591.60 s |
| Records per minute including setup | 31.28 | 31.54 |
| Final Substance fixture size | 251,379,712 bytes | 252,915,712 bytes |
| Peak process working set | 5.12 GiB | 8.87 GiB |

The matched end-to-end median increased 0.4%. Both processes ran concurrently and shared the existing Stage C derived cache. First transactions took 87.91 s and 73.28 s in the two modes. Cache state, I/O and the initial clone can therefore distort total time and memory comparisons. The measured scope gate itself accounted for 0.119 s. The 3.75 GiB peak working-set difference warrants a sequential benchmark before expanding the run. The existing combined transaction timing includes matching, registry integrity, admission, mapping and journal work. This experiment did not isolate a matching-only latency. [Paired timing and comparison](stage_c/data/pilot-safety-final/closure_results.json), [baseline integrity and storage](stage_c/data/pilot-safety-final-baseline/metrics.json).

Both isolated fixtures passed full integrity and foreign-key checks, current-revision source mapping and receipt checks, exact graph comparisons and historical audit recovery. The safety fixture recorded zero duplicate canonical identities, split targets or orphaned mappings. Both runs passed two locked replays. A restart recovered all 311 checkpoints with identical decisions, aliases and canonical digest. Its 214 s runtime includes evidence rehydration and validation, which still run before checkpoint reuse. The canonical registries, source registry, Stage B assessments and ontology remained protected by the same 70-path checksum manifest. The safety fixture preserved all 2,970 compacted historical events, and its database checksums are recorded in the verification artifact. [Safety run](stage_c/data/pilot-safety-final/run.json), [restart verification](stage_c/data/pilot-safety-final/restart_results.json), [verified metrics](stage_c/data/pilot-safety-final/metrics.json), [resolved mappings](stage_c/data/pilot-safety-final/resolved.json), [isolated Substance registry and journal](controlled_identity_reuse/fixtures/stage_c_cfa9943071a94d6e88e6bc8ba4097c81.sqlite), [isolated ChemicalConcept registry](chemical_concept_registry/fixtures/stage_c_cfa9943071a94d6e88e6bc8ba4097c81.sqlite).

### Readiness

| Gate | Result |
|---|---|
| A. Generalized scope safety | Pass on the exercised controls. Three original failures are prevented with no record-specific holds. Fresh evidence includes an independently documented branch-family abstention. Coverage of previously unseen nomenclature and free-text scope remains limited. |
| B. Identifier–structure consistency | Pass on exercised cases. The same rule withheld both the historical and fresh positional isomer conflicts. Native evidence and form-regression tests retained complete comparisons. |
| C. Fresh chemical validation | Conditional. The 120 packets yielded 19 provisional scope judgments, including targeted supplements, and zero specialist adjudications. |
| D. Integrated canonicalization | Pass in isolated fixtures, with retained mapping, alias, uniqueness, transaction and audit controls. |

A restricted monitored expansion is justified in isolated or shadow execution for well-defined discrete molecules with positive source-to-whole binding and no unresolved form evidence. Require case-level review before using the results to support authoritative writes. Withhold representative graphs, variable and branch-distributed materials, constituent-only preparations, unresolved stereo and hydration, and material identifier conflicts. Prioritize independent review of fresh exact outputs and false rejections, plus a sequential memory and cold-start check. Keep extended inorganic and unsupported multicomponent identities under the existing capability restrictions.

## Reproduction

Use the retained authority receipts, original source snapshot and pinned registries. Running the baseline intentionally reproduces the former behavior in a disposable copy.

```powershell
python -B -m canonical_registry.stage_c.evaluation.v3_pathways --safety-closure
python -B -m canonical_registry.stage_c.run --safety-closure --run safety-repro --create --replay-count 2
python -B -m canonical_registry.stage_c.evaluation.verify --run safety-repro
python -B -m canonical_registry.stage_c.run --safety-closure --safety-baseline --run safety-baseline-repro --create --replay-count 2
python -B -m canonical_registry.stage_c.evaluation.verify --run safety-baseline-repro
python -B -m canonical_registry.stage_c.evaluation.safety_closure compare --run safety-repro --baseline safety-baseline-repro
```

`STAGE_C_V3_SAFETY_CLOSURE_CONDITIONAL`
