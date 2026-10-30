"""Multiple retrieval routes plus declared snapshot-wide exhaustive fallback."""
from collections import defaultdict
import bootstrap
from chemistry import normalize_name,describe
from form_characterizer import characterize
from registry_matching_models import CandidateRetrievalResult,RetrievalPolicy

class RegistryRetriever:
 def __init__(self,registry):
  self.registry=registry;self.identifiers=defaultdict(set);self.graphs=defaultdict(set);self.constitutions=defaultdict(set);self.formulas=defaultdict(set);self.names=defaultdict(set)
  for sid,r in registry.entries.items():
   for t,v in r['identifiers']:self.identifiers[(t,v)].add(sid)
   for n in [r['candidate'].preferred_name,*r['aliases']]:self.names[normalize_name(n)].add(sid)
   d=r['descriptor']
   if d:
    self.graphs[d['smiles']].add(sid);self.constitutions[characterize(d)['connectivity']].add(sid);self.formulas[d['formula']].add(sid)
 def retrieve(self,incoming,source,policy=None):
  policy=(policy or RetrievalPolicy()).validate();self.registry.assert_unchanged();routes=defaultdict(list)
  def add(ids,route,value,qualification):
   for sid in sorted(ids):
    item=dict(route=route,value=value,qualification=qualification)
    if item not in routes[sid]:routes[sid].append(item)
  graph=source.get('graph_view') or incoming.retrieval_hypothesis
  if graph:
   try:
    d=describe(graph)
    add(self.identifiers[('InChIKey',d['inchikey'])],'FULL_INCHIKEY',d['inchikey'],'VALIDATED_GRAPH_DERIVED_RETRIEVAL_ONLY')
    add(self.graphs[d['smiles']],'EXPLICIT_GRAPH_SERIALIZATION',d['smiles'],'CANDIDATE_ONLY_FULL_COMPARISON_REQUIRED')
    add(self.constitutions[characterize(d)['connectivity']],'HEAVY_CONNECTIVITY_VIEW',characterize(d)['connectivity'],'LESS_SPECIFIC_RETRIEVAL_VIEW_ONLY')
    add(self.formulas[d['formula']],'MOLECULAR_FORMULA',d['formula'],'FORMULA_IS_NOT_IDENTITY')
   except Exception:pass
  pkg=incoming.concept.evidence_package
  record_kind={'PubChem':('COMPOUND','PubChemCID'),'ChEBI':('CHEMICAL_ENTITY','ChEBIID')}.get(pkg.source_name)
  # Source adapters establish the record referent; this correspondence is a
  # record lookup, never a certificate of chemical equivalence.
  if record_kind and pkg.source_record_type==record_kind[0]:
   value=pkg.source_record_id;add(self.identifiers[(record_kind[1],value)],'SOURCE_RECORD_REFERENCE',record_kind[1]+':'+value,'DOCUMENTED_ADAPTER_RECORD_REFERENT_ONLY')
  for c in pkg.claims:
   p=c.source_provenance;t=p.get('identifier_type')
   if t and (p.get('internal_consistency') is True or p.get('mapping_document') and c.dimension_assertions and not c.unresolved_dependencies):
    add(self.identifiers[(t,str(c.original_value))],'QUALIFIED_IDENTIFIER',t+':'+str(c.original_value),'VALIDATED_PROJECTION_OR_DOCUMENTED_MAPPING_CANDIDATE_ONLY')
  names=[incoming.name]+[c.original_value for c in pkg.claims if c.claim_role in ('CHEMICAL_NAME_ASSERTION','REPORTED_NAME_ASSOCIATION','UNVERIFIED_ALIAS') and isinstance(c.original_value,str)]
  for name in dict.fromkeys(n for n in names if n):
   n=normalize_name(name);add(self.names[n],'EXACT_REGISTRY_ALIAS_OR_NAME',name,'REGISTRY_ASSERTED_ALIAS_SOURCE_NAME_MAY_BE_UNVERIFIED')
   if policy.allow_exploratory_names and len(n)>=4:
    for stored,ids in self.names.items():
     if n.casefold() in stored.casefold():add(ids,'EXPLORATORY_NAME_CONTAINS',name,'LITERAL_TEXT_RETRIEVAL_ONLY_NOT_FUZZY_IDENTITY')
  indexed=sorted(routes)
  if policy.exhaustive:add(self.registry.entries,'EXHAUSTIVE_REGISTRY_SNAPSHOT',self.registry.sha256,'ALL_IDENTITY_RECORDS_INCLUDING_INSUFFICIENT_GRAPHS')
  ids=sorted(routes);truncated=policy.max_candidates is not None and len(ids)>policy.max_candidates
  if truncated:ids=ids[:policy.max_candidates]
  complete=policy.exhaustive and not truncated and set(ids)==set(self.registry.entries)
  return CandidateRetrievalResult(ids,{sid:routes[sid] for sid in ids},indexed,len(self.registry.entries),self.registry.sha256,complete,policy.exhaustive,truncated,[sid for sid,r in self.registry.entries.items() if r['descriptor'] is None])

def retrieve_substance_candidates(incoming_identity_evidence,registry,retrieval_policy=None):
 from comparison_session import qualify_source
 return RegistryRetriever(registry).retrieve(incoming_identity_evidence,qualify_source(incoming_identity_evidence.concept),retrieval_policy)
