"""Apply experimental trace diagnostically to 81 saved names; no provider calls."""
import collections,concurrent.futures,json
from pathlib import Path
from semantic_adapter import trace
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
rows=read(B/'NOMENCLATURE_FALSE_HOLD_TAXONOMY.json');prior={x['cuma_index']:x for x in read(B/'deterministic_form_remediation/deterministic_form_replay.json')}
assert len(rows)==81
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda x:trace(x['preferred_name']),rows))
out=[]
for row,result in zip(rows,results):
 id=row['record_id'];r=prior[id];claims=result.get('claims',[]);mapped=[c for c in claims if c['mapping_status']=='MAPPED_BOUNDED']
 out.append(dict(cuma_index=id,preferred_name=row['preferred_name'],primary_blocker=row['primary_blocker'],semantic_layer_applicable=bool(claims),trace_established=bool(mapped),source_claim_established=bool(mapped),identity_constraint='UNKNOWN',operation_composition='INCOMPLETE',mobile_h_coverage='NOT_PROVEN',previous_blocker=r['reasons'],after_blocker=r['reasons'],eligibility_changed=False,experimental_trace=result,qualification='Mapping only; layer is not wired to resolver and cannot promote eligibility.'))
taut=[x for x in out if x['primary_blocker']=='tautomer specificity'];assert len(taut)==41
summary={'cases':len(out),'mapping_established':sum(x['trace_established'] for x in out),'no_mapping':sum(not x['trace_established'] for x in out),'eligibility_changed':0,'tautomer_primary':{'total':len(taut),'indicated_h_mapping':sum(any(c['mapping_status']=='MAPPED_BOUNDED' and c['semantic_type']=='INDICATED_HYDROGEN' for c in x['experimental_trace'].get('claims',[])) for x in taut),'added_h_mapping':sum(any(c['mapping_status']=='MAPPED_BOUNDED' and c['semantic_type']=='ADDED_INDICATED_HYDROGEN' for c in x['experimental_trace'].get('claims',[])) for x in taut),'no_traceable_claim':sum(not x['experimental_trace'].get('claims') for x in taut),'mapping_unresolved':sum(bool(x['experimental_trace'].get('claims')) and not x['trace_established'] for x in taut),'operation_incomplete':len(taut),'mobile_h_coverage_not_proven':len(taut)}}
(B/'semantic_81_case_replay.json').write_text(json.dumps(dict(summary=summary,cases=out),indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(summary,indent=2))
