# Stage C v2 authority access and resolution performance

Stage C v2 restored verified access to all three public authorities through the approved network route. The isolated pilot evaluated 300 fresh CosIng concepts, 19 earlier controls and nine GSRS controls. It resolved 36 source records to 32 distinct Substances, including 31 newly admitted fixture identities. The paired benchmark improved median latency by 1.57×. Broader deployment remains conditional on independent review of source-to-chemical bindings and on the cost of the remaining integrity scan.

Stage C v1 resolved 21 of 699 source records, qualified 18 of 620 CosIng concepts, and admitted 16 Substances in its fixture. Its 21 successful transactions had a 22.2 s median and totalled 518 s. V2 preserves that lifecycle and the shared evidence contract. [Stage C v1](STAGE_C_AUTOMATED_CHEMICAL_IDENTITY_RESOLUTION_V1_REPORT.md), [authority lookup baseline](AUTHORITATIVE_CHEMICAL_IDENTITY_LOOKUP_V1_REPORT.md), [evidence contract](CHEMICAL_IDENTITY_EVIDENCE_SUFFICIENCY_CONTRACT_V1.md).

| Metric | Measured result |
|---|---|
| GSRS authority access | Live JSON and validated native definitions |
| PubChem authority access | Live name, CID, structure, synonym and depositor SID queries |
| ChEBI authority access | Live discrete entity and broad class controls |
| Fresh CosIng concepts evaluated | 300 |
| Authoritative chemical records retrieved | 67 GSRS native payloads across 66 unique accessions. 45 accessions passed native validation. PubChem and ChEBI added four candidate observations |
| Newly qualified chemical referents | 25 fresh CosIng records and one previously held CosIng record |
| Exact existing Substance matches | Five reuse operations, including three references to one baseline Substance |
| New Substance identities admitted | 31 |
| Cross-source identity reuses | Three GSRS records reused CosIng targets. Two of the targets were newly created |
| Incorrect identity merges detected | 0 in verified cases |
| Duplicate canonical identities created | 0 |
| Previous v1 median matching and admission latency | 22.2 s |
| Optimized paired median | 9.45 s |
| Paired improvement factor | 1.57× against a 14.80 s rerun baseline |
| Authority access gate | PASS for the approved bounded network route |
| Evidence qualification gate | PASS on the bounded references and regression controls |
| Matching performance gate | PASS for measured improvement and paired outcome agreement. Threefold target remains open |
| Integrated lifecycle gate | PASS in isolated fixtures |

## A. Authority connectivity and verified access

The project ran on Windows 11 and Python 3.14.3 with OpenSSL 3.0.18. The sandbox exposed its network-disabled marker and Python reported no configured proxy schemes. DNS returned Windows error 11001 in Python for the three provider hosts and unrelated public controls. Curl reported the same boundary. Sandbox requests reached neither TCP/TLS nor HTTP. No evidence attributed those failures to provider downtime, a bad hostname, authentication, a certificate chain or throttling. The web documentation tool could retrieve public documentation, while its direct API fetches did not deliver the required payloads.

Using the approved network route, the same Windows host resolved the provider names and Python received HTTPS 200 with TLS verification enabled. All 141 bounded GET requests captured JSON. The request log preserves exact host, URL, method, DNS outcome, status, response type, timestamp, duration and raw-response digest. The client bounds each response to 4 MB and retries 429 or 503 once, subject to the server delay cap. No requests required credentials. Continue using the approved public egress route for acquisition and replay the resulting versioned captures inside the sandbox. [Sandbox diagnostics](stage_c/data/authority_sandbox.json), [approved request captures](stage_c/data/authority_approved.json).

| Provider | Validation |
|---|---|
| NCATS GSRS | Approval-ID search followed by native UUID detail. Ethanol and glycerol returned approved complete primary chemical records, including names, structure, moieties, identifiers, relationships and references. Across the queue, 45 unique accessions met the existing native graph, stereo and moiety checks. |
| PubChem | Name and CID returned ethanol CID 702 with agreeing SMILES, InChI and full key. Exact structure search returned CID 702. Synonym and SID endpoints returned separate annotation and depositor identifiers. The glutamic acid search returned three CIDs and exposed ambiguity. |
| ChEBI | CHEBI:16236 supplied the released ethanol entity and agreeing structure, name and identifiers. CHEBI:30879 was a broad alcohol class with an R-group graph and no defining Standard InChI. |

PubChem and ChEBI records remain candidate and comparison evidence in this pilot. The new automatic whole-referent route relies on role-bearing GSRS records and the original source evidence. FDA/NCATS representations of the same GSRS record count as one lineage. [GSRS API documentation](https://gsrs.ncats.nih.gov/api-documentation), [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest), [ChEBI REST tools](https://www.ebi.ac.uk/chebi/tools), [record validation](stage_c/data/v2/authority_validation.json).

## B. Qualification and chemical-form controls

The frozen fresh cohort excludes the v1 authority lookup, evidence-sufficiency and Stage C cohorts. It contains 110 defined-graph, 35 other graph, 75 molecular-form, 30 conflict, 30 broad and 20 identifier-led records. Five read-only Trino shards returned at least one candidate for 246 fresh records. Public GSRS acquisition then prioritized specific previously held cases and fresh records with one preferred-name candidate and a projected chemical graph. The 65-accession network budget was applied before the canonical write run.

On the same 300 records and unchanged v2 policy, the archived-only evidence qualified zero records. Adding the live captures moved 25 from `NEEDS_MORE_EVIDENCE` to `CANDIDATE_READY` and eight from `NEEDS_MORE_EVIDENCE` to `REVIEW_HOLD`. This isolates the effect of the new authority inputs. It is distinct from the v1 result of 7/240 on a different fresh cohort. [Paired evidence comparison](stage_c/data/v2/authority_ablation.json).

The shared sufficiency contract still controls discrete scope, claim authority, whole-referent binding and form agreement. A verified native definition plus a matching source designation and concordant source graph can now qualify without a universal CAS or EC requirement. A typed source UNII can establish the identifier-mediated route with a concordant graph. The identifier-only route does not grant exact alias status to the display name. Direct GSRS referents can use the native structure. Reported aliases, flattened structures, unqualified accessions and hierarchy relationships remain retrieval evidence. Conflicting or competing forms retain their holds. The pilot exercised 37 nomenclature and three direct-structure qualifications. The typed UNII route passed its synthetic control.

| Control | Decision and chemical evidence |
|---|---|
| Hydrogen peroxide | The native complete GSRS graph and the CosIng graph agreed on neutral hydrogen peroxide. ChEBI independently corroborated the chemical form. The isolated run created a Substance. |
| Sodium chloride | ChEBI and the native record described a 1:1 ionic formula unit. The native GSRS moiety check disagreed and the separate isotonic preparation remained a candidate. The existing admission policy also excludes extended inorganic ionic compositions from the discrete molecular salt envelope. The source stayed unresolved. |
| Citric acid | The source supplied identifiers for the anhydrous and monohydrate forms. No exact assignment. |
| Magnesium sulfate | Source identifiers and native candidates covered distinct hydration states. No exact assignment. |
| Glutamic acid | Native GSRS returned a specified graph without a verified source stereo binding. ChEBI independently identifies L-glutamic acid as a specific form. No stereoisomer was selected. |
| Dimethyl ether and ethyl laurate | NIST independently corroborated the expected full keys. Dimethyl ether remained distinct from ethanol. |
| Ciclopirox olamine, silicon, titanium alkoxide and magnesium hydride | The evidence gate reached a defined candidate, and the existing admission checks withheld all four. Multicomponent semantics, electronic state or element capability blocked admission. |

All seven targeted ChEBI and NIST reference checks agreed with the pilot, including three positives and four held controls. The references establish chemical form or a specific scope distinction. They do not independently verify every source designation or measure population precision. Further case-by-case review of fresh source bindings is still needed. [Reference results](stage_c/data/pilot-v2/reference_results.json), [hydrogen peroxide](https://www.ebi.ac.uk/chebi/CHEBI:16240), [sodium chloride](https://www.ebi.ac.uk/chebi/CHEBI:26710), [citric acid](https://www.ebi.ac.uk/chebi/CHEBI:30769), [magnesium sulfate heptahydrate](https://www.ebi.ac.uk/chebi/CHEBI:31795), [L-glutamic acid](https://www.ebi.ac.uk/chebi/CHEBI:16015), [dimethyl ether](https://webbook.nist.gov/cgi/cbook.cgi?ID=C115106), [ethyl laurate](https://webbook.nist.gov/cgi/cbook.cgi?ID=C106332&Mask=C).

## C. Matching and admission performance

The 2.43 GiB starting fixture contained 562 canonical identities and 53,667 CUMA reconciliation rows. Only 2,970 existing audit events accounted for about 2.44 billion characters of decision JSON. The SQLite build lacks `dbstat`, so those figures are logical lengths. A representative full `integrity_check` took 5.03 s, the foreign-key check took 0.064 s and a table-scoped identity check took 0.001 s. The reconciliation query plan scanned its table, but the measured inventory and integrity costs showed that a new index on reconciliation would not address the main delay.

The optimization keeps the pre-mutation full integrity scan under `BEGIN IMMEDIATE`. After allocation and insertion it verifies the touched canonical tables and foreign keys, rebuilds the current snapshot and runs the full exact duplicate search again. Association can consume the signed result already evaluated for the same request, database connection and unchanged locked state. Changes to data or schema force a recheck. Ordinary association requests still run the independent locked check. Chemical comparison, ID allocation, journal and mapping atomicity, rollback and idempotency remain on the established paths.

| Paired frozen workload | Baseline | Optimized |
|---|---:|---:|
| Median, six successful or replayed requests | 14.80 s | 9.45 s |
| Nearest-rank P95, six observations | 31.55 s | 17.86 s |
| Median, two first-time admissions | 22.72 s | 9.45 s |
| Total, six successful or replayed requests | 90.94 s | 63.49 s |
| Snapshot read and integrity time, cumulative | 71.50 s | 45.73 s |
| Fixture initialization, excluded from per-record timings | 76.22 s | 73.37 s |
| One-time derived index warm-up | 68.78 s | 65.48 s |

All eight paired requests agreed on status, outcome and target, including ambiguous and preparation abstentions. Reuse latency varied with I/O and concurrent activity. The matched benchmark measures the same request mix and pinned starting registry. Its figures should not be read as a direct comparison with the v1 pilot median. Connection setup, snapshot work, index construction, allocation, insertion, recheck and audit encoding were profiled. Commit, alias writes and source mapping were retained in aggregate transaction time. Peak memory and a dedicated lock-contention benchmark were not collected. Full pre-mutation scans still dominate. A later benchmark should isolate the pilot from competing I/O and evaluate compaction of the immutable audit history with independent integrity and recovery checks. [Paired measurements](stage_c/data/v2/benchmark_comparison.json).

## D. Isolated lifecycle and registry integrity

The run started from 562 Substances and one active ChemicalConcept. It completed 328 checkpoints. Forty referents qualified and 36 resolved. Four passed qualification but were withheld by admission. The other 288 abstained at the evidence gate. The native GSRS WATER, ALCOHOL and GLYCERIN controls reused the corresponding CosIng targets. All 11 prior CosIng qualifications resolved. The live pilot produced zero eligible ChemicalConcept mappings. The retained synthetic control created a graph-grounded partial ChemicalConcept through the existing transaction. In the final fixture run, the 40 pilot transactions had a median of 4.04 s and totalled 202.76 s. The full run took 298.0 s, including setup and replay, and the copy grew by 28.0 MiB. These times come from the integrated workload and are separate from the paired comparison.

Two requests replayed through the locked workflow with identical canonical digests. An independent fixture run reproduced all 328 source-revision decisions, target IDs and 36 source-level alias assertions. The regression run passed 83 tests and 35 subtests. A separate matching optimization run passed four tests and 565 subtests. The final lookup suite passed all 28 tests, including five new native-route cases. The suites exercised concurrent duplicate prevention, rollback, stale snapshot rejection, chemical form distinctions and scope boundaries. Verification covered both isolated databases, current source revision mappings, whole-referent receipts, alias provenance and 70 protected source paths. The authoritative ontology, registries and Stage B artifacts retained their frozen digests. All new IDs belong to the isolated fixture. [Metrics](stage_c/data/pilot-v2-final/metrics.json), [resolved source mappings](stage_c/data/pilot-v2-final/resolved.json), [independent fixture replay](stage_c/data/pilot-v2-final/replay_comparison.json), [regression tests](stage_c/data/v2/tests.xml), [snapshot tests](stage_c/data/v2/matching_tests.xml), [native-route tests](stage_c/data/v2/native_route_tests.xml), [Substance fixture](controlled_identity_reuse/fixtures/stage_c_3418e26d62b144498ebfbd40311a720a.sqlite), [ChemicalConcept fixture](chemical_concept_registry/fixtures/stage_c_3418e26d62b144498ebfbd40311a720a.sqlite).

## Reproduction

Use the approved network route for acquisition and the workspace Python environment for validation and execution.

```powershell
python -B -m canonical_registry.stage_c.evaluation.authority_access --run approved --queue canonical_registry/stage_c/data/v2/native_queue.json
python -B -m canonical_registry.stage_c.evaluation.live_records
python -B -m canonical_registry.stage_c.run --v2 --run stage-c-v2-replay --create --replay-count 2
python -B -m canonical_registry.stage_c.evaluation.verify --run stage-c-v2-replay
python -B -m canonical_registry.stage_c.evaluation.benchmark optimized-repeat
```

The paired baseline profile was captured before the optimization, on the same frozen inputs. The source cohort and acquisition queue are retained with the SQL and evidence receipts. Larger controlled runs need independent review of source bindings and a sustained, I/O-isolated performance assessment before inventory-wide execution. [Frozen cohort manifest](stage_c/data/v2/freeze.json), [public accession queue](stage_c/data/v2/native_queue.json).

`STAGE_C_V2_CONDITIONAL`
