import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path[:0]=[str(H),str(B/'charge_dimension_evidence'),str(B/'nsc002_experiment'),str(B/'nsc_architecture_experiment'),str(B)]
from evidence_adapters import fixture_evidence,candidate_assertions
from source_claim_reconciler import reconcile
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def hashes():return {n:hashlib.sha256((H/n).read_bytes()).hexdigest() for n in ('identity_evidence_models.py','identity_evidence_schema.json','dimension_claim_comparator.py','source_claim_reconciler.py','evidence_adapters.py','diagnostic_reconciliation_consumer.py')}
def run(kind):
    for n,v in read(H/'controls/benchmark_freeze.json')['sha256'].items():assert hashlib.sha256((H/'controls'/n).read_bytes()).hexdigest()==v
    if kind=='heldout':assert read(H/'evaluation/implementation_freeze.json')['sha256']==hashes()
    out=[]
    for c in read(H/f'controls/{kind}_controls.json')['cases']:
        ev=[fixture_evidence(x,c['id']) for x in c['claims']];r=reconcile(ev,candidate_assertions(c['candidate']),c['required_dimensions'],c['id']);relations=[]
        for comparison,item in zip(r['claim_comparisons'],c['claims']):relations.append(comparison.get('relationship') or comparison['dimensions'].get(item['dimension'],'UNKNOWN'))
        correct=relations==c['expected_relationships'] and r['result']==c['expected_result']
        out.append({'id':c['id'],'description':c['description'],'candidate':c['candidate'],'claims':[x.to_dict() for x in ev],'expected_relationships':c['expected_relationships'],'actual_relationships':relations,'expected_result':c['expected_result'],'result':r,'pass':correct})
    summary={'total':len(out),'passed':sum(x['pass'] for x in out),'false_compatible':sum(x['result']['result']=='RECONCILED_COMPATIBLE' and x['expected_result']!='RECONCILED_COMPATIBLE' for x in out),'false_incompatible':sum(x['result']['result']=='RECONCILIATION_CONFLICT' and x['expected_result']!='RECONCILIATION_CONFLICT' for x in out)}
    write(H/f'evaluation/{kind}_results.json',{'review':'CHEMICAL_REVIEW_PENDING','summary':summary,'cases':out})
    if kind=='development':write(H/'evaluation/implementation_freeze.json',{'sha256':hashes(),'stage':'AFTER_DEVELOPMENT_BEFORE_PUBLIC_HOLDOUT'})
    print(json.dumps({'kind':kind,**summary,'failures':[(x['id'],x['actual_relationships'],x['result']['result']) for x in out if not x['pass']]},indent=2))
if __name__=='__main__':run(sys.argv[1])
