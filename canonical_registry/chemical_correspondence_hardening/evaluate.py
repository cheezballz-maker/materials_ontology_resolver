"""Replay frozen inputs only; use source files, never rebuilt labels."""
import collections,json,socket
from pathlib import Path
import bootstrap
from bootstrap import BASE as B
from assessment import assess
from record_inputs import load
from stereo_comparison import compare
H=Path(__file__).resolve().parent
R=B/'real_world_validation'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,obj):(H/'evaluation'/n).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def deny(*a,**kw):raise AssertionError('NEW_PROVIDER_QUERIES_DISABLED')
def metrics(rows):
 scored=[r for r in rows if r['accuracy_population_eligible']];out={'n':len(scored),'reference_coverage':len(scored)/len(rows),'confusion':dict(collections.Counter(r['expected_correspondence']+' -> '+r['actual_correspondence'] for r in scored))}
 for label,key in [('CHEMICALLY_EQUIVALENT','equivalence'),('CHEMICALLY_DIFFERENT','difference')]:
  tp=sum(r['actual_correspondence']==label==r['expected_correspondence'] for r in scored);pred=sum(r['actual_correspondence']==label for r in scored);exp=sum(r['expected_correspondence']==label for r in scored)
  precision=tp/pred if pred else None;recall=tp/exp if exp else None
  out[key]={'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision and recall else None,'tp':tp,'predicted':pred,'expected':exp}
 out.update(false_equivalences=sum(r['actual_correspondence']=='CHEMICALLY_EQUIVALENT' and r['expected_correspondence']!='CHEMICALLY_EQUIVALENT' for r in scored),false_differences=sum(r['actual_correspondence']=='CHEMICALLY_DIFFERENT' and r['expected_correspondence']!='CHEMICALLY_DIFFERENT' for r in scored),necessary_abstentions=sum(r['actual_correspondence']==r['expected_correspondence']=='CHEMICALLY_UNRESOLVED' for r in scored),unnecessary_abstentions=sum(r['actual_correspondence']=='CHEMICALLY_UNRESOLVED' and r['expected_correspondence']!='CHEMICALLY_UNRESOLVED' for r in scored),agreement=sum(r['actual_correspondence']==r['expected_correspondence'] for r in scored)/len(scored))
 return out
def main():
 socket.create_connection=deny
 corpus=read(R/'reference_corpus/reference_cases.json')['cases']
 old=[r for p in ('development_reference','frozen_evaluation') for r in read(R/f'evaluation/{p}_results.json')['cases']];previous={r['case_id']:r for r in old};rows=[];review=[]
 for c in corpus:
  s,t=load(c);result=assess(s,t,enabled=True);before=previous[c['case_id']];actual=result['represented_structure_comparison']['status']
  row={k:before[k] for k in ('case_id','expected_correspondence','accuracy_population_eligible','partition','category')};row.update(actual_correspondence=actual,before=before['actual_correspondence'],result=result);rows.append(row)
  review.append(dict(case_id=c['case_id'],priority='HIGH' if c['case_id'] in ('RW12','RW17','RW29','RW30') else 'NORMAL',original_case=c,documentary_expected=c['expected_correspondence'],original_output=before,corrected_output=row,disagreement=actual!=c['expected_correspondence'] if c['accuracy_population_eligible'] else None,unresolved_dimensions=[k for k,v in result['represented_structure_comparison']['dimension_comparisons'].items() if v not in ('EXACT_COMPATIBLE','NOT_APPLICABLE')],suggested_reviewer_decision='Confirm field contradiction; do not approve full record identity' if c['case_id'] in ('RW12','RW17') else 'Adjudicate bonded-metal depiction; keep UNKNOWN pending evidence' if c['case_id']=='RW29' else 'Check specified C1 mismatch under all graph mappings; proposed DIFFERENT' if c['case_id']=='RW30' else 'Confirm or correct documentary graph label; separately assess source referent and provenance',qualified_expert_review='PENDING_NOT_PERFORMED'))
 write('chemical_correspondence_results.json',{'cases':rows,'network_requests':0,'production_default':'UNCHANGED'})
 write('documentary_accuracy_before_after.json',dict(ORIGINAL_DOCUMENTARY_CORPUS=metrics(old),POST_CORRECTION_DOCUMENTARY_CORPUS=metrics(rows),EXPERT_REVIEWED_SUBSET={'n':0,'metrics':None,'status':'NOT_EVALUATED'},PROVENANCE_AUDITED_SUBSET={'n':0,'metrics':None,'status':'No pair with independently established upstream evidence'},labels_modified=False))
 write('stereo_before_after.json',{'changed_cases':[dict(case_id=r['case_id'],before=r['before'],after=r['actual_correspondence'],expected=r['expected_correspondence']) for r in rows if r['before']!=r['actual_correspondence']],'rw30_mapping':compare(corpus[29]['source_structure'],corpus[29]['reference_structure']),'controls':[dict(**c,actual=compare(c['left'],c['right'])) for c in read(H/'controls/stereo_controls.json')['cases']]})
 (H/'reference_review/chemical_review_package.json').write_text(json.dumps(dict(cases=review,qualified_expert_review='NOT_PERFORMED',purpose='Independent reviewer work queue, not completed adjudication'),indent=2,ensure_ascii=False)+'\n',encoding='utf8')
 # Reuse the existing saved-pair and read-only SQL runner with output roots
 # redirected. Original inputs/reference corpus remain at their frozen paths.
 f=R/'evaluate_saved_sources.py';code=f.read_text();code=code.replace('from correspondence_assessment import assess','from assessment import assess');code=code.replace('H=Path(__file__).resolve().parent','H=NEW_OUT').replace("H/'reference_corpus/reference_cases.json'","ORIGINAL/'reference_corpus/reference_cases.json'")
 ctx={'__file__':str(f),'__name__':'saved_pair_replay','NEW_OUT':H,'ORIGINAL':R};exec(compile(code,str(f),'exec'),ctx);ctx['main']()
 print(json.dumps(metrics(rows),indent=2))
if __name__=='__main__':main()
