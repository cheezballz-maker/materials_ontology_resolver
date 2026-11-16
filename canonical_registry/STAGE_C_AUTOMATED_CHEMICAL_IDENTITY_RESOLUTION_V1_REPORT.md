# Stage C automated chemical identity resolution v1

Stage C completed the reuse-or-create lifecycle for 699 source records in isolated SQLite copies. It resolved 21 source records to 17 distinct Substances. WATER, AQUA and the GSRS WATER record reused the existing water ID. The run admitted 16 new identities. GSRS subsequently reused the new ethanol and glycerin IDs.

## Scope and measured results

| Metric | Result |
|---|---:|
| CosIng concepts processed | 620 |
| GSRS controls processed | 79 |
| Candidate pairs retrieved for CosIng before the per-record cap | 655 |
| CosIng records with at least one GSRS candidate | 446 |
| Chemically qualified source referents | 21 |
| CosIng referents qualified | 18 of 620 |
| Fresh CosIng referents qualified | 7 of 240 |
| Source records resolved and mapped | 21 |
| Previously existing Substance identities reused | 1 |
| New Substance identities admitted | 16 |
| Distinct Substance identities represented | 17 |
| ChemicalConcept resolutions | 0 |
| Distinct qualified exact aliases associated | 18 |
| Source-level exact alias assertions | 21 |
| Unresolved or abstained | 678 |
| Failed admissions in the source pilot | 0 |
| New duplicate Substance identities detected | 0 |
| Critical incorrect identity merges detected in verified controls | 0 |

The frozen CosIng cohort combined the 380 prior lookup cases and 240 records excluded from both earlier lookup and sufficiency cohorts. Fresh strata comprised 105 defined-graph cases, 30 other graph cases, 45 molecular-form cases, 20 conflicts, 20 broad referents and 20 identifier-led cases. All 11 prior CosIng qualifications resolved. The fresh cases added seven qualifications. The seven authority-backed fresh positives were selected through a targeted retrieval queue, so the result measures demonstrated expansion under this acquisition budget.

The starting copies held 562 Substances and one active ChemicalConcept. The 30,360-concept CosIng registration database, its source revisions and Stage B assessments supplied read-only input. The fixture journal projects the existing four canonical statuses using the original source references and revisions. A source concept outside the evaluated cohort keeps its original status. [Frozen cohort and source hashes](stage_c/data/freeze.json), [run manifest](stage_c/data/pilot/manifest.json).

## Evidence and lifecycle

Stage C reused the Authoritative Chemical Identity Lookup adapters and the shared evidence sufficiency evaluator. Four new bounded Trino queries covered the 240 fresh records, and seven archived queries covered the earlier cohort. Results distinguish exact preferred-name, reported alias, typed identifier and full InChIKey retrieval. Forty-nine CosIng referents had multiple warehouse candidates. An exact lookup hit supplies a candidate.

NCATS GSRS, PubChem and ChEBI API probes failed at DNS. The run reused the saved complete native GSRS ALCOHOL definition and four archived PubChem or ChEBI candidate records. A frozen, CAS-indexed NIST queue attempted 32 species pages and captured 12 with complete fields. The generalized cross-reference requires the source and GSRS preferred designations to agree, the same typed CAS claim, and agreement among the source evidence, warehouse graph and NIST species graph. NIST title spelling may differ when this independent form check succeeds. Receipt evidence retains the authority title and source designation. [GSRS API](https://gsrs.ncats.nih.gov/api-documentation), [ChEBI REST tools](https://www.ebi.ac.uk/chebi/tools), [NIST methyl palmitate](https://webbook.nist.gov/cgi/cbook.cgi?ID=C112390), [NIST neral](https://webbook.nist.gov/cgi/cbook.cgi?ID=C106263).

The shared evaluator qualified 18 nomenclature-mediated, two identifier-mediated and one direct-structure referent. It checked the whole-referent binding and exact form using strict RDKit and official InChI validation. The downstream adapter preserves the difference between native structure and an independently qualified cross-reference. The existing matcher and admission policy execute under the creation service's `BEGIN IMMEDIATE` transaction. The existing allocator supplies new IDs and the existing association service rechecks the target before committing. The Stage C journal and exact alias assertions join that same Substance transaction. The registry keeps source concepts independently and records `mapsToSubstance` for successful source revisions.

Stage C delegates eligible partial molecular inputs to the existing ChemicalConcept transaction and `mapsToChemicalConcept` route. The source pilot produced no eligible partial referent. The ChemicalConcept database remains a separate file, so its own creation and source mapping commit together. Its Stage C checkpoint is a subsequent idempotent operation.

## Admissions, cross-source reuse and safeguards

| Case | Isolated result |
|---|---|
| CosIng WATER, CosIng AQUA and GSRS WATER | All reused `SUB_00000562` |
| CosIng ALCOHOL then GSRS ALCOHOL | Created and reused `SUB_00000563` |
| CosIng GLYCERIN then GSRS GLYCERIN | Created and reused `SUB_00000564` |
| Fresh qualified CosIng records | Methyl palmitate, neral, valeraldehyde, ethyl benzoate, amyl acetate, diethyl malonate and methyl perfluorobutyl ether admitted |
| ALCOHOL DENAT. | Unresolved as a whole material. Ethanol appeared as a candidate |
| CITRIC ACID and MAGNESIUM SULFATE | No assignments across competing anhydrous and hydrate forms |
| GLUTAMIC ACID and unspecified lactic acid | No assignment to a specific stereoisomer |
| 3-OCTANOL and 1-PENTEN-3-OL | Authority graph alone left stereochemical specificity unestablished |

Across the pilot, 499 records needed more evidence, 85 retained a review hold and 94 were outside exact molecular scope under the shared evaluator. The most frequent reasons were missing whole-referent binding, no sufficient evidence path and conflicting structural dimensions. Sodium chloride and hydrogen peroxide remain plausible missed qualifications because candidate retrieval did not establish the required whole-referent form. ACETAMINOPHEN retained its existing contradictory structure hold.

The five reuse operations avoided five additional allocations for already represented identities. The final verifier compared every resolved structure against its persisted target and checked source revisions, live mappings, receipt digests, alias provenance, one-SMILES-per-Substance cardinality and duplicates involving new entries. It detected no erroneous targets or exact-form splits under those checks. The retained form regressions cover stereo, isotopes, charge and protonation, counterions, hydrates and Fixed-H tautomers. These checks measure policy compliance and selected case correctness. Independent case-by-case accuracy and alias precision for the wider inventory remain unmeasured.

The 18 distinct exact aliases derive from validated source designations, including WATER and AQUA on the same target. Raw provider synonym lists and reported identifiers remain in the evidence journal. Newly admitted records carry their locally generated InChI and InChIKey. Other identifier assertions remain evidence. [Resolved source mappings](stage_c/data/pilot/resolved.json), [exact alias associations](stage_c/data/pilot/alias_associations.json).

## Transaction, restart and performance

The first process stopped after 120 checkpoints and the second reused those checkpoints and finished all 699. Two previously qualified requests were revalidated through the locked workflow, with identical canonical digests before and after. The final regression run passed 83 tests and 35 subtests, including synthetic concurrent reuse, isotope separation, rollback, restart, blocked writes to the pinned source and ChemicalConcept creation through its existing policy. The Substance fault injection reached the point immediately before commit, after identity, association and checkpoint writes, and verified rollback across all affected tables. [Regression results](stage_c/data/tests_final.xml).

The two pilot invocations took about 716 seconds combined, including fixture cloning and restart verification. The fresh warehouse queries took 18–54 seconds each including queueing. Qualification inside the shared evaluator took 1.6 seconds in aggregate. The 21 committed matching and admission transactions took 518 seconds total, with a median of 22.2 seconds. The Substance copy grew by about 10.2 MiB over its pinned source. Matching, transaction revalidation and copying the 2.43 GiB starting database dominate the workflow. Peak process memory and per-phase alias or mapping latency were not instrumented. Live provider requests occurred during evidence acquisition only. The Stage C execution replay used the frozen captures.

Both fixture databases passed SQLite integrity and foreign-key checks. The Substance copy retained all preexisting canonical rows and the full CUMA reconciliation table. Seventy protected source paths matched their frozen digests, including the authoritative ontology and the original registry and Stage B artifacts. The run used a separate derived index and left production canonical IDs, mappings and source statuses unchanged. [Measured pilot results](stage_c/data/pilot/metrics.json).

## Reproduce and assess readiness

From the workspace root, use a fresh run name and the retained captures.

```powershell
python -B -m canonical_registry.stage_c.run --run stage-c-replay --create --limit 120
python -B -m canonical_registry.stage_c.run --run stage-c-replay --replay-count 2
python -B -m canonical_registry.stage_c.evaluation.verify --run stage-c-replay
```

The fixture database and append-only decision journal contain the exact match, admission and source-revision proofs. The pinned starting registry, ordered inputs and existing allocator define the replay order. Fixture IDs, timestamps and event IDs are run-specific. A fresh full-copy replay was not measured. [Isolated Substance SQLite](controlled_identity_reuse/fixtures/stage_c_d47a9518f1934de9b5d0264cd9d7f6b7.sqlite), [isolated ChemicalConcept SQLite](chemical_concept_registry/fixtures/stage_c_d47a9518f1934de9b5d0264cd9d7f6b7.sqlite).

Full-scale CosIng Stage C is premature. The next bounded expansion needs accessible role-bearing authority records and independent adjudication of fresh positives and abstentions, with particular attention to form conflicts and source-to-whole-referent binding. Qualification reached 2.9% of the CosIng pilot, and the observed per-admission latency also needs improvement before a wider run.

`STAGE_C_AUTOMATED_RESOLUTION_V1_CONDITIONAL`
