# Chemical Identity Evidence Sufficiency Contract v1

## Purpose

The evaluator decides whether a source concept has enough chemical evidence to justify an attempted canonical identity match. A positive result supplies a qualified chemical referent and a potential downstream pathway. A later resolver establishes match existence, uniqueness and admission eligibility.

Source adapters preserve the original designation, field value, record revision, claimed role and provenance. They grant authority for a specific assertion only when the source contract or a revision-bound evidence receipt supports it. The shared evaluator applies the same rules to every adapter and opens no canonical registry.

## Required evidence

| Dimension | Required evidence |
| --- | --- |
| Specificity | A strictly valid molecular representation with sufficient applicable identity dimensions. Preserve constitution, isotope labels, explicit charge, protonation, radicals, stereochemistry, fixed-H form and every component. |
| Correspondence | A traceable link from the current source referent to the same evidence entity as the qualified graph. The link names the source record revision it covers. |
| Authority | A claim-specific grant backed by an authority, document, field or assertion locator and evidence revision. A provider name identifies provenance and grants no role by itself. |
| Consistency | Coherent qualified structural claims, relevant authoritative descriptors and material scope. Active source-level holds and contradictions block eligibility. |

Evidence scope is WHOLE_REFERENT, CONSTITUENT, PRECURSOR, RELATED_MATERIAL or SCOPE_UNESTABLISHED. A component can have a well-defined molecular graph while the parent material remains outside exact molecular resolution. An external graph can participate through a separately verified whole-referent link to its evidence entity. An explicitly constituent, precursor or related graph cannot fill that role.

## Evidence pathways

| Pathway | Necessary and jointly sufficient evidence, subject to common checks | Disqualifying examples |
| --- | --- | --- |
| A · Qualified direct structure | A structure-bearing source or native record explicitly defines the whole referent. The claim carries structure and referent authority and covers the current source revision. | Flattened structure without a definitional field role, constituent structure, obsolete revision or incompatible molecular forms |
| B · Authoritative nomenclature | A nomenclature claim identifies the whole referent with a defined evidence entity. A structure authority independently establishes that entity's graph. | Lexical similarity, unsupported synonymy, a name that denotes a preparation or a structure for a different entity |
| C · Identifier-mediated | A documented source-to-identifier relation, the identifier's actual authority and namespace, and an explicitly defined chemical scope link the referent to a qualified structural record. | A CAS, EC or UNII string alone, a record for a variable composition or a cross-reference without role |
| D · Other evidence | Reserved. A future extension needs a documented route establishing the same specificity, correspondence, authority and consistency guarantees. | Scoring, vote counting or accumulation of weakly scoped evidence |

The routes have no mandatory name-parser step. If several routes support one evidence entity, the evaluator reports a deterministic route label and the supporting claim IDs. Competing qualified entity links produce a review hold. Evidence entity keys belong to the qualification packet and are separate from canonical IDs.

## Molecular form and partial definitions

Strict RDKit parsing provides canonical isomeric serialization, Standard InChI and full key, fixed-H InChI, formula, charge, components and stereo/isotope features. Equivalent traversals that produce the same signatures agree. A differing signature produces a conservative hold when equality cannot be established from these exact checks. The policy preserves salts, tautomers and other exact forms. A whole multicomponent graph needs an explicit complete-composition grant. The representation can carry applicable dimensions without redundant textual declarations. A source claim with undefined stereo requires further evidence unless it explicitly defines the open dimension.

The Substance pathway requires sufficient molecular specificity and an agreeing official InChI receipt. The ChemicalConcept pathway is restricted to a supported molecular foundation with source-attested unspecified stereochemistry, a reproducible bounded isomer definition and otherwise specified applicable dimensions. It reuses the existing molecular concept contract. Broad families, polymers, generic functional groups and variable compositions remain outside this pathway. Warnings, unsupported molecular definitions and failed official validation stay visible.

## Input and output

The [input schema](identity_sufficiency/evidence_v1.schema.json) and [Python contract](identity_sufficiency/contract.py) define a versioned packet. It carries a source-independent referent key, original source reference and revision, designation, claims, source-backed material-scope evidence and holds. Each claim retains original value, kind, scope, evidence-entity key, authority grants, provenance, namespace where applicable, and the source-binding revision when it differs from the evidence document revision.

The [decision schema](identity_sufficiency/decision_v1.schema.json) records one operational decision, reason codes, applicable evidence and resolution pathways, supporting claim IDs, authority findings, scope and supported specificity, official validation where exercised, and policy/evidence versions. These decisions are stored separately from canonical statuses.

| Outcome | Meaning |
| --- | --- |
| CANDIDATE_READY | Qualified whole-referent evidence justifies an attempted match under the specified pathway. |
| NEEDS_MORE_EVIDENCE | A required graph, authority, scope or specificity condition remains unestablished. |
| NOT_APPLICABLE_TO_EXACT_MOLECULAR_RESOLUTION | The source establishes a non-discrete scope under the supported pathways. |
| REVIEW_HOLD | Conflicting evidence, an incomplete process or a validation problem prevents safe progression. |

## Examples and limits

- A native chemical registration with a complete graph, consistent integer moieties and a documented defining field can pass A when the whole record is verified and the designation is unparsed.
- A source definition explicitly identifying the ingredient as a named molecular entity can pass B with a separate qualified graph for that entity.
- A source-bound registry code linked to a verified discrete registry definition and a validated graph can pass C. The same namespace may also contain non-molecular registrations.
- An extract that reports a constituent graph remains an extract. Conflicting assignments for an enantiomer require review.
- Source-attested unspecified stereochemistry can qualify for molecular ChemicalConcept review when the supported definition retains its known constraints. Missing stereo in an imported graph alone leaves the case unresolved.

V1 has conservative limits for structural input size, comparison signatures and represented partial dimensions. Additional authority receipts must document the asserted role and be independently auditable. Target lookup, association, admission, canonical creation and ingredient equivalence are outside the evaluator's scope.
