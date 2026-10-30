# Grounded nomenclature support contract

## Executive conclusion

NSC-001 specifies a small IUPAC substitutive construction independently of OPSIN internals: one explicitly locanted, straight-chain alkyl substituent replaces the indicated parent hydrogen at N1 of a neutral `1H-pyrazole` or `1H-imidazole` parent. It provides a common operation-level target for the two proposed architectures. It does **not** assert that either architecture currently implements or validates the contract, that the entire tautomer dimension is complete, or that a canonical Substance can be admitted.

The pilot is scientifically grounded and useful for a controlled architecture comparison, but its practical reach is deliberately narrow: **0 of 81** prior withheld records have a preferred name or saved alias matching the frozen whole-name grammar. The contract and shared fixtures are **partial as a final benchmark**: they need independent human chemical review, a chemically demonstrated nontrivial symmetry case within a supported class, and a more strongly typed constraint schema before they can be considered an acceptance-ready architecture benchmark. Do not broaden this version after examining the diagnostic corpus. A broader second contract would need its own grounding, freeze and held-out controls.

## Pilot and grammar

The [frozen EBNF](nomenclature_grammar.ebnf) is a whole-input grammar. In summary:

```ebnf
name          = "1-", alkyl, "-1H-", parent ;
alkyl         = "methyl" | "ethyl" | "propyl" | "butyl" ;
parent        = "pyrazole" | "imidazole" ;
```

The rule denotes a **class**: a normal C1–C4 alkyl chain, attached at the specified ring position on either of two retained heteromonocyclic parent families. It is not a list of molecule exceptions. The finite chain bound and two numbered parent templates constrain the first experiment; longer chains and additional parents require independent template review and a new contract version. Case, punctuation and whitespace must match the grammar exactly; other variants can be chemically valid yet are `OUT_OF_CONTRACT`. Require full source consumption, one neutral molecular component, no additional substituent or suffix, and no source stereo, isotopic, charge, salt, solvate, fusion, multiplier or other operation. Source strings failing recognition are not thereby classified as chemically ambiguous.

The class is attractive because its source claims and prior trace are observable, and substitutive operations and parent templates can be reused. It also exercises meaningful H-state composition and source-to-atom correspondence. Its limited value is now explicit: the 81-record corpus contains more complex functional groups, parent families, protonation and alias questions. A simple acyclic substitutive class, or a suffix-based carbonyl class, might be easier or more useful respectively, but neither has been shown here to be a substantially better fair comparison with the existing indicated-H trace. No additional pilot was selected.

## Chemical semantics and sources

The primary authority is IUPAC, not parser behavior:

| Rule | Chemical construction and implication | Authority |
|---|---|---|
| R1 | Substitutive nomenclature exchanges a parent H for the named group; the group is connected at the specified parent site. | [Blue Book P-13.1](https://iupac.qmul.ac.uk/BlueBook/P1.html#P-13.1) |
| R2 | A locant is associated with the nomenclature unit it precedes. | [Blue Book P-14.3.2](https://iupac.qmul.ac.uk/BlueBook/P1.html#P-14.3.2) |
| R3 | Indicated H specifies a state of the parent mancude ring. It is distinct from added indicated H and need not survive a subsequent substitutive operation. | [Blue Book P-14.7.1–2](https://iupac.qmul.ac.uk/BlueBook/P1.html#P-14.7) |
| R4 | Retained `1H-pyrazole` and `1H-imidazole` parent names and their ring numbering establish the parent positions. | [Blue Book P-22, Table 2.2](https://iupac.qmul.ac.uk/BlueBook/P2.html); [numbering P-22.2.2.1](https://iupac.qmul.ac.uk/BlueBook/P2.html#P-22.2.2.1) |
| R5 | Simple normal alkyl groups have their free valence at the terminal carbon. | [Blue Book P-29.3.2.1](https://iupac.qmul.ac.uk/BlueBook/P2.html#P-29.3.2.1) |

The [rule catalog](nomenclature_rule_catalog.json) records scope and examples for each rule. The original source writes the locant, alkyl prefix, `1H`, and parent; the meaning of the numbered retained parent and terminal alkyl attachment comes from the naming convention. An OPSIN graph, a generated locant or a candidate tautomer is an interpretation to be checked, not proof that the source explicitly stated additional specificity. Unspecified isotopes and any unsupported stereo or charge must not be invented from a candidate.

The independently reviewable parent templates are five-membered cycles with locants 1–5 in order. In a conventional Kekulé depiction, `1H-pyrazole` has N1–N2–C3–C4–C5–N1, double bonds N2=C3 and C4=C5, and an H at N1; `1H-imidazole` has N1–C2–N3–C4–C5–N1, double bonds C2=N3 and C4=C5, and an H at N1. These are parent-state depictions, not an instruction to demand those precise Kekulé bond serializations. Equivalent representations require validated aromatic/resonance handling without collapsing distinct H states. Parent ring numbering and named substituent semantics are derived from the IUPAC references above; the prospective implementation must independently validate the templates against those references.

For `1-methyl-1H-pyrazole`, interpret `1H` on the parent N1, then replace that H by the attachment of methyl at the same N1. The final N1 has a C bond and need not have an H. [PubChem CID 70255](https://pubchem.ncbi.nlm.nih.gov/compound/70255) and [CID 1390](https://pubchem.ncbi.nlm.nih.gov/compound/MCTWTZJPVLRJOU-UHFFFAOYSA-N) provide independently accessible structure examples for the pyrazole and imidazole positives; they corroborate examples but do not define the naming rule.

## Representation and validation

The [contract record](nomenclature_support_contract.json) and [JSON Schema](semantic_constraint_schema.json) are parser-independent. A record includes contract version, original name, scope, a chemically numbered parent, source claims, operations, structural constraints and completeness. Claims have half-open Unicode-code-point spans into the original source, semantic owner, rule ID, value and dependencies. A constraint has a semantic type, owner, structural assertion, applicable rule, conditions, dependencies and comparison result. Semantic owners are contract-local parent/substituent fragments, never OPSIN object IDs. A consumer must be able to trace every constraint back to the exact source claim and span; the current JSON Schema permits the link inside `assertion` or dependencies but **does not enforce a typed claim ID and span reference**. That is an explicit benchmark-readiness limitation.

The independent semantic transformation is: verify the complete source and its owner; construct the numbered parent state and the terminal alkyl fragment; formally replace the specified parent H by the alkyl attachment; and check the chemical valence and relevant atom/bond states. For the pilot, compare a separately supplied candidate structure against all chemically admissible correspondences, preserving elements, connectivity, component count, formal charge, isotopes, relevant H and valence states, and applicable stereochemistry. A validated exact full-graph correspondence can establish a matching result without reconstructing OPSIN's execution history. A common-parent or other proven operation-specific correspondence is needed when the final graph differs and the result claims a particular attachment violation. Arbitrary failed graph isomorphism alone cannot establish which constraint failed.

| Result | Required meaning |
|---|---|
| `SUPPORTED` | The source claim and its applicability are established, candidate interpretation is reliable, and **every** admissible relevant correspondence satisfies the constraint. |
| `DIFFERENT` | The same prerequisites hold and **every** admissible relevant correspondence demonstrably violates the named constraint; the chemical reason is recorded. |
| `UNKNOWN` | Source meaning, representation, candidate validity, allowed mappings or a dependency is inadequate, or admissible mappings disagree. |
| `OUT_OF_CONTRACT` | The complete name falls outside the supported grammar or operation guards. The comparison result is `UNKNOWN`, without a claim of chemical ambiguity. |

Syntactic recognition and semantic validity are separate; a candidate with unsupported components, isotope or stereochemical specificity, invalid valence, failed parsing, unresolved charge, or unavailable mapping yields `UNKNOWN` unless a separately validated rule establishes a specific contradiction. An invalid candidate is not a chemical negative. When multiple source names are supplied, evaluate them separately; incompatible sufficiently specific claims remain a record-level conflict and cannot be overridden by the success of one claim.

## Operation support, identity and equivalence

`SUPPORTED` for one N1 attachment means only that this source-derived operation is satisfied. It does not automatically establish the tautomer dimension, every other source claim, external corroboration, or a canonical identity. A whole identity dimension requires an explicit closed set of all applicable features, sufficient source specificity, individually validated constraints, absence of contradictory source evidence, and an independently validated demonstration that no required site or operation is omitted. A candidate must not be more specific than the source supports. Remaining dimensions are `UNKNOWN`, or `NOT_APPLICABLE` only when justified.

Different valid name strings or SMILES traversals can denote the same graph. Different locants can refer to symmetry-equivalent atoms, and different Kekulé depictions need not imply different identity. Enumerate admissible atom mappings, respecting parent numbering and identity-relevant attributes; a result is stable only if all mappings agree. Tautomers with different source-supported H positions, distinct constitution, specified versus unspecified stereo, isotope-labelled forms, charge states and extra components require their own identity checks. No salt stripping, tautomer parent replacement, or alias promotion follows from this contract.

## Benchmark and heldout controls

The [12 development fixtures](independent_semantic_controls.json) and [6 held-out fixtures](heldout_semantic_controls.json) were fixed before reviewing the 81 records, and their [hash manifest](nomenclature_contract_freeze.json) records that freeze. Both architectures must receive the same input name, independently supplied candidate, grammar classification, operation claims, expected result, rationale and reference. These are expected outcomes, **not observed parser results**, and have not been executed against either future implementation. The held-out file is a public frozen set, not a secret or blinded adjudication.

The fixtures include N-methyl pyrazole and imidazole positives; a 3-methyl pyrazole constitutional contrast using [PubChem CID 15073](https://pubchem.ncbi.nlm.nih.gov/compound/1453-58-3); malformed structure, missing locant and suffix/salt exclusions; isotope, additional-component and unavailable-mapping abstentions; a conflicting second source claim; and alternative valid graph traversals. The heldout uses [1-ethyl-1H-imidazole, CID 81540](https://pubchem.ncbi.nlm.nih.gov/compound/1-Ethyl-1H-imidazole), and a methyl-versus-ethyl contrast. The synthetic divergent-mapping test specifies a comparator failure mode, but **does not demonstrate a real symmetry ambiguity for this parent class**. The stereochemical and explicit invalid-valence adversarial cases and a chemically grounded nontrivial symmetry control still require independent preparation and review. No implementation acceptance should be based on the current fixtures alone.

## Architecture comparison

[Shared requirements](architecture_comparison_requirements.json) require the same source names, candidates, rules, scope boundaries, independently reviewed expected outcomes, and per-case reporting. Neither architecture may use its own proposed candidate as the authority for the source name.

| Criterion | A: source-aware OPSIN | B: independent constrained interpreter |
|---|---|---|
| Source evidence | Prior trace already links written locant, substituent and indicated-H parent atom. Reliable spans, chosen parse and ownership still need a bounded public or maintained API. | Whole-name grammar and reviewed numbered parent/alkyl templates can derive claims independently of OPSIN. |
| Candidate proof | Expose stable semantic parent/atom mapping or provide a separately validated final-structure correspondence. Full internal execution logging is **not** required if an independent final-state proof suffices. | Compare the independently derived semantic graph/constraints to the separately supplied candidate; RDKit or another structural toolkit can implement comparison but is not source-semantic authority. |
| Closure and failure | Unsupported normalization, alternatives, clones and transformations must be detectable; a maintained patch and version drift create costs. The prior sidecar lacks proof of closure. | Must reject unsupported grammar and not silently duplicate parser guesses. Independent nomenclature grammar, parent templates and extension review create maintenance costs. |
| Extensibility | Can reuse OPSIN's broad parser if provenance can be exposed and kept version-consistent; general support could become a substantial fork. | More explicit scope and isolation, but broad nomenclature means duplicated language/chemistry work. |

Neither architecture has yet met the benchmark. A head-to-head experiment should first repair the stated benchmark gaps, independently review parent templates and negatives, re-freeze the revised artifacts, and run a fresh heldout set without changing admission. Select by correctness and demonstrable closure as well as maintenance burden, not implementation size.

## 81-record applicability and roadmap

After freezing grammar and controls, the [81-case assessment](contract_81_case_applicability.json) inspected complete preferred-name and saved alias strings against the frozen grammar. It found **0 within, 0 potentially within, 81 outside and 0 with missing names**. This is lexical applicability, not chemical adjudication or recovery. The outside group includes 41 prior tautomer-specificity blockers, 22 charge/protonation blockers and 18 alias-conflict blockers. No full resolver replay or provider call occurred. Substrings inside more complex names were deliberately not counted as supported operations because NSC-001 accepts a complete name only.

The [extension roadmap](nomenclature_extension_roadmap.json) prioritizes, qualitatively, richer substitution and suffix/added-H semantics, charge/protonation and salts, followed by stereo, isotopes and independently validated conventional aliases. The reusable substrate is source-span and fragment ownership, typed parent/operation claims, bounded graph correspondence and explicit unresolved dependencies. Each extension needs its own authoritative rules, dimensional comparison and holdout; current estimates are not measured coverage. Later alias enrichment remains a separate `substance_id | alias | alias_source` design requiring exact validated form correspondence.

## Integrity and limits

The ontology and identity framework require preserving applicable chemical-form distinctions and validating aliases; this contract does not change them. The older frozen-contract check passed for the ontology, framework, schema, OPSIN artifact, checked frozen inputs and provider caches; its four historical code exceptions remain outside that particular freeze's proof. New files are specification and lexical applicability artifacts; no resolver, provider, instrumentation, ontology or registry behavior was changed. JSON files parse and the JSON Schema passes Draft 2020-12 meta-schema validation. Candidate SMILES were checked for parseability, including the intentionally malformed negative, but those checks do not independently adjudicate nomenclature semantics. No architecture was implemented.

NOMENCLATURE_CONTRACT_PARTIAL
