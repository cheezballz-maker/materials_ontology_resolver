import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
def write(n,x):(H/n).write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
tax={'version':'1.0','stage':'FROZEN_BEFORE_RECORD_CATEGORIZATION','classes':{
'A_TAUTOMER_SOURCE_MAPPING':{'family':'A','meaning':'Name-to-parent/H/suffix specificity not established; toolkit tautomer enumeration is only a trigger.'},
'A_IONIC_SOURCE_MAPPING':{'family':'A','meaning':'Source meaning of charge/protonation or acid/base naming not mapped.'},
'A_CONTEXT_OWNERSHIP':{'family':'A','meaning':'Partial operation needs source span, parent ownership and surrounding-operation closure.'},
'B_CHARGE_REPRESENTATION':{'family':'B','meaning':'Formal atom charge, net charge, protonation and resonance require separate evidence.'},
'B_STRUCTURAL_COMPARISON':{'family':'B','meaning':'Pairwise identity dimensions require validated correspondence; parser disagreement alone does not adjudicate source meaning.'},
'C_CLAIM_SPECIFICITY':{'family':'C','meaning':'Claim may be broad, exact compatible or exact incompatible; independent semantics needed.'},
'C_EXACT_CONTRADICTION':{'family':'C','meaning':'A source-specific conflict is reported by current code, not necessarily independently adjudicated.'},
'D_SOURCE_INSUFFICIENT':{'family':'D','meaning':'Independent evidence establishes multiple remaining source-compatible identities.'},
'D_CLASSIFICATION_INSUFFICIENT':{'family':'D','meaning':'Evidence cannot decide whether the source is underspecified or implementation is incomplete.'},
'E_OVERBROAD_GUARD':{'family':'E','meaning':'A broad feature trigger substitutes for a dimension-specific source test; not by itself a proven unsafe decision.'},
'E_RESULT_AGGREGATION':{'family':'E','meaning':'Potential misaggregation or an unconsumed validated dimension result; requires causal demonstration.'}},
'types':{'1':'Source demonstrably sufficient, interpretation missing','2':'Source sufficient, comparison missing','3':'Claims sufficient, reconciliation missing','4':'Source demonstrably does not determine one identity','5':'Insufficient independent evidence to classify'},
'rules':['Multi-label memberships; primary historical labels retained separately.','Type 1-4 require independent evidence; otherwise use Type 5 with explicit hypotheses.','Reference correctness never supplies source specificity.','No hypothetical removal of a reason is a recovery.']}
write('blocker_taxonomy.json',tax)
files=[B/n for n in ('resolver.py','source_form.py','identity_comparator.py','form_characterizer.py','chemistry.py','providers.py','provider_capabilities.py','evidence_model.py','schema.sql','NOMENCLATURE_FALSE_HOLD_TAXONOMY.json','deterministic_value_analysis/deterministic_interpretation_cases.json','fresh_blinded_evaluation/fresh_sample.json','fresh_blinded_evaluation/run/candidates.sqlite','output/registry.sqlite')]
for directory in ('nsc_architecture_experiment/NSC-001','nsc_architecture_experiment/shared','nsc_architecture_experiment/architecture_B/implementation','nsc002_experiment/NSC-002','nsc002_experiment/architecture_B/nsc002_interpreter'):
 files += [p for p in (B/directory).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
files += [p for directory in ('http_cache','chebi_cache','gsrs_cache','comptox_cache') for p in (B/'fresh_blinded_evaluation/run'/directory).glob('*.json')]
write('pre_analysis_hashes.json',{'files':{str(p.relative_to(B)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))},'taxonomy_sha256':hashlib.sha256((H/'blocker_taxonomy.json').read_bytes()).hexdigest()})
print('Taxonomy frozen and protected inputs snapshotted.')
