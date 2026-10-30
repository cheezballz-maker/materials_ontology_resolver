import hashlib,json,socket,sys
from pathlib import Path
import bootstrap
from record_inputs import load
from correspondence_assessment import assess
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def deny(*a,**kw):raise AssertionError('NO_NETWORK_IN_VALIDATION_EXECUTION')
def main(partition):
 socket.create_connection=deny
 f=read(H/'reference_corpus/benchmark_freeze.json')
 for n,v in f['files'].items():assert sha(H/'reference_corpus'/n)==v
 for n,v in f['material_hashes'].items():assert sha(Path(n))==v
 out=[]
 for c in read(H/'reference_corpus/reference_cases.json')['cases']:
  if c['partition']!=partition:continue
  incoming,candidate=load(c);result=assess(incoming,candidate,enabled=True)
  out.append(dict(case_id=c['case_id'],partition=partition,category=c['category'],reference_quality=c['review_status'],accuracy_population_eligible=c['accuracy_population_eligible'],expected_correspondence=c['expected_correspondence'],expected_source_correspondence=c['expected_source_identity_correspondence'],expected_independence=c['expected_independence_status'],actual_correspondence=result['represented_structure_comparison']['status'],actual_source_correspondence=result['source_identity_correspondence']['status'],actual_independence=result['evidence_independence']['status'],result=result))
 (H/f'evaluation/{partition}_results.json').write_text(json.dumps({'partition':partition,'cases':out,'review_status':'DOCUMENTARY_GROUNDING_WITHOUT_QUALIFIED_EXPERT_REVIEW','blinding':'NOT_BLINDED'},indent=2,ensure_ascii=False)+'\n',encoding='utf8')
 print(json.dumps([dict(case_id=r['case_id'],expected=r['expected_correspondence'],actual=r['actual_correspondence'],source=r['actual_source_correspondence'],independence=r['actual_independence'],eligible=r['result']['admission_eligibility']['eligible']) for r in out],indent=2))
if __name__=='__main__':main(sys.argv[1])
