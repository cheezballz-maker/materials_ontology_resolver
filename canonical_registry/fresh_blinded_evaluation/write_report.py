"""Build the review report only after frozen run and disagreement review."""
import collections,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
m=read(H/'evaluation_metrics.json');sample=read(H/'SAMPLE_FROZEN.json');summary=read(H/'sample_summary.json');freeze=read(B/'FRESH_BLINDED_EVALUATION_FREEZE.json');ref=read(H/'reference_adjudication.json');cases=read(H/'resolver_results.json');run=read(H/'run/summary.json');verification=read(H/'run/verification.json');historical=read(H/'historical_regressions.json')
status=read(H/'disposition.json')['status']
assert status in ('FRESH_BLINDED_EVALUATION_PASSED','FRESH_BLINDED_EVALUATION_MIXED','FRESH_BLINDED_EVALUATION_FAILED')
next_step='Investigate the identified unsafe admissions in a separate remediation task before considering another fresh validation.' if status=='FRESH_BLINDED_EVALUATION_FAILED' else 'Continue research and plan a further independent, larger and more completely adjudicated validation.'
assert verification['result']=='PASS'
precision=m['automatic_exact_precision'];recall=m['automatic_exact_recall'];pct=lambda n,d:('%.1f%%'%(100*n/d)) if d else 'not estimable'
abstention_total=sum(m['resolver_statuses'].get(s,0) for s in ('UNRESOLVED','CONFLICT','OUT_OF_SCOPE'))
ci=precision['clopper_pearson_95'];ci_text=f'{ci[0]*100:.1f}%–{ci[1]*100:.1f}%' if ci else 'not estimable'
refs=collections.Counter(x['reference_status'] for x in ref);uncertainty=collections.Counter(str(x.get('reference_uncertainty') or 'unspecified') for x in ref if x['reference_status']=='UNADJUDICABLE')
cross=m['cross_tab'];statuses=['EXACT','UNRESOLVED','CONFLICT','OUT_OF_SCOPE','INVALID'];columns=['REFERENCE_EXACT_IDENTITY','REFERENCE_UNRESOLVED','REFERENCE_CONFLICT_AMBIGUOUS','REFERENCE_OUT_OF_SCOPE','UNADJUDICABLE']
lines=[f'''# Fresh blinded resolver evaluation

## Freeze, sample and reference

The unchanged resolver was [frozen](FRESH_BLINDED_EVALUATION_FREEZE.json) before source sampling; all 400 reference records were [frozen independently](fresh_blinded_evaluation/REFERENCE_FROZEN.json) before predictions. The CUMA source workbook had {sample['source_records']:,} numbered records; {sample['excluded_count']:,} were conservatively excluded based on known prior holdout/development IDs, historical cases, exact normalized name/alias overlap, test/report claims and obvious duplicate names. From the remaining {sample['eligible_count']:,}, a simple random sample of **400** rows was selected without replacement using seed **{sample['seed']}**. The headline population is conditional on those exclusions, not all CUMA. No capability enrichment was used and sampled records were not replaced. The [sample and exclusion manifest](fresh_blinded_evaluation/SAMPLE_FROZEN.json) identifies the selection and hashes. A [source-only leakage check](fresh_blinded_evaluation/leakage_check.json) found zero overlaps with all three prior holdout packets and the listed historical cases. Exclusions rely on known artifacts and cannot prove every historical informal exposure was captured.

The sample contains {summary['alias_occurrences']} original alias occurrences; {summary['records_with_aliases']} records have aliases and {summary['multiple_aliases']} have multiple aliases. There are {summary['duplicate_preferred_name_groups']} duplicate preferred-name groups and {summary['malformed_alias_cells']} malformed alias cells. Lexical indicators, not definitive chemistry classifications: {summary['lexical_tags']}. CTX_API_KEY configured: {'yes' if freeze['runtime']['CTX_API_KEY_configured'] else 'no'}.

Three isolated adjudicators received source records and the identity framework without resolver outcomes. They used independent public lookups, cited sources and bare RDKit checks; no candidate from the resolver was supplied. References: {dict(refs)}. Unadjudicable reasons: {dict(uncertainty)}. **51 packet-2 records received candidate screening but no completed individual source/form adjudication**; they remain unadjudicable and are not negative judgments. Other unadjudicable cases include conflicting sources, unestablished forms and unavailable evidence. [Frozen references](fresh_blinded_evaluation/reference_adjudication.json) and [packet methodologies](fresh_blinded_evaluation/packet_1/METHODOLOGY.md), [2](fresh_blinded_evaluation/packet_2/METHODOLOGY.md), [3](fresh_blinded_evaluation/packet_3/METHODOLOGY.md) contain per-case evidence and limitations. Some public services may share upstream data; two URLs do not prove independent experimental provenance. Selective adjudication means the sample's random selection does not make the adjudicable subset automatically representative.

The reference-freeze manifest hashes the labels, per-case evidence claims, source packet files and methodologies; the separately retained raw HTTP response caches were not included in that manifest.

A subsequent read-only audit of the frozen references, performed without inspecting individual predictions, identified source-form, tautomer or stereo-mapping cautions in 15 reference cases. A separate [blind check of retained lookup responses](fresh_blinded_evaluation/BLIND_SOURCE_AMBIGUITY_AUDIT.json) found a reference name query returning multiple distinct structures. The frozen labels were not changed. The other cautions are in [reference quality notes](fresh_blinded_evaluation/REFERENCE_QUALITY_NOTES.json); {len(m['reference_quality_flagged_admissions'])} flagged cases were admitted EXACT. The primary metrics retain the frozen labels and should be interpreted alongside those cautions.

## Primary metrics and abstentions

Automatic EXACT precision among independently adjudicable admissions: **{precision['confirmed']}/{precision['adjudicable']} = {pct(precision['confirmed'],precision['adjudicable'])}**, with {precision['false']} assessed false positives and {precision['unadjudicable']} unadjudicable EXACT outcomes excluded. The exact 95% Clopper–Pearson interval is **{ci_text}**. The interval is conditional on the adjudicable subset and assumes binomial observations; it does not correct for selective missing reference labels, shared source ancestry, or provider budget exhaustion by processing order.

As a sensitivity check, excluding all admissions flagged in the blinded reference-quality audit gives {m['quality_sensitivity_precision']['confirmed']}/{m['quality_sensitivity_precision']['adjudicable']} = {pct(m['quality_sensitivity_precision']['confirmed'],m['quality_sensitivity_precision']['adjudicable'])}. This does not relabel the frozen references.

Automatic EXACT recall against reference-confirmed identities: **{recall['correct']}/{recall['reference_exact']} = {pct(recall['correct'],recall['reference_exact'])}**. This is conditional on the available reference identities. Resolver statuses: {m['resolver_statuses']}; UNRESOLVED, CONFLICT and OUT_OF_SCOPE together are {abstention_total}/{m['sample_size']} = {pct(abstention_total,m['sample_size'])}. Of non-EXACT decisions, {m['abstentions'].get('reference_identity_withheld',0)} had independently available preferred-name identities, {m['abstentions'].get('consistent_with_nonexact_reference',0)} were consistent with a non-exact reference category, and {m['abstentions'].get('unassessable',0)} were unassessable. The withheld identities are recall misses, not necessarily incorrect policy decisions: a source alias can conflict with an otherwise identifiable preferred name. Among {len(m['reference_exact_conflict_holds'])} CONFLICT holds with reference identities, an independently confirmed incompatible source alias was found in {sum(x['independently_confirmed_alias_mismatch'] for x in m['reference_exact_conflict_holds'])}; the others require alias review. Accordingly, an overall count of unjustified abstentions cannot be established from this reference set. Category differences among UNRESOLVED/CONFLICT/OUT_OF_SCOPE are visible below.

Excluding the quality-audit-flagged reference cases gives recall {m['quality_sensitivity_recall']['confirmed']}/{m['quality_sensitivity_recall']['reference_exact']} = {pct(m['quality_sensitivity_recall']['confirmed'],m['quality_sensitivity_recall']['reference_exact'])}.

| Resolver outcome | Reference exact identity | Reference unresolved | Reference conflict/ambiguous | Reference out of scope | Unadjudicable |
|---|---:|---:|---:|---:|---:|''']
for s in statuses:lines.append('| '+s+' | '+' | '.join(str(cross.get(s+'|'+c,0)) for c in columns)+' |')
lines.append('''
Provider-only disagreement is **not** treated as proof the source claim is internally contradictory; those references remain unadjudicable. Inherently underspecified cases with explicit reviewer support are grouped as reference unresolved. [Per-record results](fresh_blinded_evaluation/resolver_results.json) preserve the original reference label and reason.

## Identity errors, false merges and withheld identities
''')
false_reviews=[x for x in m['case_reviews'] if x['verdict']=='FALSE_POSITIVE']
if false_reviews:
 for x in false_reviews:lines.append(f"- CUMA {x['cuma_index']}: {x.get('dimension','other')} — {x.get('reason','')}. Evidence: {x.get('evidence','see error analysis')}.")
else:lines.append('No adjudicated false-positive EXACT was found; unadjudicable admissions were not counted as correct.')
reference_by_id={x['cuma_index']:x for x in ref}
unassessed=[x for x in cases if x['resolver_status']=='EXACT' and x['verdict']=='UNADJUDICABLE']
if unassessed:
 lines.append('\nUnadjudicable EXACT decisions requiring independent follow-up:')
 for x in unassessed:
    rr=reference_by_id[x['cuma_index']];links=', '.join(f"[source]({e['url']})" for e in rr.get('evidence',[]) if isinstance(e,dict) and e.get('url'))
    lines.append(f"- CUMA {x['cuma_index']} ({x['name']}): {rr.get('reason','Reference evidence insufficient.')} {links}")
fm=m['false_merge'];lines.append(f"\nFalse merges: **{fm['false']}/{fm['assessable_pairs']} assessable merged pairs**; {fm['unadjudicable_pairs']} additional merged pairs were not assessable. "+('The denominator is too small to estimate a meaningful false-merge rate.' if fm['assessable_pairs']<30 else ''))
guards={k:m['scope_guard_reason_counts'].get(k,0) for k in ('UNSUPPORTED_ELEMENT_CAPABILITY','UNSUPPORTED_MULTICOMPONENT_CAPABILITY','UNSUPPORTED_COORDINATION_CAPABILITY','UNSUPPORTED_DISCRETE_STRUCTURE_CAPABILITY')}
lines.append(f"\nDominant blockers for reference-confirmed withheld identities: {m['withheld_blockers']}. Each withheld case and its original reason is in [error analysis](fresh_blinded_evaluation/error_analysis.json); these categories are diagnostic, not a proposal to tune the resolver. The requested element, carbon-free multicomponent, coordination and discrete-structure guard reason occurrences are {guards}; all unsupported reason occurrences are {m['scope_guard_reason_counts']}. A record can contain multiple reason codes.")
n=m['name_path'];t=m['typed_source_path'];lines.append(f'''
## Source paths, aliases and providers

The sampled workbook supplies names and aliases, not typed source structures: typed-source count **{t['source_count']}**, with no path-specific safety estimate. Among name-derived records, {n['complete_interpretations']} had complete deterministic interpretations, {n['with_qualifying_route']} had a qualifying source-linked provider route, and {n['admitted']} were admitted EXACT: {n['admitted_correct']} confirmed, {n['admitted_false']} false, {n['admitted_unadjudicable']} unadjudicable. {n['withheld_no_qualifying']} complete interpretations were held for no qualifying corroborator. Each admission's provider, route, record, source dependence and comparison dimensions are retained in [evaluation metrics](fresh_blinded_evaluation/evaluation_metrics.json). No admitted name has only a candidate-derived identifier as corroboration. Qualifying routes with a provider-reported truncated search occurred in {sum(bool(x['truncated_qualifying_queries']) for x in m['admissions'])} admissions; truncation can conceal other records and should be considered when reviewing those routes.

Alias-decision counts: {m['alias_counts']}. Among promotions assessed against a matching reference subject, alias precision is {m['alias_counts'].get('confirmed',0)}/{m['alias_counts'].get('confirmed',0)+m['alias_counts'].get('incorrect',0)} = {pct(m['alias_counts'].get('confirmed',0),m['alias_counts'].get('confirmed',0)+m['alias_counts'].get('incorrect',0))}; unverified promotions and subject-mismatch reviews are not counted as confirmed. The source-occurrence count includes held aliases on unadmitted subjects. Independent review recorded {len(m['source_alias_conflicts'])} preferred-name/alias exact-form mismatches, separately listed with evidence in the [metrics artifact](fresh_blinded_evaluation/evaluation_metrics.json); these need not imply a rejected preferred name.

Provider-route query counts are non-exclusive and not votes:

| Provider | CORROBORATES | CONTRADICTS | PROVIDER_RECORD_AMBIGUOUS | NON_DISCRIMINATING | NO_MATCH | UNAVAILABLE |
|---|---:|---:|---:|---:|---:|---:|''')
for provider in ('PubChem','ChEBI','GSRS','CompTox'):
 states=('CORROBORATES','CONTRADICTS','PROVIDER_RECORD_AMBIGUOUS','NON_DISCRIMINATING','NO_MATCH','UNAVAILABLE')
 lines.append('| '+provider+' | '+' | '.join(str(m['provider_route_counts'].get(provider+'|'+s,0)) for s in states)+' |')
lines.append('\nEvery EXACT admission and its source-linked evidence:')
lines.append('\n| CUMA index and source name | Admission basis | Provider / route / record | Source dependence | Identity dimensions compared |\n|---|---|---|---|---|')
for x in m['admissions']:
    evidence=x['qualifying_evidence']
    if x['typed_source'] and not evidence:
        lines.append(f"| {x['cuma_index']} {str(x['name']).replace('|','/')} | explicit typed source | not required | not applicable | typed structure |")
    for e in evidence:
        prov=e.get('provenance',{});dimensions=', '.join(e.get('required_dimensions',[]))
        lines.append(f"| {x['cuma_index']} {str(x['name']).replace('|','/')} | complete name + CORROBORATES | {e.get('provider')} / {prov.get('query_type')} ({prov.get('query_origin')}) / {e.get('record_id')} | {e.get('source_dependence_classification')} | {dimensions} |")
if m['ambiguous_routes']:
 lines.append('\nEvery ambiguous provider route:')
 for r in m['ambiguous_routes']:
    detail='; '.join(str(x.get('record_id'))+' '+x.get('state','') for x in r.get('per_record_states',[]))
    lines.append(f"- CUMA {r['cuma_index']}: {r['provider']} {r.get('route')} / {r.get('query',{}).get('value')} — {detail}; final {r['resolver_status']}.")
else:lines.append('\nNo `PROVIDER_RECORD_AMBIGUOUS` route was observed in this run.')
lines.append(f'''
The resolver used the frozen production adapters with initially empty caches and the default budgets: PubChem 120, ChEBI 500, GSRS 200 and CompTox 20. Records are processed by CUMA index, so exhaustion and availability can differ by position; this is a limitation of this run, not a statement about chemistry. Requests used: PubChem {run.get('pubchem_requests')}, ChEBI {run.get('chebi_requests')}, GSRS {run.get('gsrs_requests')}, CompTox {run.get('comptox_requests')}. `UNAVAILABLE` is neutral. [Route audit](fresh_blinded_evaluation/provider_route_audit.json) includes query origin, record IDs and states.

## Registry integrity, historical checks and disposition

Registry verification: **{verification['result']}**, {verification['canonical_graphs']} canonical graphs and {verification['exact_reconciliations_revalidated']} exact reconciliations revalidated. Duplicate/orphan counts: {verification['counts']}. Integrity does not establish chemical precision. [Verification](fresh_blinded_evaluation/run/verification.json).

The [post-run integrity check](fresh_blinded_evaluation/integrity_check.json) confirms the implementation, contract, sample and frozen reference hashes match, and the prior registry and candidate snapshot remain unchanged. The key itself is not included in the report or artifacts.

Five historical safety cases were rerun offline outside the fresh sample: {[(x['cuma_index'],x['status']) for x in historical]}. They are not included in headline metrics. [Details](fresh_blinded_evaluation/historical_regressions.json).

{next_step} The incomplete/non-random adjudication, possible shared chemistry-source ancestry, finite query budget and any small admission or merged-pair denominators limit conclusions. This holdout does not establish production-scale readiness or broad controlled-use safety on its own. The element, coordination and carbon-free multicomponent guards remain technical debt and were not modified.

| Use | Disposition |
|---|---|
| Continued research development | Suitable with the reported findings and a separate remediation process if needed. |
| Fresh larger-scale validation | {'Defer until the identified unsafe admissions are investigated.' if status=='FRESH_BLINDED_EVALUATION_FAILED' else 'Possible after addressing reference-coverage and availability limitations.'} |
| Limited controlled use | Not established by this single, incompletely adjudicated holdout. |
| Production-scale canonicalization | Not established. |
''')
lines.append(status+'\n')
(B/'FRESH_BLINDED_RESOLVER_EVALUATION_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
