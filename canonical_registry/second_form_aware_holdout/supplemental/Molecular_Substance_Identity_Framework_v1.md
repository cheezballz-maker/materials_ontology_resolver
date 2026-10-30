# Molecular Substance Identity and Chemical-Form Resolution Framework

**Materials Ontology — Discussion Consolidation (Version 1.0)**  
**Date:** 27 October 2026  
**Status:** Working policy report; ontology unchanged  
**Scope:** Canonical molecular and defined multicomponent chemical identities, their relationships, and source-independent resolution across CUMA, CosIng, and future datasets.

## Executive summary

The CUMA proof of concept demonstrates that the molecular resolver can avoid major overmerging failures, including formula-based matches, salt-parent collapse, stereochemical loss, malformed SMILES acceptance, and inconsistent structure/InChI matching. Its remaining limitation is a deliberately narrow **admission policy**: it abstains on many legitimate and well-defined chemical forms rather than assigning them distinct canonical Substance identities.

**Decisions settled in this discussion**

1. A canonical `Substance` (`SUB_########`) must denote a sufficiently defined chemical or material identity. **Broad or incompletely specified chemical referents do not receive their own `SUB_` IDs.**
2. Exact canonical identity, related but distinct identity, and representational equivalence are separate concepts. Names, formulae, source identifiers, and Standard InChIKeys are evidence, not unconditional identity definitions.
3. Chemically significant distinctions—where established by evidence—must be retained, including stereochemistry, isotopes, protonation, tautomeric specification, salt composition, hydration/solvation, and coordination.
4. There is **no universal parent Substance**. Peer, directional transformation, and constituent relationships require different semantics.
5. Search and resolution are different operations. An ambiguous query such as *glutamic acid* may retrieve both L- and D-glutamic acid, but the resolver may assert `EXACT` only when evidence establishes a unique identity. Related salts appear in a separate search tier.
6. Do **not modify the ontology now**. Empirically validate form recognition, admission, and relationships first; promote only useful, chemically defensible relationships.
7. For an intentionally collective referent, use the specification label **`ENSEMBLE`**, replacing “variable by definition.” `ENSEMBLE` is descriptive, not permission to admit a broad mixture as a molecular Substance.

**Main recommendation.** Extend the existing source-independent molecular core with a form-aware characterization and comparison contract, followed by strict admission and optional relationship assertion. Preserve the current CUMA adapter, RDKit, MolStandardize diagnostic views, official InChI, OPSIN, PubChem corroboration, and five-table registry unless evidence demonstrates a need for change.

## 1. Existing ontology and boundaries

Inspection of `substance_ontology.ttl` (ontology version 0.2.0) confirms:

- `Substance` is a reusable, application- and source-independent material identity with a stable `canonicalIdentifier`.
- `MolecularSubstance` is a subclass of `Substance` for identities primarily represented by a discrete chemically bonded molecular structure.
- `CosmeticsIngredientConcept` is a source/domain-facing ingredient concept, distinct from `Substance`.
- `Alias`, `Identifier`, and `Structure` have **validated identity** semantics; a related name or structure does not automatically qualify as an exact alias or accepted structure.
- Existing comments explicitly caution against collapsing chemically meaningful forms, and against treating alternative SMILES traversals, Kekulé/resonance depictions, or ordinary conformers as separate identities.
- No dedicated `tautomer_of`, `enantiomer_of`, `salt_form_of`, or related Substance-to-Substance properties currently exist.

Consequently, the next problem is predominantly **resolution policy**, not an absent ontology class hierarchy. The underlying ontology can remain unchanged during the next POC.

## 2. Identity semantics

### 2.1 Four distinct outcomes or notions

| Notion | Definition | Example | Consequence |
|---|---|---|---|
| Representational equivalence | Different serializations or depictions of the same established identity. | Two valid SMILES traversals of ethanol; equivalent Kekulé forms. | Same `SUB_` identity; no form relationship needed. |
| Exact canonical identity | Evidence establishes that two records refer to the same sufficiently defined Substance. | Two validated presentations of potassium acetate with the same ionic composition. | Reuse the existing `SUB_` ID. |
| Related, distinct identities | Two established Substance identities differ in an identity-defining feature but share a chemically characterized relationship. | L-glutamic acid and D-glutamic acid. | Separate `SUB_` IDs; possible relationship assertion. |
| Underspecified or conflicting referent | Evidence does not identify one exact Substance, or evidence is contradictory. | “Glutamic acid” without stereochemical clarification where required. | No new `SUB_` ID and no forced `EXACT`; preserve source concept and candidates. |

**Fundamental rule:** a tool-normalized match is not necessarily canonical identity. In particular, equality of molecular formula, parent structure, Standard InChI, or PubChem CID must not independently force `EXACT`.

### 2.2 Specification-state vocabulary

| State | Meaning | Example |
|---|---|---|
| `SPECIFIED` | An applicable identity feature is explicitly determined by trustworthy evidence. | The stereochemistry of L-glutamic acid. |
| `UNSPECIFIED` | An applicable identity feature remains unknown or ambiguous. | Glutamic acid without a stereochemical assignment. |
| `NOT_APPLICABLE` | The dimension has no meaningful bearing on the identity. | No tetrahedral stereocenter in ethanol. |
| `ENSEMBLE` | The referent intentionally describes more than one form collectively, rather than an unknown single form. | A stated racemate or expressly defined stereoisomer mixture. |

A form is **admissible only when every identity-defining ambiguity relevant to that chemical referent is resolved**. This does not mean that ordinary neutral, unlabeled ethanol requires every atom to be assigned an isotope: conventional isotope-unspecified chemical identity is an established reference scope, distinguishable from explicitly enriched or position-labelled forms. Likewise, an achiral molecule does not require irrelevant stereo descriptors.

An `ENSEMBLE` may be well described, but it should not be silently admitted as an **individual molecular** Substance. If the project later supports fully specified mixtures as canonical material identities, that requires a separately approved admission contract.

### 2.3 What identity must encode

Where applicable, the comparison must consider: constitutional connectivity; absolute, relative and partially specified stereochemistry; isotope mass and position; hydrogen/proton positions; charge and radical/electronic state; explicitly specified tautomer; ionic and neutral components and stoichiometry; coordination topology; and, separately, solid-state structure. Not every Substance requires every dimension.

## 3. Decision procedure for exact identity

**Stage A — Interpret the source referent.** Determine whether the record denotes a single defined chemical species, a defined chemical compound with multiple components, an ensemble/mixture, a solid-state form, or an ambiguous domain concept. Preserve the original name, structures, identifiers, evidence, and provenance.

**Stage B — Characterize the chemical form.** Parse validated candidate structures and independently record connected components, formal charges, radical electrons, isotope labels, stereogenic elements and assignments, tautomer-sensitive features, component coefficients, and coordination characteristics. Create normalized *diagnostic views*, never a destructively normalized replacement for the source evidence.

**Stage C — Apply the admissibility gate.** If essential chemical identity information is missing, contradictory, or outside validator scope, abstain. In particular, a broad name must not receive its own `SUB_` identity merely because it maps to several chemically specific candidates.

**Stage D — Retrieve candidates.** Use validated identifiers, stereo-/isotope-/tautomer-aware structure lookups, names, and safe chemical relationships. Candidate generation may be broad; assertion is strict.

**Stage E — Compare identity dimensions.** Each applicable dimension reports `EQUIVALENT`, `DIFFERENT`, or `UNKNOWN` (with `NOT_APPLICABLE` where suitable). `DIFFERENT` excludes `EXACT`; unresolved identity-significant `UNKNOWN` excludes `EXACT`; `EXACT` requires supported equivalence across all applicable dimensions.

**Stage F — Resolve or admit.** Reuse a canonical ID for `EXACT`. When no exact match exists, permit admission of a *new* `SUB_` only if the referent is independently sufficiently defined and all admission checks pass. Otherwise return `UNRESOLVED`. A proven mismatch against one candidate alone does not necessarily prove there is no exact match elsewhere in the registry.

**Stage G — Assert relationships optionally.** Evaluate chemically meaningful links between separately established identities, with specific evidence and qualifiers. Failure to classify a relationship must not invalidate an otherwise sound canonical identity.

The established external resolution statuses remain `EXACT`, `NO_MATCH`, and `UNRESOLVED`. `DISTINCT` is an *internal pairwise comparison assessment*, not a required new public status. `NO_MATCH` must not itself trigger admission without a separate sufficiency decision.

## 4. Chemical-form identity matrix

The table states the proposed default **molecular or composition-level** identity rule. Crystal structures and extended materials have additional constraints (Section 5).

| Category | When EXACT may be asserted | When separate IDs are required | Illustrative example / abstention trigger |
|---|---|---|---|
| Constitutional isomers | Validated graph equivalence, modulo representation-only aromaticity/resonance conventions. | Different constitutional connectivity. | Ethanol versus dimethyl ether: distinct; same C₂H₆O is insufficient. |
| Enantiomers and ordinary stereoisomers | Equivalent absolute configuration and all relevant stereochemical features. | Established opposite or otherwise different configuration. | L- versus D-glutamic acid: distinct; stereo-unspecified name: unresolved. |
| Diastereomers; E/Z | All defined configurations/geometries agree. | Different non-mirror configurations or opposite E/Z geometry. | (E)- versus (Z)-but-2-ene: distinct. |
| Partial / relative stereospecification | Unique specific identity has been established despite different representations of its specification. | A demonstrable configurational difference. | Unassigned stereocenter cannot be treated as a wildcard for exact matching. |
| Atropisomers | Same demonstrably configurationally meaningful axial form. | Stable atropisomers with different axial configurations. | Opposite BINOL atropisomers; rapid rotamers do not qualify. |
| Racemates and mixtures | Not in individual-molecule registry unless a separate defined-mixture policy exists. | Pure enantiomer is not the racemate. | “Racemic glutamic acid” is `ENSEMBLE`, not synonymous with L-glutamic acid. |
| Isotopologues | Same isotopic substitutions at symmetry-equivalent positions; remaining dimensions agree. | Different isotope masses or inequivalent labelled positions. | H₂O versus D₂O; ethanol-1-¹³C versus ethanol-2-¹³C. |
| Partly specified labels | Only if evidence uniquely establishes the exact labelling pattern. | Fully specified different labels. | “Monodeuterated ethanol” with no labelled site: unresolved for position-specific identity. |
| Protonation / zwitterions | Equivalent relevant proton, hydrogen, and electronic-state specification. | Distinct defined protonation sites, charge localization if chemically real, or radical states. | Acetic acid versus acetate; NH₃ versus NH₄⁺. |
| Resonance / formal-charge depiction | Depictions represent the same delocalized electronic species. | Demonstrably distinct species, not merely charge drawings. | Equivalent acetate resonance structures: EXACT. |
| Salts / counterions | Same identified ionic components, charge states, and stoichiometry. | Counterions, protonation or ratios differ. | Potassium acetate versus sodium acetate; 1:1 versus 2:1 salts. |
| Hydrates / solvates | Same compound, solvent components, established stoichiometry, and relevant state scope. | Anhydrous versus fixed hydrate; different solvent or hydration ratios. | Sodium acetate versus sodium acetate trihydrate; “hydrated salt” without number: unresolved. |
| Prototropic tautomers | Same intentionally specified hydrogen arrangement and bonding, with other dimensions equivalent. | Evidence establishes different, explicitly specified tautomers. | 2-pyridone versus 2-hydroxypyridine: separate identities when specifically identified; shared Standard InChI not decisive. |
| Molecular complexes / adducts | Same identified components, association/constitution, and ratios. | Different verified adducts or stoichiometries. | A defined 1:1 adduct versus arbitrary physical mixture. |
| Co-crystals / ion pairs | Same well-evidenced defined entity, including its structural/composition scope. | Different defined co-crystal/associated entities. | Caffeine–oxalic acid co-crystal versus physical blend: not EXACT. |
| Coordination entities | Same metal, ligands, coordination connectivity/geometry, electron state, and counterions as applicable. | Meaningful coordination geometry, ligand, or oxidation-state differences. | Cisplatin versus transplatin; ferrocene versus ferrocenium. |
| Coordination polymers / extended solids | Only under a separate sufficiently specified periodic-material identity model. | Different verified networks/phases under that model. | A discrete complex is not automatically the same as a coordination polymer. |
| Polymorphs / crystal phases | Same phase-specific periodic structure under defined tolerances, if form identities are modeled. | Different verified forms. | Rutile versus anatase TiO₂: distinct solid-state forms; do not identify from formula alone. |
| Ordinary conformers | Chemical identity unaffected by normal conformational flexibility. | Only a separately justified stable configuration/chemical state qualifies. | Chair conformations of cyclohexane: do not mint separate molecular IDs. |

### 4.1 Crucial chemical qualifications

**Stereochemistry.** Missing chiral tags or absence of an `@` symbol in SMILES do not prove that the molecule is achiral, racemic, or equivalent to a specific stereoisomer. Compare *potential* stereogenic elements with *assigned* configurations. Atropisomers and metal-centered geometrical stereoisomers need capabilities beyond routine tetrahedral matching.

**Isotopes.** Site-specific isotope substitution is identity-significant. Exchangeable isotopic hydrogen can be redistributed under experimental conditions, so software normalization or one measured label is not always sufficient to establish precise positional identity. Conventional unlabeled chemistry remains searchable and admissible at its normal chemical identity scope; it must not be equated to deliberately isotope-labelled records.

**Charge and protonation.** Real conjugate acids/bases, zwitterionic/prototropic arrangements and radicals can be distinct. Equivalent resonance contributors, by contrast, are not separate substances. A zwitterionic drawing does not alone justify splitting an existing canonical identity when it is merely representational shorthand; source intent and chemical evidence must establish the distinction.

**Salts and multicomponent forms.** Dot-disconnected SMILES is not a classification of the material as salt, co-crystal, ionic pair, adduct, or physical mixture. The canonical comparison needs constituent identities, ratio, bonding/association semantics where appropriate, and charge balance. Never replace a salt automatically with its neutral counterpart.

**Hydrates and solvates.** A fixed stoichiometric hydrate can differ in composition from its anhydrous form. A *crystalline solvate* also has a solid-state structural aspect, not merely a dot-separated molecular formula. Variable occupancy and unspecified solvation do not establish a single composition-level identity.

**Tautomers.** Standard InChI deliberately suppresses selected mobile-H distinctions; Fixed-H non-standard InChI can retain more positional information. A shared Standard InChI must therefore trigger a tautomer-sensitive check before `EXACT`. The RDKit canonical tautomer is an algorithmic normalization choice—not an assertion that a particular tautomer is predominant or uniquely intended.

**Solid-state chemistry.** Phase or polymorph identity should generally be addressed by a separate `MaterialForm`-like layer, not automatically treated as another small molecular graph. The eventual boundary between nonmolecular `Substance` and material-form identities needs its own modeling work. An unspecified formula cannot be assigned the ID of a particular crystal phase.

## 5. Relationship model: peers, transformations, and components

### 5.1 Three semantic families

1. **Peer relationships** connect distinct identities without a privileged parent: e.g., enantiomer, tautomer, isotopic variant. They are usually symmetric, may have multiple partners, and generally are **not transitive as pairwise relationships**.
2. **Directed chemical transformations or form relationships** express a specific orientation: e.g., conjugate acid of, hydrate of a defined unsolvated compound. They must not be interpreted as universal ancestry.
3. **Constituent relationships** describe a chemically defined whole through components and coefficients. These are preferably represented as typed component records rather than a simplistic `salt_form_of` link.

**Cardinality** describes permissible partners for a fully defined identity, not a claim that every partner already exists in the registry.

### 5.2 Candidate relationship assessment

| Candidate relationship | Symmetry / cardinality | Transitive? | Policy recommendation |
|---|---|---|---|
| `constitutional_isomer_of` | Symmetric; many-to-many | No | Diagnostic, not ontology now. |
| `stereoisomer_of` | Symmetric; many-to-many | No | Defer; generic family relation. |
| `enantiomer_of` | Symmetric; ordinarily one counterpart for fully specified chiral molecular identity | No | Strong eventual ontology candidate. |
| `diastereomer_of` | Symmetric; many-to-many | No | Defer; may be computed. |
| `stereo_specification_variant_of` | Not an identity-to-identity relation when one referent is unspecified | Not applicable | **Resolver diagnostic only**; do not assert between `SUB_` IDs. |
| `isotopologue_of` | Symmetric; many-to-many | No | Defer; only for established isotope identities. |
| `protonation_variant_of` | Broad symmetric family; many-to-many | No | Diagnostic; use conjugate acid/base when precise. |
| `charge_state_variant_of` | Ambiguous without constrained chemistry | Not defined | Diagnostic only. |
| `conjugate_acid_of` / `conjugate_base_of` | Directional inverse pair; potentially many-to-many | No | Strong eventual ontology candidate for validated one-proton relation. |
| `salt_form_of` | Directed when a specific neutral reference exists; potentially many-to-many | No | Defer; no universal or unique parent. |
| `hydrate_of` | Directional; potentially many-to-many | No | Defer; stoichiometric constituent data often stronger. |
| `solvate_of` | Directional; potentially many-to-many | No | Defer; include crystal-state caveat. |
| `tautomer_of` | Symmetric; many-to-many | No for direct pair assertions | Strong eventual ontology candidate. |
| `oxidation_state_variant_of` | Broad peer relation; many-to-many | No | Diagnostic until specific redox/coordination semantics exist. |
| `coordination_form_of` | Undefined without ligand/connectivity/geometry qualifiers | Not defined | Do not introduce generic ontology property. |
| `adduct_of` | Ambiguous binary relation to a multi-component whole | Not defined | Model components/association instead. |
| `multicomponent_form_of` | Ambiguous binary relation | Not defined | Model defined components and stoichiometry instead. |

A specific `enantiomer_of` assertion is symmetric but not transitive: A↔B does not imply that A is its own enantiomer. Broad family membership or connectedness may be transitive under *separate* semantics; do not conflate it with direct pairwise chemical relationships.

### 5.3 A minimal relationship data contract

Initially keep relationships in a registry-side **generic typed assertion layer**, not dedicated ontology properties:

```text
subject_substance_id
relation_type
object_substance_id
qualifiers (e.g., stoichiometry, transformation, comparison basis)
evidence/provenance
validation_status
policy_version
```

For a multicomponent salt, an n-ary statement is often preferable:

```text
Magnesium chloride
  component: Mg²⁺, coefficient 1
  component: Cl⁻,  coefficient 2
```

This is not a free-standing “parent” link. Its components and coefficients describe the defined composition. Chemical-bond structure or lattice structure may require additional information.

### 5.4 Relationship promotion rule

A relationship should enter the ontology only after (a) recurring real examples, (b) unambiguous semantics, (c) reliable assertion evidence, and (d) demonstrated retrieval or reasoning utility. Formal OWL characteristics—especially symmetry, domain/range, inverses, and transitivity—should be declared only when they are true for the selected definition. Do not create a property merely because RDKit can generate the relation.

## 6. Distinguishing forms in practice: software and reference data

| Resource | Role | Strongest categories | Critical limitation |
|---|---|---|---|
| **RDKit** | Parse and compare molecular graphs, fragments, charges, isotopes, standard stereo and selected atropisomerism. | Constitution, stereochemistry, isotopes, ionic components. | A valid depiction does not prove the record's intended identity; complex metals and condensed-phase chemistry need special treatment. |
| **RDKit MolStandardize** | Generate alternative parent, charge, and tautomeric comparison views. | Tautomers, salt/fragment comparisons, charge diagnostics. | **Never** silently replace the admitted chemical identity with a standardized parent. |
| **Official InChI** | Layered chemical identifier and interoperability check; optional Fixed-H and metal-reconnected modes. | Connectivity, stereo, isotope, selected tautomer/metal investigations. | Standard InChI intentionally collapses some tautomeric distinctions and suppresses metal reconnection. |
| **OPSIN** | Interpret supported systematic names as structures. | Chemical name-to-structure evidence. | A parsed structure is candidate evidence; ambiguous names and source conflicts remain. |
| **PubChem / PUG REST** | Retrieve reference structures, identifiers, synonyms and structurally related candidate sets. | Broad molecular and ionic candidate retrieval; alternate identity comparisons. | PubChem CID and similarity/identity search conventions do not define this project's canonical scope. |
| **ChEBI** | Curated chemical entities and documented specific ontology links. | Enantiomers, tautomers, conjugate acid/base; chemical role distinctions. | Source coverage and classification granularity vary. |
| **FDA GSRS** | Regulatory substance descriptions and structured non-simple-molecule examples. | Salts, defined substances, mixtures and complex chemical entries. | Regulatory substance concept may differ from a strict single chemical-identity policy. |
| **Crystallography Open Database (COD)** | Empirical crystallographic structures. | Polymorphs, co-crystals, coordination solids. | Structural evidence is not automatically the same as canonical chemical identity. |
| **pymatgen** | Periodic crystal representation and structure matching. | Solid-state comparisons and polymorph work. | Requires crystal structure input; tolerance-sensitive and separate from molecular comparison. |

**Availability check:** PubChem PUG REST offers candidate-search `identity_type` values including `same_connectivity`, `same_tautomer`, `same_stereo`, and `same_isotope`. They are **search options**, not automatic `EXACT` verdicts for this registry.

**Automation limits:** Routine graph, standard stereochemistry, fixed isotope labels, formal charge, and explicit component ratios are highly automatable when well encoded. Atropisomers, coordination stereochemistry, co-crystal-versus-mixture distinction, dynamic tautomeric identity, and crystal-phase assignment may need specialized evidence or human review.

## 7. Search is not resolution

An underspecified query can and should be searchable even though it must not create a `Substance` identity.

**Example — search input:** `glutamic acid`

| Search tier | Example result | Interpretation |
|---|---|---|
| Direct chemical candidates | L-glutamic acid (`SUB_…`) | Specific compatible stereoisomer candidate. |
| Direct chemical candidates | D-glutamic acid (`SUB_…`) | Another compatible stereoisomer candidate. |
| Related chemical substances | Monosodium L-glutamate (`SUB_…`) | A related salt; not an equivalent glutamic-acid identity. |

Candidate ranking should use lexical variants, systematic names, validated source concepts, safe structural candidate-generation, and **already validated** chemical relationships. It must not simply return every `preferredName` containing a substring, nor treat chemical relatedness as exact synonymy.

The ontology's `Alias` is **exact-identity-scoped**: a broad label such as `glutamic acid` is not automatically a validated `Alias` for both L- and D-glutamic acid. Broader search terms and source/domain concept labels belong in the search/concept layer.

**Resolution input:** `glutamic acid`, with no evidence establishing stereochemistry.

```text
candidate_ids: [SUB_… (L-glutamic acid), SUB_… (D-glutamic acid)]
result: UNRESOLVED
reason: STEREOCHEMISTRY_UNSPECIFIED
new_substance_created: false
```

If instead a source record contains a fully validated, stereochemically specified structure compatible with L-glutamic acid, the resolver can return `EXACT` even if a generic name is present, subject to evidence consistency checks.

**General contract:** discovery is allowed to be inclusive; canonical assertion must be exact or abstain.

## 8. Engine architecture and evidence policy

Recommended pipeline:

```text
CUMA / CosIng / future source
          ↓
Source-specific adapter (preserve provenance)
          ↓
Chemical referent interpretation
          ↓
Form-aware evidence extraction and diagnostic views
          ↓
Sufficiency / contradiction / validator-coverage gate
          ↓
Broad candidate retrieval
          ↓
Dimension-wise identity comparison
          ↓
EXACT / NO_MATCH / UNRESOLVED
          ↓
New SUB_ admission only if independently warranted
          ↓
Optional, evidence-backed chemical relationships
```

**Per-dimension comparison output:** `EQUIVALENT`, `DIFFERENT`, `UNKNOWN`, `NOT_APPLICABLE` plus evidence references and reason codes. The earlier `SPECIFIED` / `UNSPECIFIED` / `NOT_APPLICABLE` / `ENSEMBLE` vocabulary characterizes the **source referent**, not the pairwise comparison result; keep the two contracts separate.

**Evidence controls:**

- Preserve raw input, parsing provenance, tool versions, and both original and diagnostic structures.
- Validate whole structures, not merely accepted prefixes of malformed SMILES.
- Require evidence agreement at appropriate granularity; name parsing alone does not override explicit conflicting structure or isotope/stereo data.
- Do not treat multiple tools deriving the same PubChem/structure datum as independent corroboration.
- Keep broad/ambiguous identifiers in the source concept/evidence layer until their referent is proven exact.
- Do not assert ontology `has_alias`, `has_structure`, or `has_identifier` for mere candidates.
- Expose precise abstention reasons (e.g., `STEREO_UNSPECIFIED`, `TAUTOMER_CONFLICT`, `COUNTERION_RATIO_UNKNOWN`, `COORDINATION_UNSUPPORTED`).

## 9. Representative acceptance tests

| Test pair / record | Expected result |
|---|---|
| Different valid SMILES traversals of ethanol | `EXACT` |
| Equivalent benzene Kekulé depictions | `EXACT` |
| Ethanol versus dimethyl ether | Distinct — constitutional isomers |
| L- versus D-glutamic acid | Distinct — enantiomers |
| “Glutamic acid”, stereo not otherwise established | `UNRESOLVED`; **no new `SUB_`** |
| (E)- versus (Z)-but-2-ene | Distinct — E/Z isomers |
| H₂O versus D₂O | Distinct — isotope-labelled identity |
| ¹³C at ethanol C1 versus C2 | Distinct — positional isotopologues |
| Acetic acid versus acetate | Distinct — conjugate acid/base |
| Equivalent acetate resonance depictions | `EXACT` |
| Potassium acetate versus sodium acetate | Distinct — counterion |
| Sodium acetate versus sodium acetate trihydrate | Distinct — defined hydration |
| “Hydrated sodium acetate” without hydration number | `UNRESOLVED` as specific fixed hydrate |
| Explicit 2-pyridone versus 2-hydroxypyridine | Distinct tautomeric forms, provided source intent is established |
| Same Standard InChI, contradictory validated fixed-tautomer evidence | **Not** auto-`EXACT`; reconcile or `UNRESOLVED` |
| Cisplatin versus transplatin | Distinct — coordination geometry |
| Ferrocene versus ferrocenium | Distinct — oxidation/electronic state |
| Defined caffeine–oxalic acid co-crystal versus arbitrary component mixture | Not `EXACT` |
| Anatase versus rutile TiO₂ | Distinct crystal forms; **deferred to solid-state identity model** |
| Search “glutamic acid” | Both stereoisomers are discoverable; salts separated as related results |

Assess independently: (i) exact-matching precision, (ii) new-identity admission coverage, (iii) false overmerges, (iv) correct abstentions, and (v) optional relationship assertion accuracy. The benchmark must be reusable with normalized evidence derived from CUMA and CosIng.

## 10. Ontology disposition and development plan

### 10.1 Changes justified *now*

**None.** Keep `substance_ontology.ttl` unchanged. There is no demonstrated need to add a large chemical-form taxonomy, a universal parent property, or dedicated relations before validation.

### 10.2 Consider *later*, conditional on evidence

- **Likely first candidates:** `enantiomer_of`, `tautomer_of`, and inverse `conjugate_acid_of` / `conjugate_base_of`, after verifying expected semantics and usefulness.
- **Likely structural need:** a constituent/stoichiometry representation for fixed salts, hydrates, solvates, and some adducts; this may be registry-side initially and is not reducible to a binary `has_component` assertion without coefficients.
- **Separate modeling exercise:** nonmolecular `Substance` identities, coordination polymers, polymorphs, crystal phases and amorphous forms; reconsider how `MolecularSubstance` applies.
- **Cross-domain mapping:** an explicit validated `CosmeticsIngredientConcept` → `Substance` mapping relation may eventually be justified; ambiguous concepts must not be assigned arbitrary exact links.

### 10.3 Implementation order

1. Publish a versioned, source-independent **chemical identity policy**, including specification-state vocabulary, exact-match test matrix, and evidence thresholds.
2. Implement chemical-form feature extraction/comparison using the current tools, prioritizing stereo, isotopes, protonation, salts, hydrates, and tautomer-sensitive checks.
3. Increase admission coverage only for **sufficiently defined** identities; test continuously against the original anti-overmerge failures.
4. Build an optional generic typed relationship assertion layer and evaluate it on observed CUMA/CosIng pairs.
5. Add ontology properties only if recurring, semantically coherent and demonstrably useful; treat extended solids separately.

## 11. Conclusion

The next POC is a **chemical identity semantics and admission** exercise, not a general chemical-name parser. A valid Substance identity must be specific enough for an exact assertion; otherwise the source record remains unresolved and searchable through candidate and domain-concept indexing. Distinct chemical forms retain distinct identifiers when their identity-defining differences are established. Relationships explain relatedness without merging identities or imposing a fictitious single parent. Software and reference databases supply evidence; the project identity contract controls the final decision.

**No ontology file was modified as part of this report.**

## References and verification resources

1. **Source ontology:** `substance_ontology.ttl`, version 0.2.0, project attachment inspected 27 October 2026.
2. **InChI Trust.** *Technical FAQ* (Standard InChI, mobile H, Fixed-H, isotopes, metal reconnection). https://www.inchi-trust.org/technical-faq/
3. **RDKit.** *RDKit Book* (stereochemistry, atropisomerism). https://www.rdkit.org/docs/RDKit_Book.html
4. **RDKit.** *MolStandardize / TautomerEnumerator API*. https://www.rdkit.org/docs/source/rdkit.Chem.MolStandardize.rdMolStandardize.html
5. **PubChem.** *PUG REST documentation* (identity search and identifiers), updated September 2026. https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
6. **EMBL-EBI ChEBI.** *The ChEBI ontology* (enantiomer, tautomer, conjugate acid/base). https://www.ebi.ac.uk/training/online/courses/chebi-quick-tour/the-chebi-ontology/
7. **FDA.** *Substance Identification / Global Substance Registration System*. https://www.fda.gov/industry/data-standards/substance-identification
8. **IUPAC Gold Book.** *Tautomer*. https://goldbook.iupac.org/terms/view/12734
9. **IUPAC Gold Book.** *Hydrate*. https://goldbook.iupac.org/terms/view/15195
10. **IUPAC Gold Book.** *Solvate*. https://goldbook.iupac.org/terms/view/15234
11. **Crystallography Open Database.** https://www.crystallography.net/cod/
12. **pymatgen.** *StructureMatcher*. https://pymatgen.org/pymatgen.core.html
