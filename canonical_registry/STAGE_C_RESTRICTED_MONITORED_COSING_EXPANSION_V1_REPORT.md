# Restricted monitored CosIng Stage C expansion v1

The three phases processed all 2,000 frozen fresh CosIng records and 33 controls in one isolated fixture. The resolver recorded 61 fresh exact mappings. Provisional review found an unsupported exact assignment of Pyridoxine Salicylate to a covalent ester despite evidence that the same designation can denote an ion pair. The result and its alias are quarantined from use. All authoritative data passed the final checksum comparison.

## Scope and cohort

The expansion uses the existing Stage C v3 evidence-sufficiency contract and safety-closure gate, with the existing complete matcher, admission service, source-association transaction, canonical ID allocator and compacted audit history. Writes use capability-limited copies pinned to the 562-Substance and one-active-ChemicalConcept development snapshots. The source registry, Stage B evidence, ontology v0.7.0 and authoritative canonical registries are protected by the frozen checksum manifest. [Safety closure baseline](STAGE_C_V3_SAFETY_CLOSURE_REPORT.md), [Stage C v3 baseline](STAGE_C_V3_AUTHORITY_COVERAGE_AND_SCALABLE_CANONICALIZATION_REPORT.md), [shared evidence contract](CHEMICAL_IDENTITY_EVIDENCE_SUFFICIENCY_CONTRACT_V1.md).

The frozen, disjoint 2,000-record sample excludes the earlier Stage C, evidence-sufficiency and authority-lookup cohorts. Selection uses a deterministic hash of the source concept ID with a fixed salt. The proposed phases are 200, 600 and 1,200 fresh records with the same stratum proportions. Form-sensitive selection uses designation hints so that sparsely supported forms remain represented. Eligibility still requires independently established form specificity.

| Stratum | Calibration | Full frozen cohort |
|---|---:|---:|
| Defined graph with identifier | 75 | 750 |
| Other graph | 20 | 200 |
| Form-sensitive | 30 | 300 |
| Identifier-led | 30 | 300 |
| Conflict | 20 | 200 |
| Broad or preparation | 25 | 250 |

[Frozen sampling manifest](stage_c/data/restricted_expansion/freeze.json), [source revisions and evidence](stage_c/data/restricted_expansion/fresh.json).

## Acquisition and qualification

Warehouse queries used bounded, read-only name, alias, typed identifier and full-key routes. The first REST submission returned an ID and the direct client failed during polling. MCP confirmed success for that same query ID. Calibration used the first 200 records, of which 125 had warehouse candidates. Public lookups used public InChIKeys, UNIIs and CAS numbers. Cached GSRS and NIST evidence was retained by accession or CAS. Missing or failed lookups are stored as such and do not confer whole-referent authority. An initial preflight caught a capture changing while ChEBI acquisition was in progress. No fixture was opened in that attempt. The run proceeded after acquisition finished and the immutable evidence set was resealed. [Calibration acquisition manifest](stage_c/data/restricted_expansion/acquisition_freeze.json).

The calibration capture records 84 PubChem calls, including 83 JSON responses, and 129 ChEBI calls, including 87 JSON responses. The GSRS capture contains 251 successful responses, 80 new and 171 previously captured, including fixed provider controls and native record requests. The operational NIST cache contains 143 distinct CAS lookup results, including 82 prior captures. A separate 150-record reference plan returned 24 NIST structures from 111 distinct CAS lookups. An overlapping operational CAS is tagged in each review packet. A Standard InChIKey comparison is a structural check. It does not establish whole-ingredient scope, and it can leave Fixed-H or stereo questions open. [Reference plan](stage_c/data/restricted_expansion/reference_plan.json), [acquisition captures and SQL](stage_c/data/restricted_expansion/).

The 34 warehouse query receipts cover all frozen fresh IDs. Warehouse candidates were present for 125/200 calibration records, 397/600 second-phase records and 763/1,200 final-phase records. Phase 2 reused the calibration authority budget. Phase 3 retrieved the following bounded additions on the approved network route. Durations are measured from the first to last new receipt timestamps, and the providers ran concurrently during acquisition. The original receipts were reused byte-for-byte at the record level.

| Authority | New calls | Result | Receipt span |
|---|---:|---|---:|
| PubChem | 120 | 116 JSON, four HTTP 404 | 137 s |
| ChEBI | 177 | 111 JSON, 66 HTTP 404 | 328 s |
| GSRS | 100 | 50 UNII searches and 50 native records, all captured | 170 s |
| NIST | 96 | 52 structural references, 44 with required fields unavailable | 116 s |

The final preflight again detected a capture changing. After verifying that every queued lookup and native record request had a receipt, the runner resealed the evidence before opening the fixture. The failed preflights, acquisition receipts, and final seal are retained. [Final acquisition seal](stage_c/data/restricted_expansion/phase_3_freeze.json), [final captures](stage_c/data/restricted_expansion/phase_3_authority/).

## Targeted diagnostic cases

| Source concept | Finding |
|---|---|
| Isopropyl alcohol | The safety-closure matcher accounted for all 583 identities and excluded 582 by the constitution index's necessary condition. Its only possible duplicate was acetone. The reduced heavy-atom adjacency is the same. The full graphs differ in molecular formula, hydrogen count and bond order, and direct comparison returns `DISTINCT`. The charge-attribution adapter suppresses a protonation inference when hydrogen count differs without the corresponding charge change. The registry correspondence layer then loses the global chemical distinction and reports `UNKNOWN` for the decisive dimension. This is a conservative correspondence defect after a complete search. The expansion leaves the existing hold in place pending a regression-tested distinction that preserves tautomer, resonance, isotope and composition rules. [NIST isopropyl alcohol](https://webbook.nist.gov/cgi/cbook.cgi?ID=000067-63-0), [NIST acetone](https://webbook.nist.gov/cgi/cbook.cgi?ID=67-64-1). |
| Retinyl palmitate | NIST provides a specific retinyl palmitate structure with defined double-bond geometry. The earlier source evidence did not establish that exact form for the whole source referent. This is an evidence-binding gap. [NIST vitamin A palmitate](https://webbook.nist.gov/cgi/cbook.cgi?ID=79-81-2). |
| Sodium chloride | The 1:1 ionic formula unit is defined. Native moiety validation and the existing registry envelope for extended ionic solids remain separate limitations. The expansion retains the existing policy. [PubChem sodium chloride](https://pubchem.ncbi.nlm.nih.gov/compound/5234). |

The three current-run controls stopped at `WHOLE_REFERENT_BINDING_UNESTABLISHED`. The isopropyl duplicate diagnosis uses the earlier safety-closure trace and a direct graph comparison. [Current diagnostic decisions](stage_c/data/pilot-expansion/diagnostic_controls.json), [isopropyl trace and graph comparison](stage_c/data/pilot-expansion/isopropyl_duplicate_diagnostic.json).

## Monitored execution results

| Phase | Fresh records | Warehouse candidates | Qualified | Exact mappings | Unresolved |
|---|---:|---:|---:|---:|---:|
| 1. Calibration | 200 | 125 | 26 | 26 | 174 |
| 2. Controlled expansion | 600 | 397 | 0 | 0 | 600 |
| 3. Full restricted cohort | 1,200 | 763 | 38 | 35 | 1,165 |
| Fresh total | 2,000 | 1,285 | 64 | 61 | 1,939 |
| All checkpoints, including controls | 2,033 | 1,317 | 79 | 76 | 1,957 |

Calibration physically wrote 196 fresh checkpoints and 33 control checkpoints. A boundary comparison exposed a selection error that let four historic rows consume fresh positions. Selection now uses frozen fresh IDs. The next execution recovered the four missing fresh records before processing its 600. All four were unresolved. The verifier confirmed exact cohort membership at the 800- and 2,000-record boundaries. The 33 controls comprise 24 historical CosIng cases and nine GSRS cases. WATER, AQUA, ALCOHOL, GLYCERIN and HYDROGEN PEROXIDE resolved. The three known unsafe historical assignments were held.

The 61 fresh exact mappings were 57/750 in the defined graph stratum and 4/200 in the other graph stratum. All 1,050 records across the four other strata were unresolved. Across all checkpoints, the eligibility breakdown was 79 candidate-ready, 371 review hold, 1,443 needing more evidence and 140 outside applicable exact molecular resolution. Whole-referent binding was unestablished in 872 decisions. The 116 records with a variable-composition or distribution observation were all withheld. One decision triggered the explicit source identifier–structure conflict reason, seven triggered disagreement with all validated graphs on InChIKey, and 185 triggered conflicting structural dimensions. Reason counts may overlap. Two qualified multicomponent salt graphs were withheld because component semantics were unknown. Platinum was withheld for unsupported element capability and incomplete uniqueness proof. All 300 fresh form-stratum records abstained.

The fixture recorded 71 new Substances and five reuse operations, representing 72 distinct canonical Substance IDs. One distinct target existed in the baseline. Four reuse operations reused identities already assigned earlier in the run. WATER and AQUA reused the same baseline target as the GSRS WATER control. GSRS ALCOHOL and GLYCERIN reused IDs already admitted for the CosIng controls. The matcher verified complete search accounting for successful creation and reuse. The fixture recorded zero ChemicalConcept mappings, 76 exact alias assertions and 73 distinct Substance–alias pairs. Those counts describe persisted fixture output before review exclusions. The Pyridoxine Salicylate mapping and its alias are excluded from any downstream use, and Tridecyl Neopentanoate is flagged for scope review. [Registry verification](stage_c/data/pilot-expansion/metrics.json), [phase and stratum metrics](stage_c/data/pilot-expansion/expansion_metrics.json), [mappings](stage_c/data/pilot-expansion/resolved.json), [alias provenance](stage_c/data/pilot-expansion/alias_associations.json).

## Performance and integrity

| Sequential execution | Calibration | Phase 2 with recovery | Phase 3 |
|---|---:|---:|---:|
| Decisions newly checkpointed | 229 | 604 | 1,200 |
| Elapsed including setup and verification inside the runner | 492.2 s | 182.7 s | 366.3 s |
| Setup wall time | 361.4 s | 157.0 s | 156.8 s |
| Peak process working set | 303.1 MiB | 415.6 MiB | 419.5 MiB |
| End-to-end checkpoints per second | 0.47 | 3.31 | 3.28 |
| Isolated Substance file growth from phase start | 9,347,072 B | 4,972,544 B | 16,187,392 B |
| Cumulative compressed audit payload growth | 1,410,279 B | 1,410,279 B | 2,588,434 B |
| Derived index cache on disk | 27,033,600 B | 27,033,600 B | 52,363,264 B |

Across 79 matching/admission transactions, median latency was 1.885 s and P95 was 4.526 s. For the 38 fresh phase-3 attempts those figures were 2.002 s and 6.398 s. Median qualification latency was 0.276 ms and P95 was 3.114 ms across 2,033 decisions, after authority acquisition and setup. Total qualification time was 4.197 s, including 0.284 s measured in the source-safety layer. The transaction timer covers matching, lock acquisition, admission and persistence together. It does not isolate lock wait or commit time. The retained concurrent-admission and interruption tests exercise locking, uniqueness and atomic rollback.

The working-set peak occurred during setup in all three processes. Later batches loaded the cumulative warehouse evidence and phase-specific authority captures. These measurements do not isolate memory by data structure or separate workload size from cache effects. SQLite checkpoints and cumulative growth were verified at each completed phase. The original 2,970 audit events, totaling 2,438,269,181 uncompressed evidence bytes, remained recoverable from the compacted archive. Compaction preserved the ordered event-content digest and stored 74,047,027 compressed payload bytes before new admissions. The Substance fixture finished at 274,518,016 bytes with 633 Substances. The ChemicalConcept fixture matched its initial digest.

Both SQLite integrity and foreign-key checks passed. Verification detected zero new structural duplicates, zero splits of an exact identity across IDs and zero mapping, revision or alias-provenance failures under the implemented checks. All 70 protected paths matched the frozen digests, including the authoritative registries, CosIng registration, Stage B assessments and ontology v0.7.0. The retained test run reported 40 passed and 35 passed subtests, including injected admission failure, concurrent same-identity admission and revision changes. No ingredient-equivalence operation ran. [Calibration timings](stage_c/data/pilot-expansion/phase_1_run.json), [phase 2 timings](stage_c/data/pilot-expansion/phase_2_run.json), [final timings](stage_c/data/pilot-expansion/run.json), [100-record checkpoint summaries](stage_c/data/pilot-expansion/phase_checkpoint_summary.json), [test results](stage_c/data/restricted_expansion/tests.xml).

Calibration ran two locked canonical replays and confirmed an identical canonical digest. A separate final-phase restart recovered all 1,200 saved checkpoints in 283.9 s, of which 251.4 s was setup. All 2,033 decisions, aliases, the canonical digest and both fixture file digests were identical before and after restart. The equivalent final-phase replay reused the authority captures and derived index cache. Its 420.3 MiB peak was within 0.8 MiB of the write run. The failed preflights exercised recovery from an unsealed acquisition boundary. This run did not inject interruptions into live acquisition or qualification. Before-commit interruption, concurrent same-identity admission and changed source evidence were exercised in the retained fixture tests. [Restart verification](stage_c/data/pilot-expansion/restart_results.json).

## Reference review

The review set combines a 150-record calibration plan frozen before execution with every fresh exact assignment. Review packets preserve the original definition and identifiers, revision, target graph, designation promoted as alias, authority receipt, external structural comparison, and whether that CAS lookup was also available to the pipeline. Positive and negative examples below are provisional source-grounded judgments. The verified mapping and alias counts are measures of internal integrity.

| Case | Provisional scope and form finding |
|---|---|
| AMYL FORMATE, `CIC_00010623` | The source designation and CAS 638-49-3 support the straight-chain pentyl formate graph and alias. BAM identifies the same linear ester and NIST lists both the designation and the matching structure. [BAM](https://www.dgg.bam.de/dgginfo/detailinfo/rid/rmbluxniyovw), [NIST](https://webbook.nist.gov/cgi/cbook.cgi?ID=638-49-3). |
| PHENYLPARABEN, `CIC_00004957` | The source defines the phenol ester of 4-hydroxybenzoic acid. The regulator explicitly binds the INCI name and CAS 17696-62-7 to phenyl 4-hydroxybenzoate, which agrees with the isolated target and supports the alias. [Saudi FDA](https://www.sfda.gov.sa/en/details_data?id=17696-62-7&nid=17589&page=137), [ECHA](https://echa.europa.eu/de/substance-information/-/substanceinfo/100.037.892). |
| TRIPALMITIN, `CIC_00028821` | The external cosmetic definition specifies glycerol esterified by three palmitic acid chains. The NIST reference material defines the same graph and name, supporting the mapping and alias. [CIR](https://www.cir-safety.org/sites/default/files/Triglycerides.pdf), [NIST reference material certification](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=957259). |
| ETHYL PERFLUOROBUTYL ETHER, `CIC_00016802` | The source's sole CAS 163702-05-4 identifies the linear molecule. The FDA report links the INCI name to that CAS and NIST agrees with the graph. The same FDA report also lists a trade name which the manufacturer's SDS identifies as a two-isomer mixture. The fixture's source alias is the INCI name. This case requires preserving the distinction between the CAS-defined chemical and the commercial product designation. [FDA report](https://www.fda.gov/media/190319/download), [NIST](https://webbook.nist.gov/cgi/cbook.cgi?ID=C163702054), [3M SDS](https://multimedia.3m.com/mws/mediawebserver?mwsId=SSSSSuUn_zu8l00xlYtUmxtePv70k17zHvu9lxtD7SSSSSS--). |
| MYRCENE, `CIC_00023718` | The source's sole CAS, the EU flavour entry and the NIST β-myrcene graph agree. The EU specification separately permits secondary components in a commercial grade. The alias is supported for the source's CAS-defined chemical. [EU flavour entry](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=celex%3A32012R0872), [NIST](https://webbook.nist.gov/cgi/cbook.cgi?ID=C123353). |
| METHYLCHLOROISOTHIAZOLINONE, `CIC_00028720` | The reported CAS and NIST graph identify a discrete active. An SCCS opinion distinguishes the active from a preparation that combines it with methylisothiazolinone. The source definition and complete revision should be reviewed before treating this hold as a false rejection. [NIST](https://webbook.nist.gov/cgi/cbook.cgi?ID=C26172554), [SCCS](https://health.ec.europa.eu/system/files/2016-11/sccs_o_009_0.pdf). |
| ISOMALT, `CIC_00005972` | The source defines a mixture. JECFA identifies two principal saccharides, one specified as a dihydrate. Withholding a single exact molecular mapping preserves the whole ingredient. [JECFA specification](https://www.fao.org/4/i0345e/i0345e.pdf). |
| PYRIDOXINE SALICYLATE, `CIC_00019582` | **Unsupported exact mapping and alias.** The frozen record has no definition, CAS or EC. OPSIN and the PubChem structure for CID 187064 agree on a specific covalent ester. The same designation is used for an ion pair in a primary patent source. This demonstrates a form ambiguity that the record cannot settle. The patent does not establish that the CosIng source denotes the ion pair. The isolated target `SUB_00000621` and the source alias remain in the run's audit evidence and are quarantined from use. [PubChem properties](https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/187064/property/SMILES,InChI,InChIKey,IUPACName/JSON), [patent, claims 18–19](https://patents.google.com/patent/US20060147508A1/en). |
| TRIDECYL NEOPENTANOATE, `CIC_00019455` | **Historical scope conflict.** The current frozen revision explicitly describes the linear n-tridecyl ester and the fixture matches it. The earlier EU inventory describes a branched tridecyl ester under the same INCI designation. The current revision supports the linear graph. An unqualified alias or historical equivalence remains unresolved. [EU inventory](https://www.legislation.gov.uk/eudn/1996/335/pdfs/eudn_19960335_adopted_en.pdf). |

All 61 fresh exact assignments appear in the 190 packets alongside 129 abstentions. NIST supplied a Standard InChIKey comparison for 37/61 exact assignments. All 37 agreed and used CAS captures also available to the pipeline. Another 13/129 abstentions had a structural reference, six outside the operational capture. The remaining 140 packets had no structural comparison. An external identifier lookup can verify the referenced species without settling whether the complete source concept denotes it.

The provisional review records 38 case-level judgments, including seven positives and 31 abstentions. Five of seven positive mappings and their aliases were supported, one positive mapping and alias were unsupported, and one raised a historical scope conflict for the unqualified alias. Thirty of 31 abstentions were supported by the source definitions, and one needs a complete source definition. The reviewer also identified one technically false duplicate hold in the separate isopropyl diagnostic. There were zero independent specialist judgments. The 150-case adjudication target remains open. These counts do not support a cohort-wide precision or recall estimate. [Review packets](stage_c/data/pilot-expansion/reference_packets.json), [provisional judgments](stage_c/data/pilot-expansion/provisional_review.json), [quarantined findings and evidence](stage_c/data/pilot-expansion/quarantined_findings.json).

## Gates and next decision

| Gate | Result | Basis |
|---|---|---|
| A. Operational scaling | PASS within the frozen scope | The sealed phases reached all 2,033 checkpoints within measured resources. The selection defect was recovered without repeating saved decisions. |
| B. Chemical identity safety | FAIL | Matching a parser-derived covalent ester to the same authority graph can pass the source-scope gate despite unresolved salt versus ester semantics. |
| C. Reference validation | CONDITIONAL | Positive and negative cases have provisional evidence, and the 150-case adjudication target and independent specialist review remain open. |
| D. Canonical registry integrity | PASS for transactional integrity | SQLite, audit, protected digests and duplicate checks passed. The chemical exclusion is tracked by Gate B. |

Suspend wider automatic mapping or admission. Before a wider run, require a source-bound positive specification for ambiguous ester, salt and adduct designations, then rerun held-out whole-referent and alias controls for that evidence pathway. Continue reference review in the isolated fixture and keep the three diagnostic holds until their individual proof obligations are satisfied.

## Reproduction

```powershell
python -B -m canonical_registry.stage_c.evaluation.verify --run pilot-expansion
python -B -m canonical_registry.stage_c.evaluation.restricted_expansion summarize --run pilot-expansion
python -B -m canonical_registry.stage_c.run --expansion --expansion-phase 3 --run pilot-expansion --checkpoint-only
```

The replay CLI refreshes `run.json` with replay timing. Preserve the original run metrics before using it. Fresh isolated re-execution uses phase 1 with `--create` and then phases 2 and 3 with matching per-run seals that bind each preceding verified manifest. The supplied seals and receipts document the executed fixture.

The isolated registry files preserve the run for diagnosis and replay. [Substance fixture and decision journal](controlled_identity_reuse/fixtures/stage_c_178ac2cde8e34c429bfbf196e200948e.sqlite), [ChemicalConcept fixture](chemical_concept_registry/fixtures/stage_c_178ac2cde8e34c429bfbf196e200948e.sqlite).

**STAGE_C_RESTRICTED_EXPANSION_V1_FAILED**
