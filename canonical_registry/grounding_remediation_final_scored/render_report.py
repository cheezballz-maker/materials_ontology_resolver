"""Render the remediation report from frozen replay and read-only case evidence."""
import json,collections,ast
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
m=read(H/'metrics.json');a=read(H/'change_analysis.json');probe=read(H/'historical_case5_probe.json');v=read(H/'run/verification.json');after=m['after'];before=m['before']
clean=lambda s:str(s).replace('|','\\|').replace('\n',' ')
rows=a['changed'];trans=a['transitions'];classes=collections.Counter(x['classification'] for x in rows);causes=collections.Counter(x['likely_cause'] for x in rows)
changes='\n'.join(f"| {x['cuma_index']} | {clean(x['name'])} | {x['before']} → {x['after']} | {x['classification']} | {x['likely_cause']}: {clean(x['after_reason'])} |" for x in rows)
tests='''| Changed test(s) | Why the prior expectation changed |
| --- | --- |
| `test_salts`, `test_hydrate_and_solvate` | A salt word or numeric hydrate suffix did not independently establish the disconnected graph; named solvate vocabulary is held. |
| `test_parser_failure_recovered_by_validated_original_alias`, `test_lexical_link_never_collapses_numeric_locants` | A hyphen/space or case-only variant was not proof of source-name identity. |
| `test_unknown_source_claim_conflict`, `test_sulfate_sulfite_conflict_without_name_dictionary`, `test_alias_retrieval_cannot_override_sulfate_claim` | Sulfur-name tokens cannot establish a parsed constitutional contradiction; unparsed preferred claims now remain unknown. |
| `test_wrong_alias_alone_is_not_a_record_veto` | The requested general mechanism compares two independently parsed source claims; a constitutional disagreement is now a source conflict. |
| `test_named_alditol_is_not_assumed_to_be_a_cyclic_sugar`, `test_explicit_cyclic_name_cannot_use_open_chain`, `test_broad_sugar_cannot_inherit_open_chain_or_anomer`, `test_expanded_key_cannot_make_generic_sugar_exact` | Root, ring and alditol shortcuts did not establish carbohydrate structure; D/L-only examples remain unresolved without a verified mapping. |
| `test_bounded_registry_inversion` | The specific ethanol transformation was not a grounded general index-name grammar. |
| `test_unique_stereogenic_duplicate_locant` | Only one topologically eligible atom does not prove name-fragment ownership. |
| `test_ratio_requires_typed_original_component_claims`, `test_ionic_pair_preserves_explicit_graph_and_charges`, `test_added_component_rejected_when_source_component_set_complete` | The slash/colon ratio was not a documented general grammar; graph/charge and added-component comparisons now use an independently supplied typed source structure. |
| `test_provider_cannot_upgrade_hydrochloride_protonation` | The earlier multicomponent guard can now produce a different conservative reason; the no-admission assertion remains. |'''
txt=f'''# Resolver grounding remediation

**Result: partial.** The name-specific evidence fixture, sulfate/sulfite shortcut, duplicate-locant ownership exception and unsupported lexical transformations were removed or quarantined. A historical tautomer probe then exposed a general safety bug: a failed source-provider lookup could be ignored when another provider returned a hit. The new general guard holds that case as incomplete evidence. The remaining element and organic/inorganic scope heuristics are still admission-relevant, so the grounding success criterion is not yet met. **Do not resume feature development.**

The changed-rule matrix is [resolver_grounding_matrix.json](resolver_grounding_matrix.json); the prior [grounding audit](RESOLVER_GROUNDING_AUDIT.md) contains independent sources and implementation-risk analysis. This task did not modify ontology, persistent schema, prior registry snapshots, or add providers, a CAS/carbohydrate parser, OPSIN ownership adapter, salt semantics, or ontology relationships. The runtime retains the old `reviewed_evidence` constructor argument only as an ignored compatibility argument; the historical file remains an audit/test artifact and is never read by the resolver.

## Removed, quarantined and retained

- **Removed:** sulfur-token/oxygen-neighbor source conflict; the hard-coded reviewed-evidence injection; ethanol inversion and alphabetic hyphen rewrite; sugar-root, ring-proxy and alditol recognition; salt-name-word admission; name-based solvate inference.
- **Quarantined:** duplicate locants now return `LOCANT_SCOPE_UNRESOLVED`; unowned colon or solidus ratios are recorded as unspecified and block admission; alternative parse input cannot establish the preferred source claim; D/L alone cannot establish generic absolute stereo. Source and curated-provider name matches preserve descriptor case and punctuation. A case-only provider hit is retained as *incomplete evidence*, not silently discarded or declared equivalent.
- **Retained:** strict structures, explicit numeric sodium/potassium/hydrochloride and hydrate constraints, explicit charge capture, exact graph/form comparison, original evidence checks and abstention. A water suffix alone cannot establish disconnected water. Explicit source hydration semantics can support a count; non-water solvates remain held. The old element allowlist, organic-carbon and some coordination/material-scope guards remain active: removing them without a defensible replacement could admit unsupported structures. This unresolved conflict with the requested quarantine is why the result is partial.
- **General source conflict:** when the preferred claim and an alias both parse and their constitutional graphs differ, `source_form.assess` records `SOURCE_CONSTITUTION_CONFLICT`. A failed source parse cannot infer a sulfate/sulfite conflict. These source conflicts require review; they do not establish that the preferred structure itself is wrong.
- **General provider-safety correction:** source-claim `ERROR` or `NOT_QUERIED` is now incomplete evidence even if another provider succeeds. The original provider failure is retained; no new source or case mapping is introduced.

## Test changes and independent examples

The final frozen run passed **139 tests**, including ten new tests in [test_grounding_remediation.py](test_grounding_remediation.py). The retained suite still exercises R/S, E/Z, cis/trans, isotope locants, and exact-form comparisons. Independent source examples added include IUPAC disodium carbonate and addition-compound notation ([Blue Book salts](https://iupac.qmul.ac.uk/BlueBook/P6.html), [addition compounds](https://iupac.qmul.ac.uk/BlueBook/P1.html)); WHO dehydroemetine dihydrochloride and sodium phosphate monohydrate ([monograph](https://cdn.who.int/media/docs/default-source/medicines/pharmacopoeia/omitted-monographs/dehydroemetine_dihydrochloride.pdf), [pharmacopoeial comparison](https://cdn.who.int/media/docs/default-source/essential-medicines/2023-eml-expert-committee/applications-for-addition-of-new-medicines/a33_phosphorus.pdf?sfvrsn=9f401afc_2)); and chloral hydrate ([IUPAC Gold Book](https://goldbook.iupac.org/terms/view/15195)). IUPAC [P-9](https://iupac.qmul.ac.uk/BlueBook/P9.html), [P-82](https://iupac.qmul.ac.uk/BlueBook/P8.html), and [carbohydrate recommendations](https://iupac.qmul.ac.uk/2carb/06n07.html) independently ground the distinctions, not complete implementation coverage. Tests also cover case-preserving provider matching, unsupported CAS-style inversion, alias structure conflict, fixture isolation and unavailable source providers. [Test log](grounding_remediation_final_scored/tests.log).

{tests}

## Frozen 400-record development replay

The same frozen input and reference labels were replayed against copied cached evidence, **offline and without new provider requests**. This is a development replay, not an independent holdout. [Freeze](grounding_remediation_final_scored/IMPLEMENTATION_FROZEN.json), [metrics](grounding_remediation_final_scored/metrics.json), [case evidence](grounding_remediation_final_scored/change_analysis.json), and [all case comparisons](grounding_remediation_final_scored/comparison.json).

| Measure | Before | After |
| --- | ---: | ---: |
| EXACT | {before['predicted_status'].get('EXACT',0)} | {after['predicted_status'].get('EXACT',0)} |
| UNRESOLVED | {before['predicted_status'].get('UNRESOLVED',0)} | {after['predicted_status'].get('UNRESOLVED',0)} |
| CONFLICT | {before['predicted_status'].get('CONFLICT',0)} | {after['predicted_status'].get('CONFLICT',0)} |
| OUT_OF_SCOPE | {before['predicted_status'].get('OUT_OF_SCOPE',0)} | {after['predicted_status'].get('OUT_OF_SCOPE',0)} |
| Confirmed exact / known false / unverified | {before['automatic_exact']['correct']} / {before['automatic_exact']['false_positive']} / {before['automatic_exact']['unverified']} | {after['automatic_exact']['correct']} / {after['automatic_exact']['false_positive']} / {after['automatic_exact']['unverified']} |
| Assessed false merges / pairs | {before['false_merges']['count']} / {before['false_merges']['assessed_pairs']} | {after['false_merges']['count']} / {after['false_merges']['assessed_pairs']} |
| Correct / incorrect / unverified promoted aliases | {before['alias_promotion']['correct']} / {before['alias_promotion']['incorrect']} / {before['alias_promotion']['unverified']} | {after['alias_promotion']['correct']} / {after['alias_promotion']['incorrect']} / {after['alias_promotion']['unverified']} |

**{trans.get('EXACT->EXACT',0)} prior EXACT admissions remain admitted**, classified `PRIOR_ADMISSION_REMAINED_SUPPORTED` by the current gates; that is not independent proof of every underlying rule. **{trans.get('EXACT->UNRESOLVED',0)+trans.get('EXACT->CONFLICT',0)} previous EXACT admissions were withheld**. **{trans.get('CONFLICT->UNRESOLVED',0)} prior conflicts became unresolved**; this does not mean the underlying evidence was reconciled. Previously UNRESOLVED → EXACT: {trans.get('UNRESOLVED->EXACT',0)}; UNRESOLVED → CONFLICT: {trans.get('UNRESOLVED->CONFLICT',0)}. New EXACT admissions from any prior state: {sum(n for k,n in trans.items() if k.endswith('->EXACT') and not k.startswith('EXACT->'))}. Alias claims removed: {len(a['alias_removed'])}; added: {len(a['alias_added'])}. {len(a['unchanged_reason_changes'])} unchanged-status records acquired different reason text; these are available in the case evidence, not counted as changed outcomes.

The loss classification is evidence-based but not an independent chemical adjudication: `PRIOR_ADMISSION_LOST_DUE_TO_UNGROUNDED_HEURISTIC_REMOVAL` is used for the recorded D/L/case, locant, source-name and case-only-provider holds. `OTHER` includes new general parsed-alias conflicts and cases where multiple changed gates make causality uncertain. Changed outcomes: {len(rows)}. Category counts: {dict(classes)}. Recorded cause groups: {dict(causes)}. No prior admission was restored merely because the frozen reference supported it.

| CUMA | Name | Before → after | Classification | Recorded cause and new reason |
| ---: | --- | --- | --- | --- |
{changes}

## Historical unsafe admissions and runtime integrity

The four historical cases remain non-EXACT: 5684 sulfate/sulfite is **{next(x['after_status'] for x in m['prior_false_positive_cases'] if x['cuma_index']==5684)}**; relative-stereo cases 5997 and 23839 are **{next(x['after_status'] for x in m['prior_false_positive_cases'] if x['cuma_index']==5997)}** and **{next(x['after_status'] for x in m['prior_false_positive_cases'] if x['cuma_index']==23839)}**; glucose-form case 30142 is **{next(x['after_status'] for x in m['prior_false_positive_cases'] if x['cuma_index']==30142)}**. They are blocked by general unavailable-source, form or stereo checks, not index rules.

The separately probed historical dithiazole case 5 is **{probe['status']}**, reason `{';'.join(probe['reason_codes'])}`, using the old form-aware cache, without injected reviewed fixture or network access. A preliminary probe before the general provider-failure fix returned AUTO_ACCEPT while ChEBI had errored; this is why that general guard was added. The final result is an incomplete-evidence abstention, not proof that the tautomer conflict has been resolved or that future complete source results cannot miss it. [Probe](grounding_remediation_final_scored/historical_case5_probe.json).

Registry verification: **{v['result']}**, {v['exact_reconciliations_revalidated']} exact reconciliations checked, {v['canonical_graphs']} canonical graphs, zero checked duplicates and orphans. The previous explicit-multicomponent, stereo and second-holdout scored registry/candidate snapshots match their frozen hashes; schema, ontology and framework hashes are unchanged. [Verification](grounding_remediation_final_scored/run/verification.json). The production OPSIN jar hash and live class-loading check match the original artifact; neither diagnostic instrumentation nor a shadow OPSIN class was loaded. [Classpath evidence](grounding_remediation/classpath.json).

## Remaining weak grounding and capability gaps

The existing element allowlist, carbon-based organic/inorganic test and coordination heuristics still gate admission and are not independently justified as complete chemical classification. Some bounded stereo/token, protonation, isotope, tautomer and source-claim mechanisms retain the limitations in the audit. Parser-generated names, external lookup status and source aliases can remain dependent; missing or contradictory information now produces more holds, not proof of correctness. No grounded carbohydrate form interpreter, source grammar for general component ratios, general fragment ownership, general solvate classifier, or broader salt/protonation semantics was added. The fresh independent examples are small and the reused 400-case sample cannot demonstrate scale safety. Resolve the scope-guard grounding and review the conservative provider-failure policy and evidence provenance in a separate remediation; **feature development should not resume yet**.

RESOLVER_GROUNDING_REMEDIATION_PARTIAL
'''
(B/'RESOLVER_GROUNDING_REMEDIATION_REPORT.md').write_text(txt,encoding='utf-8')
print('wrote report; changed rows',len(rows),'classes',dict(classes))
