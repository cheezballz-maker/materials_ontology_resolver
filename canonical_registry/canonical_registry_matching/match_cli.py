"""JSON-in / proposal-out CLI. Only diagnostic JSON may be written."""
import argparse,json,socket
from dataclasses import fields
from pathlib import Path
import bootstrap
from providers import Bridge
from registry_identity_adapter import RegistrySnapshot
from registry_matcher import RegistryMatcher
from registry_matching_models import MatchingInput,RetrievalPolicy
from evaluate_real_registry import make_input
from correspondence_models import IncomingConcept
from evidence_adapter_contract import EvidencePackage
from identity_evidence_models import IdentityEvidence

def decode(packet):
 if packet.get('provider') in ('PubChem','ChEBI'):
  result=make_input(packet['provider'],packet['record'],packet['provenance'],packet['source_concept_id'])
 else:
  c=packet['concept'];p=c['evidence_package'];allowed={f.name for f in fields(EvidencePackage)}
  args={k:v for k,v in p.items() if k in allowed};args['claims']=[IdentityEvidence(**v) for v in p['claims']]
  result=MatchingInput(IncomingConcept(c['source_concept_id'],EvidencePackage(**args),c['binding'],c.get('identity_scope','DISCRETE_MOLECULAR'),c.get('provenance',{})),packet.get('name',''))
 for k in ('retrieval_hypothesis','official_validation','external_evidence','form_assertion','source_profile','evidence_origin'):
  if k in packet:setattr(result,k,packet[k])
 if packet.get('identity_scope'):result.concept.identity_scope=packet['identity_scope']
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True,type=Path);p.add_argument('--registry',type=Path,default=Path(__file__).resolve().parent.parent/'output/registry.sqlite');p.add_argument('--output',type=Path);p.add_argument('--indexed-only',action='store_true');p.add_argument('--max-candidates',type=int);p.add_argument('--no-official-validation',action='store_true');a=p.parse_args()
 if a.output and (a.output.suffix.lower()!='.json' or a.output.exists()):raise ValueError('Output must be a NEW diagnostic .json file; existing files cannot be overwritten')
 socket.create_connection=lambda *args,**kwargs: (_ for _ in ()).throw(RuntimeError('NETWORK_DISABLED_READ_ONLY_MATCHING'))
 incoming=decode(json.loads(a.input.read_text(encoding='utf-8-sig')));registry=RegistrySnapshot(a.registry);bridge=None if a.no_official_validation else Bridge()
 try:r=RegistryMatcher(registry,official_validator=bridge.official if bridge else None).match(incoming,RetrievalPolicy(exhaustive=not a.indexed_only,max_candidates=a.max_candidates))
 finally:
  if bridge:bridge.close()
 text=json.dumps(r,indent=2,ensure_ascii=False)+'\n'
 if a.output:a.output.write_text(text,encoding='utf8')
 else:print(text,end='')
if __name__=='__main__':main()
