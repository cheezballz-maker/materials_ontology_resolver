# Chemical registry and resolution workflows

Launch **Registry Explorer** from the workspace root, the directory containing
`canonical_registry`.

```powershell
python -m streamlit run canonical_registry/substance_explorer/app.py
```

From inside `canonical_registry`, use:

```powershell
python -m streamlit run substance_explorer/app.py
```

After updating the viewer, stop the previous Streamlit process with **Ctrl+C**
before restarting. Open the **Local URL** printed by the new process.

Substances and Chemical Concepts browse the persistent development registries used by **Resolve Chemicals**, so committed records are searchable immediately. Browsing remains read-only. Before development initialization, the viewer falls back to the frozen pilot and historical molecular Concept demonstration. `SUBSTANCE_EXPLORER_DB`, when explicitly configured, overrides the Substance browsing database. Search at the top to update the list and open the first matching record. Click a record or focus the list and use ↑ and ↓ to update the detail card. Use Previous and Next to move between Substance result pages. Substance search supports formulas, identifiers, structures and exact source association filters. Chemical Concept search supports formulas and source record IDs. Validated memberships open the linked Substance details from the recorded registry.

## Resolve Chemicals and enrich the development registries

Initialize once per workspace. The full pilot copy requires about 2.6 GB.

```powershell
python -m canonical_registry.enrichment init
python -m canonical_registry.enrichment resolve --name "butan-2-ol"
python -m canonical_registry.enrichment commit --yes --name "butan-2-ol"
```

In **Resolve Chemicals**, choose **Names or CSV** to enter one name per line or upload a CSV with a
`name` column. Optional CSV columns are `smiles`, `inchi`, `inchikey`, `cas`, `ec`,
`inci_name`, `source_system`, `source_record_id` and `referent_key`.
Choose **Single with evidence** to enter one chemical with optional structure, identifier, or source fields. Preview first, select eligible rows, then commit. Committed records appear in the corresponding **Substances** or **Chemical Concepts** section. **Look up ID** also opens previously committed development records after a restart.

The CLI also accepts `--text` and `--csv`. Python callers can use
`Enrichment.resolve`, `Enrichment.batch` and `Enrichment.commit` with
`ChemicalInput` records. Each commit is independently transactional.
Validated names and explicit structures can now create or reuse a Substance through
the source-independent qualification adapter. External providers are optional.
Examples from the workspace root:

```powershell
python -m canonical_registry.enrichment resolve --name "water"
python -m canonical_registry.enrichment commit --yes --name "water"
python -m canonical_registry.enrichment resolve --structure "O"
python -m canonical_registry.enrichment commit --yes --structure "O"
```

Use `--name "" --inchi "InChI=1S/H2O/h1H2"` for an InChI-only input.
The UI accepts a blank name when a structure is supplied in **Single with evidence**.
Optional retained PubChem or ChEBI evidence can be supplied with `--saved-evidence`.
Identifiers such as CAS and EC remain retrieval claims until their referents are validated.

Keep the development capability manifest under `enrichment/local` private.
See the [enrichment report](CHEMICAL_RESOLUTION_AND_REGISTRY_ENRICHMENT_V1_REPORT.md)
for validation results and scope.

The combined molecular routing API is `UnifiedChemicalResolver.resolve` in
`chemical_concept_registry/unified_chemical.py`. It can return an exact Substance match,
a broader ChemicalConcept, or an unresolved or conflicting result. The CLI below demonstrates
Concept routing with a disposable fixture.

```powershell
python canonical_registry/chemical_concept_registry/resolve_v11.py --smiles "CC(O)F"
```

See the [unified chemical validation](UNIFIED_CHEMICAL_RESOLUTION_V1_1_VALIDATION_REPORT.md).

## Exact Substance resolver

The reusable entry point is `SubstanceResolver.resolve` in
`unified_substance_resolution/unified_resolver.py`. It coordinates source
evidence qualification, claim reconciliation, existing canonical matching,
admission, optional creation/reuse and source-concept association. Those remain
separate decisions. A matching proposal is not a committed association.

The current warehouse increment is documented in
[WAREHOUSE_ADMISSION_AND_RESOLVER_CONSOLIDATION_V1_REPORT.md](WAREHOUSE_ADMISSION_AND_RESOLVER_CONSOLIDATION_V1_REPORT.md).
The production seed remains `output/registry.sqlite` (112 Substances). The new
1,000-record run and all writes are confined to disposable fixtures. No full
CUMA or 280-million-row warehouse canonicalization is claimed.

## Scope and admission

Supported identities are sufficiently specified discrete molecular graphs and
supported fixed molecular compositions. Stereo, isotopes, charge/protonation,
tautomer, components and electronic state remain distinct where meaningful.
Parsing, Standard InChIKey equality, names and formula alone do not prove exact
identity. No automatic parent selection or canonical alias promotion is added.
Variable polymers, alloys, minerals/crystalline phases, mixtures and unsupported
coordination/electronic/stereo representations remain outside the bounded scope
or unresolved. Incomplete supported molecular identities are withheld.

Three evidence paths remain distinct:

- Verified directly source-supplied structures retain the existing exemption
  from external corroboration, with all required structural/source checks.
- Name-derived structures can use the bounded source-independent interpretation
  adapter. It validates chemical meaning, supported completeness and reference InChI.
  Legacy unqualified evidence packages retain their original restrictions.
- `TRUSTED_INTERNAL_STRUCTURE_ASSERTION` v1.0 accepts internal graph assertions
  only through a configured `TrustedWarehouseAdapter` for
  `pd_dw.dws_material_substance_entity_v2`. Configured batch SHA-256 and exact
  record membership establish the POC boundary. Original-provider provenance
  stays UNKNOWN. An in-process sealed certificate is not serialized and cannot
  be activated by a JSON Boolean. This is operator configuration, not hostile
  client authentication. Existing `WarehouseAdapter` remains unverified.

Every persistence path still needs a marked fixture capability, live matching
and admission revalidation under a transaction, complete unique matching for
reuse or complete no-match for creation, and official structural validation.
Production paths, links and arbitrary writable paths are rejected.

## Run from the workspace root

Use Python/RDKit and the existing JDK/OPSIN/reference-InChI installation. The
saved examples use local evidence and disable live provider requests.
This run used Python 3.14.3, RDKit 2025.09.6, SQLite 3.50.4 and JDK 17.0.12;
the exact runtime strings are in `warehouse_admission_consolidation/evaluation/runtime_environment.json`.

Read-only resolution:

```powershell
python canonical_registry/unified_substance_resolution/run.py --input canonical_registry/unified_substance_resolution/examples/pubchem_input.json --verbosity summary
```

Disposable existing-ID association, creating/reusing a private fixture permit:

```powershell
python canonical_registry/unified_substance_resolution/run.py --input canonical_registry/unified_substance_resolution/examples/pubchem_input.json --persist --permit-file canonical_registry/unified_substance_resolution/evaluation/local-association.permit.json
```

Disposable creation/reuse requires a separate fresh pair of capabilities:

```powershell
python canonical_registry/unified_substance_resolution/run.py --input canonical_registry/canonical_substance_creation/examples/pubchem_creation_input.json --persist --allow-creation --permit-file canonical_registry/canonical_substance_creation/evaluation/local-association.permit.json --creation-permit-file canonical_registry/canonical_substance_creation/evaluation/local-creation.permit.json
```

An association-only fixture cannot be upgraded to creation. Keep `*.permit.json`
private. `--output` must name a new JSON file.

The programmatic API accepts an `AdaptedRecord`-producing configured adapter,
`FixturePermit` and distinct `CreationPermit`. There is no generic warehouse
trust switch on the CLI. The bounded warehouse runner configures its adapter
from the frozen sample manifest:

```powershell
$env:RESOLVER_POC_SQLITE_READ_CACHE='1'
python canonical_registry/warehouse_admission_consolidation/pilot_runner.py
python canonical_registry/warehouse_admission_consolidation/finalize_pilot.py
python canonical_registry/warehouse_admission_consolidation/verify_pilot.py
```

The pilot resumes durable per-record checkpoints. A completed delivery verifies
hashes and is preserved. Its output is
`warehouse_admission_consolidation/output/normalized_pilot.sqlite`, with CSVs
for `sampled_source_records`, `normalized_canonical_substances` and
`source_to_canonical_associations`. Seed rows are explicitly distinguished from
pilot creations. The exported snapshot is for read-only review; write-capable
interfaces reject its output location.

## Tests and implementation map

The focused viewer and resolver suite runs from the workspace root.

```powershell
python -m pytest -q canonical_registry/substance_explorer/tests canonical_registry/chemical_concept_registry/test_registry.py canonical_registry/chemical_concept_registry/test_v11.py canonical_registry/canonical_registry_matching/matching_tests.py canonical_registry/chemical_resolution_improvements/test_corrections.py
```

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:RESOLVER_POC_SQLITE_READ_CACHE='1'
python canonical_registry/warehouse_admission_consolidation/regressions.py B
```

This runs the retained 378 unit/integration, 25 association, 19 unified,
39 creation, 9 creation-safety and 8 warehouse tests, plus the new 21 admission,
11 additional safeguards, two formula-charge controls, six explicit material-scope
controls, two unsupported formula-annotation controls and differential
memoization checks. Frozen controls
remain under the respective milestone `controls/` directories. Replays write
separate checkpoint results, not historical reference labels.

| Responsibility | Active modules |
|---|---|
| Source semantics/evidence | `source_evidence_adapters/`, `source_candidate_correspondence/`, NSC/charge layers |
| Nine-dimension comparison | `chemical_correspondence_hardening/` and its retained stereo/isotope wrappers |
| Registry search/proposals | `canonical_registry_matching/` |
| Existing-ID association | `controlled_identity_reuse/` |
| Atomic creation and association | `canonical_substance_creation/` |
| Orchestration and source CLI | `unified_substance_resolution/` |
| Scoped warehouse adapter | `real_world_normalization/warehouse_sample_adapter.py`, `internal_structure_policy.py` |
| Current bounded run/evaluation | `warehouse_admission_consolidation/` |

Historical milestone reports, experiments, source payloads and controls remain
in place to preserve frozen references and dynamic regression dependencies.
Old `pipeline.py`/resolver commands and older milestone READMEs describe their
own historical workflows; this root guide is authoritative for current use.
The previous root guide is preserved byte-for-byte under
`archive/documentation/README_pre_consolidation_20261103.md`.
See [cleanup manifest](RESOLVER_REPOSITORY_CLEANUP_MANIFEST.md) for retained and
removed artifacts. Historical correctness wrappers were not removed merely
because they have old names or no unique static import consumer.

Never write to the production seed, ontology or warehouse, migrate historical
CUMA reconciliation automatically, publish private permits, or run cleanup
against source/evidence/registry files. Production deployment and large-scale
creation require separate validation and authorization.

## Canonical identity model

The authoritative Materials Ontology is v0.7.0. Version 0.6.0 added [ingredient mappings and reported source anatomy](ONTOLOGY_REUSE_AND_COSMETICS_CONCEPT_ALIGNMENT_V1_REPORT.md). Version 0.7.0 adds broad Material subclasses and separates Material from Application while preserving the Substance hierarchy. Active ChemicalConcepts require supported molecular definitions with explicit underspecification. Family definitions are excluded. The development Concept registry uses schema v2 with additive compatibility and validated-label tables. See the [implementation and evidence index](maintenance/IMPLEMENTATION_INDEX.md) for current entry points and [identity alignment](CANONICAL_IDENTITY_MODEL_ALIGNMENT_V1_REPORT.md) for migration and shared fields.

## Configure chemical input adapters

`enrichment.chemical_qualification.InputAdapters` registers adapters by name.
An adapter implements `interpret(ChemicalInput, local_resolver, reference_bridge)`
and returns the validated descriptor and existing `AdaptedRecord` contract.
Pass the registry and adapter name through `Enrichment(input_adapters=..., input_adapter=...)`.
`ChemicalInputSourceAdapter` bridges the same implementation to
`SubstanceResolver.resolve` and its existing `AdapterRegistry.register` API.
Adapters must preserve original claims, reconcile structures, qualify supported
meaning and recompute official validation. Registration is local operator configuration.

See [source-independent admission](SOURCE_INDEPENDENT_CHEMICAL_ADMISSION_V1_REPORT.md)
for gate changes, negative controls and remaining limits.

## Chemical candidate index

Prepare the development registry index once before interactive resolution:

```powershell
python -m canonical_registry.enrichment.build_index
```

Resolution and explicit commit use indexed chemical candidate retrieval automatically.
The first build validates all stored candidate graphs and can take about a minute.
Later runs reuse the versioned sidecar. SQLite integrity checks still contribute
to startup and commit latency. Registry files remain the source of inventory and
chemical identity. Unsupported inputs or candidate definitions retain the complete
comparison fallback.

Python callers can request the retained reference strategy with
`RetrievalPolicy(strategy="exhaustive")`. Result diagnostics distinguish actual
comparisons, proven exclusions and complete coverage.

See [chemical indexing](COMPLETENESS_PRESERVING_CHEMICAL_INDEXING_V1_REPORT.md)
for soundness conditions, timings, differential controls and scaling limits.
