import json
import sqlite3
from pathlib import Path
from collections import Counter
from providers import ROOT

def run():
    out=ROOT/'output'; s=json.loads((out/'summary.json').read_text()); e=json.loads((ROOT/'evaluation/results.json').read_text())
    c=sqlite3.connect(out/'candidates.sqlite'); r=sqlite3.connect(out/'registry.sqlite')
    lines=['# CUMA registry POC results','', 'Run date: 27 October 2026 (Asia/Singapore). Input: CUMA v1 (ENG Only). Ontology: unchanged Substance Ontology 0.2.0.','',
        'This is a deliberately bounded seed registry. Every source record and name/alias was locally analyzed; only the first 120 eligible unique preferred-name requests were budgeted for external corroboration. Low coverage is intentional.','', '| Measure | Count |','|---|---:|',f"| Total CUMA records | {s['total_cuma_records']:,} |",f"| Preferred names with validated local molecular candidate graphs | {s['molecular_candidates']:,} |"]
    lines.append(f"| Local candidates within narrow admission envelope, before corroboration | {s['local_candidates_within_admission_envelope']:,} |")
    for status in ['EXACT','UNRESOLVED','CONFLICT','OUT_OF_SCOPE','INVALID']: lines.append(f"| {status} | {s['statuses'].get(status,0):,} |")
    for key,label in [('canonical_substances','Canonical Substances created'),('multi_cuma_exact_clusters','Multi-CUMA exact clusters'),('alias_claims_accepted','CUMA alias occurrences accepted'),('alias_claims_held','CUMA alias occurrences held/rejected'),('stored_aliases','Distinct stored aliases including validated preferred names')]: lines.append(f'| {label} | {s[key]:,} |')
    lines+=['','The local molecular-candidate count is not a confirmed in-scope count. A parsable graph does not establish that a material is a discrete molecule. EXACT records are confirmed admissions under the narrow v1 envelope; other molecular and form claims remain unadjudicated. Alias occurrence counts include repeated source strings; stored aliases are deduplicated within each Substance.','', '## Principal decision reasons','', '| Reason | Records |','|---|---:|']
    for reason,n in sorted(s['principal_failure_reasons'].items(),key=lambda x:-x[1]): lines.append(f'| {reason} | {n:,} |')
    lines+=['','## Evaluation','',f"13 unit/integration test methods passed before the full run. The explicit name gold set contains {e['metrics']['records']} cases and {e['metrics']['automatic_admissions']} automatic admissions. Admission precision: {e['metrics']['admission_precision']:.0%}; alias promotion precision: {e['metrics']['alias_precision']:.0%}; false-merge rate: {e['metrics']['false_merge_rate']:.0%}; abstention: {e['metrics']['abstention_rate']:.1%}; coverage: {e['metrics']['coverage']:.1%}.",'', 'These metrics describe only the small engineering gold set, including 15 graph pairs (13 negative pairs) and four alias claims (one promoted). They are not statistically representative CUMA precision measurements and have not received independent expert adjudication. The test labels are never used as production identity evidence.','', '## Representative difficult cases','', '| CUMA index | Name | Result / diagnostic |','|---|---|']
    selected=set()
    for status in ['EXACT','CONFLICT','OUT_OF_SCOPE','INVALID','UNRESOLVED']:
        for i,name,reason in c.execute('SELECT cuma_index,name,diagnostic FROM candidate WHERE status=? ORDER BY cuma_index LIMIT 3',(status,)):
            selected.add(i); lines.append(f"| {i} | {(name or '').replace('|','/')} | {status}: {reason} |")
    lines+=['','### Held aliases on accepted records','']
    shown=0
    for i,name,raw in c.execute("SELECT cuma_index,name,evidence_json FROM candidate WHERE status='EXACT' ORDER BY cuma_index"):
        ev=json.loads(raw)
        bad=[a for a in ev['alias_decisions'] if a.get('relation')]
        if bad:
            lines.append(f"- CUMA {i}, {name}: "+'; '.join(f"`{x['alias']}` → {x['relation']}" for x in bad[:3]))
            shown+=1
        if shown==8: break
    if not shown: lines.append('No structurally resolved alternate-form alias examples among accepted records; unresolved aliases remain in candidate evidence.')
    lines+=['','## Limits and safeguards','',
        '- Canonical IDs are fresh, snapshot-local SUB numbers. No CUMA index or external identifier is used as the Substance ID.',
        '- Automatic admissions exclude stereo, isotope, charge, multicomponent and complex-form cases. Their original graphs remain in audit evidence; no salt stripping or parent selection occurs.',
        '- Only PubChem is queried externally. CAS/EC/ChEBI identifiers are not fabricated or extracted from unvalidated alias strings.',
        '- Alias promotion uses separate OPSIN interpretation plus equality to the externally corroborated graph. Each alias does not receive its own external lookup.',
        '- Unknown material families remain unresolved; regex scope screening is not a comprehensive materials classifier.',
        '- Reference InChI via JNA checks RDKit molfile serialization. It is not an independent source attestation.',
        '- Exact keys combine graph and full InChIKey; no formula, name-overlap, parent-view or transitive ambiguous merge is used.',
        '- MolStandardize parent views exist only in development diagnostics. No ontology or relationship table was changed.',
        '- Full candidate evidence and provider responses are local audit data. The registry itself contains exactly five tables.','']
    (ROOT/'CUMA_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    coverage=out/'legacy_coverage.json'
    if coverage.exists():
        rows=json.loads(coverage.read_text(encoding='utf-8')); v=rows[0]
        text='# Legacy-table candidate-presence coverage\n\nRead-only database-side aggregates, 27 October 2026. No legacy records downloaded or reconciled.\n\n'
        text+=f"Matched by at least one channel: **{v['matched_any_channel']} / {v['canonical_substances']} ({float(v['coverage']):.1%})**. Not matched: **{v['not_matched']}**.\n\n"
        text+='| Measure | Result |\n|---|---:|\n'
        for k,value in v.items(): text+=f'| {k} | {value} |\n'
        text+='\nChannel counts are non-exclusive. Alias matching means candidate presence, not canonical equivalence. InChIKey matches also do not override this registry’s graph-specific identity policy. CAS channel is zero eligible identifiers in this POC, not evidence of legacy CAS absence. Alias scope: exact literals in substance_name_all plus English master, IUPAC, JChem, compound and scientific names. No case/whitespace folding.\n\nSQL: `output/legacy_coverage.sql`. Canonical input is restricted to the accepted registry; aggregation occurs in Trino against the source table.\n'
        text+='\nSuccessful query ID: `2114922003525357569` (SUCCEEDED; one aggregate row). Initial query `2114921724801273858` failed with an array-constructor argument limit. Its SQL is preserved in `output/legacy_coverage_failed_array_limit.sql`; the corrected query concatenates smaller arrays with identical matching semantics.\n'
        (ROOT/'LEGACY_COVERAGE_REPORT.md').write_text(text,encoding='utf-8')
    print('Reports written')

if __name__=='__main__': run()
