# Implemented form-aware identity policy

Authority: `C:\Users\IT PatsnapSG\Downloads\Molecular_Substance_Identity_Framework_v1.md`. Substance Ontology 0.2.0 and the five-table schema are unchanged. Historical reports describe the earlier bounded policy.

Supported referents are sufficiently specified discrete molecules and defined molecular salts/hydrates/solvates. Stereo, isotopes/positions, charge/protonation, electronic state, tautomeric hydrogen/bond placement and all components/multiplicities are preserved. Unspecified or partial stereo is not a wildcard. Advanced stereo, radicals, unsupported coordination/elements, mixtures, co-crystals and extended solids remain held or excluded.

`form_characterizer.py` separates graph features from source intent. Original input and validated graph remain intact. Explicit typed source assertions may specify form kind and component/solvent counts; provider hits cannot manufacture them. Ionic salts require retained positive/negative components and charge-balanced supported composition. Neutral base-plus-acid depictions are held, never automatically proton-transferred. Fixed hydrate/solvate stoichiometry must agree with the graph.

`identity_comparator.py` returns EQUIVALENT, DIFFERENT, UNKNOWN or NOT_APPLICABLE for connectivity, stereo, isotopes, protonation/charge, electronic state, tautomeric form, components and stoichiometry. EXACT requires a shared validated resonance representation and supported equivalence for every applicable dimension. Traversal, Kekule/aromatic and supported resonance differences can be equivalent. Any significant DIFFERENT or UNKNOWN prevents EXACT. Standard InChIKey, formula, aliases and standardized parents never suffice as merge keys. MolStandardize and Fixed-H InChI remain comparison diagnostics.

| Evidence/state | Internal decision/reason |
|---|---|
| Missing name, malformed source input or invalid typed structure | INVALID |
| Excluded material family | OUT_OF_SCOPE / EXCLUDED_MATERIAL_FAMILY |
| OPSIN warning | UNRESOLVED / NAME_PARSER_WARNING_REQUIRES_REVIEW |
| Insufficient/unsupported form | UNRESOLVED / specific form reason codes |
| Provider identifiers contradict its graph | CONFLICT / PROVIDER_IDENTIFIER_CONFLICT |
| Invalid purported molecular provider graph | CONFLICT / PROVIDER_STRUCTURE_INVALID |
| Conflicting preserved tautomers | CONFLICT / TAUTOMER_CONFLICT |
| Other identity contradiction | CONFLICT / IDENTITY_DIMENSION_CONFLICT |
| Unknown comparison dimension | UNRESOLVED / IDENTITY_DIMENSION_UNKNOWN |
| Reference InChI/key not confirmed | UNRESOLVED / OFFICIAL_INCHI_NOT_CONFIRMED |
| Missing/incomplete corroboration | UNRESOLVED / external-evidence reason |
| Sufficient form, local/official validation and coherent corroboration | AUTO_ACCEPT / ALL_APPLICABLE_DIMENSIONS_CORROBORATED |

Warning-free OPSIN or an explicit typed structure generates a candidate; at least one coherent external molecular record is required. All retrieved applicable records are compared. External generation after local failure requires both PubChem and ChEBI molecular evidence. Ordinary reference-InChI proton adjustment warnings can pass only if regenerated Standard InChI and key agree; unresolved stereo/valence warnings are held. Toolkit ancestry is not independent chemical evidence.

ChEBI uses bounded search, released three-star full records and exact preferred-name/alias attestation. Wildcard residues/classes remain in retrieval diagnostics but are excluded from discrete-molecule evidence. Search truncation is recorded without claiming exhaustive coverage; failed full-record retrieval blocks acceptance. PubChem/ChEBI may share upstream sources. Reviewed contradictory structures are veto-only evidence, never positive corroboration.

Names receive NFC/whitespace normalization with originals retained. Structures use strict typed parsing without name normalization or trailing text. An alias needs its own warning-free OPSIN interpretation, sufficient form specification, exact comparison, and a qualifying ChEBI name attestation or separately validated PubChem lookup. Conflicting/unsupported aliases are held independently; provider alias lists are not bulk imported.

The public `Resolver.resolve` returns EXACT, NO_MATCH or UNRESOLVED. NO_MATCH permits consideration of a sufficiently evidenced new identity but never allocates an ID. CUMA persistence retains EXACT/UNRESOLVED/CONFLICT/OUT_OF_SCOPE/INVALID. Internal AUTO_ACCEPT becomes persisted EXACT only after successful clustering/allocation.

Clustering uses all-to-all exact comparisons, not transitive ambiguous edges. Existing IDs are reused by exact structural comparison; new SUB_######## values start above the base registry maximum. Ambiguous existing identities block admission. Snapshots are fresh and the base registry read only. Preferred name is the shortest accepted CUMA preferred name, then lexical order/index; display selection is not evidence.

The graph, comparison, policy and resolver modules contain no CUMA indices. CUMA ingestion/persistence remains in its adapter. No universal parent, ontology relationships or permanent evidence tables are introduced.
