"""Render frozen evaluation results; never executes or tunes the resolver."""
import json
from collections import Counter
from pathlib import Path
from freeze_and_prepare import H,B,read,sha,save

def pct(v):return 'not assessable' if v is None else f'{100*v:.2f}%'
def text(s):return str('' if s is None else s).replace('|','\\|').replace('\n',' ')
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |']+['| '+' | '.join(text(c) for c in row)+' |' for row in rows])
def ratio(c,n):return f'{c}/{n} ({pct(c/n if n else None)})'
def precision(m):
    e=m['automatic_exact'];return ratio(e['correct'],e['correct']+e['false_positive'])
def interval(v):return 'not assessable' if v is None else f'{100*v[0]:.2f}%–{min(100,100*v[1]):.2f}%'
def primary_links(r):
    return '; '.join('['+e['provider']+']('+e['url']+')' for e in r['evidence'] if 'pubchem.ncbi.nlm.nih.gov' not in e['url'] and 'opsin.ch.cam.ac.uk' not in e['url'])

frozen=read(H/'METRICS_FROZEN.json')
for p,v in frozen['files'].items():assert sha(H/p)==v,p
a=read(H/'ASSESSMENT.json');assert a['metrics_freeze_sha256']==sha(H/'METRICS_FROZEN.json')
m=read(H/'metrics.json');sample=read(H/'SAMPLE_FROZEN.json');selection=read(H/'steward/selection.json')
forms=read(H/'by_reference_form.json');aliases=read(H/'alias_comparison.json');pairs=read(H/'near_form_pairs.json');copairs=read(H/'coassigned_pairs.json');refpairs=read(H/'reference_exact_pairs.json');routes=read(H/'retrieval_routes.json');usage=read(H/'provider_usage.json');supp=read(H/'supplemental_review.json');tax=read(H/'taxonomy.json');dis=read(H/'disagreements.json')
review=read(H/'POST_UNBLINDING_REVIEW.json');assert review['metrics_freeze_sha256']==sha(H/'METRICS_FROZEN.json')
e=m['automatic_exact'];ab=m['abstention'];al=m['alias_promotion'];merge=m['false_merges']
refs=[r for n in (1,2,3) for r in read(H/f'packet_{n}/reference.json')]
allalias=Counter(x['judgment'] for r in refs for x in r['alias_judgments'])
lines=['# Second fresh form-aware holdout evaluation','',a['lead'],'',
'## Sampling and leakage controls','',
f"The frozen sample contains **{m['records']} previously unused CUMA records**, seed **{sample['seed']}**, from {sample['eligible']:,} eligible records after excluding {sample['excluded']:,} of {sample['source_records']:,} source records. This deliberately enriched capability sample does not estimate population prevalence.",'',
'Exclusions cover the original 300 records, first 360-record holdout, development/manual-review/contradiction examples, regression literals, exact preferred-name and known alias overlaps, and obvious duplicate source names. Source-only lexical selection never read current predicted outcomes. Full eligible IDs, exclusion names/indices, source workbook hash, implementation hashes and original sample packets were saved before adjudication. All existing registries and protected files remain unchanged.','',
table(['Candidate sampling category','Selected records (overlapping)'],sorted(selection['candidate_tags'].items())),'',
f"There are {len(pairs)} frozen lexical pair groups. These hints are not reference chemistry: some name transformations identify ordinary duplicates or constitutional differences rather than the hinted form. Actual reference forms and pair outcomes are reported below. {a['sampling_limitations']}",'',
'## Adjudication and evidence independence','',
'Three fresh agents with no inherited project conversation received only original indices, preferred names, aliases, the unchanged molecular identity framework and independent-investigation instructions. They were not given strata, expected gaps, resolver candidates or predictions. Access isolation was procedural on a shared filesystem, not an operating-system barrier. Every original alias occurrence was adjudicated before promotion decisions were available. A separate supplemental packet was excluded from holdout metrics.','',
'References preserve explicit molecular forms and track URLs, queries, provider records, available lineage and uncertainty. Shared database records/mirrors are one lineage; database synonym membership or a shared Standard InChIKey alone cannot establish SAME. Independent public retrieval and name interpretation were combined with standalone RDKit validation and focused authoritative-reference investigation. A parser result alone was not sufficient. Strong evidence with uncertain upstream independence is identified as such.','',
a['adjudication_limitations'],'',
'Every reference packet was frozen and hashed before the single resolver execution. Independent QA checked record/alias coverage, strict full structures, generated InChI/InChIKey and required identity dimensions. No label was revised after unblinding to improve agreement. Reference UNRESOLVED due to insufficient evidence remains unverified; documented inherent ambiguity is assessed as nonadmissible.','',
'## Overall results','',
table(['Metric','Result'],[
 ('Automatic EXACT',e['admissions']),('Adjudicable EXACT precision',precision(m)),('Confirmed false-positive EXACT',e['false_positive']),('Unverified EXACT admissions',e['unverified']),('Confirmed EXACT recall',ratio(m['correct_exact_recall']['correct'],m['correct_exact_recall']['reference_exact'])),('Reference-EXACT records withheld',ab['excessive']),('Correct-abstention precision',ratio(ab['correct'],ab['correct']+ab['excessive'])),('Correct-abstention recall',ratio(ab['correct'],ab['reference_nonadmissible'])),('False merges / assessable coassigned pairs',ratio(merge['count'],merge['assessed_pairs'])),('Unassessed coassigned pairs',merge['unassessed_pairs']),('Abstention (all non-EXACT)',ratio(ab['nonexact'],m['records'])),('Five-status agreement',ratio(m['status_agreement']['count'],m['records']))]),'',
table(['Status','Reference','Resolver'],[(s,m['expected_status'].get(s,0),m['predicted_status'].get(s,0)) for s in ['EXACT','UNRESOLVED','CONFLICT','OUT_OF_SCOPE','INVALID']]),'',
f"Among non-admissions, {ab['correct']} are supported abstentions, {ab['excessive']} withhold reference-confirmed identities, and {ab['unverified']} remain unassessable. Adjudicable precision excludes {e['unverified']} inconclusive admissions; it is not a claim that all admissions were independently confirmed. {a['overall_interpretation']}",'',
f"Descriptive Wilson 95% intervals: admission precision {interval(e['wilson95'])}; alias precision {interval(al['wilson95'])}. These do not correct for enriched sampling, duplicate concepts or correlated reference evidence.",'',
'## Capability-specific results','',
table(['Frozen reference-form group','N','EXACT admissions','Admission precision','Confirmed recall','Abstention','Alias precision'],[(k,v['records'],v['automatic_exact']['admissions'],precision(v),ratio(v['correct_exact_recall']['correct'],v['correct_exact_recall']['reference_exact']),pct(v['abstention']['rate']),ratio(v['alias_promotion']['correct'],v['alias_promotion']['correct']+v['alias_promotion']['incorrect'])) for k,v in forms.items()]),'',
'Categories are nonexclusive blinded-adjudicator classifications, not sampling strata. Empty or small positive denominators cannot support broad conclusions. '+a['form_interpretation'],'',
'Diagnostic category-membership sensitivity, excluding the misclassified neutral cyclic compound 5684 only from the three affected form groups (all primary scores and labels above remain frozen):','',
table(['Form group','N','Admissions','Assessed precision','Confirmed recall','Abstention'],[(tag,forms[tag]['records']-1,forms[tag]['automatic_exact']['admissions']-1,ratio(forms[tag]['automatic_exact']['correct'],forms[tag]['automatic_exact']['correct']+forms[tag]['automatic_exact']['false_positive']-1),ratio(forms[tag]['correct_exact_recall']['correct'],forms[tag]['correct_exact_recall']['reference_exact']),ratio(forms[tag]['abstention']['nonexact'],forms[tag]['records']-1)) for tag in ['protonation_charge','salt','multicomponent']]),'',
'## Alias evaluation','',
f"All **{sum(allalias.values())} original alias occurrences** were labelled before predictions: {allalias.get('SAME',0)} SAME, {allalias.get('DIFFERENT',0)} DIFFERENT and {allalias.get('UNRESOLVED',0)} UNRESOLVED. The resolver promoted **{al['promoted']}** claims: **{al['correct']} confirmed correct, {al['incorrect']} confirmed incorrect, {al['unverified']} unverified**. Adjudicable alias precision is **{ratio(al['correct'],al['correct']+al['incorrect'])}**. Preferred names stored as aliases are excluded from this promotion metric.",'',
a['alias_interpretation'],'',
'## Merge and near-form safety','',
table(['Frozen source-pair outcome','Count'],sorted(Counter(p['result'] for p in pairs).items())),'',
f"All coassignments were assessed separately: {len(copairs)} pairs, {merge['assessed_pairs']} assessable and {merge['unassessed_pairs']} unassessed. Independent reference graphs identify {len(refpairs)} exact-equivalent source pairs across the whole sample. Coassignment precision and exact-duplicate recovery are different questions; withholding both sides does not demonstrate successful exact matching.",'',
table(['Reference-exact pair recovery across the whole sample','Count'],sorted(Counter(p['result'] for p in refpairs).items())),'',
a['near_form_interpretation'],'',
table(['CUMA pair','Reference relation','Resolver outcome'],[(f"{p['a']} / {p['b']}",p['reference_relation'],p['result']) for p in pairs]),'',
'## Evidence-retrieval generalization','',
'Route use is distinguished from necessity. Older-path attribution uses saved original-name evidence and the documented old sufficiency conditions; it is a counterfactual inference, not a second resolver run. Ambiguous causal attribution is UNKNOWN. Different providers or multiple queries are not automatically independent evidence. The [per-admission retrieval appendix](second_form_aware_holdout/retrieval_admissions.md) records every admission, route, lineage, reference verdict and older-path inference.','']
route_rows=[]
for label in ['full InChIKey','InChI/complete structure','validated original alias','GSRS','supplied identifier','validated provider name']:
    v=[r for r in routes if r['predicted_status']=='EXACT' and label in r['supporting_increment_routes']]
    necessary=[r for r in v if r['older_path_counterfactual']=='WOULD_REMAIN_UNRESOLVED']
    route_rows.append((label,len(v),sum(r['reference_verdict']=='CORRECT' for r in v),sum(r['reference_verdict']=='INCORRECT' for r in v),sum(r['reference_verdict']=='UNVERIFIED' for r in v),len(necessary)))
lines += [table(['Supporting admission route','Used','Confirmed','Incorrect','Unverified','Older path inferred unresolved'],route_rows),'',a['retrieval_interpretation'],'',
table(['Provider','HTTP requests / budget','Observed cache hits','Cached request failures'],[(k,f"{v['http_requests']} / {v['budget']}",v['observed_cache_hits'],v['cache_statuses'].get('ERROR',0)) for k,v in usage['providers'].items()]),'',
'Runtime caches started empty and remained separate from adjudicator caches. Cache hits are reconstructed from repeated recorded URLs, excluding in-memory query deduplication; detailed HTTP failures, request utilization and query modes are preserved in `provider_usage.json`. No budgets, routes, adapters or retries were changed after outcomes. '+a['execution_limitations'],'',
'## Complete disagreement taxonomy','',
table(['Dominant cause','Substantive disagreements','Confirmed identities withheld'],[(k,n,tax['confirmed_identity_losses'].get(k,0)) for k,n in sorted(tax['disagreements'].items(),key=lambda x:(-x[1],x[0]))]),'',
'Every disagreement has a case-level classification, expected/predicted result, resolver reason and reference evidence in [the complete disagreement appendix](second_form_aware_holdout/disagreements.md). Attribution records dominant observed gates; a gate can conceal a second limitation. Confirmed errors, unverified predictions, conservative abstentions and reference uncertainty remain separate. '+a['taxonomy_interpretation'],'',
'### Confirmed unsafe admissions','',
table(['CUMA / preferred name','Blinded reference → resolver','Retrieval route','Specific cause'],[(str(r['cuma_index'])+' / '+r['preferred_name'],r['expected']+' → '+r['predicted'],', '.join(r['routes']),r['cause']+'. '+r['explanation']) for r in review['safety_cases']]),'',
'### Evaluation limitations found during review','',
'These are separate annotations, not changes to reference outcomes, original form tags, comparison logic or frozen metrics.','',
table(['Case(s)','Issue','Effect on interpretation'],[(str(r.get('case',r.get('cases'))),r['issue'],r['impact']) for r in review['methodological_issues']]),'',
'## Supplemental independent review — excluded from holdout metrics','',
table(['CUMA','Independent review','Reason / key evidence'],[(r['cuma_index'],r['review'],r['reason']+' '+primary_links(r)) for r in supp]),'',
a['supplemental_interpretation'],'',
'## Ranked remaining capabilities and ontology disposition','',
'This ranking was made only after metrics and disagreements were frozen. Confirmed identity losses inform it alongside safety, deterministic feasibility, cross-source applicability, scope and policy implications.','',
table(['Rank / capability','Confirmed losses','Safety and feasibility; policy boundary'],[(f"{n}. {r['capability']}",r['confirmed_losses'],r['assessment']) for n,r in enumerate(a['ranked_gaps'],1)]),'',
f"**One primary next capability: {a['primary_next_capability']}.** {a['recommendation']}",'',
a['ontology_disposition'],'',
'## Reproducibility and integrity','',
'The audit package contains [sample/exclusion hashes](second_form_aware_holdout/SAMPLE_FROZEN.json), [frozen adjudication](second_form_aware_holdout/ADJUDICATION_FROZEN.json), [frozen metrics](second_form_aware_holdout/METRICS_FROZEN.json), [retrieval attribution](second_form_aware_holdout/retrieval_routes.json), [provider usage](second_form_aware_holdout/provider_usage.json), [alias comparison](second_form_aware_holdout/alias_comparison.json), [supplemental evidence](second_form_aware_holdout/supplemental_review.json), [post-unblinding methodological review](second_form_aware_holdout/POST_UNBLINDING_REVIEW.json), [ranked assessment](second_form_aware_holdout/ASSESSMENT.json) and [final verification](second_form_aware_holdout/FINAL_VERIFICATION.json). Registry output is a separate evaluation snapshot. No full CUMA canonicalization was performed or recommended.','',f"**{a['conclusion']}**",'']
(B/'SECOND_FORM_AWARE_HOLDOUT_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
appendix=['# Complete second-holdout disagreement appendix','','Frozen results; no reference relabeling.','',table(['CUMA','Preferred name / alias','Reference','Resolver','Class / dominant cause','Evidence and reason'],[(r['cuma_index'],r.get('preferred_name',r.get('alias')),r.get('expected_status',r.get('reference_judgment')),r.get('predicted_status','PROMOTED'),str(r['disagreement_type'])+' / '+str(r['dominant_cause']),r.get('reference_reason','')+'; '+r.get('resolver_reason','')+'; '+' '.join(e.get('url','') for e in r.get('evidence',[]))+' '+' '.join(r.get('evidence_urls',[]))) for r in dis]),'']
(H/'disagreements.md').write_text('\n'.join(appendix),encoding='utf-8')
def lineage_text(r):
    return '; '.join(sorted({json.dumps(p,ensure_ascii=False,sort_keys=True) for p in r['lineage']}))
retrieval=['# Per-admission retrieval audit','','Derived from frozen traces. Route use is nonexclusive and does not prove causal necessity. Each row retains provider provenance; multiple hits from one upstream lineage are not independent confirmation. Full query records and non-admission contradictions remain in retrieval_routes.json.','',table(['CUMA / preferred name','Supporting increment routes','Reference verdict','Older-path inference / basis','Near or conflicting discoveries','Supporting provenance'],[(str(r['cuma_index'])+' / '+r['preferred_name'],', '.join(r['supporting_increment_routes']) or 'none recorded',r['reference_verdict'],r['older_path_counterfactual']+' / '+r['counterfactual_basis'],len(r['near_or_conflicting_discoveries']),lineage_text(r)) for r in routes if r['predicted_status']=='EXACT']),'']
(H/'retrieval_admissions.md').write_text('\n'.join(retrieval),encoding='utf-8')
print('Rendered report and complete disagreement appendix from frozen metrics.')
