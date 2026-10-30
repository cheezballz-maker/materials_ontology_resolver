"""Replay prior B controls without invoking OPSIN or modifying old artifacts."""
import json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;OLD=H.parent/'nsc_architecture_experiment';sys.path[:0]=[str(H),str(OLD)]
from architecture_B.implementation.interpreter import interpret_name,validate_candidate
from shared.semantic_interface import validate_interpretation
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
cases=[]
for kind in ('development','heldout'):
 controls=read(OLD/f'shared/{kind}_controls.json')['cases'];prior={r['id']:r for r in read(OLD/f'evaluation/{kind}_results.json')['cases']}
 for c in controls:
  x=interpret_name(c['input_name']);v=validate_candidate(x,c['candidate_structure'],c['evaluation_context']);old=prior[c['id']]['B']
  if x.scope_status=='IN_CONTRACT':validate_interpretation(x)
  same=(v.result==old['result'] and x.scope_status==old['scope'] and x.structural_constraints==old['constraints'])
  cases.append({'id':c['id'],'prior':old['result'],'actual':v.result,'scope':x.scope_status,'source_spans_verified':x.scope_status!='IN_CONTRACT' or all(x.input_name[y['source_span']['start']:y['source_span']['end']]==y['source_text'] for y in x.source_claims),'constraints_unchanged':x.structural_constraints==old['constraints'],'same':same})
payload={'status':'PASS' if all(x['same'] and x['source_spans_verified'] for x in cases) else 'FAIL','count':len(cases),'cases':cases,'method':'Replayed existing NSC-001 B only against previously saved outputs; no OPSIN calls.'}
(H/'evaluation/nsc001_regression.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':payload['status'],'cases':len(cases)},indent=2));assert payload['status']=='PASS'
