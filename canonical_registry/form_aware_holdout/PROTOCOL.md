# Fresh form-aware holdout protocol

Evaluation only. Resolver, admission/provider code, tests, schema, ontology, original registries and previous reference labels are protected by hashes. All new files remain inside this holdout directory except the final report.

## Sampling and blindness

360 original CUMA records were selected with seed 2026102702 from the source workbook, using lexical source-name/alias strata. No resolver prediction, diagnostic or parser-result table was read for selection. All previous 300 record indices, recorded development examples, exact name/alias overlaps with that set, and known test/framework examples were excluded. `steward/exclusions.json` records the conservative exclusion set; `SAMPLE_FROZEN.json` records the workbook, script, selection, packet hashes, indices and timestamp.

The sample is deliberately enriched for chemical-form capability testing, not prevalence estimation. Lexical strata are candidate categories, not chemical truth. In particular, “ethanolate” may name an alkoxide rather than an ethanol solvate. All 33 eligible solvate-keyword candidates were included, with the quota shortfall reassigned to hydrates/ordinary names by the frozen algorithm. Adjudicators determine actual form semantics independently; the report must distinguish candidate-solvate strata from evidenced solvates.

Three fresh agents with no inherited conversation history each receive 120 shuffled records and the authoritative framework. Their project access is procedurally restricted to their own packet, containing only original index/name/aliases and the framework. They may independently retrieve external evidence and use bare RDKit. They receive no strata, prior results, resolver logic, expected failure modes or predictions. The shared filesystem is not an OS access-control barrier; blindness is enforced through scoped instructions and by not running predictions until every reference is frozen.

Each reference must include a status, reason, evidence, applicable form dimensions and judgments for every original alias occurrence. EXACT requires a validated preserved molecular structure, regenerated full InChIKey and coherent support beyond a single database hit. Shared upstream evidence must be acknowledged. UNRESOLVED must distinguish insufficient evidence from established intrinsic ambiguity. References and supporting methodology are frozen and hashed before any resolver run. No reference revision after unblinding is permitted.

## Fixed evaluation execution

After all three reference freezes and structural/schema QA pass, prepare a new candidate workspace from the frozen original inputs and run the unchanged `pipeline.py build` once. Empty HTTP caches prevent reference retrievals from becoming engine evidence. Budgets: at most 1,800 PubChem and 3,000 ChEBI requests, including alias/full-record lookups. No retry/cache deletion, policy tuning or code patching is allowed during this evaluation. The default reviewed evidence fixture is unchanged; its known record/name examples were excluded. Existing production registry is read only for ID reuse. Holdout-generated IDs are confined to a new evaluation registry, not deployed.

## Prespecified scoring

- EXACT precision: correct admitted graphs divided by adjudicable admissions. Reference EXACT provides a graph check; confirmed CONFLICT/OUT_OF_SCOPE/INVALID or documented intrinsic ambiguity provides evidence of inappropriate admission. Reference UNRESOLVED from insufficient evidence remains unverified, never automatically an error. Report all denominators and unverified counts.
- Exact graph equivalence in scoring uses standalone strict RDKit graphs and ordinary resonance representations, preserving H placement, stereo, isotopes, charges and every component. No import of resolver comparison/policy code and no key-only matching.
- Correct EXACT recall: correct admissions divided by all reference EXACT records.
- False merges: differing reference EXACT graphs assigned one ID, divided by assessable coassigned pairs; unassessable pairs reported separately.
- Abstention: all non-EXACT predictions / total, with internal UNRESOLVED separately. Correct-abstention precision: justified non-admissions / assessable non-admissions (reference EXACT losses are incorrect abstentions; insufficient-evidence references are unassessed). Also report abstention recall over references establishing a non-admissible referent.
- Alias precision: verified-correct promoted source alias occurrences / assessable promoted occurrences. SAME needs exact subject agreement and reference source support; DIFFERENT with a correct subject is wrong. Unverified subject/alias evidence remains unassessed. Preferred names stored as aliases are excluded from the promotion metric.
- Five-status agreement: identical expected/predicted statuses / all records, not a chemical-precision substitute.
- Report strata separately using frozen nonexclusive lexical tags and, separately, adjudicated actual form categories. No population weighting or whole-CUMA extrapolation.

After scoring, classify every status/structure/alias disagreement as unsafe admission, conservative abstention, form distinction, merge error, evidence limitation or unresolved comparison, with a likely causal category. Rank gaps using holdout frequency, reference-confirmed identities lost, safety risk, deterministic feasibility and cross-source usefulness. Choose one primary recommendation only after inspecting scored results; do not patch it in this task.
