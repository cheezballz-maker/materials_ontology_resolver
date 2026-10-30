"""Annotated independent controls exercise field semantics, not CUMA rules."""
import bootstrap
from evidence_adapter_contract import *
from semantic_bridges import interpret

def adapt(record,candidate):
 pkg=EvidencePackage(record['source'],'ANNOTATED_CONTROL',record['record_id'],{'payload_path':'control:'+record['record_id'],'payload_sha256':'ANNOTATED_FIXTURE_NOT_REAL_SOURCE','url':'control:documented-field-semantics'})
 ids={i:pkg.referent_id+':field'+str(i) for i in range(len(record['fields']))}
 for i,f in enumerate(record['fields']):
  key='field'+str(i);path=f'$.fields[{i}].value';v=f['value'];kind=f['kind'];deps=[ids.get(f['depends_on'],pkg.referent_id+':missing')] if 'depends_on' in f else []
  if kind=='structure':structural_field(pkg,key,v,path,qualified=not f.get('missing_provenance'),dependencies=deps)
  elif kind=='record_identifier':record_identifier(pkg,key,v,path,'TEST_RECORD_ID')
  elif kind=='derived_key':
   dep=next((c for c in pkg.claims if c.evidence_id in deps),None);identifier_field(pkg,key,v,path,'InChIKey',graph=dep.original_value if dep else None,dependency=dep)
  elif kind=='inchi':identifier_field(pkg,key,v,path,'InChI')
  elif kind=='validated_mapping':validated_mapping(pkg,key,v,path,f.get('smiles'),f.get('mapping_document'),independent=f.get('independent',False))
  elif kind in ('name','generated_name'):interpret(pkg,key,v,path,candidate=candidate,dependencies=deps,candidate_derived=f.get('candidate_derived',False),charge=f.get('charge',False))
  elif kind=='annotated_name':
   a=assertion(None,f['dimension'],f['state'],f['framework']);pkg.add(evidence(pkg,key,'PARTIAL_IDENTITY_ASSERTION',v,path,binding='QUALIFIED_PARTIAL_ASSERTION',basis='RULE_ESTABLISHED',assertions={f['dimension']:a},extra={'annotation_basis':'Frozen reviewed-rule fixture; not automatic name parsing'}),['TERMINOLOGY','INCOMING_CONCEPT'])
  elif kind=='association':associated_name(pkg,key,v,path)
  elif kind=='metadata':pkg.add(evidence(pkg,key,'NONBINDING_METADATA',v,path,binding='NONBINDING_ASSOCIATION'),[])
  else:pkg.add(evidence(pkg,key,'UNKNOWN_ROLE',v,path,established=False,unresolved=['SOURCE_FIELD_ROLE_UNKNOWN']),ALL)
 return pkg
