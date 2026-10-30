"""Report an interrupted pre-prediction stage; do not freeze provisional labels."""
import collections,hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
freeze=read(B/'FRESH_BLINDED_EVALUATION_FREEZE.json');sample=read(H/'SAMPLE_FROZEN.json');summary=read(H/'sample_summary.json')
changed=[n for n,v in freeze['implementation_hashes'].items() if sha(B/n)!=v]
externals=[n for n,v in freeze['external_hashes'].items() if sha(v['path'])!=v['sha256']]
assert sha(H/'fresh_sample.json')==sample['sample_sha256']
assert not (H/'RUN_STARTED.json').exists() and not (H/'REFERENCE_FROZEN.json').exists()
rows=[];packet_counts={}
for n in (1,2,3):
    p=H/f'packet_{n}';references=read(p/'reference.json');source=read(p/'records.json')
    assert len(references)==len(source) and {r['cuma_index'] for r in references}=={r['cuma_index'] for r in source}
    packet_counts[str(n)]=dict(collections.Counter(r['reference_status'] for r in references));rows+=references
assert len(rows)==400 and len({r['cuma_index'] for r in rows})==400
counts=dict(collections.Counter(r['reference_status'] for r in rows));uncertainty=dict(collections.Counter(str(r.get('reference_uncertainty') or 'not supplied') for r in rows if r['reference_status']=='UNADJUDICABLE'))
status=dict(implementation_changed=changed,contract_changed=externals,sample_intact=True,predictions_generated=False,reference_labels_frozen=False,reference_counts=counts,reference_uncertainty_counts=uncertainty,packet_counts=packet_counts)
(H/'PARTIAL_STATUS.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
reason='BLINDED_EVALUATION_INVALIDATED_BY_CODE_CHANGE' if changed else 'FRESH_BLINDED_EVALUATION_MIXED'
configured='yes' if freeze['runtime']['CTX_API_KEY_configured'] else 'no'
history=read(H/'historical_regressions.json')
lines=[f'''# Fresh blinded resolver evaluation — interrupted before prediction

**This evaluation is incomplete; no performance result or scale-readiness conclusion is available.** The automatic approval review rejected one adjudicator's bulk PubChem lookup because it would transmit the packet's preferred names to an external service and could disclose potentially sensitive source data. The rejection was not bypassed. Partial references are drafts, and no fresh-sample predictions were produced. The report's final `MIXED` marker denotes this interrupted state, not a measured accuracy result.

## Freeze and sample

The [implementation freeze](FRESH_BLINDED_EVALUATION_FREEZE.json) was recorded before sampling. Current production file hashes {'match' if not changed else 'DO NOT MATCH'} the freeze; contract/configuration hashes {'match' if not externals else 'DO NOT MATCH'}. OPSIN jar, ontology, schema and framework were hashed without including credentials. CTX_API_KEY configured: {configured}.

The [frozen sample](fresh_blinded_evaluation/fresh_sample.json) is a simple random sample without replacement of **{sample['sample_size']}** CUMA rows from **{sample['eligible_count']:,}** eligible rows, seed **{sample['seed']}**. The workbook had {sample['source_records']:,} rows; {sample['excluded_count']:,} were conservatively excluded using earlier holdout/development IDs, historical targeted indices, exact normalized name/alias overlaps, current test/report claims, and obvious duplicates of excluded names. The population is conditional on those exclusions, not all CUMA. Sampled duplicate rows were not intentionally enriched or removed. [Sample manifest](fresh_blinded_evaluation/SAMPLE_FROZEN.json) records IDs, hashes and detailed exclusions.

The source records contain {summary['alias_occurrences']} alias occurrences; {summary['records_with_aliases']} records have at least one alias and {summary['multiple_aliases']} have multiple aliases. There are {summary['malformed_alias_cells']} malformed alias cells and {summary['duplicate_preferred_name_groups']} exact preferred-name duplicate groups in this sample. Lexical tags, not chemical classifications: {summary['lexical_tags']}. No capability enrichment was used.

## Independent reference review

Three isolated reviewers received only source records and the identity framework, with no resolver outcomes. [Packet 1](fresh_blinded_evaluation/packet_1/METHODOLOGY.md), [packet 2](fresh_blinded_evaluation/packet_2/METHODOLOGY.md), and [packet 3](fresh_blinded_evaluation/packet_3/METHODOLOGY.md) describe methods and evidence limitations. Their provisional classifications total: {counts}. Unadjudicable cases by stated reason: {uncertainty}. A candidate-only lookup or unreviewed record is not a reference judgment or a negative case. These counts describe progress, not resolver performance.

The references have **not been frozen** because review remains incomplete. Consequently, the fresh sample was not passed to the resolver, and there is no `REFERENCE_FROZEN.json`, `RUN_STARTED.json`, fresh registry or predictions. That preserves the opportunity to finish independent adjudication and freeze the references before making any comparison.

## Metrics and analyses not yet available

Automatic EXACT precision and recall, status confusion, abstention correctness, false-positive reviews, false-merge rate, alias-promotion precision, typed versus name-derived paths, per-provider route states and availability, ambiguous-route cases, scope-guard impact, and fresh-registry integrity are **not measured**. No numerator, denominator, confidence interval or zero false-merge rate can responsibly be supplied. The frozen sample and partial review do not establish research, controlled-use or production readiness.

## Historical checks outside the sample

The five historical safety cases were rerun offline with existing caches and the frozen implementation; they do not contribute to fresh holdout metrics:
''']
for x in history:lines.append(f"- CUMA {x['cuma_index']}: {x['status']} ({'; '.join(x['reason_codes'])})")
lines.append(f'''
[Historical check details](fresh_blinded_evaluation/historical_regressions.json). No resolver code, capability profile, threshold or registry data was modified.

Next step: obtain approval for the rejected external disclosure, complete independent adjudication, freeze the reference labels, and only then run the frozen resolver with its normal provider adapters. The incomplete reference coverage and any provider availability limitations must be reported without treating unreviewed cases as negative.

{reason}
''')
(B/'FRESH_BLINDED_RESOLVER_EVALUATION_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(status,indent=2))
