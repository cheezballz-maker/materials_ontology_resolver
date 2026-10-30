"""Existing NSC and charge producers; no grammar expansion, no name guessing."""
import bootstrap
from rdkit import Chem
from architecture_B.implementation import interpreter as nsc1
from architecture_B.implementation.semantic_operations import compose
from architecture_B.nsc002_interpreter import interpreter as nsc2
from build_evidence import build as build_charge
from evidence_adapter_contract import evidence
from evidence_adapters import assertion

def source_graph(obj):
 if obj.contract_id=='NSC-001':
  p=obj.semantic_operations[0]['parameters'];return Chem.MolToSmiles(compose(p['parent'],p['chain_length']))
 # Compile only already recognized operations into a comparison view. This is
 # not a new parser. Ring locants correspond to ordered source scaffold atoms.
 r=Chem.RWMol(Chem.MolFromSmiles('c1ccccc1'))
 for op in obj.semantic_operations:
  p=op['parameters'];kind=p['substituent']
  for loc in p['positions']:
   group=Chem.MolFromSmiles({'fluoro':'F','chloro':'Cl','bromo':'Br','iodo':'I','nitro':'[N+](=O)[O-]'}[kind]);offset=r.GetNumAtoms()
   r=Chem.RWMol(Chem.CombineMols(r,group));r.AddBond(loc-1,offset,Chem.BondType.SINGLE)
 m=r.GetMol();Chem.SanitizeMol(m);return Chem.MolToSmiles(m)

def interpret(pkg,key,name,path,*,candidate=None,dependencies=(),candidate_derived=False,charge=True):
 obj=nsc1.interpret_name(name)
 if obj.scope_status!='IN_CONTRACT':obj=nsc2.interpret_name(name)
 c=evidence(pkg,key,'PARTIAL_IDENTITY_ASSERTION' if obj.scope_status=='IN_CONTRACT' else 'CHEMICAL_NAME_ASSERTION',name,path,binding='QUALIFIED_PARTIAL_ASSERTION' if obj.scope_status=='IN_CONTRACT' else 'ACTIVE_UNRESOLVED_CLAIM',basis='RULE_ESTABLISHED' if obj.scope_status=='IN_CONTRACT' else 'UNVERIFIED',origin='CANDIDATE_DERIVED' if candidate_derived else 'DERIVED_SOURCE',dependencies=dependencies,extra={'contract_id':obj.contract_id,'contract_version':obj.contract_version,'source_span':{'start':0,'end':len(name)},'source_claims':obj.source_claims,'semantic_operations':obj.semantic_operations,'structural_constraints':obj.structural_constraints,'semantic_interpretation':obj.to_dict(),'verified_exact_alias':False})
 if obj.scope_status=='IN_CONTRACT':
  graph=source_graph(obj);c.dimension_assertions={'constitution':assertion(graph,'constitution')}
  validate=nsc1.validate_candidate if obj.contract_id=='NSC-001' else nsc2.validate_candidate
  v=validate(obj,candidate or graph);c.source_provenance['candidate_correspondence']=v.to_dict()
  # Source assertion itself is candidate-independent. UNKNOWN correspondence
  # remains a dependency rather than assuming an operation established identity.
  if v.result=='UNKNOWN':c.unresolved_dependencies=['SEMANTIC_CANDIDATE_CORRESPONDENCE_UNKNOWN']
 else:c.unresolved_dependencies=list(obj.unresolved_dependencies)
 pkg.add(c,['TERMINOLOGY','INCOMING_CONCEPT'])
 if charge:
  result=build_charge(name,[],candidate or (source_graph(obj) if obj.scope_status=='IN_CONTRACT' else 'C'))
  q=evidence(pkg,key+':charge','PARTIAL_IDENTITY_ASSERTION',name,path,binding='QUALIFIED_PARTIAL_ASSERTION',basis='RULE_ESTABLISHED' if result.dimension_result=='SUPPORTED' else 'UNVERIFIED',origin='CANDIDATE_DERIVED' if candidate_derived else 'DERIVED_SOURCE',dependencies=[c.evidence_id],unresolved=result.unresolved_dependencies,extra={'contract_id':'ChargeDimensionEvidence','contract_version':result.version,'producer_result':result.to_dict(),'source_span':{'start':0,'end':len(name)}})
  if result.dimension_result=='SUPPORTED' and obj.scope_status=='IN_CONTRACT':q.dimension_assertions={'protonation_charge':assertion(source_graph(obj),'protonation_charge')}
  # Unknown charge is retained as a dimension obligation only when that
  # dimension is requested; package evaluation projects assertions by scope.
  pkg.add(q,['TERMINOLOGY','INCOMING_CONCEPT'])
 return c
