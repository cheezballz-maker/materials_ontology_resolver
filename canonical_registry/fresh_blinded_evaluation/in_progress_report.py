"""Replace the earlier interrupted report with an honest in-progress notice."""
import collections,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
assert (H/'REFERENCE_FROZEN.json').exists() and (H/'RUN_STARTED.json').exists() and not (H/'RUN_FINISHED.json').exists()
refs=json.loads((H/'reference_adjudication.json').read_text(encoding='utf-8'))
counts=dict(collections.Counter(x['reference_status'] for x in refs))
text=f'''# Fresh blinded resolver evaluation — run in progress

The user approved the previously blocked external name disclosure. The original 400-record random sample and resolver implementation remain frozen; independent references were frozen before the unchanged resolver began. Reference counts: {counts}. Some cases remain unadjudicable, including 51 with candidate screening only; those cases are not negative labels.

The normal provider-backed resolver run is ongoing, with the default bounded budgets and empty initial caches. Precision, recall, false merges, alias precision and provider-state results have not yet been calculated. The final report will replace this notice after the run, reference comparison and registry verification complete.

[Implementation freeze](FRESH_BLINDED_EVALUATION_FREEZE.json) · [sample manifest](fresh_blinded_evaluation/SAMPLE_FROZEN.json) · [reference freeze](fresh_blinded_evaluation/REFERENCE_FROZEN.json) · [source-only leakage check](fresh_blinded_evaluation/leakage_check.json)

FRESH_BLINDED_EVALUATION_MIXED
'''
(B/'FRESH_BLINDED_RESOLVER_EVALUATION_REPORT.md').write_text(text,encoding='utf-8')
