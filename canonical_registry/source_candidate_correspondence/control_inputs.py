"""Translate frozen, explicitly annotated controls into existing evidence objects.

This adapter never parses general names or obtains expected benchmark outcomes.
"""
import bootstrap
import copy
from correspondence_models import IncomingConcept,CanonicalCandidate
from evidence_adapter_contract import EvidencePackage,structural_field,evidence,associated_name,identifier_field
from evidence_adapters import assertion,candidate_assertions
from semantic_bridges import interpret

def incoming(item):
 s=item['source'];pkg=EvidencePackage('IndependentIncoming','CONTROL',s['source_concept_id'],{'payload_path':'Frozen:'+s['source_concept_id'],'document':s['provenance']['document']});binding=[]
 for j,c in enumerate(s['claims']):
  key='claim'+str(j);kind=c['kind'];path=f'$.source.claims[{j}]';value=c.get('original') or c.get('structure')
  if kind=='structure':x=structural_field(pkg,key,c['structure'],path,qualified=not c.get('unverified'))
  elif kind in ('annotated_name','validated_identifier'):
   # Explicit upstream annotated identities are separate from the name parser.
   # No runtime dictionary maps these names to benchmark candidate structures.
   x=evidence(pkg,key,'CHEMICAL_NAME_ASSERTION' if kind=='annotated_name' else 'STRUCTURAL_IDENTIFIER',value,path,binding='BINDING_IDENTITY_ASSERTION',basis='RULE_ESTABLISHED',assertions=candidate_assertions(c['structure']),extra={'annotation_document':c.get('annotation_document','Frozen explicit independently annotated identity claim'),'review_status':'CHEMICAL_REVIEW_PENDING'});pkg.add(x,['INCOMING_CONCEPT'])
  elif kind=='association':x=associated_name(pkg,key,value,path)
  elif kind=='name':x=interpret(pkg,key,value,path,charge=False)
  elif kind=='identifier':x=identifier_field(pkg,key,value,path,'CASRegistryNumber')
  else:x=pkg.add(evidence(pkg,key,'UNKNOWN_ROLE',value,path,established=False,unresolved=['SOURCE_IDENTITY_MEANING_UNESTABLISHED']),['INCOMING_CONCEPT'])
  if kind!='association':binding.append(x.evidence_id)
  if c.get('origin'):x.source_provenance['origin']=c['origin']
  for d in c.get('unknown_dimensions',[]):x.dimension_assertions[d]={'state':'UNKNOWN','rule_id':'SOURCE_SPECIFICITY_UNESTABLISHED'}
 return IncomingConcept(s['source_concept_id'],pkg,dict(status=s['link_status'],kind=s['link_kind'],evidence_ids=binding,document=s['provenance']['document']),s['identity_scope'],s['provenance'])

def candidates(ids,inventory):
 byid={x['candidate_substance_id']:x for x in inventory['candidates']}
 return [CanonicalCandidate(**copy.deepcopy(byid[i])) for i in ids]
