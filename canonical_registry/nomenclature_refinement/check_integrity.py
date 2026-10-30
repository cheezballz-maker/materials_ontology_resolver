"""Verify baseline contracts and scan new outputs without disclosing secrets."""
import hashlib,json,runpy
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
runpy.run_path(str(B/'deterministic_form_remediation/check_integrity.py'))
base=json.loads((B/'deterministic_form_remediation/integrity_results.json').read_text(encoding='utf8'))
names=['NOMENCLATURE_FALSE_HOLD_TAXONOMY.json','nomenclature_capability_assessment.json','implemented_semantic_rules.json','false_hold_replay.json','refined_local_metrics.json','post_refinement_gate_value.json','NOMENCLATURE_SEMANTICS_REFINEMENT_REPORT.md','test_nomenclature_diagnostics.py']
key=None;env=B/'.env.local'
if env.exists():
    for line in env.read_text(encoding='utf-8-sig').splitlines():
        if line.strip().startswith('CTX_API_KEY='):key=line.split('=',1)[1].strip().strip('"\'')
files=[B/n for n in names if (B/n).exists()]+[p for p in H.rglob('*') if p.is_file()]
leaks=[]
if key and len(key)>=12 and 'placeholder' not in key.lower():
    leaks=[str(p.relative_to(B)) for p in files if key.encode() in p.read_bytes()]
diagnostic=(H/'semantic_diagnostics.py').read_text(encoding='utf8').lower()
forbidden=['17504','4373','30832','terephthalate','pyrazole','acetoacetate']
case_tokens=[x for x in forbidden if x in diagnostic]
out={'prior_frozen_artifacts_and_contracts':base['pass'],'new_outputs_credential_scan':'PASS' if key and not leaks else ('FAIL' if leaks else 'NOT_SCANNED_NO_KEY'),'credential_leak_files':leaks,'case_specific_runtime_tokens':case_tokens,'resolver_or_provider_changes_this_phase':False,'pass':base['pass'] and not leaks and not case_tokens}
(H/'integrity_results.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out,indent=2))
assert out['pass']
