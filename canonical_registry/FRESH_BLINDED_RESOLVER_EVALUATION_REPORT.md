# Fresh blinded resolver evaluation

## Freeze, sample and reference

The unchanged resolver was [frozen](FRESH_BLINDED_EVALUATION_FREEZE.json) before source sampling; all 400 reference records were [frozen independently](fresh_blinded_evaluation/REFERENCE_FROZEN.json) before predictions. The CUMA source workbook had 53,667 numbered records; 4,794 were conservatively excluded based on known prior holdout/development IDs, historical cases, exact normalized name/alias overlap, test/report claims and obvious duplicate names. From the remaining 48,873, a simple random sample of **400** rows was selected without replacement using seed **2026102901**. The headline population is conditional on those exclusions, not all CUMA. No capability enrichment was used and sampled records were not replaced. The [sample and exclusion manifest](fresh_blinded_evaluation/SAMPLE_FROZEN.json) identifies the selection and hashes. A [source-only leakage check](fresh_blinded_evaluation/leakage_check.json) found zero overlaps with all three prior holdout packets and the listed historical cases. Exclusions rely on known artifacts and cannot prove every historical informal exposure was captured.

The sample contains 1273 original alias occurrences; 324 records have aliases and 250 have multiple aliases. There are 0 duplicate preferred-name groups and 0 malformed alias cells. Lexical indicators, not definitive chemistry classifications: {'stereo_notation': 40, 'salt_term': 18, 'hydrate_term': 1, 'isotope_term': 0, 'mixture_polymer_term': 1}. CTX_API_KEY configured: yes.

Three isolated adjudicators received source records and the identity framework without resolver outcomes. They used independent public lookups, cited sources and bare RDKit checks; no candidate from the resolver was supplied. References: {'EXACT_REFERENCE_AVAILABLE': 223, 'OUT_OF_SCOPE_REFERENCE': 10, 'UNADJUDICABLE': 167}. Unadjudicable reasons: {'LOOKUP_FAILED_NOT_ADJUDICATED': 11, 'inherently_underspecified': 9, 'source_conflict': 14, 'CANDIDATE_SCREENED_NOT_ADJUDICATED': 51, 'evidence_unavailable': 18, 'INHERENTLY_UNDERSPECIFIED': 21, 'CONFLICTING_EVIDENCE': 7, 'SOURCE_CONFLICT_OR_FORM_NOT_VERIFIED': 10, 'TAUTOMER_SCOPE_UNRESOLVED': 2, 'SOURCE_STEREOCHEMISTRY_UNSPECIFIED': 1, 'form_unresolved': 13, 'EVIDENCE_INSUFFICIENT': 9, 'SOURCE_STEREO_OR_ENSEMBLE_UNCLEAR': 1}. **51 packet-2 records received candidate screening but no completed individual source/form adjudication**; they remain unadjudicable and are not negative judgments. Other unadjudicable cases include conflicting sources, unestablished forms and unavailable evidence. [Frozen references](fresh_blinded_evaluation/reference_adjudication.json) and [packet methodologies](fresh_blinded_evaluation/packet_1/METHODOLOGY.md), [2](fresh_blinded_evaluation/packet_2/METHODOLOGY.md), [3](fresh_blinded_evaluation/packet_3/METHODOLOGY.md) contain per-case evidence and limitations. Some public services may share upstream data; two URLs do not prove independent experimental provenance. Selective adjudication means the sample's random selection does not make the adjudicable subset automatically representative.

The reference-freeze manifest hashes the labels, per-case evidence claims, source packet files and methodologies; the separately retained raw HTTP response caches were not included in that manifest.

A subsequent read-only audit of the frozen references, performed without inspecting individual predictions, identified source-form, tautomer or stereo-mapping cautions in 15 reference cases. A separate [blind check of retained lookup responses](fresh_blinded_evaluation/BLIND_SOURCE_AMBIGUITY_AUDIT.json) found a reference name query returning multiple distinct structures. The frozen labels were not changed. The other cautions are in [reference quality notes](fresh_blinded_evaluation/REFERENCE_QUALITY_NOTES.json); 0 flagged cases were admitted EXACT. The primary metrics retain the frozen labels and should be interpreted alongside those cautions.

## Primary metrics and abstentions

Automatic EXACT precision among independently adjudicable admissions: **6/6 = 100.0%**, with 0 assessed false positives and 2 unadjudicable EXACT outcomes excluded. The exact 95% Clopper–Pearson interval is **54.1%–100.0%**. The interval is conditional on the adjudicable subset and assumes binomial observations; it does not correct for selective missing reference labels, shared source ancestry, or provider budget exhaustion by processing order.

As a sensitivity check, excluding all admissions flagged in the blinded reference-quality audit gives 6/6 = 100.0%. This does not relabel the frozen references.

Automatic EXACT recall against reference-confirmed identities: **6/223 = 2.7%**. This is conditional on the available reference identities. Resolver statuses: {'UNRESOLVED': 387, 'EXACT': 8, 'CONFLICT': 2, 'OUT_OF_SCOPE': 3}; UNRESOLVED, CONFLICT and OUT_OF_SCOPE together are 392/400 = 98.0%. Of non-EXACT decisions, 217 had independently available preferred-name identities, 40 were consistent with a non-exact reference category, and 135 were unassessable. The withheld identities are recall misses, not necessarily incorrect policy decisions: a source alias can conflict with an otherwise identifiable preferred name. Among 2 CONFLICT holds with reference identities, an independently confirmed incompatible source alias was found in 1; the others require alias review. Accordingly, an overall count of unjustified abstentions cannot be established from this reference set. Category differences among UNRESOLVED/CONFLICT/OUT_OF_SCOPE are visible below.

Excluding the quality-audit-flagged reference cases gives recall 6/207 = 2.9%.

| Resolver outcome | Reference exact identity | Reference unresolved | Reference conflict/ambiguous | Reference out of scope | Unadjudicable |
|---|---:|---:|---:|---:|---:|
| EXACT | 6 | 0 | 0 | 0 | 2 |
| UNRESOLVED | 215 | 30 | 0 | 7 | 135 |
| CONFLICT | 2 | 0 | 0 | 0 | 0 |
| OUT_OF_SCOPE | 0 | 0 | 0 | 3 | 0 |
| INVALID | 0 | 0 | 0 | 0 | 0 |

Provider-only disagreement is **not** treated as proof the source claim is internally contradictory; those references remain unadjudicable. Inherently underspecified cases with explicit reviewer support are grouped as reference unresolved. [Per-record results](fresh_blinded_evaluation/resolver_results.json) preserve the original reference label and reason.

## Identity errors, false merges and withheld identities

No adjudicated false-positive EXACT was found; unadjudicable admissions were not counted as correct.

Unadjudicable EXACT decisions requiring independent follow-up:
- CUMA 4570 (4-octyl-N-phenylaniline): pubchem candidate has 1 component(s), total formal charge 0, and no RDKit-detected unassigned potential stereo. The two retrieved isomeric graphs agree after RDKit parsing. The source name and identity-defining form have not been independently corroborated; this is a candidate screen, not a completed adjudication or a finding of inherent ambiguity. [source](https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/4-octyl-N-phenylaniline/property/IsomericSMILES,InChIKey,IUPACName/JSON), [source](https://cactus.nci.nih.gov/chemical/structure/4-octyl-N-phenylaniline/smiles)
- CUMA 6634 (2-chloro-5-methylpyridin-3-amine): PubChem and NCI agree on a 2-chloro-5-methyl-3-aminopyridine graph, but the additional supplier page gives a SMILES corresponding to a different substituted arrangement. Independent source-specific correction is needed before an exact assignment. [source](https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/2-chloro-5-methylpyridin-3-amine/property/IsomericSMILES,InChIKey,IUPACName/JSON), [source](https://cactus.nci.nih.gov/chemical/structure/2-chloro-5-methylpyridin-3-amine/smiles), [source](https://cymitquimica.com/cas/34552-13-1/)

False merges: **0/0 assessable merged pairs**; 0 additional merged pairs were not assessable. The denominator is too small to estimate a meaningful false-merge rate.

Dominant blockers for reference-confirmed withheld identities: {'no qualifying external corroborator': 174, 'source interpretation incomplete': 9, 'parser failure or no validated candidate': 23, 'stereo mapping or specification unsupported': 7, 'component or hydration semantics unsupported': 2, 'evidence or source contradiction': 2}. Each withheld case and its original reason is in [error analysis](fresh_blinded_evaluation/error_analysis.json); these categories are diagnostic, not a proposal to tune the resolver. The requested element, carbon-free multicomponent, coordination and discrete-structure guard reason occurrences are {'UNSUPPORTED_ELEMENT_CAPABILITY': 12, 'UNSUPPORTED_MULTICOMPONENT_CAPABILITY': 6, 'UNSUPPORTED_COORDINATION_CAPABILITY': 2, 'UNSUPPORTED_DISCRETE_STRUCTURE_CAPABILITY': 1}; all unsupported reason occurrences are {'UNSUPPORTED_DISCRETE_STRUCTURE_CAPABILITY': 1, 'UNSUPPORTED_ELEMENT_CAPABILITY': 12, 'UNSUPPORTED_MULTICOMPONENT_CAPABILITY': 6, 'UNSUPPORTED_COORDINATION_CAPABILITY': 2}. A record can contain multiple reason codes.

## Source paths, aliases and providers

The sampled workbook supplies names and aliases, not typed source structures: typed-source count **0**, with no path-specific safety estimate. Among name-derived records, 224 had complete deterministic interpretations, 10 had a qualifying source-linked provider route, and 8 were admitted EXACT: 6 confirmed, 0 false, 2 unadjudicable. 214 complete interpretations were held for no qualifying corroborator. Each admission's provider, route, record, source dependence and comparison dimensions are retained in [evaluation metrics](fresh_blinded_evaluation/evaluation_metrics.json). No admitted name has only a candidate-derived identifier as corroboration. Qualifying routes with a provider-reported truncated search occurred in 0 admissions; truncation can conceal other records and should be considered when reviewing those routes.

Alias-decision counts: {'source_occurrences': 1273, 'subject_not_admitted': 1254, 'subject_admitted_decisions': 19, 'promoted': 1, 'unverified': 1}. Among promotions assessed against a matching reference subject, alias precision is 0/0 = not estimable; unverified promotions and subject-mismatch reviews are not counted as confirmed. The source-occurrence count includes held aliases on unadmitted subjects. Independent review recorded 17 preferred-name/alias exact-form mismatches, separately listed with evidence in the [metrics artifact](fresh_blinded_evaluation/evaluation_metrics.json); these need not imply a rejected preferred name.

Provider-route query counts are non-exclusive and not votes:

| Provider | CORROBORATES | CONTRADICTS | PROVIDER_RECORD_AMBIGUOUS | NON_DISCRIMINATING | NO_MATCH | UNAVAILABLE |
|---|---:|---:|---:|---:|---:|---:|
| PubChem | 5 | 0 | 0 | 104 | 0 | 804 |
| ChEBI | 1 | 0 | 0 | 27 | 30 | 518 |
| GSRS | 3 | 0 | 0 | 34 | 134 | 330 |
| CompTox | 1 | 0 | 0 | 9 | 0 | 316 |

Every EXACT admission and its source-linked evidence:

| CUMA index and source name | Admission basis | Provider / route / record | Source dependence | Identity dimensions compared |
|---|---|---|---|---|
| 1116 3-aminooxazolidin-2-one | complete name + CORROBORATES | CompTox / name (source_preferred_name) / DTXSID00229996 | SOURCE_DEPENDENCE_UNKNOWN | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 4570 4-octyl-N-phenylaniline | complete name + CORROBORATES | PubChem / name (source_preferred_name) / 61335 | SOURCE_DEPENDENCE_UNKNOWN | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 6634 2-chloro-5-methylpyridin-3-amine | complete name + CORROBORATES | PubChem / name (source_preferred_name) / 2734422 | SOURCE_DEPENDENCE_UNKNOWN | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 8546 methyl 2,6-dichloro-4-fluorobenzoate | complete name + CORROBORATES | PubChem / name (source_preferred_name) / 54177775 | SOURCE_DEPENDENCE_UNKNOWN | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 9104 2-ethenylbenzaldehyde | complete name + CORROBORATES | PubChem / name (source_preferred_name) / 39391 | SOURCE_DEPENDENCE_UNKNOWN | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 9356 [4-(difluoromethoxy)phenyl]boronic acid | complete name + CORROBORATES | PubChem / name (source_preferred_name) / 23082146 | SOURCE_DEPENDENCE_UNKNOWN | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 11426 3,6,9,12,15,18,21,24-octaoxahexacosane-1,26-diol | complete name + CORROBORATES | ChEBI / name (source_preferred_name) / CHEBI:39784 | SOURCE_DEPENDENCE_UNKNOWN | connectivity, electronic_state, protonation_charge, tautomeric_form |
| 17165 Benzoyl chloride, 2-fluoro-4-nitro- | complete name + CORROBORATES | GSRS / name (source_preferred_name) / 066af66b-429a-4f5d-9ef0-3f61e6bfe1d8 | SOURCE_DEPENDENCE_UNKNOWN | connectivity, electronic_state, protonation_charge, tautomeric_form |

No `PROVIDER_RECORD_AMBIGUOUS` route was observed in this run.

The resolver used the frozen production adapters with initially empty caches and the default budgets: PubChem 120, ChEBI 500, GSRS 200 and CompTox 20. Records are processed by CUMA index, so exhaustion and availability can differ by position; this is a limitation of this run, not a statement about chemistry. Requests used: PubChem 120, ChEBI 500, GSRS 200, CompTox 20. `UNAVAILABLE` is neutral. [Route audit](fresh_blinded_evaluation/provider_route_audit.json) includes query origin, record IDs and states.

## Registry integrity, historical checks and disposition

Registry verification: **PASS**, 8 canonical graphs and 8 exact reconciliations revalidated. Duplicate/orphan counts: {'duplicate_substance_identity': 0, 'duplicate_substance_alias': 0, 'duplicate_substance_identifier': 0, 'duplicate_substance_reconciliation': 0, 'orphan_substance_alias': 0, 'orphan_substance_identifier': 0, 'orphan_substance_structure': 0, 'orphan_substance_reconciliation': 0}. Integrity does not establish chemical precision. [Verification](fresh_blinded_evaluation/run/verification.json).

The [post-run integrity check](fresh_blinded_evaluation/integrity_check.json) confirms the implementation, contract, sample and frozen reference hashes match, and the prior registry and candidate snapshot remain unchanged. The key itself is not included in the report or artifacts.

Five historical safety cases were rerun offline outside the fresh sample: [(5997, 'UNRESOLVED'), (23839, 'UNRESOLVED'), (30142, 'UNRESOLVED'), (5684, 'UNRESOLVED'), (5, 'UNRESOLVED')]. They are not included in headline metrics. [Details](fresh_blinded_evaluation/historical_regressions.json).

Continue research and plan a further independent, larger and more completely adjudicated validation. The incomplete/non-random adjudication, possible shared chemistry-source ancestry, finite query budget and any small admission or merged-pair denominators limit conclusions. This holdout does not establish production-scale readiness or broad controlled-use safety on its own. The element, coordination and carbon-free multicomponent guards remain technical debt and were not modified.

| Use | Disposition |
|---|---|
| Continued research development | Suitable with the reported findings and a separate remediation process if needed. |
| Fresh larger-scale validation | Possible after addressing reference-coverage and availability limitations. |
| Limited controlled use | Not established by this single, incompletely adjudicated holdout. |
| Production-scale canonicalization | Not established. |

FRESH_BLINDED_EVALUATION_MIXED
