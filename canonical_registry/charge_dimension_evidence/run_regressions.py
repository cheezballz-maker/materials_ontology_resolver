import json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path[:0]=[str(H),str(B/'nsc002_experiment'),str(B/'nsc_architecture_experiment'),str(B)]
from architecture_B.implementation import interpreter as one
from architecture_B.nsc002_interpreter import interpreter as two
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
out=[]
for kind in ('development','heldout'):
    root=B/'nsc_architecture_experiment';prior={x['id']:x['B'] for x in read(root/f'evaluation/{kind}_results.json')['cases']}
    for c in read(root/f'shared/{kind}_controls.json')['cases']:
        i=one.interpret_name(c['input_name']);v=one.validate_candidate(i,c['candidate_structure'],c['evaluation_context']);p=prior[c['id']]
        spans=all(i.input_name[x['source_span']['start']:x['source_span']['end']]==x['source_text'] for x in i.source_claims)
        out.append({'contract':'NSC-001','id':c['id'],'pass':v.result==p['result'] and i.structural_constraints==p['constraints'] and spans,'result':v.result})
    root=B/'nsc002_experiment';prior={x['id']:x for x in read(root/f'evaluation/{kind}_results.json')['cases']}
    for c in read(root/f'NSC-002/{kind}_controls.json')['cases']:
        i=two.interpret_name(c['source_name']);v=two.validate_candidate(i,c['candidate_structure'],c['context']);p=prior[c['id']]
        out.append({'contract':'NSC-002','id':c['id'],'pass':v.result==p['actual'] and i.source_claims==p['source_claims'] and i.structural_constraints==p['constraints'],'result':v.result})
(H/'evaluation/nsc_regression.json').write_text(json.dumps({'cases':out,'passed':sum(x['pass'] for x in out),'total':len(out)},indent=2)+'\n',encoding='utf8');assert all(x['pass'] for x in out);print(f'{len(out)} unchanged NSC controls')
source=B/'source_aware_substitution_poc/run_safety.py';code=source.read_text(encoding='utf8');old="(H/'safety_results.json')";assert code.count(old)==1;code=code.replace(old,"(OUT/'historical_safety_results.json')")
exec(compile(code,str(source),'exec'),{'__file__':str(source),'__name__':'__main__','OUT':H/'evaluation'})
