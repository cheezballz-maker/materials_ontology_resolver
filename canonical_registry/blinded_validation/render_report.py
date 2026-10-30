"""Render frozen-reference comparison only. Does not access or change registry data."""
import json
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parent
def read(name): return json.loads((ROOT/name).read_text(encoding='utf-8'))
def pct(v): return 'N/A' if v is None else f'{v:.2%}'
def c(v): return str(v).replace('|','/').replace('\n',' ')
def reference_link(i):
    for n in (1,2,3):
        if i in IDS[n]: return f'[frozen evidence](blinded_validation/packet_{n}/reference.json)'
def evidence(row):
    text=c(row.get('reference_reason') or '')
    if row.get('expected_smiles'):text+='; reference `'+c(row['expected_smiles'])+'`'
    if row.get('predicted_smiles') and row.get('exact_verdict')=='CONFIRMED_INCORRECT':text+='; engine `'+c(row['predicted_smiles'])+'`'
    links=[]
    sources=[e for e in row.get('evidence',[]) if isinstance(e,dict)]
    sources.sort(key=lambda e: any(host in str(e.get('url','')) for host in ('pubchem.ncbi.nlm.nih.gov','cactus.nci.nih.gov','/es_search/')))
    for e in sources:
        if 'http_status' in e and e['http_status']!=200:continue
        if '/es_search/' in str(e.get('url','')):continue
        if isinstance(e,dict) and isinstance(e.get('url'),str) and e['url'].startswith(('https://','http://')):
            label=c(e.get('source') or e.get('provider') or 'source').replace('[','').replace(']','')
            if 'https://' in label or 'http://' in label:label='Reference source'
            link='['+label+']('+e['url']+')'
            if link not in links:links.append(link)
    return text+' '+'; '.join(links[:3])+' '+reference_link(row['cuma_index'])
def table(rows,reason=True):
    lines=['| CUMA index | Preferred name | Blinded expected | Engine | Key evidence | Likely cause |','|---:|---|---|---|---|---|']
    for row in rows:
        lines.append(f"| {row['cuma_index']} | {c(row['preferred_name'])} | {row['expected_status']} | {row['predicted_status']} | {evidence(row)} | {c(row.get('likely_cause','')) if reason else ''} |")
    return lines

IDS={n:{r['cuma_index'] for r in read(f'packet_{n}/records.json')} for n in (1,2,3)}
def run():
    m=read('metrics.json');rows=read('comparison.json');spot=read('spot_check_set.json');manifest=read('comparison_manifest.json')
    aliases=read('alias_disagreements.json');held=read('held_supported_aliases.json')
    a=m['automatic_exact'];p=m['alias_promotion'];f=m['false_merges']
    # Conservative rule fixed before seeing results: insufficient verification or
    # material confirmed safety errors cannot justify scaling automatic admission.
    insufficient=(a['reference_verification_rate'] or 0)<0.9 or (p['confirmed_correct_lower_bound'] or 0)<0.9
    unsafe=a['confirmed_incorrect']>0 or p['confirmed_incorrect']>0 or f['confirmed_pairs']>0
    conclusion='NOT_READY_TO_SCALE' if insufficient or unsafe else 'SCALE_WITH_CAUTION'
    lines=['# CUMA blinded validation report','',f'**Conclusion: {conclusion}.**', '',
    f"The frozen review corroborates {a['verified_correct']}/{a['admissions']} automatic admissions and {p['verified_correct']}/{p['occurrences']} promoted alias occurrences. One admission retains a source-level tautomer conflict; the remaining uncertainty and only {f['adjudicable_coassigned_pairs']} testable merge pairs prevent a reliable scale-up claim.",'',
    '## Design and blinding','',
    '300 original CUMA records were sampled with seed 20261027. Sampling includes the full existing automatic-admission cohort, all existing provider-conflict records, and randomly selected challenge strata; overlapping traits are assigned one primary sampling stratum. The sampling steward used engine categories to assemble strata but did not assign reference judgments. Three fresh adjudicator agents received shuffled original indices, preferred names and aliases only. They received no earlier chat history, engine outputs or stratum labels. This is procedural blinding on a shared filesystem, not OS-enforced isolation or independent human expert review. The parent had prior exposure to some results and did not assign reference labels.','',
    'Every packet was frozen with a SHA256 before the comparison program opened predictions. Frozen files were verified unchanged, as were both source databases. The canonicalization pipeline and registry were not altered. Reference labels were not revised after unblinding. The [protocol](blinded_validation/PROTOCOL.md), [300-record reference index](blinded_validation/reference_index.json), and [full comparison](blinded_validation/comparison.json) accompany this report. The reference index includes exact structures, full InChIKeys and corroborated SAME aliases; original aliases, alternate-form diagnostics and complete evidence remain in the three frozen packets.','',
    '| Primary sampling stratum | Records |','|---|---:|']
    lines += [f'| {k} | {v} |' for k,v in m['sampling_strata'].items()]
    lines+=['','The reference judgment asks what molecular identity is independently supported, not whether the engine had query budget available. Expected EXACT versus engine UNRESOLVED can therefore represent intentional conservative abstention. Challenge strata are lexical/candidate screens, not ground-truth classifications (a chloride name need not denote an ionic salt). This enriched sample does not estimate whole-CUMA coverage or outcome prevalence.','',
    '## Summary metrics','',
    '| Measure | Result |','|---|---|',
    f"| Automatic EXACT precision among adjudicable admissions | {a['verified_correct']}/{a['verified_correct']+a['confirmed_incorrect']} = {pct(a['precision_adjudicable'])} |",
    f"| Verified-correct lower bound over all automatic EXACT | {a['verified_correct']}/{a['admissions']} = {pct(a['confirmed_correct_lower_bound'])} |",
    f"| Automatic EXACT unverified / contradicted | {a['unverified']} / {a['confirmed_incorrect']} |",
    f"| Contradicted admissions: incompatible exact graphs / reference CONFLICT | {sum(x['exact_verdict']=='CONFIRMED_INCORRECT' and x['expected_status']=='EXACT' for x in rows)} / {sum(x['predicted_status']=='EXACT' and x['expected_status']=='CONFLICT' for x in rows)} |",
    f"| Precision identification interval, treating unresolved references as unknown | {pct(a['confirmed_correct_lower_bound'])}–{pct(a['precision_upper_bound'])} |",
    f"| False merges | {f['confirmed_pairs']} pairs in {f['confirmed_clusters']} clusters |",
    f"| False-merge rate, adjudicable coassigned pairs | {f['confirmed_pairs']}/{f['adjudicable_coassigned_pairs']} = {pct(f['rate_adjudicable_pairs'])} |",
    f"| Unassessed coassigned pairs | {f['unassessed_coassigned_pairs']} |",
    f"| Alias-promotion precision among adjudicable occurrences | {p['verified_correct']}/{p['verified_correct']+p['confirmed_incorrect']} = {pct(p['precision_adjudicable'])} |",
    f"| Alias verified-correct lower bound over all promotions | {p['verified_correct']}/{p['occurrences']} = {pct(p['confirmed_correct_lower_bound'])} |",
    f"| Alias promotions unverified / contradicted | {p['unverified']} / {p['confirmed_incorrect']} |",
    f"| Exact status agreement | {pct(m['outcome_agreement'])} |",
    f"| Engine abstention (UNRESOLVED / 300) | {pct(m['abstention_rate_unresolved'])} |",
    f"| Engine non-admission (all non-EXACT / 300) | {pct(m['non_admission_rate'])} |",'',
    'UNRESOLVED reference evidence is not a proven false identity. “Contradicted” includes a different exact graph or a substantive frozen CONFLICT/OUT_OF_SCOPE/INVALID judgment; a reference CONFLICT rejects automatic certainty without necessarily proving one alternative structure correct. Alias metrics count promoted source occurrences, excluding insertion of preferred names alone. An alias can be judged correct only against a verified subject identity and additional alias-specific source attestation. The interval above reflects unresolved labels, not a statistical confidence interval.','',
    'Before unblinding, a methodology audit found that many original SAME alias labels relied on one PubChem alias lookup against a separately corroborated preferred structure. Those frozen labels were retained. Still-blinded reviewers added separately frozen alias attestations; metrics treat unsupported original SAME/DIFFERENT claims as unverified. This evidence refinement preceded prediction access and did not change the recommendation thresholds.',
    f"Supplementary alias evidence across all source occurrences: {m['alias_attestation_counts']}. Each packet contains alias_attestations.json and ALIASES_FROZEN.json.",'',
    '| Status | Expected | Predicted |','|---|---:|---:|']
    for s in ['EXACT','UNRESOLVED','CONFLICT','OUT_OF_SCOPE','INVALID']:lines.append(f"| {s} | {m['expected_counts'][s]} | {m['predicted_counts'][s]} |")
    pairs=Counter((x['expected_status'],x['predicted_status']) for x in rows if x['disagreement'])
    lines+=['','The one false-positive EXACT classification is CUMA 5, **5-Amino-3H-1,2,4-dithiazole-3-thione**. The engine, PubChem and Fisher support amino-thione `Nc1nc(=S)ss1`; the frozen review found a Wiley SpectraBase record under the same name represented as imino-thiol `N=c1nc(S)ss1`. Both regenerate Standard InChIKey `YWZHEXZIISFIDA-UHFFFAOYSA-N`. This is a missed conflicting-evidence finding under the strict tautomer policy, **not proof that the admitted amino-thione graph is wrong**. Human review should inspect the source assignment before treating it as a confirmed chemical misidentification. [Fisher](https://www.fishersci.nl/nl/en/browse/cas/6846-35-1), [Wiley SpectraBase](https://spectrabase.com/spectrum/LHSxszxMwZO).','',
    f"Of the {m['disagreement_records']} record disagreements, {pairs[('UNRESOLVED','EXACT')]} are unverified engine admissions and {pairs[('EXACT','UNRESOLVED')]} are independently supported identities on which the engine abstained. Low status agreement therefore combines reference uncertainty, conservative engine scope/budget decisions, and substantive evidence differences; it is not the automatic identity-error rate."]
    lines+=['','## All record-level disagreements','',
    'The table includes every status disagreement and every incompatible graph within matching EXACT statuses. Evidence links point to hash-checked frozen per-index judgments, including reference URLs and alias-level findings.','']
    disagree=[r for r in rows if r['disagreement']]
    lines+=table(disagree) if disagree else ['None.']
    lines+=['','## Alias-promotion disagreements and uncertainty','',
    '| CUMA index | Preferred name | Promoted alias | Reference judgment | Verdict / evidence |','|---:|---|---|---|---|']
    for x in aliases:
        j=x['reference_alias_judgment']
        at=x['alias_attestation']
        lines.append(f"| {x['cuma_index']} | {c(x['preferred_name'])} | {c(x['alias'])} | {j['judgment']} | {x['verdict']}; {at['attestation_status']}: {c(at.get('reason',''))} {reference_link(x['cuma_index'])} |")
    if not aliases:lines.append('| — | — | — | — | No contradicted or unverified promotions |')
    lines+=['','### Independently supported aliases held by the engine','',
    'These are conservative alias-recall differences on verified EXACT subjects, not false promotions.','',
    '| CUMA index | Preferred name | Held alias | Evidence |','|---:|---|---|---|']
    for x in held:lines.append(f"| {x['cuma_index']} | {c(x['preferred_name'])} | {c(x['alias'])} | {reference_link(x['cuma_index'])} |")
    if not held:lines.append('| — | — | — | None |')
    lines+=['','## Human spot-check packet','',
    'Selections use seed 20261028. The separate [spot_check_set.json](blinded_validation/spot_check_set.json) contains all evidence summaries. Abstentions are sampled across primary strata and expected outcomes.','',
    f"### Random EXACT agreements ({len(spot['exact_agreements'])}/20 requested)",'']
    lines+=table(spot['exact_agreements'],False)
    if len(spot['exact_agreements'])<20:lines+=['','Fewer than 20 independently verified EXACT agreements exist; no replacements were invented.']
    lines+=['','### All false-positive EXACT outcomes','']
    lines+=table(spot['all_confirmed_false_positive_exact']) if spot['all_confirmed_false_positive_exact'] else ['None confirmed. Unverified admissions are listed in the disagreement table and machine-readable spot-check packet.']
    lines+=['','### All detected false merges','']
    if spot['all_false_merges']:
        for x in spot['all_false_merges']:lines.append(f"- {x['substance_id']}: CUMA {x['cuma_indices']}; frozen structures {x['reference_smiles']}.")
    else:lines.append(f"None detected among {f['adjudicable_coassigned_pairs']} adjudicable coassigned pairs; {f['unassessed_coassigned_pairs']} pairs remain unassessed. This does not establish a population false-merge rate.")
    lines+=['',f"### Representative abstentions ({len(spot['representative_abstentions'])}/20)",'']
    lines+=table(spot['representative_abstentions'])
    lines+=['','## Audit and interpretation limits','',
    f"- Adjudicator-reported independent_source_support flags: {m['reference_independent_source_support']}; verified automatic admissions carrying a true flag: {m['verified_admissions_with_independent_source_support']}/{a['admissions']}. Flag interpretation varies: some reviewers conservatively use unknown for supplier provenance, while others mean an additional primary/curated assertion. These are not counts of statistically independent experimental determinations.",
    '- References may share upstream data. PubChem/NCI agreement is not automatically independent corroboration; packet judgments record source dependence and stronger curated/supplier evidence where obtained.',
    '- RDKit is shared with the engine for structure validation, creating a common-tool failure mode. No engine OPSIN output or acceptance logic was used as reference evidence.',
    '- The admission census measures the current bounded cohort; future eligible records may differ. Challenge strata are deliberately enriched, and the sampled coassigned-pair denominator is small.',
    '- Agent adjudication with preserved references is reviewable evidence, not a substitute for independent expert sign-off. All uncertain references and alias judgments remain visible.',
    f"- Predictions were opened at {manifest['predictions_opened_at_utc']}, after every packet freeze. [Comparison manifest](blinded_validation/comparison_manifest.json) records freeze timestamps, hashes and unchanged source-database hashes.",'',
    '## Final conclusion','',f'**{conclusion}**. ']
    if unsafe:lines[-1]+=f"The frozen comparison found {a['confirmed_incorrect']} automatic EXACT outcome with conflicting tautomer evidence, {p['confirmed_incorrect']} contradicted alias promotions and {f['confirmed_pairs']} false-merge pairs. The conflict does not prove the chosen graph wrong. More decisively, {a['unverified']}/{a['admissions']} admissions and {p['unverified']}/{p['occurrences']} alias promotions remain unverified, and only {f['adjudicable_coassigned_pairs']} merge pairs were testable. This validation does not yet establish sufficiently reliable admission and alias precision for expansion; targeted independent expert review and stronger reference coverage are needed."
    elif insufficient:lines[-1]+='No unsupported claim of safety is made from unresolved references: verification coverage is insufficient to establish reliable admission and alias precision before increasing the external-query budget.'
    else:lines[-1]+='Observed admission and alias precision support only controlled expansion: source dependence, agent-based adjudication, an enriched sample and a small merge denominator still limit generalization.'
    (ROOT.parent/'CUMA_VALIDATION_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(conclusion)

if __name__=='__main__':run()
