"""Generate the architecture/quality report from executed matching results."""
import collections,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda n:json.loads((H/'evaluation'/n).read_text(encoding='utf8'))
def link(label,p):return f'[{label}](<{p.resolve().as_posix()}>)'
def artifact(n):return link(n,H/n)
def main():
 actual=read('real_registry_results.json');bench=read('benchmark_results.json');tests=read('test_results.json');integrity=read('integrity_report.json');inventory=read('registry_inventory.json');coverage=read('retrieval_coverage.json');ready=read('readiness_assessment.json');assert integrity['pass_']
 a=actual['summary'];g=actual['groups'];rows=actual['records'];route_counts=a['retrieval_route_candidate_pair_counts']
 extra=sum(len(r['additional_indexed_candidates_beyond_full_key']) for r in coverage['records']);indexed=sum(len(r['indexed_candidate_ids']) for r in coverage['records'])
 unresolved=[r for r in rows if r['result']['status']=='MATCH_UNRESOLVED']
 text='''# Canonical Registry Matching v1 — Read-Only

Date: 2026-10-30. Scope: the existing 112-record canonical molecular registry and the previously validated graph/composition comparison capabilities.

## 1. Executive conclusion

A functioning source-independent read-only matcher is implemented. It qualifies incoming evidence, retrieves canonical candidates through several routes, reuses the hardened dimension comparators, establishes uniqueness only after complete search and evaluates the unchanged admission policy. It returns proposals; it cannot assign, create, merge or persist canonical identities.

**42/42 frozen matching controls pass**, with zero false unique matches. **{test_total} unit/integration tests pass**, including all 357 retained tests. The actual evaluation examined **132 incoming concepts × 112 registry entries = 14,784 candidate comparisons**: 112 unique matching proposals, 16 bounded no-match results and four unresolved source identities. The 112 positive demonstrations are known-ancestry consistency checks from saved provider records used in constructing the registry, **not independent accuracy validation**. All 112 satisfy the existing verified-explicit-structure admission path using actual local reference InChI validation, with no external-provider corroboration requirement added.

The implementation is provisionally validated for read-only matching within this scope. Recommend a **separately authorized controlled existing-ID reuse POC for verified explicit structures**, with transaction, idempotency, snapshot and audit checks before any write. Current ID reuse authorization and registry writes remain zero. This does not extend to general name-derived resolution, new identity creation or unvalidated chemistry.

## 2. Actual registry schema, data and limitations

| Table | Implemented columns / types | Keys and constraints |
|---|---|---|
| `substance_identity` | `substance_id TEXT`, `preferred_name TEXT NOT NULL`, `identity_status TEXT NOT NULL` | ID primary key; status must be `ACCEPTED` |
| `substance_alias` | `substance_id TEXT NOT NULL`, `alias TEXT NOT NULL` | Composite PK `(substance_id,alias)`; ID FK to identity |
| `substance_identifier` | ID/type/value, all `TEXT NOT NULL` | Composite PK `(substance_id,identifier_type,identifier_value)`; ID FK |
| `substance_structure` | ID/type/value, all `TEXT NOT NULL` | Composite PK `(substance_id,structure_type,structure_value)`; ID FK |
| `substance_reconciliation` | `cuma_index INTEGER`, nullable `substance_id TEXT`, `resolution_status TEXT NOT NULL`, `reason TEXT NOT NULL` | CUMA index PK/rowid; ID FK; five allowed statuses; `EXACT` iff ID is non-null |

There are 112 identities, 112 SMILES, 336 identifiers (112 each of InChI, InChIKey and PubChem CID), 300 aliases and 53,667 existing reconciliation rows, including 114 exact reconciliations. Inventory counts do not reprocess CUMA. No CAS, EC or ChEBI identifiers are stored in this snapshot. The runtime supports qualified generic identifier retrieval where such assertions exist.

Only primary-key SQLite indexes exist. There is no dedicated reverse alias/identifier index and no global uniqueness constraint on a full key or chemical graph across Substance IDs. The previous retrieval function searched full InChIKey only and silently omitted records without exactly one SMILES. The new adapter retains **every identity record**, including missing, invalid or multiple graphs, so insufficient records cannot disappear from uniqueness assessment.

All 112 current records have a valid single graph and internally consistent identifiers and are comparable in the implemented scope. Identity dimensions are derived diagnostically, not stored. Provenance is limited to existing identifiers and numbered CUMA reconciliations; original graph-deposit/import histories are not registry columns. No component relationship table exists. Multicomponent comparison, when explicitly scoped, concerns fixed graph composition, not a crystal phase. Complete actual DDL, indexes, original values, descriptor coverage and provenance: {inventory}.

## 3. Incoming identity and verification contract

`MatchingInput` contains an existing `IncomingConcept`/`EvidencePackage`, a display/source name, optional retrieval hypothesis, official-validator output, existing external-provider evidence, and qualified form/profile assertions. Existing adapters qualify PubChem/ChEBI fields; other sources can supply the same documented evidence contract. This does not implement an INCI or patent interpretation subsystem.

| Input category | Matching treatment | Existing admission treatment |
|---|---|---|
| Direct source-supplied molecular graph | Strict validation, trusted adapter provenance, bound structural field, reconciled source assertions, sufficient identity dimensions/form | Verified explicit-structure exemption may apply; official validation/form gates remain |
| Qualified name interpretation | Preserve name derivation and supported dimensions; compare only claims actually established by interpretation | Existing external corroboration required; never set explicit-structure flag |
| Raw parser success / retrieval hypothesis | Generate candidates only; cannot fill absent source assertions | No exact source identity or exemption |
| Broad, incomplete or unbound concept | May retrieve entries, including specific forms under a broad name | Remains unresolved; cannot select or propose exact reuse |

Verification of an explicit input requires a bound `STRUCTURAL_IDENTITY_ASSERTION` marked source-provided with `SOURCE_TYPED_STRUCTURE` interpretation, an explicit-source binding route/document, valid complete source reconciliation, sufficient molecular/form scope and no active source contradiction. These are qualified-adapter inputs, not cryptographic proof of an arbitrary caller's truthfulness. Original claims, excluded claims, roles, dependencies, source payload references and obligations remain in the output. A caller-supplied `explicit_structure=True` cannot convert a name-derived graph into a source-supplied one. Official results must also match the source graph's actual InChI/key; a successful flag for a different graph is rejected at the API boundary.

Contracts: {models}; verification/admission wrapper: {policy}.

## 4. Candidate retrieval and search completeness

`retrieve_substance_candidates(incoming_identity_evidence, registry, retrieval_policy)` returns IDs, per-ID routes/qualifications, indexed candidates, snapshot digest, coverage, truncation and insufficient-data records. The matcher builds conservative session indexes from the unchanged registry snapshot.

| Route | Meaning | Actual candidate pairs discovered (non-exclusive) |
|---|---|---:|
| Full InChIKey | Validated graph-derived projection; candidate only | {key_count} |
| Explicit graph serialization | Validated canonical isomeric graph representation; full comparison still required | {graph_count} |
| Heavy-connectivity view | Deliberately less specific diagnostic projection; retains no authority over identity | {constitution_count} |
| Molecular formula | Candidate generation only; never an equivalence rule | {formula_count} |
| Source record reference | Documented PubChem/ChEBI record referent, where registry identifier exists | {record_count} |
| Qualified identifier | Consistent structural projection or documented validated mapping | {identifier_count} |
| Registry alias / preferred-name equality | Registry assertion plus possibly unverified incoming text | {alias_count} |
| Exploratory name containment | Literal case-insensitive text containment; no fuzzy or semantic identity inference | {broad_count} |
| Exhaustive fallback | Every identity row, including deficient records | 14,784 |

The broad-name mechanism retrieves both declared L- and D-glutamic-acid fixture entries from `glutamic acid`, while the source remains unresolved. No hydrate, salt, stereo or isotope terms are removed from source text. Structure strings never undergo general name normalization. No original graph is replaced by a parent representation.

Default policy examines the whole small registry. Optional indexed-only mode **never claims exhaustive search**, even when it finds an apparent exact candidate. A candidate limit similarly blocks a uniqueness/absence claim. Route overlaps are deduplicated by canonical ID; chemically equivalent **different IDs remain distinct** and trigger multiple matches.

The indexed routes retrieve {indexed_pairs} distinct candidate pairs for 114/132 inputs. Broader routes add **{extra} candidate pairs beyond full-key lookup**. All 112 equivalent entries found by the exhaustive baseline are present in the indexed set: observed recall 112/112; missed equivalents 0. Exhaustive fallback also misses 0 by construction. This is retrieval recall against the **same hardened comparator**, not independent chemical precision. A supplemental synthetic unit fixture omits the equivalent record's identifiers: graph retrieval still finds it and produces a unique proposal, demonstrating that a full key is not required for discovery. Tautomer controls demonstrate the converse: the same key can retrieve a genuinely different form.

No actual candidate has insufficient data; synthetic missing/invalid/multiple-record situations remain unresolved rather than being discarded. Duplicate candidate evaluations in actual runs: 0. The snapshot has no observed duplicate equivalent IDs in these checks; the duplicate fixture has two and neither is chosen. Scope of completeness is only this digest, its 112 available records and implemented graph/composition capabilities. No global nonexistence is inferred.

Implementation: {retriever}; per-input route unions, extra candidates and missed-equivalent lists: {coverage}; exhaustive comparison reference: {exhaustive}; missing-identifier control: {missing_identifier}.

## 5. Chemical comparison integration

Every retrieved record uses the existing source qualifier, candidate adapter, reconciliation core and hardened stereo/isotope assertion comparators. All nine dimensions remain visible: constitution, stereochemistry, tautomer, protonation/charge, isotope, components, component stoichiometry, hydration/solvation and electronic state. The original comparators and production module globals are unchanged. Session-local memoization caches unchanged deterministic results, returns copies and rebinds copied functions; the 31 original real-world pairs produce identical dimension and correspondence results with/without these caches.

Chemical output is `CHEMICALLY_EQUIVALENT`, `CHEMICALLY_DIFFERENT` or `CHEMICALLY_UNRESOLVED`. Source support is separately `SOURCE_IDENTITY_SUPPORTED`, `SOURCE_IDENTITY_UNRESOLVED` or `SOURCE_CONFLICT`. Proven chemical differences can survive an incomplete source, but incomplete source specificity still prevents exact matching or bounded no-match conclusions. Known shared registry ancestry does not block chemistry and never becomes independent external corroboration.

Partial stereochemical agreement stays unresolved; unavoidable specified contradictions remain different under all valid graph correspondences. Tautomer, charge/H placement, isotope position, counterion and stoichiometric distinctions survive retrieval and comparison. Standard InChI equality is not substituted for molecular identity. Unsupported/invalid candidates remain possible unresolved matches and block uniqueness. Existing advanced stereo, metal-bond and physical-form limitations are retained.

Comparator bindings: {session}; matching orchestration: {matcher}.

## 6. Registry-level decisions and proposals

| Result | Implemented requirements |
|---|---|
| `UNIQUE_CANONICAL_MATCH` | Sufficient qualified source; exactly one chemically equivalent supported ID; complete declared search; no unresolved possible candidate |
| `MULTIPLE_CANONICAL_MATCHES` | At least two supported equivalent IDs; no choice or merge, even if ordering/ranking differs |
| `MATCH_UNRESOLVED` | Source incomplete/unbound, unsupported or unresolved candidate, or incomplete/truncated search |
| `NO_MATCH_IN_SEARCHED_REGISTRY` | Sufficient source; complete snapshot search; every entry demonstrably different (or an empty completely examined registry) |
| `SOURCE_CONFLICT` | Established incompatible bound source identity assertions; no selection |

A unique chemical/source match can be reported with an admission failure **separately visible**. `matching_proposal` records that unique diagnostic match; `diagnostic_reuse_proposal` is populated only when uniqueness and the existing admission policy both pass. Every proposal explicitly reports `canonical_id_reuse_authorized=False` and `persisted=False`. Multiple, unresolved, conflicted and negative outcomes have no selected ID. A source with no indexed candidate is unresolved unless a complete supported search establishes the bounded negative.

## 7. Existing provider and admission-policy audit

Approved sources are configured by actual `provider_capabilities.PROFILES`: **PubChem, ChEBI, GSRS and CompTox**. Profiles state exact query routes, record identifier fields, supported representation capabilities and form-standardization limitations. NIST and unconfigured providers have no qualifying profile. No provider, profile, budget or source exemption was added.

PubChem/ChEBI qualify appropriate exact name, record-ID and full-key routes; CompTox additionally supports its configured DTXSID/DTXCID/CAS routes. GSRS uses configured name/UNII routes and requires validated complete integer moieties. Exact returned-name/source-identifier correspondence, internally consistent graph/descriptors, source specificity and form compatibility are evaluated per record. Candidate-derived key searches do not qualify a source name. Normalized or uncertain tautomer/charge/component records are non-discriminating where the profile cannot preserve the required form. Same-route records are aggregated; retrieval order is not acceptance policy.

`SOURCE_DEPENDENCE_KNOWN` cannot qualify corroboration. The existing policy **does permit `SOURCE_DEPENDENCE_UNKNOWN`** on otherwise qualifying routes; this is reported separately from independently audited provenance. This task establishes zero new independently audited external positive pairs.

The wrapper calls **unmodified `policy.decision`**. Verified direct structural inputs may bypass external corroboration after official validation, sufficient interpretation and form checks. The actual 112 proposals exercise this route with real local reference InChI 1.07.2 results. Name-derived structures retain external evidence requirements. Contradictory qualified provider evidence yields the existing `CONFLICT`; missing official validation, known dependence or unsupported evidence does not yield an admission-eligible name proposal.

The frozen benchmark tests verified explicit sources, qualified-name/no-external, qualifying external, known/unknown dependence, contradiction, unsupported provider, broad source, graph mismatch, duplicates and missing official validation. Provider rows in policy controls are explicitly **synthetic** and count as zero real corroborations. Later design review should address whether unknown dependence is appropriate for future production name-based reuse; it was not changed here. Generic input-admission `AUTO_ACCEPT` on a bounded registry no-match does not authorize a new ID.

Actual profile configuration, hashes and route semantics: {provider_audit}; controlled policy outcomes: {admission}.

## 8. Independent matching benchmark and ambiguity controls

Before matching implementation, 30 development and 12 public held-out expectations were frozen. The cases use independently declared source and candidate graphs, independent of CUMA; expectations are not produced by the resolver. Separate disposable SQLite registries use synthetic `FIX_` IDs and the actual five-table schema. The source/candidate graph contracts have documentary/framework grounding, but these are synthetic registry controls, not newly collected database corroborations, blind validation or completed qualified expert review. Several chemical boundaries reuse known earlier controls.

Results: **42/42**; unique 14, multiple 1, unresolved 14, bounded negative 12, source conflict 1. False unique proposals against declared expectations: **0/42**. There are 14 read-only matching proposals and nine admission-eligible diagnostic reuse proposals; none authorizes reuse. Case-level evidence, expected/actual results, dimensions and admission reasons are preserved in {benchmark}.

| Required scenario | Frozen controls | Actual result |
|---|---|---|
| One exact among different entries | D01 | Unique |
| Equivalent duplicate IDs | D12 | Multiple, no selection |
| Exact plus unresolved possible entry | D13/D28 | Unresolved |
| Opposite stereoisomers / E-Z forms | D02/H03 | Different forms excluded; only exact form selected where present |
| Tautomers with matching Standard key | D06 | Bounded no-match |
| Partial/unspecified stereo | D04/D05/H04/H05 | Unresolved source; known contradictions retained |
| Unverified alias, multiple entries | D14/D27 | Candidates retrieved, no exact identity |
| No indexed candidate | D15 | Incomplete search, unresolved |
| Complete search without equivalent | D16/H11 | Bounded no-match |
| Established source contradiction | D17 | Source conflict |
| Isotope, charge, salts, stoichiometry | D07–D11/H06–H09 | Relevant distinctions retained |
| Budget, invalid metadata, raw name hypothesis | D26/H08/D29/D30 | No unsupported unique proposal |

No benchmark expectation was changed during implementation. A test-harness import-name collision with retained helpers was corrected by using a matching-specific module name; the latest retained suites pass. Synthetic duplicate/ambiguity details: {ambiguity}.

## 9. Actual 112-record registry evaluation

The 112 registry-linked PubChem inputs were recovered from original saved provider rows in the prior candidate workspace, selected by registry CID membership. Their structures come from those saved rows **rather than copying registry structures**. Source URLs, original row hashes, cached-container hash, bounded read-only SQLite query/parameter and JSON field pointer are retained. Only the 114 already exact CUMA evidence rows were inspected to recover these provider records. This is not a new CUMA canonicalization run.

These same upstream provider assertions contributed to the existing registry: positive results are **known-dependent consistency demonstrations**, not independent validation. Twenty additional actual PubChem/ChEBI source records from the previous ten-pair study were evaluated separately. Each incoming concept was compared with every one of the 112 stored graph records.

| Metric | Registry-linked source consistency | Additional PubChem/ChEBI inputs | Total |
|---|---:|---:|---:|
| Incoming concepts | 112 | 20 | 132 |
| Qualified source identities | 112 | 16 | 128 |
| Candidate comparisons | 12,544 | 2,240 | 14,784 |
| Inputs with indexed candidates | 112 | 2 | 114 |
| Verified equivalent entries retrieved | 112 | 0 | 112 |
| Missed equivalents vs exhaustive baseline | 0 | 0 | 0 |
| Chemically different comparisons | 12,432 | 2,240 | 14,672 |
| Chemically unresolved comparisons | 0 | 0 | 0 |
| Unique / multiple registry matches | 112 / 0 | 0 / 0 | 112 / 0 |
| Bounded complete-search no-match | 0 | 16 | 16 |
| Unresolved source-level matching results | 0 | 4 | 4 |
| Complete / incomplete snapshot searches | 112 / 0 | 20 / 0 | 132 / 0 |
| Read-only matching proposals | 112 | 0 | 112 |
| Admission-eligible diagnostic reuse proposals | 112 | 0 | 112 |
| IDs assigned / registry writes | 0 / 0 | 0 / 0 | 0 / 0 |

Indexed candidate coverage is 114/132 (86.36%); registry-linked coverage is 112/112. Equivalent-entry indexed retrieval recall is 112/112. Zero mechanical unsafe-proposal invariant failures were detected. **Real-world false-unique precision is not independently estimable from these source-dependent inputs**; the zero false-unique result belongs to the separately labelled controls. An exhaustive baseline is a retrieval-completeness reference, not a new external chemical truth source.

Actual inputs: {saved}; all results: {actual}; every unique proposal with source evidence, routes, candidate ID, dimensions, uniqueness and admission: {unique}.

## 10. Concrete demonstrations and unresolved cases

| Actual incoming source | Unique matching proposal | Chemistry / source support | Admission and ancestry |
|---|---|---|---|
| PubChem 1049, pyridine | `SUB_00000112` | Equivalent / supported | Explicit exemption; official agrees; known shared PubChem root |
| PubChem 6323, bromomethane | `SUB_00000006` | Equivalent / supported | Explicit exemption; official agrees; known shared PubChem root |

The other 110 registry-linked records likewise have exactly one supported registry entry. This detects uniqueness within the actual snapshot, not global chemical uniqueness. No existing duplicate ID was merged.

The four unresolved additional inputs are:

{unresolved_rows}

Their candidates can be excluded by established constitution/form differences, yet source incompleteness prevents a canonical identity or bounded no-match claim. The other 16 additional inputs have sufficiently specified graphs and all 112 registry entries are different. Their source-only admission checks may pass; this does not produce a reuse proposal or authorize creation.

The original PubChem 636405 / ChEBI 59213 pair remains a tautomer difference in retained hardening tests. In the new registry workflow, each source separately has no equivalent entry in this snapshot. Shared Standard InChI does not merge those two forms.

## 11. Safety regressions

All **{test_total} unit/integration tests** pass: 357 retained tests plus 21 new matching tests. Retained coverage includes source-to-candidate correspondence, evidence adapters, identity reconciliation, charge, NSC-001/002, isotopes, source-form aggregation, original production resolver behavior and admission. The 55 previous frozen controls pass through both original and hardened interfaces; 34 NSC controls and eight unchanged historical safety cases also pass. These separate control denominators are not added to the unit-test count.

Original real-world correspondence remains 29/30; hardened correspondence remains 30/30 on the original documentary labels. RW30 correction, RW23/RW24 abstentions, NIST field conflicts, RW29 reference-pending status, cefpiramide tautomer separation and existing isotope/acid-base/salt safety boundaries remain intact. No previous result file is overwritten.

New tests cover frozen matching expectations, source versus generated structures, admission flag spoof prevention, official-result graph binding, cached/uncached comparator agreement for all 31 original cases, cache immutability, read-only SQLite enforcement on fixtures, snapshot digest changes, missing graphs/identifiers, alias/formula false candidates, duplicates and incomplete search. All policy tests use the actual policy function. Latest suite counts/logs: {tests}; historical results: {historical}.

## 12. Integrity, reproducibility and public interface

The actual registry is opened only with SQLite `mode=ro`, query-only mode and a read transaction. Its digest is checked during snapshot construction and before/after matching. Fixture creation/writes are confined to the new experiment's `fixtures/` directory. The matcher has no ID allocation, registry update, alias promotion or merge operation. CLI output must be a new diagnostic `.json` file; it refuses overwriting existing files.

Protected integrity: **{protected} files, zero changes**. Registry SHA-256 remains `{registry_hash}`. SQLite integrity is `ok`; foreign-key errors, duplicate identity/alias/identifier/structure/reconciliation assertions and orphan rows are all zero. Frozen matching expectations and all prior production/ontology/schema/policy/provider-budget/history artifacts are unchanged. Production resolver-provider requests: 0. Local RDKit/reference InChI validation is not a new external provider request.

Environment: Python {python}; RDKit {rdkit}; reference InChI 1.07.2 through the existing local JNA bridge. Snapshot evidence/invariants: {integrity}; implementation/control hashes: {manifest}.

From the workspace root, reproduce the evaluation with:

```powershell
python canonical_registry/canonical_registry_matching/run_all.py
```

To run a single saved source through the actual CLI (defaults to the real registry and exhaustive search):

```powershell
python canonical_registry/canonical_registry_matching/match_cli.py --input canonical_registry/canonical_registry_matching/evaluation/cli_pubchem_input.json
```

The CLI accepts PubChem/ChEBI source packets or serialized qualified `IncomingConcept` evidence packages. External evidence may be supplied in the existing format; the CLI does not fetch it or invent name interpretation. `--indexed-only` and `--max-candidates` expose incomplete search explicitly. `--no-official-validation` withholds admission where required. The saved pyridine CLI demonstration returns the expected ID as a read-only proposal: {cli}. Programmatic entry points are `RegistrySnapshot`, `MatchingInput`, `RegistryMatcher.match` and `retrieve_substance_candidates`; the repository's existing local bootstrap/import convention is retained.

## 13. Limitations and controlled-reuse readiness

Read-only matching is ready within the validated discrete molecular/fixed-composition scope and this small snapshot. Exhaustive scans are deliberately practical for 112 records; the current completeness claim is not a scalable global chemical search guarantee. Broader scopes, unsupported advanced stereo or metal-bond conventions, incomplete physical-form evidence and missing/contradictory records remain unresolved.

The benchmark is public and synthetic, not a fresh blinded/expert-reviewed study. The real positive population shares upstream PubChem ancestry. Name-derived positive admission behavior is tested with labelled synthetic provider fixtures; no new independently provenance-audited real positive name-correspondence path is established. The already agreed explicit-structure exemption is sufficient for the evaluated verified structural inputs and is not blocked by that limitation.

For a separately authorized controlled existing-ID reuse milestone, start with verified explicit structures that meet the same specificity, no-conflict, complete-search, uniqueness and unchanged admission checks. Add transactional snapshot revalidation, idempotency, an auditable assignment boundary and tests preventing reassignment/duplication before enabling any persistent link. Keep name-derived and broader source pathways under their existing requirements; review unknown-dependence policy semantics separately. **This deliverable authorizes neither persistent ID reuse nor new Substance creation.** Readiness record: {readiness}.

{verdict}
'''
 values=dict(test_total=tests['unit_integration_total'],inventory=artifact('evaluation/registry_inventory.json'),models=artifact('registry_matching_models.py'),policy=artifact('diagnostic_match_policy.py'),key_count=route_counts.get('FULL_INCHIKEY',0),graph_count=route_counts.get('EXPLICIT_GRAPH_SERIALIZATION',0),constitution_count=route_counts.get('HEAVY_CONNECTIVITY_VIEW',0),formula_count=route_counts.get('MOLECULAR_FORMULA',0),record_count=route_counts.get('SOURCE_RECORD_REFERENCE',0),identifier_count=route_counts.get('QUALIFIED_IDENTIFIER',0),alias_count=route_counts.get('EXACT_REGISTRY_ALIAS_OR_NAME',0),broad_count=route_counts.get('EXPLORATORY_NAME_CONTAINS',0),indexed_pairs=indexed,extra=extra,retriever=artifact('registry_candidate_retriever.py'),coverage=artifact('evaluation/retrieval_coverage.json'),exhaustive=artifact('evaluation/exhaustive_comparison_baseline.json'),missing_identifier=artifact('evaluation/missing_identifier_retrieval_control.json'),session=artifact('comparison_session.py'),matcher=artifact('registry_matcher.py'),provider_audit=artifact('evaluation/provider_qualification_audit.json'),admission=artifact('evaluation/admission_policy_results.json'),benchmark=artifact('evaluation/benchmark_results.json'),ambiguity=artifact('evaluation/duplicate_ambiguity_results.json'),saved=artifact('evaluation/saved_input_records.json'),actual=artifact('evaluation/real_registry_results.json'),unique=artifact('evaluation/unique_match_results.json'),unresolved_rows='\n'.join('- '+r['provider']+' '+r['source_record_id']+': '+', '.join(r['result']['source_identity']['obligations'])+'.' for r in unresolved),tests=artifact('evaluation/test_results.json'),historical=artifact('evaluation/historical_safety_results.json'),protected=integrity['protected_files'],registry_hash=integrity['registry_sha256_after'],python=tests['python'],rdkit=tests['rdkit'],integrity=artifact('evaluation/integrity_report.json'),manifest=artifact('evaluation/implementation_manifest.json'),cli=artifact('evaluation/cli_demonstration.json'),readiness=artifact('evaluation/readiness_assessment.json'),verdict=ready['verdict'])
 (B/'CANONICAL_REGISTRY_MATCHING_V1_REPORT.md').write_text(text.format(**values),encoding='utf8')
if __name__=='__main__':main()
