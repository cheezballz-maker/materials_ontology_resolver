"""Freeze the bounded capability assessment and saved-evidence replay."""
import json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path.insert(0,str(B))
from nomenclature_refinement.semantic_diagnostics import indicated_hydrogen_tokens
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
write=lambda name,data:(B/name).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf8')
taxonomy=read(B/'NOMENCLATURE_FALSE_HOLD_TAXONOMY.json')
replay=read(B/'deterministic_form_remediation/deterministic_form_replay.json')
metrics=read(B/'deterministic_form_remediation/local_eligibility_metrics.json')
gate=read(B/'deterministic_form_remediation/post_remediation_gate_value.json')
assert len(taxonomy)==81 and len(replay)==224
capabilities=[
 dict(capability='indicated hydrogen lexical observation',status='READY_TO_IMPLEMENT',meaning='Observe a possible numbered H token only; it can refer to indicated or added indicated hydrogen, or be syntactically ambiguous.',citation='https://iupac.qmul.ac.uk/BlueBook/P1.html',examples=['1H-pyrrole','3H-pyrrole'],observable='numbered H token and character span',result='UNMAPPED; not an admission signal',limitations='Does not determine fragment ownership, isotope meaning, atom mapping, or whether every tautomeric site is fixed.'),
 dict(capability='indicated hydrogen atom mapping and tautomer support',status='TOO_COMPLEX_FOR_CURRENT_RESOLVER',meaning='Indicated hydrogen can locate a ring hydrogen; added indicated hydrogen has different grammar.',citation='https://iupac.qmul.ac.uk/BlueBook/P1.html',examples=['1H-pyrrole','3H-pyrrole'],observable='CML locants plus grammatical fragment ownership and candidate graph',result='UNKNOWN until unique ownership and all tautomer-sensitive sites are validated',limitations='Existing locant labels do not in general establish fragment ownership; a local H does not specify all other tautomeric sites.'),
 dict(capability='functional-group suffix and keto/enol specificity',status='NEEDS_MORE_GROUNDING',meaning='Named functional groups constrain structure but a general suffix matcher cannot establish the complete tautomer without grammatical scope and mapped atoms.',citation='https://goldbook.iupac.org/terms/view/T06252',examples=['propan-2-one','prop-1-en-2-ol'],observable='parsed name grammar, group locants, candidate atom and hydrogen mapping',result='UNKNOWN',limitations='Retained names, multiple tautomeric systems and implicit hydrogen placement require independent analysis.'),
 dict(capability='ionic suffix and counterion semantics',status='NEEDS_MORE_GROUNDING',meaning='Operational suffixes specify ionic centers in context, not solely by matching a substring.',citation='https://iupac.qmul.ac.uk/BlueBook/P7.html',examples=['tetramethylammonium chloride','sodium ethanoate'],observable='parsed suffix ownership, counterion counts and atom mapping',result='UNKNOWN',limitations='-ate may denote an ester and charged sites or counterions can be missing, repeated or distributed.'),
 dict(capability='nitro resonance versus protonation',status='NEEDS_MORE_GROUNDING',meaning='Nitro denotes a nitrogen-bound NO2 group; formal charge-separated drawings can represent a neutral group.',citation='https://goldbook.iupac.org/terms/view/N04158',examples=['nitrobenzene','1-nitropropane'],observable='mapped source nitro group and all charged atoms/components',result='UNKNOWN for source form until all charge and protonation sites are accounted for',limitations='Nitro presence alone does not justify every charge state or infer that a name lacks another ionic center.'),
 dict(capability='dimension-specific alias specificity dominance',status='NEEDS_MORE_GROUNDING',meaning='An alias omitting a descriptor may be broader; two genuinely specific incompatible claims can conflict.',citation='https://goldbook.iupac.org/terms/view/S05984',examples=['butan-2-ol versus (R)-butan-2-ol','(R)-butan-2-ol versus (S)-butan-2-ol'],observable='independently verified per-claim dimension-specificity and source scope',result='Existing coarse broad-alias handling retained; no new admission rule',limitations='Parser-produced graphs do not establish alias scope, and the 18 primary alias-conflict records mostly include constitutional differences.'),
]
write('nomenclature_capability_assessment.json',capabilities)
write('implemented_semantic_rules.json',{'rules':[capabilities[0]],'integration':'standalone audit-only lexical observation; resolver and admission policy unchanged','admission_changing_rules':[]})
byid={x['cuma_index']:x for x in replay};out=[]
for t in taxonomy:
    r=byid[t['record_id']];assert r['local_status']=='LOCALLY_WITHHELD'
    out.append(dict(record_id=t['record_id'],preferred_name=t['preferred_name'],previous_blocker=t['primary_blocker'],after_status=r['local_status'],after_reasons=r['reasons'],outcome='STILL_WITHHELD',changed_blocker=False,new_conflict=False,new_rule=None,source_observations=indicated_hydrogen_tokens(t['preferred_name']),candidate_structure=t['opsin_candidate'],reference_smiles=t['reference_smiles'],reference_verdict=r['prior_verdict']))
write('false_hold_replay.json',{'method':'same saved evidence and unchanged local admission code; lexical observation cannot change decisions','total':len(out),'recovered':0,'still_withheld':len(out),'changed_blocker':0,'new_conflict':0,'cases':out})
write('refined_local_metrics.json',dict(metrics,admission_changing_rules=0,newly_eligible=0,note='Identical to prior local replay because no grounded identity-admission capability was implemented.'))
write('post_refinement_gate_value.json',dict(categories=metrics['post_gate_categories'],definition='Frozen provider states are comparative only; no provider calls.',source_case_count=len(gate['cases'])))
print('81 prior holds replayed: 0 recovered, 81 still withheld; no admission-policy change')
