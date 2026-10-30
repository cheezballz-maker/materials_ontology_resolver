"""Execute frozen declared expectations against isolated SQLite fixtures."""
import collections,hashlib,json,socket
from pathlib import Path
import bootstrap
from providers import Bridge
from registry_identity_adapter import RegistrySnapshot
from registry_matcher import RegistryMatcher
from registry_matching_models import RetrievalPolicy
from matching_control_inputs import matching_input,fixture_registry
H=Path(__file__).resolve().parent
def deny(*a,**kw):raise AssertionError('NO_LIVE_PROVIDER_REQUESTS')
def main():
 socket.create_connection=deny
 freeze=json.loads((H/'controls/benchmark_freeze.json').read_text())['files']
 for name,d in freeze.items():assert hashlib.sha256((H/'controls'/name).read_bytes()).hexdigest()==d
 bridge=Bridge();rows=[]
 try:
  for kind in ('development','heldout'):
   for c in json.loads((H/f'controls/{kind}_controls.json').read_text())['cases']:
    registry=RegistrySnapshot(fixture_registry(c));incoming=matching_input(c);matcher=RegistryMatcher(registry,official_validator=bridge.official);result=matcher.match(incoming,RetrievalPolicy(**c.get('retrieval',{})),retain_full=True)
    matched=sorted(result['supported_candidate_ids']);ok=result['status']==c['expected_status']
    if 'expected_ids' in c:ok=ok and matched==sorted(c['expected_ids'])
    if 'expected_admission' in c:ok=ok and result['admission']['existing_policy_result']['status']==c['expected_admission']
    if 'expected_reason' in c:ok=ok and c['expected_reason'] in result['admission']['existing_policy_result']['reason_codes']
    if 'expected_chemical' in c:ok=ok and [r['chemical_status'] for r in result['candidate_results']]==c['expected_chemical']
    if result['status'] in ('MULTIPLE_CANONICAL_MATCHES','MATCH_UNRESOLVED','SOURCE_CONFLICT'):ok=ok and result['unique_matched_substance_id'] is None and result['diagnostic_reuse_proposal'] is None
    if c['id']=='D27':ok=ok and len(result['retrieval']['indexed_candidate_ids'])==2
    rows.append(dict(id=c['id'],partition=kind,issue=c['issue'],expected=c['expected_status'],passed=ok,control=c,result=result));print(c['id'],result['status'],result['admission']['existing_policy_result']['status'],ok,flush=True)
 finally:bridge.close()
 summary=dict(cases=len(rows),passed=sum(r['passed'] for r in rows),status_counts=dict(collections.Counter(r['result']['status'] for r in rows)),unsafe_unique_match_proposals=sum(r['result']['status']=='UNIQUE_CANONICAL_MATCH' and r['expected']!='UNIQUE_CANONICAL_MATCH' for r in rows),real_independent_external_corroborations=0,fixtures_are_disposable_registry_only=True,expectations_from_resolver=False)
 for file,obj in [('benchmark_results.json',dict(summary=summary,cases=rows)),('duplicate_ambiguity_results.json',{'cases':[r for r in rows if r['id'] in ('D12','D13','D14','D26','D27','D28','D17')]}),('admission_policy_results.json',{'cases':[r for r in rows if 'expected_admission' in r['control'] or r['id'] in ('D12','D13','D29','D30')]})]:
  (H/'evaluation'/file).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
 print(summary);assert summary['passed']==summary['cases'] and not summary['unsafe_unique_match_proposals']
if __name__=='__main__':main()
