import json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda name:json.loads((H/name).read_text(encoding='utf-8'))
a=read('analysis.json');p=read('provider_probe.json');ctx=read('live_probe.json')
lines=['''# Provider qualification report

## Model and boundaries

The qualification layer combines a static, typed [capability profile](provider_capabilities.py), exact correspondence, validated returned structure and the existing dimension-wise comparator. It does not score or rank providers, count votes, or require per-response human certification. A provider that exposes a representation is not assumed to preserve every form. `CORROBORATES`, `CONTRADICTS`, `NO_MATCH`, `UNAVAILABLE` and `NON_DISCRIMINATING` remain distinct. The last three never veto an otherwise supported result. A complete deterministic name needs one qualifying corroborator; a complete explicit typed structure does not, though an independently established contradiction still blocks it. Missing source specificity cannot be supplied by a provider.

Correspondence is limited to a literal returned name/synonym matching the original preferred name or alias; an exact source-supplied provider identifier; or a full InChIKey computed from a source-supported structure and checked against both the returned key and locally parsed graph. GSRS requires a complete adapter-validated moiety graph. Case variants, fuzzy lookup, formula and general substructure/similarity lookup do not qualify. An exact-name search alone is insufficient when the exact returned name is unavailable. Key matches are not fixed-tautomer proof. `SOURCE_DEPENDENCE_UNKNOWN` and `SOURCE_INDEPENDENT` may qualify; `SOURCE_DEPENDENCE_KNOWN` cannot. Known dependence must be carried in provenance; there is no general automatic detection of direct copying, and cross-database independence is not inferred.

| Provider | Adapter correspondence routes | Representation and conservative limits |
|---|---|---|
| PubChem | exact returned IUPAC name; source CID; full InChIKey | Standardized SMILES, InChI, InChIKey and CID. Stereo/isotopes checked per graph. Tautomer-sensitive, charged or multicomponent candidates held as non-discriminating because normalization/form preservation is not established. |
| ChEBI | literal returned curated name/synonym; source ChEBI ID; full InChIKey | Released three-star discrete structure, SMILES and standard InChI/key. Same conservative tautomer/charge/component holds. An ontology synonym by itself does not establish identity. |
| GSRS | literal returned name; source UNII | Only approved complete chemical records with validated molfile, SMILES, InChI/key and matching integer moieties; explicit graph can discriminate tautomer/charge/components in this bounded adapter. Broader substances, incomplete stereo and unsupported moieties are excluded. Current live examples below did not validate an eligible GSRS record. |
| CompTox/DSSTox | exact returned search value; source DTXSID/DTXCID or CAS; full InChIKey | SMILES plus locally checked provider InChI/key where present. Charged, multicomponent and tautomer-sensitive forms are held as non-discriminating; DSSTox representative structures are not assumed to preserve a source form. |

Capabilities are grounded in the [PubChem PUG-REST tutorial](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest-tutorial), [PubChem standardization documentation](https://pubchem.ncbi.nlm.nih.gov/docs/standardization-service), [ChEBI documentation](https://www.ebi.ac.uk/chebi/about), [FDA GSRS registration guide](https://www.fda.gov/media/169513/download), [EPA DSSTox description](https://www.epa.gov/comptox-tools/distributed-structure-searchable-toxicity-dsstox-database) and [EPA CTX client](https://github.com/USEPA/ctx-python/blob/main/src/ctxpy/chemical.py). The distinction between standardized InChI and fixed-form structures is also relevant; see the [InChI FAQ](https://www.inchi-trust.org/download/104/inchi-faq.pdf). Capability profiles are conservative implementation choices, not claims that every provider standardizes every form in the same way.

## Independent example probes

Six independently chosen names per public provider were attempted: ethanol, (R)-butan-2-ol, acetate, sodium acetate, deuterium oxide and 2-pyridone. They cover simple, stereo, charge, salt, isotope and tautomer cases. The examples were chosen independently of the 400-record replay; their absence from all CUMA records was not checked. The results are observational, not an accuracy benchmark. The complete per-record structures, features, statuses and exclusions are in [provider_probe.json](provider_qualification/provider_probe.json). `SUCCESS` with no eligible record means the search completed but yielded no record passing the adapter gate. `INCOMPLETE` does not mean no database record exists.

| Provider | Input | Lookup status | Returned eligible record and qualification |
|---|---|---|---|''']
for x in p:
    res='; '.join(f"{r['record_id']}: {r['qualification']} ({r['reason']})" for r in x['records']) or 'none'
    lines.append(f"| {x['provider']} | {x['query']} | {x['status']} | {res} |")
lines.append('''
## Authenticated CompTox smoke test

Five exact-name lookups used 11 bounded live requests; a later reproduction used only the response cache. All rows below actually returned SMILES, InChI and InChIKey in the detail response, checked locally. The extra deuterium-oxide record conflicts under the exact returned-name claim; it is not silently discarded. Per-record features and comparison are in [live_probe.json](provider_qualification/live_probe.json). The API key is read from the existing local configuration; a scan found it in zero new report, cache, script or log files.

| Exact-name query | DTXSID / DTXCID | Observed qualification |
|---|---|---|''')
for x in ctx:
 for r in x['records']:
    lines.append(f"| {x['query']} | {r['DTXSID']} / {r['DTXCID']} | {r['qualification']}: {r['reason']} |")
lines.append('''
## Tests and offline development replay

The 12 new deterministic tests pass, covering exact name/ID, unknown and known dependence, inconsistent keys, name case, tautomer and salt normalization, stereo contradiction, unavailable provider, source completeness and an end-to-end one-corroborator admission. [Test log](provider_qualification/qualification_tests.log). The latest combined existing plus new suite ran **173 tests and has 24 failures**. Several older fixtures assume manually certified `TEST` records or blanket form preservation, while others expect admissions now held by the conservative profiles. These failures were retained for review; they are not proof that all changes are safe. [Full test log](provider_qualification/tests_latest.log). The original generic `pytest` discovery also encounters duplicate archived test modules; the explicit unittest suite avoids that collection problem.

The frozen 400-record development set was replayed **offline** using copies of previous provider caches; this is not a new blinded validation. No prior registry was modified. Results: **11 EXACT, 363 UNRESOLVED, 4 CONFLICT, 22 OUT_OF_SCOPE**. Replay registry verification passed (11 exact reconciliations revalidated, zero duplicate or orphan rows). [Freeze](provider_qualification/frozen.json), [replay log](provider_qualification/replay.log), [full analysis](provider_qualification/analysis.json). No claim of precision or readiness to scale follows from this reused development set.

Query-state counts below are non-exclusive **query counts**, not record counts; a record can have several lookups. Zero states are explicit.

| Provider | CORROBORATES | NON_DISCRIMINATING | CONTRADICTS | NO_MATCH | UNAVAILABLE |
|---|---:|---:|---:|---:|---:|''')
for provider in ('PubChem','ChEBI','GSRS','CompTox'):
 counts=[a['provider_query_states'].get(provider+':'+s,0) for s in ('CORROBORATES','NON_DISCRIMINATING','CONTRADICTS','NO_MATCH','UNAVAILABLE')]
 lines.append('| '+provider+' | '+' | '.join(map(str,counts))+' |')
lines.append('''
## Recovered admissions

All 11 were UNRESOLVED in the immediately preceding replay. Each uses a source preferred-name claim, OPSIN `ESTABLISHED`, source-form `SUPPORTED`, an exact local graph comparison and `SOURCE_DEPENDENCE_UNKNOWN`; each final reason is `INDEPENDENT_EXACT_FORM_CORROBORATION`. “Dimensions” are those used by the qualifying comparison. Other provider/query states are shown per admission. Complete per-record claims, source-form diagnostics, comparison dimensions, queries and provenance are in [analysis.json](provider_qualification/analysis.json); this includes conflicting aliases that were held back. Exact admission is not independent validation of the source name.

| CUMA index and preferred name | Qualifying provider / record | Route and correspondence | Dimensions | Other query states |
|---|---|---|---|---|''')
for x in a['admissions']:
    good=[e for e in x['evidence_states'] if e.get('state')=='CORROBORATES']
    g=good[0];prov=g['provenance'];dims=', '.join(g['required_dimensions'])
    other='; '.join(f"{q['provider']} {q['query']['kind']}:{q['state']}" for q in x['provider_states'] if not (q['provider']==g['provider'] and q['query']['kind']==prov['query_type'] and q['query']['value']==prov['query']))
    lines.append(f"| {x['cuma_index']} {x['name'].replace('|','/')} | {g['provider']} {g['record_id']} | {prov['query_type']} / {g['correspondence_basis']} | {dims} | {other or 'none'} |")
lines.append('''
## Historical safety cases and remaining work

The sulfate/sulfite case 5684, relative-stereo cases 5997 and 23839, and glucose-form case 30142 remain UNRESOLVED in the 400 replay. The historical dithiazole tautomer case was independently re-run with old offline caches and remains UNRESOLVED / `NO_INDEPENDENT_CORROBORATION`; no case-specific runtime rule was added. [Probe](provider_qualification/case5_probe.json).

The current charge/component/tautomer holds are deliberately broad and can lose valid admissions. Whether each returned name and graph proves the asserted form remains a source-specific limitation; real GSRS examples did not pass the bounded smoke gate. The known-source-dependence classification relies on provenance supplied to the adapter, so unrecorded copying can remain unknown. Existing element, coordination, carbon-free multicomponent and other capability guards remain unchanged and need a separately grounded treatment. Conflicting legacy tests, recovered admissions and the new qualification logic need independent review and a fresh blinded evaluation before scale-up. Registry integrity is not a measure of chemical precision.

Recommendation: the layer is usable for constrained research and further review, but not yet qualified for scaling or production admission given the failing regression suite, incomplete real-provider coverage and unmeasured blinded precision.

PROVIDER_QUALIFICATION_PARTIAL
''')
(B/'PROVIDER_QUALIFICATION_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
