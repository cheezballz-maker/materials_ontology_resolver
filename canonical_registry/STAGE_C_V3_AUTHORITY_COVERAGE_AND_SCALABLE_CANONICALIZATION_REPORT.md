# Stage C v3 authority coverage and scalable canonicalization

Stage C v3 exercised additional PubChem and ChEBI whole-referent pathways and reduced median paired processing time from 6.40 s to 2.74 s. The independent-reference screen and targeted source review exposed scope and structure conflicts that the first isolated execution had missed. The reviewed execution applies source-revision-bound holds before qualification. Broader execution remains conditional on testing whether the same kinds of conflict can be detected reliably on unseen records.

## Baseline and architecture

V2 qualified 25 of 300 fresh CosIng referents. Across its cohort and controls it resolved 36 source records, admitted 31 Substances and reused an identity five times. Its historical optimized paired median was 9.45 s. The 4.04 s integrated v2 median came from a separate workload. V3 started from the same pinned 562 Substances and one active ChemicalConcept. Materials Ontology v0.7.0, Stage A and B state, the shared evidence contract, the complete exact matcher and the existing creation and association services govern the run. Stage C writes only to capability-limited copies. Chemical identity mappings preserve separate source concept IDs. [V2 report](STAGE_C_V2_AUTHORITY_ACCESS_AND_RESOLUTION_PERFORMANCE_REPORT.md), [shared evidence contract](CHEMICAL_IDENTITY_EVIDENCE_SUFFICIENCY_CONTRACT_V1.md).

## Authority acquisition and qualification

The frozen cohort contains 600 fresh CosIng concepts, excluding the earlier evaluation cohorts. It has 210 defined graph, 90 other graph, 160 form-sensitive, 55 conflict, 50 broad and 35 identifier-led cases. Nineteen earlier CosIng controls and nine GSRS controls accompany the cohort. Ten bounded read-only Trino queries found warehouse candidates for 474 fresh concepts. The lookups preserved route, count and digest, including capped candidate lists whose incompleteness prevents qualification. The evidence queue uses 115 full public InChIKeys and 38 selected native accessions, plus fixed GSRS probes. These strata and acquisition choices affect observed coverage. [Cohort and query receipts](stage_c/data/v3/).

| Provider | New live acquisition | Qualification pathway |
|---|---|---|
| GSRS | 87 successful requests, including 40 distinct native detail records. The existing native checks validated 21 unique accessions in this capture. | Approved native chemical definitions can supply whole structure and component evidence. Preferred designation or typed identifier binding remains source-specific. Ionic moieties, fragment roles, and projected warehouse rows cannot establish whole scope by themselves. |
| PubChem | 115 successful exact-key requests and 130 distinct Compound records. 110 passed adapter descriptor and component checks. | A CID and validated standardized graph supply the entity and structural representation. A retained deterministic source designation must independently establish the same exact form. When the computed IUPAC name differs, a separate deterministic reading must reproduce the full graph. |
| ChEBI | 174 requests, with 115 successful responses and 59 HTTP 404 responses. 59 distinct detail records were inspected and 40 passed adapter checks. | A released, curated three-star record with a definition and concordant, non-R-group default structure can support exact identity when its preferred name and the retained source graph establish the whole referent. |

The three new acquisition batches account for 229 authority-scoped chemical record IDs, before overlap between providers. The sum of measured HTTP request durations was 86.39 s for PubChem, 222.43 s for ChEBI and 117.59 s for the GSRS capture including fixed probes. These totals exclude pacing sleeps. The integrated run consumes the captures locally.

PubChem Compound structures are standardized from depositor Substance records. CID, SID, a synonym, and a depositor cross-reference carry distinct semantics. Standardization can normalize or select representations involving charge, tautomerism and other form details. V3 keeps the source graph and compares isomeric SMILES, Standard InChI, full key and Fixed-H InChI. It grants no exact alias from a PubChem synonym or SID. ChEBI broader classes, parent or role relations, and cross-references remain candidate information. The new adapters withhold disconnected graphs when they lack complete component-role evidence. The common evaluator still checks structural validity and official InChI before matching. [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest), [PubChem standardization](https://pubchem.ncbi.nlm.nih.gov/docs/standardization-service), [ChEBI tools](https://www.ebi.ac.uk/chebi/tools), [GSRS API](https://gsrs.ncats.nih.gov/api-documentation).

Candidate comparisons preserve full forms and provenance. Conflicting authority forms and name-linked warehouse structures can place a case on hold. Multiple receipts are retained when they agree. Upstream independence remains unestablished where lineage cannot be resolved. In a separate qualification-only control, PubChem alone qualified two real records and ChEBI alone qualified three, including hydrogen peroxide. Anisole qualified separately through either provider with no GSRS, CAS corroboration or registry write. The integrated run chooses one primary receipt and retains the overlapping support. [Isolated provider pathways](stage_c/data/v3/isolated_pathways.json).

## Chemical scope and source validation

| Case | Finding and disposition |
|---|---|
| Sodium chloride | The native whole graph represents the 1:1 ionic formula unit. Native moiety entries encode the sodium cation and a chlorine moiety whose parsed charge does not match chloride. This might reflect a representation convention, but the current adapter lacks documented semantics to equate them. The source stayed unresolved at whole-referent qualification. Separately, the existing discrete molecular salt policy withholds extended inorganic ionic compositions. ChEBI's defined formula unit establishes a chemical identity at its own granularity. Supporting such solids in the Substance registry requires a distinct representation and admission decision. [ChEBI sodium chloride](https://www.ebi.ac.uk/chebi/CHEBI:26710). |
| Hydrogen peroxide | The native GSRS and ChEBI structures agree on neutral `OO` with full key `MHAJPDPJQMAIIY-UHFFFAOYSA-N`. The isolated workflow admits that form. [ChEBI hydrogen peroxide](https://www.ebi.ac.uk/chebi/CHEBI:16240). |
| Citric acid and magnesium sulfate | The source evidence spans different hydration states. A particular hydrate or anhydrous target remains unassigned. [ChEBI citric acid](https://www.ebi.ac.uk/chebi/CHEBI:30769), [magnesium sulfate heptahydrate](https://www.ebi.ac.uk/chebi/CHEBI:31795). |
| Glutamic acid | The source lacks verified absolute stereochemical scope. L-glutamic acid is a specific candidate with its own identity. [ChEBI L-glutamic acid](https://www.ebi.ac.uk/chebi/CHEBI:16015). |
| Ciclopirox olamine, magnesium hydride, silicon and titanium alkoxide | V2 controls demonstrated that sufficient evidence for a candidate can coexist with a downstream admission hold for composition, electronic state or element support. Titanium dioxide remains a separate extended-solid case. The v3 run retains the same admission rules. [V2 case analysis](STAGE_C_V2_AUTHORITY_ACCESS_AND_RESOLUTION_PERFORMANCE_REPORT.md). |
| Ethylcyclohexene-1-carboxylate | The first isolated run selected a name-derived structure. NIST ties the source CAS 15111-56-5 to a different double-bond position. The reviewed run withholds the assignment. [NIST reference](https://webbook.nist.gov/cgi/cbook.cgi?ID=C15111565). |
| Tridecyl isononanoate and butylene glycol diisononanoate | Both originally acquired exact graph assignments in the exploratory copy. Published ingredient descriptions encompass branched-chain nonanoic acid esters. The selected structures establish possible components or forms. The reviewed run withholds both whole-referent assignments. [Tridecyl ingredient definition](https://www.accessdata.fda.gov/drugsatfda_docs/omuf/order/supportDoc/OTC000039/3.3_Literature_References/rev_cir-2015-isopropylmyristate_090026f88e12645a.pdf), [butylene glycol ingredient definition](https://www.cir-safety.org/sites/default/files/magdae092017final.pdf). |

The reference set was frozen before execution. It comprises 110 distinct fresh concepts, with 70 targeted for public authority retrieval, 22 other cases and 18 scope or conflict cases. Of these, 90 had one source CAS and were queried separately against NIST. Forty-three provided usable independent structural references. Forty-seven lacked the needed fields and 20 lacked a usable singleton CAS. Case-level chemical specialist reviews total zero. A shared full InChIKey checks one structural comparison. It does not determine the complete source referent or settle every Fixed-H distinction. A structural reference paired with an abstention cannot establish a false rejection without resolving source scope. The three targeted source reviews informed explicit holds and are development findings for the reviewed execution. They cannot establish accuracy on a new blind holdout. Whole-referent precision, recall, false rejection and exact synonym error rates are unavailable. [Frozen reference cohort](stage_c/data/v3/reference_cohort.json), [NIST captures](stage_c/data/v3/nist_reference.json), [exploratory assignments](stage_c/data/v3/exploratory_scope_findings.json), [review hold receipts](stage_c/data/v3/review_holds.json).

## Audit storage and performance

The starting SQLite fixture contained 53,667 CUMA reconciliation rows and 2,970 immutable audit events with 2,438,269,181 UTF-8 payload bytes. The existing `zlib-json-v1` content store retains the full original payloads behind SHA-256 references. V3 compacts only a verified private clone before it exposes the fixture capability. It verifies every round trip, checks content and event order after vacuum, and rechecks historical decoding after execution. The compacted payload bytes total 74,047,027. The original append-only trigger is restored within the conversion transaction, and the payload table retains its immutable update/delete guards. No historical events were removed.

| Paired frozen workload | V2 layout, rerun | V3 compacted layout |
|---|---:|---:|
| Median, six successful or replayed requests | 6.40 s | 2.74 s |
| P95, nearest rank with six observations | 9.20 s | 3.89 s |
| Total, six successful or replayed requests | 40.94 s | 17.07 s |
| Snapshot read and integrity, cumulative | 27.51 s | 4.11 s |
| Snapshot materialization, cumulative | 4.09 s | 3.93 s |
| Constitution index work, cumulative | 4.48 s | 4.06 s |
| Initialization, one time | 61.17 s | 102.04 s |
| Cache priming, one time | 74.92 s | 68.10 s |
| Database bytes after the workload | 2,612,330,496 | 244,649,984 |

All eight paired outcomes and target IDs agreed, including two abstentions. Median speed improved 2.34× and size fell 90.6%. Compaction took 48.92 s in this pair. Snapshot reads and integrity checks were the dominant improvement. The existing locked pre-mutation scan, targeted checks, foreign keys and complete duplicate search still run. Source mapping, alias writes and commit remain part of aggregate transaction timing. The SQLite build lacks `dbstat`, so table and index page allocations are unmeasured. The individual lock-wait and commit costs, peak memory and sustained concurrent throughput are also unmeasured. Under the measured paired latencies, the roughly 41 s extra initialization cost would be recovered after about 12 successful or replayed requests. That projection excludes network acquisition, cache priming, concurrency and changes in workload mix. [Baseline profile](stage_c/data/v2/v3-baseline/profile.json), [compacted profile](stage_c/data/v2/v3-compact/profile.json).

## Integrated lifecycle and verification

| Metric | Reviewed cohort result |
|---|---:|
| Fresh CosIng concepts | 600 |
| Earlier CosIng controls / GSRS controls | 19 / 9 |
| Source records qualified and resolved | 46 / 628 |
| Fresh CosIng resolved | 31 / 600 |
| New Substance identities / reuse operations | 41 / 5 |
| Distinct targets / pre-existing target IDs reused | 42 / 1 |
| Unresolved | 582 |
| GSRS / PubChem / ChEBI / NIST qualified referents, overlapping | 24 / 32 / 13 / 4 |
| ChemicalConcept mappings | 0 |
| Exact alias assertions / distinct Substance–alias pairs | 46 / 43 |
| Source–identifier disagreement explicitly withheld after review | 1 |
| Reviewed whole-referent scope ambiguities withheld | 2 |
| Review holds / non-discrete exclusions / further evidence needed | 70 / 51 / 461 |
| Duplicate canonical identities created | 0 |
| Independent structural agreement among resolved cases with a NIST key | 21 / 21 |
| Specialist-reviewed cases | 0 |

Provider intersections among the 46 qualified referents were GSRS only 10, PubChem only 12, NIST only 4, GSRS and PubChem 7, PubChem and ChEBI 6, and all three live authority pathways 7. Primary receipts were GSRS 24, PubChem 18 and NIST 4. ChEBI supplied valid overlapping receipts in the integrated cohort and passed standalone qualification in the provider controls. A provider's presence in an intersection records qualifying evidence and does not establish independent upstream lineage.

The five reuse operations include GSRS water, ethanol and glycerol mappings to the same targets as their CosIng counterparts. WATER and AQUA retain separate CosIng records and share the existing water target. New Substance rows carry 41 InChI and 41 InChIKey assertions. Authority accessions and source CAS/EC remain in evidence receipts where reported. The run imports no bulk synonym lists. The existing ChemicalConcept transaction passed the synthetic partial stereochemical definition control. An unspecified stereo designation without source-attested partial scope, broad materials and component-only controls did not receive a live ChemicalConcept mapping.

The most frequent reasons were `WHOLE_REFERENT_BINDING_UNESTABLISHED` (426), `CONFLICTING_STRUCTURE_DIMENSIONS` (53), `SOURCE_ATTESTED_NONDISCRETE_SCOPE` (51) and `NO_SUFFICIENT_EVIDENCE_PATH` (35). Two further records were withheld for `COMPETING_AUTHORITY_STRUCTURAL_FORMS`. The 110-case structural screen found 21 agreements, 22 references paired with abstentions and 67 cases without usable references. The preliminary disagreement became a source-identifier hold. The available references cannot bound the number of undetected whole-referent errors. Zero duplicate identity groups or split target groups detected by the registry checks describes fixture integrity.

The retained chemistry, matching, admission and Stage C suites passed 136 tests and 49 subtests. The additional Stage B handoff and ChemicalConcept suites passed 47 tests and 40 subtests. They cover interrupted creation, rollback after partial work, same-identity concurrency, incompatible forms, replay, stale evidence, snapshot mutation and production-path rejection. The first reviewed execution stopped at its final guard because a regression used the shared derived chemistry cache. Of the 70 guarded paths, only that reproducible cache changed. The two pinned canonical registries, original CosIng records, Stage B artifacts and ontology retained their checksums. The cache change is recorded separately and was repinned after the tests, before the final isolated runs. [Regression output](stage_c/data/v3/tests.xml), [scope regressions](stage_c/data/v3/scope_regressions.xml), [derived cache digest change](stage_c/data/v3/derived_cache_repin.json).

The verified run completed all 628 checkpoints in 372.18 s, including fixture setup and two locked replays. Across 46 canonical transactions, median latency was 2.31 s, P95 was 2.96 s and total transaction time was 176.10 s. Qualification took 2.73 s in total after local evidence loading. The final Substance fixture occupied 255,320,064 bytes, including the original audit history, new events and per-source decisions. The integrated timing comes from a separate workload from the paired benchmark.

Both isolated runs passed the protected-path check and retained identical canonical content on locked replay. The second run reproduced all 628 source-revision decisions, outcome codes and target IDs, all 46 alias assertions and the canonical registry digest. A restart then recovered all 628 checkpoints. The main verifier confirmed SQLite and foreign-key integrity in both registry types, replay-safe mappings, current source revisions, all three documented holds, exact target graph comparison, alias receipts and the historical audit digest. It found zero orphaned mappings, duplicate canonical identity groups, split target groups or other integrity issues. The initial pinned registries and ontology were never written by Stage C. [Verified run](stage_c/data/pilot-v3-verified/run.json), [integrity and database checksums](stage_c/data/pilot-v3-verified/metrics.json), [authority and timing metrics](stage_c/data/pilot-v3-verified/authority_and_performance.json), [independent fixture replay](stage_c/data/pilot-v3-verified-replay/replay_comparison.json), [restart results](stage_c/data/pilot-v3-verified-replay/run.json), [resolved mappings](stage_c/data/pilot-v3-verified/resolved.json), [alias assertions](stage_c/data/pilot-v3-verified/alias_associations.json), [reference comparisons](stage_c/data/pilot-v3-verified/reference_results.json), [Substance fixture and journal](controlled_identity_reuse/fixtures/stage_c_e4c2522b5da040fcb60f96d203c335c3.sqlite), [ChemicalConcept fixture](chemical_concept_registry/fixtures/stage_c_e4c2522b5da040fcb60f96d203c335c3.sqlite).

| Acceptance gate | Result |
|---|---|
| A. Authority qualification | **Conditional.** GSRS remains operational and both new providers qualify real records. The exploratory whole-referent failures required targeted holds. A general safeguard for the newly observed scope and identifier conflicts still needs validation. |
| B. Performance | **Pass.** The paired median improved 2.34×, all paired decisions matched, and integrity and transaction regressions passed. |
| C. Chemical validation | **Conditional.** Independent structural checks and published definitions found actionable issues. Whole-referent accuracy on a fresh holdout remains unmeasured, with no independent specialist review. |
| D. Integrated lifecycle | **Pass in the reviewed fixture.** Creation, reuse, cross-source deduplication, aliases, replay and the audit history verified. This result applies to the frozen cohort and its recorded holds. |

## Readiness and reproduction

Keep further evaluation in isolated copies. First, independently review fresh positive and negative source bindings, including representative structures used for ingredient families, identifier conflicts and withheld salts, hydrates, stereochemical forms and constituent-only records. The reviewed holds are revision-specific and give no assurance for unseen families. The next qualification increment should acquire positive evidence for whole-material scope where a molecular name may stand for an isomer distribution, and compare qualified identifier-linked forms before a proposed exact association. This need does not impose a universal CAS or multiple-provider requirement. Measure sustained I/O, peak memory and contention before choosing a broader batch size. A broader inorganic identity capability requires a separate policy decision.

```powershell
python -B -m canonical_registry.stage_c.evaluation.v3_pathways
python -B -m canonical_registry.stage_c.evaluation.benchmark v3-baseline-repro
python -B -m canonical_registry.stage_c.evaluation.benchmark v3-compact-repro --compact
python -B -m canonical_registry.stage_c.run --v3 --run v3-repro --create --replay-count 2
python -B -m canonical_registry.stage_c.evaluation.verify --run v3-repro
python -B -m canonical_registry.stage_c.evaluation.v3_reference score --run v3-repro
python -B -m canonical_registry.stage_c.evaluation.v3_metrics --run v3-repro
python -B -m canonical_registry.stage_c.run --v3 --run v3-repro-second --create --replay-count 2
python -B -m canonical_registry.stage_c.evaluation.replay_compare --first v3-repro --second v3-repro-second --count 628
```

Resume a verified fixture with the same command, omitting `--create`. The retained performance summary reads the original paired profiles. The two benchmark commands produce separate reproduction profiles. Use the retained public captures for replay. Acquisition uses the approved HTTPS route and caches bounded public GET requests with timestamps and response hashes.

`STAGE_C_V3_CONDITIONAL`
