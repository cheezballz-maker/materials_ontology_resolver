# Exact-form evidence acquisition

`evidence_retrieval.py` is an acquisition layer around the existing resolver. It contains no source indices, chemical exception dictionary or validation-set lookup. `policy.py`, `form_characterizer.py`, `identity_comparator.py`, `chemistry.py`, the ontology and the five-table schema are unchanged.

The public `Resolver.resolve` outcomes remain EXACT / NO_MATCH / UNRESOLVED. Its `analysis` contains internal admission/conflict diagnostics; NO_MATCH never allocates an ID. `Resolver.evaluate` accepts the existing name, aliases, optional typed structure and explicit source assertions, plus `identifiers=[{"identifier_type": "CASRegistryNumber", "identifier_value": "141-78-6"}]`. Identifiers remain claims/retrieval keys. Only supported typed formats are accepted; CAS/EC check digits are checked, and source InChI/InChIKey disagreement with a candidate blocks resolution. CAS/EC values used for lookup are not automatically promoted into the registry.

## Retrieval and assertion

1. Preserve the original preferred name and original aliases. Reject visibly incomplete delimiters rather than reconstructing a name. Existing source scope, OPSIN warnings and form-eligibility gates remain in place.
2. Retrieve the exact original name and supplied typed identifiers. Validate all returned structures and supplied InChI/InChIKeys. An original-claim disagreement is retained and evaluated by the existing policy; no provider wins.
3. When evidence is insufficient for an otherwise admissible hypothesis, search by its regenerated full InChIKey, full preserved SMILES and InChI. A validated provider IUPAC name may support another bounded lookup. No parent, charge, tautomer, isotope, salt or stereo transformation generates a retrieval key.
4. Compare every returned graph with the hypothesis. Discovery-only related/unknown forms stay in audit diagnostics and cannot corroborate. A shared Standard InChIKey cannot erase a fixed-tautomer difference. Malformed or internally inconsistent provider structure/identifier assertions are not repaired. Incomplete bounded result sets remain uncertainty.
5. If the original name did not parse, an original source alias can provide local nomenclature evidence only after warning-free OPSIN parsing, exact graph agreement, eligibility under its own name and a separate successful external exact-alias lookup. The primary preferred-name form gate still applies. A provider-generated name is never independent local source evidence. A failed or conflicting alias is held back without replacing the primary referent.
6. Apply the unchanged official-InChI, form-characterization, dimension-comparison and admission policy. Alias promotion still requires individual validation. Registry allocation is separate.

## Implemented providers

| Provider | Retrieval modes | Scope and limitations |
|---|---|---|
| OPSIN | Original name and original alias claims | Warning-free candidate generation only; failed/ambiguous parses are preserved. No generated name is treated as independent source evidence. |
| RDKit / MolStandardize / reference InChI | Existing local validation and diagnostic views | Same modules and identity semantics; no parent view is a retrieval/merge key. |
| PubChem | Name, CID, full InChIKey, InChI, complete SMILES identity search, CAS/EC name lookups | Identity search requests stereo/isotope preservation, but all returned full graphs are locally compared. Standardized provider identity is not the project definition. |
| ChEBI | Exact name, ChEBI ID, full InChIKey, InChI, CAS/EC search | Only released three-star discrete full records contribute. Identifier searches need not match the original name; related records remain candidates. No relaxation of curation or wildcard exclusions. |
| GSRS (NCATS public deployment) | Exact original name, UNII, CAS, complete structure | Only approved PRIMARY/COMPLETE chemical records, supported stereo scope, internally consistent full molfile/SMILES/InChI/key and matching positive integer moiety ratios. No mixture/protein/polymer construction or fractional-ratio assembly. Raw records and structure references retained. |

GSRS is the single additional provider. Its reusable structured chemical records, named-form registrations, complete structures and explicit moieties fit this increment better than adding general web search or supplier-page scraping. NIST and supplier adapters were not added. The GSRS adapter does not broaden supported coordination or hydrate/solvate modeling; an otherwise coherent GSRS candidate may still fail the existing form gate.

## Provenance and dependency

Every acquisition result records provider, record ID, exact query/key type and origin, URL, retrieval time, raw response/cache and returned identity fields. Repeated queries for the same record and structure are deduplicated; conflicting structures from one record remain visible. FDA/NCATS GSRS mirrors share a family; known upstream references join lineages.

Unknown aggregate lineage is explicitly UNDETERMINED. PubChem plus a copied record is not two independent votes. For external-only recovery, two provider names alone no longer establish independence: two documented nondependent lineages are required. The current public adapters retain references but do not claim independently proved experimental provenance, so external-only candidates without validated local source nomenclature can remain unresolved. This conservative provenance check changes evidence sufficiency, not chemical equivalence. It may withhold previously admitted external-only cases and must be reported in evaluation.

All evidence and related-form diagnostics remain within the existing temporary candidate JSON. No permanent evidence/relationship schema is introduced. Validated GSRS UNII values use the existing generic identifier table; no SUB ID is derived from a UNII.

## Bounds, failures and replay

Every HTTP request has a 15-second timeout, pacing, request budget and cached success/failure envelope. Offline mode never requests the network. PubChem structure discovery requests at most nine IDs and refuses a set exceeding eight; ChEBI examines at most eight records; GSRS examines at most four. Per referent there are at most 16 query operations, with at most three structurally matching source-alias recovery lookups among the first 64 aliases. All original aliases remain preserved and individually considered for promotion. Budget exhaustion or unavailable corroboration cannot allocate a Substance.

The development run under `evidence_upgrade/run` copies original name-query caches to control baseline evidence and stores new retrievals separately. Reuse those caches offline in a new output directory for reproducibility; never overwrite the frozen holdout or existing registries. `verify.py` replays the acquired evidence classification and validates any original-alias local support. No unit-test or frozen-reference fixture is imported by resolution.

Documentation and protocol checks: [GSRS API](https://gsrs.ncats.nih.gov/api-documentation), [ChEBI public tools](https://www.ebi.ac.uk/chebi/tools), [ChEBI API schema](https://www.ebi.ac.uk/chebi/backend/api/schema/), [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest). Actual API smoke responses are preserved under `evidence_upgrade/provider_smoke/`; no interface behavior is accepted solely from these links.
