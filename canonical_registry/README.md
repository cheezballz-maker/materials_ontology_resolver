# Canonical Substance Registry POC

The source-form safety gate is described in [SOURCE_FORM_INTERPRETATION_UPGRADE_REPORT.md](SOURCE_FORM_INTERPRETATION_UPGRADE_REPORT.md). `Resolver.evaluate` records source claims and checks candidate specificity before admitting a retrieved identity or promoting an alias. Its source-name interpretation is deliberately bounded: unfamiliar unparsed names and unsupported form distinctions can remain unresolved. `source_form_upgrade/run/` is a development replay of the existing 400-case holdout, not a fresh validation set or a production registry. Run all current tests with `python -m unittest test_registry test_forms test_evidence_retrieval test_source_form -v`.

The current evidence-acquisition increment is documented in [EVIDENCE_RETRIEVAL.md](EVIDENCE_RETRIEVAL.md) and [EXACT_FORM_EVIDENCE_UPGRADE_REPORT.md](EXACT_FORM_EVIDENCE_UPGRADE_REPORT.md). It adds bounded exact-form retrieval, provenance tracking and a GSRS adapter without changing the form characterizer, comparator, admission-policy module, ontology or schema. `evidence_upgrade/run/` is a separate **development re-evaluation** of the frozen 360-case set, not a fresh holdout or production migration.

```powershell
python -m unittest test_registry test_forms test_evidence_retrieval -v
python verify.py --output evidence_upgrade/run
python score_evidence_evaluation.py
```

The reusable API also accepts typed source `identifiers` and an optional `gsrs=GSRS(cache_path, budget=..., offline=...)` adapter. `pipeline.py build` enables GSRS with `--gsrs-budget` (default 200). Use a fresh output directory; builds never overwrite an existing registry. For offline reproduction, copy the original candidate inputs and all three saved provider caches into a new directory and use `--offline`. Do not rerun preparation against the existing evaluation directory. See `evidence_upgrade/PROTOCOL.md` and its frozen implementation manifest for the actual evaluation bounds.

The resolver now supports sufficiently defined molecular forms. See [current policy](IDENTITY_POLICY.md) and [upgrade results](FORM_AWARE_UPGRADE_REPORT.md). The ontology and five persistent tables are unchanged. Original reports and `output/` describe the historical bounded run; the upgraded 300-record snapshot is separate.

Run from this directory with Python 3.14, RDKit 2025.09.6, openpyxl 3.1.5 and JDK 17 (`java`/`javac` on PATH). The adjacent OPSIN 3.0-SNAPSHOT fat JAR supplies OPSIN and the existing reference-InChI bridge. No new package dependency was introduced.

```powershell
python -m unittest test_registry test_forms -v
python verify.py --output form_aware_evaluation/validated
python score_forms.py --run form_aware_evaluation/validated
```

Replay the original 300 source inputs using saved HTTP evidence in a **new** directory:

```powershell
python reevaluate_forms.py prepare --output form_aware_evaluation/replay --cache-source form_aware_evaluation/validated
python pipeline.py build --output form_aware_evaluation/replay --budget 0 --chebi-budget 0 --offline
python verify.py --output form_aware_evaluation/replay
```

Preparation reads original inputs only, not reference judgments. Scoring reads frozen labels after prediction and writes common metrics under `form_aware_evaluation/`; its manifest identifies the scored snapshot. This is development re-evaluation of a previously blinded benchmark, not a fresh blinded study.

For another source run, use `pipeline.py analyze --output <new-directory> --input <workbook>` then `pipeline.py build --output <same-directory> --budget <PubChem-cap> --chebi-budget <ChEBI-cap>`. The default workbook remains the existing CUMA file. `--base-registry` defaults to `output/registry.sqlite`, read only, for exact ID reuse and allocation above its maximum. Builds refuse to overwrite registries. Use fresh candidates after policy/source changes; existing analyzed rows are not automatically invalidated. Failed HTTP responses remain cached. Offline mode never makes HTTP requests.

The source-independent API is `Resolver.evaluate(name, aliases=..., structure=..., input_type=..., assertion=...)` for evidence analysis and `Resolver.resolve(name, identities, ...)` for EXACT/NO_MATCH/UNRESOLVED lookup. `identities` contains `(substance_id, validated_descriptor)` pairs; create descriptors with strict `chemistry.describe`. Typed assertions may specify form kind and solvent/component stoichiometry. NO_MATCH never writes a registry automatically. `registry_builder.populate` clusters accepted identities and allocates IDs separately.

Current artifacts:

- `form_aware_evaluation/validated/registry.sqlite`: five-table evaluation snapshot, with exact existing IDs reused.
- `form_aware_evaluation/validated/candidates.sqlite`: one temporary candidate table with original strings, diagnostics and evidence JSON.
- `form_aware_evaluation/validated/summary.json` and `verification.json`: results and integrity checks.
- `form_aware_evaluation/{before_metrics,after_metrics,comparison,alias_comparison,score_manifest}.json`: comparison against unchanged labels.
- `form_aware_evaluation/tests.log`: current tests.
- `reviewed_evidence.json`: prior dithiazole contradiction, used only as veto evidence.

The original databases, frozen labels, framework and ontology are protected by hashes. This snapshot is not a production registry migration or full CUMA canonicalization. CUMA provenance remains numbered indices only. No legacy-table ingestion/write, CosIng mapping or permanent alternate-form relationships are added.

`CUMA_REPORT.md`, `LEGACY_COVERAGE_REPORT.md`, `VALIDATION_ADDENDUM.md`, `CUMA_VALIDATION_REPORT.md` and `REUSE_SUMMARY.md` are historical reports, not specifications of the upgraded policy. The updated `evaluate.py` is an optional separate engineering evaluation; the reported validation uses the frozen 300-case set.
