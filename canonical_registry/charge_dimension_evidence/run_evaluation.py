import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
sys.path[:0]=[str(H),str(B/'nsc002_experiment'),str(B/'nsc_architecture_experiment'),str(B)]
from build_evidence import build
from charge_comparison_attribution import compare
from chemistry import describe
from diagnostic_evidence_consumer import consume
from source_form import assess
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def baseline_source(name,candidate,aliases):
    d=describe(candidate);primary={'status':'SUCCESS','structure':d}
    pairs=[(a,{'status':'SUCCESS','structure':d}) for a in aliases]
    # Synthetic consumer tests use independently specified same-structure aliases,
    # not provider lookups; source evidence builder still interprets each name.
    return assess(name,primary,pairs,d)
def impl_hashes():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in list(H.glob('*.py'))+[H/'charge_evidence_schema.json'] if p.name not in ('freeze_controls.py','run_evaluation.py','evaluate_cohort.py','finalize.py','test_charge_evidence.py')}
def run(kind):
    for n,v in read(H/'controls/benchmark_freeze.json')['sha256'].items():assert hashlib.sha256((H/'controls'/n).read_bytes()).hexdigest()==v
    lock=H/'evaluation/implementation_freeze.json'
    if kind=='heldout':assert read(lock)['hashes']==impl_hashes()
    controls=read(H/'controls/heldout_controls.json') if kind=='heldout' else read(H/'controls/positive_controls.json')+read(H/'controls/unknown_controls.json')
    out=[]
    for c in controls:
        e=build(c['source_name'],c['aliases'],c['candidate']);out.append({'id':c['id'],'expected_operation':c['expected_operation'],'expected_dimension':c['expected_dimension'],'actual_operation':e.operation_result,'actual_dimension':e.dimension_result,'pass':e.operation_result==c['expected_operation'] and e.dimension_result==c['expected_dimension'],'evidence':e.to_dict()})
    write(H/f'evaluation/{kind}_results.json',out)
    if kind=='development':
        comparisons=[]
        for c in read(H/'controls/contradiction_controls.json')['cases']:
            r=compare(describe(c['a']),describe(c['b']));comparisons.append({**c,'actual':r['dimensions']['protonation_charge'],'pass':r['dimensions']['protonation_charge']==c['expected'],'comparison':r})
        write(H/'evaluation/comparator_attribution_results.json',comparisons)
        write(lock,{'hashes':impl_hashes(),'stage':'AFTER_DEVELOPMENT_BEFORE_PUBLIC_HOLDOUT'})
    print(json.dumps({'suite':kind,'cases':len(out),'passed':sum(x['pass'] for x in out),'comparators_passed':sum(x['pass'] for x in comparisons) if kind=='development' else None},indent=2))
if __name__=='__main__':run(sys.argv[1])
