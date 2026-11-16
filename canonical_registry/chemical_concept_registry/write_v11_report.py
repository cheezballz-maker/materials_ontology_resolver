"""Render the bounded v1.1 evaluation report from saved experiment results."""
import json,statistics
from collections import Counter
from pathlib import Path
H=Path(__file__).resolve().parent
d=json.loads((H/'evaluation_v11.json').read_text(encoding='utf8'));rows=d['records']
b=json.loads((H/'comparison_benchmark_v11.json').read_text(encoding='utf8'))
prior=Counter(x['v1_capability'] for x in rows if x['outcome']=='CHEMICAL_CONCEPT_CREATED')
reasons=Counter('; '.join(x['diagnostics']) for x in rows if x['diagnostics'])
examples=[x for x in rows if x['outcome']=='CHEMICAL_CONCEPT_CREATED' and x['v1_capability']=='UNSUPPORTED_MOLECULAR_SCOPE'][:5]
example_lines='\n'.join('| `{}` | {} | {} | `{}` |'.format(x['source_id'],', '.join(x['elements']),x['stratum'],x['outcome']) for x in examples)
reason_lines='\n'.join('| `{}` | {} |'.format(k,v) for k,v in reasons.most_common())
report=f'''# Chemical Concept Registry v1.1

## Executive conclusion

The disposable POC now accepts a validated molecular graph with genuinely unassigned ordinary stereochemistry without requiring a declaration of the original author's intent. It supports a bounded expansion beyond CHNO and routes exact inputs through the existing Substance matcher. It is **partial**: the bounded real-record run created 19 concepts but produced no exact Substance matches, the name/structure qualification path remains conservative, and no independent expert has confirmed the new warehouse interpretations. Fixture success does not authorize production writes.

## Molecular admission and comparison

The representation state is `UNASSIGNED_IN_REPRESENTATION`; this records an open constraint, not a racemate, physical mixture, or source intention. `UNKNOWN`, `CONFLICT` and unsupported states remain distinct. Strict existing RDKit parsing, sanitization and InChI generation are reused. A single neutral closed-shell graph with supported ordinary tetrahedral/carbon-double-bond stereo and at least one truly unassigned stereogenic feature may qualify. Existing specified stereo is preserved. Name and multiple supplied graph claims are compared using the existing nine-dimension and stereo comparison functions. If a more specific compatible assertion can be established through complete bounded isomer-set containment, it is selected; conflicts and unproved overlaps are withheld. A name-only OPSIN result is not sufficient for admission.

Reuse continues to compare the proposal with every stored fixture concept under `BEGIN IMMEDIATE`. Equivalent meanings reuse one ID; unresolved comparisons withhold creation. Known opposing configurations, constitution, and other differing dimensions cannot be merged. The prior 64-stereoisomer ceiling remains: existing graph/isomorphism comparison alone has not been validated as a complete replacement for bounded set containment in all symmetry and partial-stereo cases. Stereoisomers are comparison views, not evidence of actual constituent materials.

## Molecular scope and remaining boundaries

Before: neutral, closed-shell single-component CHNO, explicit open-stereo declaration, ordinary stereo and <=64 generated isomers. After: the same feature boundaries plus F, Cl, Br, I, S, P, Si and B, with ordinary carbon-centred tetrahedral and carbon-carbon double-bond stereo only. The structural checks additionally reject noncovalent/dative bond types, non-carbon stereocentres, stereo groups, charged atoms, radicals, isotopes, multicomponent graphs, unsupported elements and material warnings. Valence and standard/fixed-H InChI use the existing toolchain. Neutral element membership is not blanket approval for coordination complexes or all chemistry of an element. Fully specified chemistry is routed toward the Substance resolver rather than being forced into a broader concept.

`v11_regression_corpus.json` and `test_v11.py` provide synthetic supported examples for each newly admitted element and rejected counterparts with unsupported components, as well as charge, isotope, metal/coordination, malformed-text, specified stereo, and enumeration-limit cases. The retained tests cover conflicting R/S, E/Z, alternate traversal, open versus partially specified stereo, unknown states, concurrent creation, rollback and incomplete-comparison withholding. No claim is made that sulfur, phosphorus, silicon or boron stereochemistry beyond the explicitly bounded ordinary-carbon scope is supported.

## Unified workflow and safety

`unified_chemical.py` is the single POC entry point for typed structures plus optional names and qualified source adapters. `resolve_v11.py` supplies a small CLI. It delegates name interpretation to the existing OPSIN bridge, exact matching and admission to `SubstanceResolver`, and concept comparison and transactional creation to the existing registry. Family access is limited to existing fixed family keys. Missing/failed name interpretation, source-claim inconsistencies and incompatible graphs do not silently select a claim. A more specific name can narrow an unassigned representation only when bounded graph/isomer comparison establishes compatibility; exact matching additionally requires the adapter's qualified exact graph to match the chosen interpretation. The current exact route may therefore abstain where name-derived specificity has not been qualified by the existing adapter.

Outcomes are `EXACT_SUBSTANCE_MATCH`, `EXACT_SUBSTANCE_NOT_IN_REGISTRY`, `CHEMICAL_CONCEPT_CREATED`, `CHEMICAL_CONCEPT_REUSED`, `CONFLICT` and `UNRESOLVED`. Substance creation is disabled; `EXACT_SUBSTANCE_CREATED` is never claimed. A no-match requires the existing matcher to report a complete snapshot search and admission eligibility. An incomplete or bounded search returns unresolved. Results include interpretation, open stereo, evidence, blockers, version, snapshot where available, timing and comparison counts. Labels are concept labels only; no Substance aliases are promoted. Source metadata never becomes a canonical ID.

Concept writes use newly initialized, marked fixtures only. Existing serialized transactions, complete comparisons, idempotency keys, request hashes, events, rollback and unique IDs are retained. New event evidence records the source record key, parsed claims and request key; a changed evidence payload cannot silently reuse an idempotency key. A result's concept-registry digest is a post-operation observation, not a cross-database atomic snapshot. The existing resolver can reuse a `RegistrySnapshot`; each matcher still verifies its digest before and after use. This is a performance change to the existing read-only path, not a chemical comparator. There is no cross-database atomicity claim. The original ontology, canonical seed, pilot and concept fixture hashes match before and after the real run (`evaluation_v11.json`); no production record, Substance, or source association was changed.

## Real-record evaluation

The deterministic selection (`v11-eval-20261104`) covers {d['cohort_size']} unique records from the frozen 200-record feasibility cohort, not new warehouse sampling. It included 10 earlier-supported open graphs, 10 F, 6 Cl/Br/I, 8 S, 5 P/Si/B, 8 earlier exact admissions, 4 known-conflict cases, 5 multicomponent cases, 2 previously over-budget graphs and 7 other abstentions. Categories are priority selection strata, not mutually exclusive chemistry. Shortfalls: {json.dumps({k:v for k,v in d['shortfalls'].items() if v})}. Names and all provided primary structure fields were interpreted against the available claims. The full per-record old v1 capability, prior pilot outcome, new decision, evidence, diagnostic, comparisons and timing are in `evaluation_v11.json`.

| Outcome | Count |
|---|---:|
| ChemicalConcept created in disposable fixture | {d['outcomes'].get('CHEMICAL_CONCEPT_CREATED',0)} |
| ChemicalConcept reused | {d['outcomes'].get('CHEMICAL_CONCEPT_REUSED',0)} |
| Exact Substance match / created / complete no-match | 0 / 0 / 0 |
| Unresolved | {d['outcomes'].get('UNRESOLVED',0)} |
| Conflict | {d['outcomes'].get('CONFLICT',0)} |

Of the created records, {prior.get('REPRESENTATION_SUPPORTED_ASSUMING_EXPLICIT_OPEN_STEREO',0)} had passed the v1 hypothetical representation screen and {prior.get('UNSUPPORTED_MOLECULAR_SCOPE',0)} had been rejected by that screen. Real examples of expanded-scope routed concepts:

| Warehouse source ID | Elements | Selection stratum | POC outcome |
|---|---|---|---|
{example_lines}

These are automated interpretations based on supplied claims, not independently adjudicated accuracy or source-ground-truth certification. The earlier v1 screen assumed explicit-open stereo and did not perform the v1.1 source/name reconciliation; its screen results are not equivalent to old production admissions. The real run used the frozen 560-identity pilot and capped exact retrieval at eight candidates, so no incomplete search was converted into a no-match. The run is purposive and does not measure warehouse-wide coverage. No exact-match or reuse claims are inferred merely from earlier pilot ancestry.

| Remaining diagnostic | Count |
|---|---:|
{reason_lines}

## Controlled validation and performance

Synthetic controls exercise real marked-fixture transactions: `CC(O)F` and `FC(O)C` create and then reuse one concept, repeated request keys replay without a new ID, disjoint R/S restrictions remain distinct, broader open stereo stays separate, and incomplete comparisons block new IDs. The retained fixture tests cover concurrent identical requests and rollback. Synthetic existing-registry controls use the actual Substance matcher, admission and official validator to exercise an exact match, a complete no-match and an incomplete bounded search. A supplied input graph that differs from the qualified adapter graph is withheld. Tests are not independent real-world accuracy evidence.

The most recent combined run covered the concept registry, v1.1 controls, chemical resolution corrections and canonical matching: **44 passed, 99 subtests passed**. A subsequent focused rerun verifies the added bound-search and supported-element negative cases; see the accompanying test invocation results. Existing source and chemical safeguard suites are not all rerun for this milestone and prior evidence is not presented as a new pass.

For these {d['cohort_size']} records the median end-to-end time was {statistics.median(x['elapsed_seconds'] for x in rows):.3f} s and maximum {max(x['elapsed_seconds'] for x in rows):.3f} s. There were {sum(x['concept_comparisons'] for x in rows)} recorded concept comparisons and {sum(x['substance_comparisons'] for x in rows)} exact candidate comparisons. These times exclude the one-time loading of the pilot snapshot, which was reused. A separate synthetic two-isomer alternate-traversal pair took median {b['median_seconds']:.4f} s over {b['comparisons']} comparisons (`comparison_benchmark_v11.json`). These are small local observations, not scale guarantees.

## Limitations and next milestone

The implementation does not create exact Substances, support charged/isotopic open concepts, perform general mixture/family normalization, resolve every source-name syntax, or establish whether a parsed name and upstream record are independently correct. The <=64 enumeration ceiling remains, and the evaluated old and new cohorts are not independent expert controls. Broader stereochemical classes, organometallics, solid phases and multicomponent concept semantics remain unresolved. Add a frozen expert-reviewed, source-diverse holdout and extend source-evidence qualification for compatible more-specific names; benchmark safe comparison coverage and exact matching separately before considering production deployment or any identity-policy changes.

**CHEMICAL_CONCEPT_REGISTRY_V1_1_PARTIAL**
'''
(H.parent/'CHEMICAL_CONCEPT_REGISTRY_V1_1_REPORT.md').write_text(report,encoding='utf8')
print('wrote report')
