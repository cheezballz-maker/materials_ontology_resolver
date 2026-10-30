"""Render frozen holdout results; qualitative decision is supplied after scoring."""
import json
from datetime import datetime,timedelta,timezone
from collections import Counter
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def esc(s):return str(s if s is not None else '—').replace('|','\\|').replace('\n',' ')
def pct(x):return 'N/A' if x is None else f'{100*x:.2f}%'
def frac(a,b):return f'{a}/{b} ({pct(a/b if b else None)})'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(esc(c) for c in row)+' |' for row in rows])
def main():
    m=read(H/'metrics.json');rows=read(H/'comparison.json');aliases=read(H/'alias_comparison.json');s=read(H/'SAMPLE_FROZEN.json');selection=read(H/'steward/selection.json');decision=read(H/'decision.json');freeze=read(H/'ADJUDICATION_FROZEN.json');verify=read(H/'verification_summary.json')
    a=m['automatic_exact'];r=m['correct_exact_recall'];ab=m['abstention'];al=m['alias_promotion'];f=m['false_merges'];agree=m['status_agreement']
    actual=read(H/'by_reference_form.json');tags=read(H/'by_sampling_tag.json');summary=read(H/'predictions/summary.json')
    sample_time=datetime.fromisoformat(s['frozen_at_utc']).astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S SGT')
    md=['# Fresh form-aware CUMA holdout evaluation','',decision['lead'],'','## Scope and leakage controls','',f"360 CUMA records, seed `{s['seed']}`, source workbook SHA-256 `{s['source_sha256']}`. The sample was frozen at {sample_time}; all references were frozen before resolver execution. The cohort is deliberately enriched for capability boundaries and is not representative of whole-CUMA prevalence.",'',
        'Selection used original names/aliases only, with no resolver outcome or parser-result filtering. It excluded the prior 300 indices, known development examples and conservative name/alias overlaps: 1,545 source records in total. Known development leakage was checked by index and lexical overlap; undocumented historical exposure or unrecognized chemical synonyms cannot be ruled out. Source workbook, sample, selection procedure and protected implementation artifacts were hashed.',
        '', 'Three fresh agents with no inherited chat history independently investigated 120 shuffled records each. They received only their original input packet and the authoritative identity framework, with no sampling stratum, previous results, resolver diagnostics or predictions. Access isolation was procedural on a shared filesystem, not an OS sandbox. No holdout predictions were generated until all three references had been hashed and structurally validated. A pre-unblinding clarification kept primary identity and misleading-alias judgments separate.',
        '', 'References use independent external investigation and bare RDKit validation; no project resolver/provider logic was imported for adjudication. EXACT requires corroboration beyond a single database hit. Source dependence and uncertainty remain explicit. The independent graph scorer preserves stereo, isotopes, charge, hydrogen/bond placement and components; Standard InChIKey alone cannot establish exactness. No label was changed after unblinding.',
        '',table(['Primary source-text stratum','Records'],sorted(Counter(selection['primary_strata'].values()).items())),
        '', 'All 33 eligible solvate-keyword candidates were selected, including alias-only signals. These are not 33 established solvates: ethanolate/methanolate can denote alkoxides, and aliases can be misleading. Actual reference forms are reported separately below. No synthetic hydrate/solvate was substituted for a real CUMA record.',
        '', '## Overall metrics','',table(['Metric','Result'],[
            ['Automatic EXACT admissions',a['admissions']],['Adjudicable EXACT precision',frac(a['correct'],a['correct']+a['false_positive'])],['False-positive EXACT count',a['false_positive']],['Admissions with inconclusive reference',a['unverified']],['Confirmed-correct share of all admissions',frac(a['correct'],a['admissions'])],['Correct EXACT recall in reference EXACT',frac(r['correct'],r['reference_exact'])],['False merges / assessable coassigned pairs',frac(f['count'],f['assessed_pairs'])],['Unassessable coassigned pairs',f['unassessed_pairs']],['All non-EXACT predictions / records',frac(ab['nonexact'],m['records'])],['Internal UNRESOLVED / records',frac(ab['internal_unresolved'],m['records'])],['Correct-abstention precision among assessable non-admissions',frac(ab['correct'],ab['correct']+ab['excessive'])],['Correct-abstention recall over established non-admissible references',frac(ab['correct'],ab['reference_nonadmissible'])],['Reference-EXACT records lost to non-admission',ab['excessive']],['Non-admissions with inconclusive reference',ab['unverified']],['Alias-promotion precision among assessable occurrences',frac(al['correct'],al['correct']+al['incorrect'])],['Promoted aliases: correct / wrong / unverified',f"{al['correct']} / {al['incorrect']} / {al['unverified']}"],['Five-status agreement',frac(agree['count'],m['records'])]]),
        '', 'Reference UNRESOLVED due to insufficient evidence does not prove either correctness or error. Documented intrinsic ambiguity can justify abstention and identify inappropriate certainty. Correct-abstention precision excludes research-inconclusive references and counts lost reference EXACT records as excessive abstentions. Alias metrics count promoted original alias occurrences, not stored preferred names or deduplicated table rows. Zero detected false merges with a zero or small assessable denominator does not establish a population false-merge rate.',
        '',table(['Status','Reference','Resolver'],[(x,m['expected_status'].get(x,0),m['predicted_status'].get(x,0)) for x in ['EXACT','UNRESOLVED','CONFLICT','OUT_OF_SCOPE','INVALID']]),
        '', '## Capability results','', 'Nonexclusive frozen source-text tags; a record may occur in more than one row. “Potentially unspecified stereo” is a sampling heuristic, not a chemical judgment.', '',table(['Source tag','N','EXACT precision','Correct EXACT recall','Non-admission','Alias precision'],[(k,v['records'],frac(v['automatic_exact']['correct'],v['automatic_exact']['correct']+v['automatic_exact']['false_positive']),frac(v['correct_exact_recall']['correct'],v['correct_exact_recall']['reference_exact']),pct(v['abstention']['rate']),frac(v['alias_promotion']['correct'],v['alias_promotion']['correct']+v['alias_promotion']['incorrect'])) for k,v in tags.items()]),
        '', 'Adjudicator-assessed form categories, also nonexclusive. These are distinct from lexical sampling tags and can reflect an established form even when its exact molecular identity remains unresolved.', '',table(['Reference form','N','Resolver EXACT','EXACT precision','Correct EXACT recall','Non-admission','Alias precision','Status agreement'],[(k,v['records'],v['automatic_exact']['admissions'],frac(v['automatic_exact']['correct'],v['automatic_exact']['correct']+v['automatic_exact']['false_positive']),frac(v['correct_exact_recall']['correct'],v['correct_exact_recall']['reference_exact']),pct(v['abstention']['rate']),frac(v['alias_promotion']['correct'],v['alias_promotion']['correct']+v['alias_promotion']['incorrect']),pct(v['status_agreement']['rate'])) for k,v in actual.items()]),
        '',decision['form_discussion'],
        '', '## Disagreements and error taxonomy','', 'Every substantive status/structure disagreement and unverified admission is listed below. Causes are diagnostic hypotheses, not revised reference labels. Status disagreement between two non-admitting outcomes is distinguished from unsafe admission. The complete preserved structures, form dimensions and evidence are in `form_aware_holdout/comparison.json`.',
    ]
    overrides=decision.get('case_annotations',{})
    for title,subset in [
        ('Confirmed unsafe admissions / incorrect identities',[x for x in rows if x['exact_verdict']=='INCORRECT']),
        ('Reference-confirmed identities not admitted',[x for x in rows if x['abstention_verdict']=='EXCESSIVE']),
        ('Admissions not adjudicable with current reference evidence',[x for x in rows if x['exact_verdict']=='UNVERIFIED']),
        ('Other non-admission status disagreements',[x for x in rows if x['failure_type'] in ('NON_ADMISSION_STATUS_DISAGREEMENT','UNRESOLVED_REFERENCE_COMPARISON')])]:
        md+=['',f'### {title}','']
        if not subset:md+=['None.'];continue
        tab=[]
        for x in subset:
            links=[]
            for e in x['evidence']:
                if e.get('url'):
                    links.append(f"[{e.get('source','source')}]({e['url']})")
                if len(links)==2:break
            note=overrides.get(str(x['cuma_index']),{}).get('cause','; '.join(x['likely_causes']))
            tab.append([x['cuma_index'],x['preferred_name'],x['expected_status'],x['predicted_status'],x['resolver_reason'],x['reference_reason']+' '+', '.join(links),note])
        md += [table(['CUMA','Preferred name','Reference','Resolver','Diagnostic','Key reference evidence','Likely cause'],tab)]
    badaliases=[x for x in aliases if x['verdict']=='INCORRECT'];md+=['','### Incorrect alias promotions','']
    md += [table(['CUMA','Alias','Reference judgment','Evidence'],[(x['cuma_index'],x['alias'],x['reference_judgment'],x['reference_reason']+' '+', '.join(x['evidence_urls'])) for x in badaliases]) if badaliases else 'None detected among assessable promoted aliases.']
    merges=read(H/'false_merges.json');md+=['','### Detected false merges','',table(['Substance ID','CUMA indices'],[(x['substance_id'],', '.join(map(str,x['cuma_indices']))) for x in merges]) if merges else 'None detected; see assessable-pair denominator above.',
        '', '## Next capability, ranked after scoring','',decision['ranking_method'],'',table(['Rank','Capability gap','Holdout frequency','Confirmed identities lost','Safety risk','Deterministic feasibility / reuse'],[(i+1,x['gap'],x['frequency'],x['lost'],x['risk'],x['feasibility']) for i,x in enumerate(decision['ranking'])]),'',f"**Primary recommendation: {decision['primary_gap']}.** {decision['justification']}",
        '', '## Execution integrity and limitations','',f"The unchanged resolver processed exactly 360 frozen inputs once, with fresh engine HTTP caches and fixed caps of 1,800 PubChem / 3,000 ChEBI requests. Actual requests: {summary['pubchem_requests']} PubChem, {summary['chebi_requests']} ChEBI. Reference caches were not copied into engine evidence. The evaluation registry contains {summary['canonical_substances']} identities; it is isolated from the production registry. No resolver/admission/provider code, test, ontology, schema, previous reference or existing registry was changed.",
        '',verify['description'],'',decision['limitations'],
        '', 'The benchmark is a capability-enriched, agent-adjudicated holdout, not independent expert certification or an estimate of whole-CUMA prevalence. Shared underlying reference databases and shared graph tooling can correlate errors. Sparse positive cases limit form-specific conclusions. No tuning, retries designed to change outcomes, or development extension was performed during this task.',
        '', 'Audit artifacts: `SAMPLE_FROZEN.json`, `PROTOCOL_FROZEN.json`, `REFERENCE_GUIDANCE.json`, packet `reference.json`/`FROZEN.json`/`methodology.json` and raw evidence, `ADJUDICATION_FROZEN.json`, prediction databases/log, metrics by tag/form, comparison/alias/merge/gap files and `SCORING_MANIFEST.json`, all under `form_aware_holdout/`. The three packet methodologies document individual reference-source limitations.',
        '', f"**Core identity model:** {decision['core_model']}", '', f"**Ontology disposition:** {decision['ontology']}", '',decision['conclusion']]
    assert decision['conclusion'] in ('READY_FOR_BROADER_CUMA_RUN','TARGETED_RESOLVER_EXTENSION_REQUIRED','NOT_READY_FOR_SCALE')
    (B/'FORM_AWARE_HOLDOUT_REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print('Wrote',B/'FORM_AWARE_HOLDOUT_REPORT.md')
if __name__=='__main__':main()
