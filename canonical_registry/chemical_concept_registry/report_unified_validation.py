"""Audit the frozen replay and render its review report."""
import json
import statistics
from collections import Counter
from pathlib import Path

from validate_unified_v11 import BASELINE, H, P, TrustedWarehouseAdapter, read, sha
from comparison_session import qualify_source
from unified_chemical import describe, reconcile_graphs


def main():
    path=H/'unified_validation_v11.json'
    d=read(path)
    old=read(BASELINE)
    reuse=read(H/'concept_reuse_validation_v11.json')
    assert sha(BASELINE)==d['frozen_baseline_sha256']
    assert {p:sha(Path(p)) for p in d['hashes_before']}==d['hashes_before']==d['hashes_after']
    packets={p['source_record_id']:p for p in map(json.loads,(P/'sampled_records.jsonl').read_text(encoding='utf8').splitlines())}
    adapter=TrustedWarehouseAdapter(batch_file=P/'sampled_records.json',expected_sha256=read(P/'sampling_manifest.json')['source_json_sha256'])
    targeted=[]
    changes=[]
    for r in d['records']:
        b,c=r['baseline'],r['corrected']
        if b['outcome']!=c['outcome']:
            r['change_explanation']={
                'EXACT_SUBSTANCE_MATCH': ('Continued past an unparsed nonbinding name association; exact supplied evidence qualified and complete search established the unique equivalent.'
                    if b['diagnostics']==['NAME_NOT_DETERMINISTICALLY_INTERPRETED'] else
                    'Replaced incomplete index-only search with complete snapshot comparison; same pilot identity was uniquely equivalent.'),
                'CONFLICT':'Continued past an unparsed nonbinding name association and reached a contradiction between the available validated graphs.',
            }[c['outcome']]
            changes.append(r)
        if r['previous_pilot_outcome']=='NEW_SUBSTANCE_CREATED':
            sid=r['source_id']
            q=qualify_source(adapter.adapt(packets[sid]).incoming.concept)
            graph=q['graph_view']
            pilot=r['pilot_registry_structure']
            relation=reconcile_graphs(describe(graph),describe(pilot))[1] if graph and pilot else 'NOT_ESTABLISHED'
            r['prior_admission_audit']={'source_qualification':{k:q[k] for k in ('state','binding_valid','graph_view','obligations','source_conflicts')},
                'registry_membership':bool(pilot),'supplied_graph_vs_pilot_graph':relation,
                'scope':'Comparison of bound supplied graph to the historical registry entry; not permission to dismiss a name conflict.'}
            if r['stratum']=='exact_pilot_admission':
                targeted.append(r)
        s=c.get('substance_search')
        if s:
            # Retain coverage counts and indexed/relevant routes. The same
            # exhaustive fallback route is otherwise repeated 560 times.
            retrieval=s['retrieval']
            ids=retrieval.pop('candidate_ids',None)
            if ids is not None:
                retrieval['candidate_count']=len(ids)
                relevant=set(retrieval['indexed_candidate_ids'])|{x['candidate_substance_id'] for x in s['relevant_comparisons']}
                retrieval['routes']={key:value for key,value in retrieval['routes'].items() if key in relevant}
                retrieval['full_ids_reproducible_from_snapshot']=retrieval['search_complete']
    assert len(targeted)==8 and len(changes)==16
    assert [r['source_id'] for r in d['records']]==[r['source_id'] for r in old['records']]
    assert all(r['pilot_substance_id']==r['corrected']['substance_id'] for r in changes if r['corrected']['outcome']=='EXACT_SUBSTANCE_MATCH')
    assert all('EXACT_REFINEMENT_NOT_QUALIFIED' not in r['corrected']['diagnostics']
               and ((r['corrected'].get('substance_search') or {}).get('reconciliation') or {}).get('binding',{}).get('kind')!='QUALIFIED_NAME_IDENTITY'
               for r in d['records'])
    path.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    outcome_order=['EXACT_SUBSTANCE_MATCH','EXACT_SUBSTANCE_NOT_IN_REGISTRY','SUBSTANCE_SEARCH_INCOMPLETE',
                   'CHEMICAL_CONCEPT_CREATED','CHEMICAL_CONCEPT_REUSED','UNRESOLVED','CONFLICT']
    counts='\n'.join(f"| {k} | {old['outcomes'].get(k,0)} | {d['outcomes'].get(k,0)} |" for k in outcome_order)
    table=[]
    for r in targeted:
        b,c=r['baseline'],r['corrected']
        search=c.get('substance_search')
        before='Indexed only; '+str(b['substance_comparisons'])+' compared' if b['substance_comparisons'] else ', '.join(b['diagnostics'])
        after='Complete; 1 equivalent, 559 different' if search else 'Stopped before retrieval'
        dims=[k for x in c['evidence'] for k,v in (x.get('dimensions') or {}).items() if v=='DIFFERENT']
        rationale='; incompatible dimensions: '+', '.join(dict.fromkeys(dims)) if dims else ''
        table.append(f"| `{r['source_id']}` | {r['pilot_substance_id']} | {before} | {after} | {c['substance_id'] or c['outcome']}{rationale} |")
    timing=lambda row: statistics.median(x[row]['elapsed_seconds'] for x in d['records'])
    compared=lambda row: sum(x[row]['substance_comparisons'] for x in d['records'])
    prior=[r for r in d['records'] if r['previous_pilot_outcome']=='NEW_SUBSTANCE_CREATED']
    screened=reuse['open_records']
    over_limit=[r for r in d['records'] if r['stratum']=='over_64']
    at_limit=sum('STEREO_ENUMERATION_LIMIT' in r['corrected']['diagnostics'] for r in over_limit)
    search_rows=[r['corrected'] for r in d['records'] if r['corrected']['substance_comparisons']]
    t=read(H/'unified_validation_tests.json')
    report=f"""# Unified Chemical Resolution v1.1 validation

## Conclusion

The corrected resolver matched **14 of 65** records to existing Substance IDs, including **seven of the eight** records in the targeted exact-admission stratum. The eighth remains a conflict. All 14 matches agreed with their historical pilot IDs, with one exact equivalent and 559 chemically different candidates each. The replay produced 19 broader concepts in a disposable fixture. Six generated alternative representations of real records reused their concept IDs in a separate experiment. These results support a subsequent **bounded INCI evaluation**; they are not an INCI readiness claim or an independent measure of chemical accuracy.

## Exact routing and completeness

The baseline used `exhaustive=False` and a ceiling of eight indexed candidates. Five of the eight targeted records actually compared only one candidate apiece. The eight-candidate ceiling did not cut those searches short: the index-only procedure itself could not certify snapshot coverage or uniqueness. Two other targeted records stopped because OPSIN could not read a warehouse display label containing formatting markup. Those labels are explicitly classified as nonbinding associations by the trusted adapter. A parser failure on such a label now remains in the audit trail and does not veto an independently qualified exact supplied graph; an explicit user name, parser warning or parsed contradiction is not waived. The last record stopped on conflicting structure dimensions and still does. This is not a registry absence or a retrieval defect.

The wrapper returns `SUBSTANCE_SEARCH_INCOMPLETE` for an otherwise eligible unresolved bounded search and distinguishes truncation from incomplete snapshot coverage. A complete no-match requires the unchanged matcher to exclude every candidate chemically. Eligibility, source binding and snapshot stability still gate exact matches. The replay used the existing exhaustive procedure because the available index routes are candidate generators, without a completeness proof. The ceiling remains available for bounded calls, which can abstain explicitly. No new index, comparator or admission policy was introduced.

## Name, structure and identifier evidence

The router retains original claims and records parsed structures, InChI warnings, compatible specificity and conflicting dimensions. When the existing comparator plus bounded stereo containment establishes that an exact graph refines an open one, a read-only comparison view can prioritize the qualified exact witness. Redundant projections that encode the missing stereo are preserved in provenance. A name-derived witness retains its derived status and requires the existing official InChI and corroboration checks; it cannot borrow an explicit-structure exemption. An exact supplied secondary graph can retain its original structural authority. Opposite specified configurations and incompatible constitutional, form or identifier evidence do not become exact or broader assignments.

The positive name-refinement control uses actual OPSIN, official InChI, a disposable Substance fixture and **synthetic** corroboration. With corroboration removed it withholds the ID. Name-only OPSIN success remains insufficient. The 65-record replay did not exercise the newly qualified refinement branch; its gains came from complete search and the treatment of unparsed nonbinding names.

## Frozen 65-record replay

| Outcome | Before | After |
|---|---:|---:|
{counts}

Two previous abstentions became conflicts once reconciliation could proceed past an unparsed nonbinding association. The [record results](chemical_concept_registry/unified_validation_v11.json) carry the before/after evidence and a specific explanation for each of the {len(changes)} changed outcomes. The cohort includes {len(prior)} historically admitted records across all strata; eight were explicitly sampled in the named exact-admission stratum. No inferred duplicate, accession, name or historical ID was used as a chemical match.

| Targeted source record | Historical Substance | Baseline stopping point | Corrected comparison | Final |
|---|---|---|---|---|
{chr(10).join(table)}

All eight historical IDs are present. The bound supplied graph agrees with the historical registry graph for each; that does not settle the contradictory record, whose parsed evidence remains incompatible. The JSON includes literal names and structural fields, validated parsed graphs, adapter qualification, registry graph, official validation when reached, candidate dimensions, search coverage and outcome. For the conflict, the historical-graph check is diagnostic only.

## Concept reuse and boundary controls

The [reuse results](chemical_concept_registry/concept_reuse_validation_v11.json) separate three evidence sources. Screening the 1,000 frozen pilot packets found {screened} open-stereo graph records, with zero pairs sharing the screening constitution key. This is a bounded duplicate screen, not evidence of uniqueness across the warehouse or of provenance independence. Six chemically validated alternative traversals derived from actual records reused the respective original IDs (6/6); they are not independent warehouse observations. Five synthetic comparison controls covered opposite known configurations, broader/narrower containment, constitutional isomers, the same display name for different meanings, and an unsupported comparison. The real cohort itself produced no reuse. The 64-isomer ceiling blocked {at_limit} of the {len(over_limit)} records sampled for that limit; it did not block any of the 14 exact matches. The ceiling was retained.

## Tests, performance and protection

{t['summary']} The controls include exact match and complete no-match, bounded search, stale snapshots, unsupported exact chemistry, ambiguous or failed names, structure and identifier contradictions, alternative traversal, rollback, idempotency and concurrent creation. Substance creation and association writes are disabled in this router.

Exact comparisons increased from **{compared('baseline'):,}** to **{compared('corrected'):,}**. Median end-to-end time moved from {timing('baseline'):.3f} s to {timing('corrected'):.3f} s across all rows. For the {len(search_rows)} rows that reached exhaustive matching, median end-to-end time was {statistics.median(r['elapsed_seconds'] for r in search_rows):.1f} s. Each search covered all {d['registry_count']} identities; the corrected run including setup took {d['elapsed_seconds']:.1f} s. Use explicit budgets for interactive workloads and preserve the incomplete result rather than guessing. A validated completeness-preserving prefilter would be a separate follow-up.

Before/after SHA-256 hashes agreed for ontology v0.4.0, the canonical seed and frozen pilot (including associations), and both previous Concept fixtures. The replay used a fresh disposable fixture and passed SQLite integrity and foreign-key checks. Reproduce with `validate_unified_v11.py`, `validate_concept_reuse.py` and this report script; the original evaluation remains intact.

## Readiness and limits

Proceed with an offline, source-diverse INCI holdout using typed structure and qualified nomenclature claims, with human review of conflicts and cases where registry coverage is incomplete. Keep mixtures, polymers, alloys and other broad material meanings outside this molecular evaluation. The narrow Concept rules still withhold unsupported charged, isotope-specific, multicomponent and advanced-stereo inputs; name refinement is bounded to supported compatible graphs. Independent real-record concept reuse and prospective expert validation remain open. No production normalization or ontology expansion is recommended from these results.

**UNIFIED_CHEMICAL_RESOLUTION_V1_1_PARTIAL**
"""
    (H.parent/'UNIFIED_CHEMICAL_RESOLUTION_V1_1_VALIDATION_REPORT.md').write_text(report,encoding='utf8')


if __name__=='__main__':
    main()
