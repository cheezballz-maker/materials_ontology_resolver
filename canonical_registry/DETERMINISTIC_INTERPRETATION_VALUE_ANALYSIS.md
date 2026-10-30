# Deterministic source-name interpretation and corroboration value

## Decision and method

**Keep mandatory corroboration provisionally.** In this holdout the complete preferred-name interpreter produced one demonstrated charge-form mismatch that the current gate withheld, while 152 reference-matching interpretations passed the other *observed* local checks but were held without a qualifying corroborator. The gate's substantial coverage cost and its safety benefit are both real observations; **the provider did not detect the mismatch**. The incorrect candidate was held because no qualifying provider evidence was available. One adjudicated error and incomplete reference coverage do not establish a general error rate for a new policy or justify inventing a narrow exception class.

This is an analysis of the [frozen fresh holdout](FRESH_BLINDED_RESOLVER_EVALUATION_REPORT.md), not a new resolver run. The source sample, original labels and predictions were not changed. The primary cohort contains the 224 records for which the original preferred-name OPSIN claim succeeded and produced a saved structure, `name_interpretation` was `ESTABLISHED`, preliminary source-form status was `SUPPORTED`, and the local form was `SPECIFIED`; the saved source candidate also matched the final candidate exactly. The other 176 records did not meet those criteria and are excluded from interpretation precision. `preliminary` matters: alias conflict checks are sometimes deferred until after the provider gate. The [case-level artifact](deterministic_value_analysis/deterministic_interpretation_cases.json) records each candidate, source-form dimensions, graph features, frozen outcome, reference comparison and provider states.

The strict frozen identity comparator compares constitution, stereo, isotope, charge/hydrogen, tautomer, electronic state and components/stoichiometry; it does not use a provider hit as proof of correctness. Its own chemistry implementation is shared with the resolver, so a shared comparator defect could escape this analysis. An `UNRESOLVED` comparison is excluded, not counted as correct or incorrect. Reference identity availability is selectively incomplete, and PubChem, NCI CACTUS and suppliers may share upstream information with the evaluated system. The sample was random within a known-exclusion population, but the adjudicated subset is not guaranteed representative.

## Supplemental adjudications of the two previously unresolved EXACTs

The two follow-up adjudicators received the source names and public-source task without the resolver candidates or admissions. Their independent graphs were constructed and checked before comparison to frozen results. These are **targeted post-holdout supplements**, not new labels in the original frozen reference file. Detailed claims and source links are in [completed adjudications](deterministic_value_analysis/completed_exact_adjudications.json).

| CUMA | Independent finding | Structure / InChIKey | Frozen comparison |
|---|---|---|---|
| 4570, 4-octyl-N-phenylaniline | **REFERENCE_EXACT_CONFIRMED**. The named n-octyl chain is para to the aniline nitrogen, which also bears phenyl; the molecular name does not specify a salt or stereoisomer. [IUPAC](https://iupac.qmul.ac.uk/BlueBook/Papp2.html) defines octyl as octan-1-yl; [PubChem CID 61335](https://pubchem.ncbi.nlm.nih.gov/compound/61335) supplies corroborating structure evidence. | `CCCCCCCCc1ccc(Nc2ccccc2)cc1` / `DMLLDZGHGNLZNW-UHFFFAOYSA-N` | EXACT graph match |
| 6634, 2-chloro-5-methylpyridin-3-amine | **REFERENCE_EXACT_CONFIRMED**. Pyridine N is position 1; Cl, NH₂ and CH₃ occupy positions 2, 3 and 5 respectively. [PubChem CID 2734422](https://pubchem.ncbi.nlm.nih.gov/compound/2-Chloro-5-methylpyridin-3-amine) and the [TCI SDS](https://www.tcichemicals.com/BE/en/sds/A2405_EU_6N.pdf) support the named compound. | `n1c(Cl)c(N)cc(C)c1` / `CQKIBEOVARIBDN-UHFFFAOYSA-N` | EXACT graph match |

For 6634 the [Cymit indexed page](https://cymitquimica.com/cas/34552-13-1/) labels the same name and CAS but reports `Cc1cc(cnc1Cl)N`, whose locally regenerated key `VSBISZPNLZFTPG-UHFFFAOYSA-N` is a different regioisomer. The indexed text descriptors conflict with its label; the full page/image was not independently verified, so the finding is not an allegation about a particular physical product. Formula equality cannot resolve this discrepancy. For 4570, a broad commercial "octylated diphenylamine" product name is not evidence of purity or chain specificity and is not promoted merely by this decision.

Descriptively, the earlier final-admission precision was **6/6** adjudicable EXACTs; adding these two targeted independent determinations gives **8/8 = 100%** (exact 95% binomial interval **63.06%–100.00%**). This supplemental calculation does not rewrite the original report or its labels and cannot be interpreted as a new blinded random sample.

## Interpretation accuracy before corroboration

| Measure | All adjudicable references | Excluding the pre-recorded reference-quality flags |
|---|---:|---:|
| Correct complete interpretations / assessed | **183/184 = 99.46%** | **177/178 = 99.44%** |
| Exact 95% Clopper–Pearson interval | **97.01%–99.99%** | **96.91%–99.99%** |
| Correct complete interpretations / available exact references | **183/225 = 81.33%** | **177/209 = 84.69%** |

The denominator of 184 contains 183 graph matches and 1 graph mismatch; **40 of 224** complete interpretations remain unadjudicable and are excluded, including two with independently documented source-form ambiguity. The 225 reference identities are the original 223 plus the two independently adjudicated names. Excluding reference-quality flags removes 6 assessed cohort cases and 16 exact reference identities from the corresponding denominators; it does not alter any frozen labels. The intervals assume binomial observations and do not correct for selection, shared reference ancestry or incomplete adjudication. The two ambiguity cases below are not silently counted as errors in either precision denominator.

## Incorrect interpretation and unresolved source-form risks

**CUMA 17504 — 1-methyl 2-aminoterephthalate.** The source-derived OPSIN candidate was the carboxylate anion `COC(=O)c1ccc(C(=O)[O-])cc1N`, formal charge −1, key `QKOKLMFCKLEFDV-UHFFFAOYSA-M`. The frozen independently reviewed reference was the neutral monoester acid `COC(=O)c1ccc(C(=O)O)cc1N`, charge 0, key `QKOKLMFCKLEFDV-UHFFFAOYSA-N`; [Fisher's structural listing](https://www.fishersci.ca/ca/en/browse/cas/60728-41-8) names and depicts the neutral acid. The comparator reports **PROTONATION_DIFFERENT**. The terse `terephthalate` name plausibly contributed to the anionic parser output; this analysis does not establish the parser's internal root cause. The source also contains acid and anion aliases. In the saved evidence the post-gate source check records the protonation difference but still says `SUPPORTED`, so under the observed other local checks the anion would have been eligible if only mandatory corroboration were removed. All relevant provider routes were `NO_MATCH` or `UNAVAILABLE`, with no provider contradiction. **The gate withheld one incorrect interpretation; it did not chemically diagnose it.** No code or label was changed.

Two more complete claims are safety-relevant but their frozen references are `UNADJUDICABLE`, so they are **not counted** in the one-error precision denominator or A/B/C/D totals:

- **4373, 3-methyl-4-phenylpyrazole:** the candidate fixes one pyrazole proton/bond arrangement, while the reference review found the preferred name did not settle the hydrogen locant. The cited [primary pyrazole study](https://www.electronicsandbooks.com/edt/manual/Magazine/J/Journal%20of%20the%20American%20Chemical%20Society%20US/1964%20%20%28vol%20086%29/07%20%20%281275-1462%29/1456-1457.pdf) discusses the 3(5)-methyl-4-phenylpyrazole tautomer problem. Corroboration was not qualifying; the saved alias/source-form check was `SUPPORTED`. This is a potential unsupported-specificity admission if the gate were removed, not a confirmed wrong molecular graph.
- **30832, benzyl acetoacetate:** the reference review did not establish a single fixed tautomer. A [primary study of benzyl acetoacetate](https://doi.org/10.1016/J.MOLSTRUC.2010.12.034) reports keto/enol forms and predominantly keto in its studied solutions; that does not by itself prove the source's intended identity. Corroboration was not qualifying, and the saved source-alias check separately found `SOURCE_CONSTITUTION_CONFLICT`. Thus a downstream alias gate also blocks this case under the evaluated checks.

These two examples justify caution about source-form completeness; neither is relabelled as a false graph. All other unadjudicable records remain unscored.

## What the corroboration gate did

The A/B/C/D categories below cover only the 184 independently graph-adjudicable complete interpretations. “Corroboration available” means at least one source-linked provider route returned `CORROBORATES`; it does not count repeated records as votes. A contradictory source-linked provider route, if present, would separately veto. Here none occurred in the assessed cohort.

| Category | Meaning | Count |
|---|---|---:|
| A | Correct interpretation, qualifying corroboration available | **10** |
| B | Correct interpretation, no qualifying corroboration | **173** |
| C | Incorrect interpretation, corroboration gate blocked admission | **1** |
| D | Incorrect interpretation, corroboration gate would permit admission | **0** |

In A, eight became EXACT and two were held by later source-alias conflicts. In B, all 173 were unresolved for `NO_QUALIFYING_CORROBORATION`. We re-evaluated the **already saved** individual alias claims through the unchanged source-form helper, without rerunning OPSIN, a provider or the resolver: 152 had `SUPPORTED` alias/source-form checks, a confirmed official InChI, complete composition and no recorded provider contradiction; the other **21** had later source-alias conflicts. Thus **152 is the observed conditional count of reference-matching interpretations held solely at the corroboration gate**, not 173 and not 214. In the quality-flag-excluded sensitivity subset the analogous count is **148**. This saved-evidence counterfactual is not a full policy rerun: unobserved lookups, registry allocation, future source-quality review or differing execution order could change an actual admission. It is therefore not proof that all 152 are safe canonical additions.

One incorrect interpretation, 17504, was gate-blocked and satisfied the other observed local checks. Thus **one adjudicated wrong interpretation would have become locally eligible** under the modeled removal of only the corroboration requirement; actual allocation was not simulated. The two reference-unadjudicable tautomer cases are additional uncertainty, not included in that count. The case-level [corroboration analysis](deterministic_value_analysis/corroboration_value_analysis.json) retains every assessed record and its gate/source status.

Among correct interpretations, qualifying corroboration was available for **10/183 = 5.46%**; among incorrect interpretations it was available for **0/1 = 0%**. The latter denominator is one, so no reliable provider-discrimination estimate follows. The gate's observed C-case benefit comes from abstention on missing qualification, not demonstrated provider error detection.

For the 173 B records, the saved queries show at least one `UNAVAILABLE` route in **172**, at least one `NO_MATCH` in **58**, and at least one `NON_DISCRIMINATING` route in **48**; these are non-exclusive record counts, not votes. `PROVIDER_RECORD_AMBIGUOUS`: **0**; `CONTRADICTS`: **0**. CUMA 17504 had unavailable and no-match queries, no qualified contradiction. Unavailability, absence and nondiscriminating evidence are not chemical contradictions. Provider budgets were exhausted in sorted source-index order in the original holdout, so availability and the apparent gate pass rate are run-specific and may be systematically uneven.

## Future policy assessment

- **A — mandatory corroboration:** retain for now. It blocked one demonstrated charge-form error and at least abstained on the two documented form-uncertain cases, at the observed cost above. This does not show that provider results reliably detect errors; here the decisive observation was absence of a qualifying source-linked result.
- **B — deterministic-primary:** the measured 183/184 precision and 152 locally eligible correct holds make this worth investigation, but the saved anion example demonstrates that adopting it globally now would admit an unsupported form unless another safeguard changes. Do not adopt it from this sample.
- **C — conditional corroboration:** potentially useful later, but one confirmed charge mismatch and two unadjudicable tautomer concerns are too few to establish validated risk classes or safe exemptions. Do not infer a whitelist or threshold here.

This analysis changes no production policy. More complete, independently curated references and a separate fresh evaluation are needed before changing the identity gate. No increase in provider budgets is proposed as the solution to recall.

## Secondary provider enrichment and alias provenance

Once a canonical molecular identity is independently established, a later cached, incremental and rate-limited enrichment process may retrieve provider records and compare their complete structures and applicable form dimensions against that identity. Only an **EXACT, form-discriminating** record may be considered for alias enrichment. This is necessary, not sufficient: each provider name must also be validated as an exact claim, since a record's synonym list can contain broad names, stereoisomers, salts or product names. Hold ambiguous, parent-normalized, charge/tautomer-altered, isotope/stereo-different and multicomponent-mismatched records. For `PROVIDER_RECORD_AMBIGUOUS`, do not harvest from that route unless a stronger source-linked identifier separately selects an exact form.

A future relational alias assertion can be **`substance_id | alias | alias_source`**, with `alias_source` identifying a record, such as `PubChem:CID1140`, `ChEBI:CHEBI:17578`, `GSRS:<record-id>` or `CompTox:DTXSID7021360`. A uniqueness constraint on `(substance_id, alias, alias_source)` permits the same alias to carry multiple source assertions. Detailed retrieval provenance stays in audit/cache artifacts rather than large alias-table objects. A derived export can join the current preferred name to expose `preferred_name | alias | alias_source`; it is a convenience view, because preferred names and authority conventions can change while `substance_id` remains the relational key.

An enriched alias is never a recursive identity assertion: a later alias hit only proposes a candidate, which must still undergo deterministic source interpretation and exact identity validation or abstention. This is a future architecture recommendation; no table or asynchronous process was implemented in this task.

## Limitations and reproducibility

The 400-record source sample was randomly selected from the documented eligible population, but reference completeness and provider availability are not random. Fifty-one source records had screening-only references, and the final comparison is conditional on those independently assessable. Public references can share data with each other and with resolver providers. The reference-freeze manifest did not hash raw HTTP response caches, only reference records and their stated evidence. Supplemental adjudications were targeted after the original holdout and are shown separately. The category C denominator is one; there were no category D examples. Structural equivalence is assessed using the same comparator implementation as the resolver and does not independently certify its completeness. Counterfactual source-form checks were applied only to saved claims, not a full rerun. See the [metrics](deterministic_value_analysis/deterministic_interpretation_metrics.json), [cases](deterministic_value_analysis/deterministic_interpretation_cases.json), [input hashes](deterministic_value_analysis/input_snapshot.json), and [original reference-quality notes](fresh_blinded_evaluation/REFERENCE_QUALITY_NOTES.json).

MANDATORY_CORROBORATION_STILL_JUSTIFIED
