"""Run frozen public controls, retaining every result and disagreement."""
import hashlib,importlib,json,sys
from collections import Counter
from pathlib import Path
H=Path(__file__).resolve().parents[1];sys.path.insert(0,str(H))
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify_freeze():
    f=read(H/'NSC-001/benchmark_freeze.json')
    for n,v in f['sha256'].items():
        if digest(H/n)!=v:raise ValueError('FROZEN_BENCHMARK_CHANGED: '+n)
def impl_hashes():
    paths=list((H/'architecture_A/implementation').glob('*.py'))+list((H/'architecture_B/implementation').glob('*.py'))+[H/'shared/semantic_interface.py',H/'shared/structural_comparator.py']
    return {str(p.relative_to(H)).replace('\\','/'):digest(p) for p in sorted(paths)}
def run(which):
    verify_freeze();lock=H/'evaluation/implementation_freeze.json'
    if which=='heldout' and (not lock.exists() or read(lock)['sha256']!=impl_hashes()):raise ValueError('DEVELOPMENT_IMPLEMENTATION_NOT_FROZEN')
    A=importlib.import_module('architecture_A.implementation.interpreter');B=importlib.import_module('architecture_B.implementation.interpreter')
    controls=read(H/'shared'/f'{which}_controls.json')['cases'];rows=[]
    for c in controls:
        rec={'id':c['id'],'source_name':c['input_name'],'candidate_id':c['id']+':candidate','expected_scope':c['expected_grammar_classification'],'expected_result':('OUT_OF_CONTRACT' if c['expected_grammar_classification']=='OUT_OF_CONTRACT' else c['expected_comparison_result']),'review':'CHEMICAL_REVIEW_PENDING'}
        for label,engine in [('A',A),('B',B)]:
            i=engine.interpret_name(c['input_name']);v=engine.validate_candidate(i,c['candidate_structure'],c.get('evaluation_context',{}))
            rec[label]={'scope':i.scope_status,'result':v.result,'constraints':i.structural_constraints,'reason_codes':v.reason_codes,'evidence':v.evidence,'scope_correct':i.scope_status==rec['expected_scope'],'correct':v.result==rec['expected_result']}
            if 'alternate_candidate' in c.get('evaluation_context',{}):rec[label]['alternate_result']=engine.validate_candidate(i,c['evaluation_context']['alternate_candidate']).result
            if 'second_source_name' in c.get('evaluation_context',{}):
                second=engine.interpret_name(c['evaluation_context']['second_source_name']);sv=engine.validate_candidate(second,c['candidate_structure'])
                rec[label]['second_claim_result']=sv.result
                rec[label]['record_conflict_proven']=sv.result=='DIFFERENT' and v.result=='SUPPORTED'
                rec[label]['record_conflict_correct']=rec[label]['record_conflict_proven'] if c['evaluation_context'].get('expected_record_resolution')=='CONFLICT' else None
        rec['agreement']=rec['A']['result']==rec['B']['result'];rows.append(rec)
    result={'suite':which,'review':'CHEMICAL_REVIEW_PENDING','cases':rows,'counts':{k:dict(Counter((x[k]['result'],x[k]['correct']) for x in [])) for k in []}}
    for k in ('A','B'):
        result['counts'][k]={'total':len(rows),'correct':sum(x[k]['correct'] for x in rows),'scope_correct':sum(x[k]['scope_correct'] for x in rows),'false_supported':sum(x[k]['result']=='SUPPORTED' and x['expected_result']!='SUPPORTED' for x in rows),'false_different':sum(x[k]['result']=='DIFFERENT' and x['expected_result']!='DIFFERENT' for x in rows),'record_conflicts_correct':sum(x[k].get('record_conflict_correct') is True for x in rows),'record_conflicts_total':sum('record_conflict_correct' in x[k] for x in rows),'results':dict(Counter(x[k]['result'] for x in rows))}
    write(H/'evaluation'/f'{which}_results.json',result)
    for k in ('A','B'):write(H/f'architecture_{k}/results_{which}.json',{'review':result['review'],'counts':result['counts'][k],'cases':[{'id':x['id'],**x[k]} for x in rows]})
    if which=='development':write(lock,{'sha256':impl_hashes(),'meaning':'Implementation frozen after development and before held-out execution.'})
    print(json.dumps({'suite':which,'counts':result['counts'],'disagreements':sum(not x['agreement'] for x in rows)},indent=2))
if __name__=='__main__':run(sys.argv[1])
