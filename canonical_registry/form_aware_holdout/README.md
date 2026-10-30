# Frozen holdout audit workspace

This directory contains evaluation artifacts only. The canonical resolver and its tests/policy/providers/schema are unchanged.

`SAMPLE_FROZEN.json` identifies the source workbook and 360 records. `PROTOCOL_FROZEN.json` fixes sampling/scoring rules. `packet_1` through `packet_3` contain disjoint source-only packets, copied authoritative policy, independent retrievals and adjudicator references. `steward/` contains excluded development indices/names, lexical strata and protected-file hashes; adjudicators must not inspect it.

Run these from `canonical_registry` only **after all three independent adjudicators finish**:

```powershell
python form_aware_holdout/freeze_and_prepare.py
python pipeline.py build --output form_aware_holdout/predictions --budget 1800 --chebi-budget 3000
python form_aware_holdout/score_holdout.py
python verify.py --output form_aware_holdout/predictions
```

Preparation refuses an existing prediction directory. The engine refuses an existing registry. Do not repeat the frozen sampling step or change any reference after unblinding. Existing provider caches are not copied into predictions. Re-running the scorer is read-only with respect to all databases and labels, but refreshes derived metric files.

`comparison.json` preserves per-record outcomes, graph evidence, reasons and hypotheses. `alias_comparison.json` contains promoted alias occurrences. `by_sampling_tag.json` uses frozen nonexclusive lexical categories; `by_reference_form.json` uses adjudicated chemical forms. These categories must not be confused. `gap_counts.json` is diagnostic and overlapping, not a causal experiment.

Only after scoring, `decision.json` records the qualitative ranking/recommendation, and `render_report.py` creates `../FORM_AWARE_HOLDOUT_REPORT.md`. `SCORING_MANIFEST.json` and final verification metadata tie results to immutable input/reference/code/database hashes. Raw UTC audit timestamps are retained; the report uses Singapore time.
