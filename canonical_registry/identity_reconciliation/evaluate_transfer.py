"""Transfer frozen rules to real saved CUMA and PubChem records without new lookups."""
import collections,hashlib,json,sqlite3,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path[:0]=[str(H),str(B/'charge_dimension_evidence'),str(B/'nsc002_experiment'),str(B/'nsc_architecture_experiment'),str(B)]
from run_benchmark import hashes
from evidence_adapters import raw_claim,architecture_b_claim,source_structure,candidate_assertions
from identity_evidence_models import DIMENSIONS
from source_claim_reconciler import reconcile
from diagnostic_reconciliation_consumer import consume
from chemistry import describe
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,x):(H/'evaluation'/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
assert hashes()==read(H/'evaluation/implementation_freeze.json')['sha256']
source=B/'deterministic_form_remediation/replay_local.py';code=source.read_text(encoding='utf8')
for n in ('deterministic_form_replay.json','local_eligibility_metrics.json','newly_blocked_cases.json','post_remediation_gate_value.json'):
    old=f"(H/'{n}')";assert code.count(old)==1;code=code.replace(old,f"(OUT/'{n}')")
ctx={'__file__':str(source),'__name__':'__main__','OUT':H/'evaluation'};exec(compile(code,str(source),'exec'),ctx)
samples={x['cuma_index']:x for x in read(B/'fresh_blinded_evaluation/fresh_sample.json')}
db=sqlite3.connect((B/'fresh_blinded_evaluation/run/candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
saved={i:json.loads(raw) for i,raw in db.execute('select cuma_index,evidence_json from candidate')};db.close()
out=[];providers={}
for r in ctx['results']:
    i=r['cuma_index'];sample=samples[i];claims=[architecture_b_claim('CUMA',i,'preferred',sample['preferred_name'])]
    claims += [raw_claim('CUMA',i,'alias'+str(j),'UNVERIFIED_ALIAS',a) for j,a in enumerate(sample['aliases'])]
    candidate=raw_claim('CUMA',i,'parsed_candidate','CANDIDATE_OBSERVATION',r['candidate'],role_established=True,origin='CANDIDATE_DERIVED');candidate.dimension_assertions=candidate_assertions(r['candidate']);claims.append(candidate)
    for j,identifier in enumerate(saved[i].get('source_identifiers',[])):claims.append(raw_claim('CUMA',i,'identifier'+str(j),'SOURCE_IDENTIFIER',identifier,role_established=True))
    rec=reconcile(claims,candidate_assertions(r['candidate']),DIMENSIONS,'CUMA:'+str(i));before=consume(r['source_form'],rec);after=consume(r['source_form'],rec,enabled=True,referent_id='CUMA:'+str(i))
    out.append({'source_type':'source_terminology','source_id':'CUMA','record_id':i,'claims':[c.to_dict() for c in claims],'reference_status':r['prior_verdict'],'candidate':r['candidate'],'reconciliation':rec,'before':before,'after':after})
    for p in saved[i]['providers']:
        if p.get('provider')=='PubChem':
            for row in p.get('rows',[]):
                if row.get('CID') is not None and row.get('SMILES'):
                    providers.setdefault(str(row['CID']),{'origin_cuma_record':i,'row':row})
external=[]
for cid,item in sorted(providers.items(),key=lambda x:int(x[0]))[:20]:
    row=item['row'];claims=[]
    try:
        d=describe(row['SMILES']);candidate=d['smiles'];claims.append(source_structure('PubChem',cid,'provided_structure',row['SMILES']))
        if row.get('IUPACName'):claims.append(architecture_b_claim('PubChem',cid,'provided_name',row['IUPACName']))
        claims.append(raw_claim('PubChem',cid,'provided_CID','SOURCE_IDENTIFIER',cid,role_established=True))
        rec=reconcile(claims,candidate_assertions(candidate),DIMENSIONS,'PubChem:'+cid)
        external.append({'source_type':'chemical_reference_database','source_id':'PubChem','record_id':cid,'saved_origin':item,'claims':[c.to_dict() for c in claims],'candidate':candidate,'reconciliation':rec,'scope':'Self-consistency of actual cached record fields, not independent validation or CUMA corroboration.'})
    except Exception as e:external.append({'record_id':cid,'error':str(e),'saved_origin':item})
def summary(records):
    valid=[x for x in records if 'reconciliation' in x];comparisons=[c for r in valid for c in r['reconciliation']['claim_comparisons']];relations=collections.Counter(v for c in comparisons for v in c.get('dimensions',{}).values())
    return {'records':len(records),'records_with_multiple_claims':sum(len(r.get('claims',[]))>1 for r in valid),'claims_with_at_least_one_comparable_dimension':sum(any(v not in ('UNKNOWN',) for v in c.get('dimensions',{}).values()) for c in comparisons),'dimension_relationship_counts':dict(relations),'record_outcomes':dict(collections.Counter(r['reconciliation']['result'] for r in valid)),'complete_for_all_requested_dimensions':sum(r['reconciliation']['complete_for_requested_dimensions'] for r in valid),'errors':len(records)-len(valid)}
write('cross_source_results.json',{'method':'After rule/benchmark freeze, transfer to original 224 CUMA records and up to first 20 unique cached PubChem CIDs sorted numerically. No source records manufactured. PubChem self-consistency is not independent corroboration. Parser-derived CUMA candidate remains an observation. Unmapped identifier and active alias roles remain unresolved.','source_type_summaries':{'CUMA':summary(out),'PubChem':summary(external)},'CUMA':out,'PubChem':external,'available_unique_saved_pubchem_CIDs':len(providers)})
def eligibility(key):return {'correct_eligible':sum(r[key]['local_eligible'] and r['reference_status']=='CORRECT' for r in out),'incorrect_eligible':sum(r[key]['local_eligible'] and r['reference_status']=='INCORRECT' for r in out),'unadjudicable_eligible':sum(r[key]['local_eligible'] and r['reference_status']=='UNADJUDICABLE' for r in out),'status_counts':dict(collections.Counter(r[key]['source_form']['status'] for r in out))}
write('local_eligibility_before_after.json',{'method':'Default-off preserves existing source-form output. Enabled adds unresolved active-claim obligations and preserves conflicts. No existing specific reason is deleted. Conservative gating losses measure evidence-adapter incompleteness, not proved chemical ambiguity.','before':eligibility('before'),'after':eligibility('after'),'changed_records':[r for r in out if r['before']!=r['after']],'all_records':len(out),'gained':sum(r['after']['local_eligible'] and not r['before']['local_eligible'] for r in out),'production_admission':'UNCHANGED'})
print(json.dumps({'CUMA':summary(out),'PubChem':summary(external),'before':eligibility('before'),'after':eligibility('after')},indent=2))
