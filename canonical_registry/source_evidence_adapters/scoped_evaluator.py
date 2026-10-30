"""Default-off source-independent scope wrapper around the unchanged reconciler."""
import copy
import bootstrap
from evidence_adapter_contract import SCOPES,evidence
from evidence_adapters import candidate_assertions
from source_claim_reconciler import reconcile

def evaluate(pkg,candidate,dimensions,scope='RECORD_STRUCTURE',*,enabled=False):
 if not enabled:return {'diagnostic_enabled':False,'production_behavior':'UNCHANGED','canonical_admission':'NOT_PERFORMED'}
 if scope not in SCOPES:raise ValueError('UNKNOWN_RECONCILIATION_SCOPE')
 byid={c.evidence_id:c for c in pkg.claims};selected={i for i,scopes in pkg.claim_scopes.items() if scope in scopes}
 # Charge-only unknowns do not claim anything about constitution. A charge
 # question still includes them; scope projection never clears dependencies.
 selected={i for i in selected if not (byid[i].source_provenance.get('contract_id')=='ChargeDimensionEvidence' and 'protonation_charge' not in dimensions)}
 pending=list(selected)
 while pending:
  for dep in byid[pending.pop()].derivation_dependencies:
   if dep in byid and dep not in selected:selected.add(dep);pending.append(dep)
 claims=[]
 for c in pkg.claims:
  if c.evidence_id not in selected:continue
  c=copy.deepcopy(c)
  # Dependencies without assertions may be valid lineage but cannot themselves
  # establish dimensions. The current core treats them as active unknowns, so
  # no broader completeness claim is made in that situation.
  # Required dimensions define completeness, not permission to erase other
  # asserted contradictions. Keep all supported assertions for the core's
  # candidate and source/source incompatibility checks.
  claims.append(c)
 if scope=='INCOMING_CONCEPT':
  claims.append(evidence(pkg,'incoming_correspondence','UNKNOWN_ROLE',None,'$incoming',unresolved=['INCOMING_SOURCE_CORRESPONDENCE_NOT_ESTABLISHED']))
 if scope=='TERMINOLOGY' and not any(c.claim_role in ('CHEMICAL_NAME_ASSERTION','PARTIAL_IDENTITY_ASSERTION','REPORTED_NAME_ASSOCIATION','UNVERIFIED_ALIAS','UNKNOWN_ROLE') for c in claims):
  claims.append(evidence(pkg,'terminology_unavailable','UNKNOWN_ROLE',None,'$terminology',unresolved=['TERMINOLOGY_NOT_AVAILABLE']))
 rec=reconcile(claims,candidate_assertions(candidate) if candidate else {},dimensions,pkg.referent_id)
 established=bool(rec['supported_dimensions'])
 status='RECONCILIATION_CONFLICT' if rec['result']=='RECONCILIATION_CONFLICT' else 'RECONCILED_WITHIN_DECLARED_SCOPE' if rec['complete_for_requested_dimensions'] else 'STRUCTURAL_EVIDENCE_ESTABLISHED' if established and scope=='RECORD_STRUCTURE' else 'PARTIAL_IDENTITY_EVIDENCE_ESTABLISHED' if established else 'RECONCILIATION_UNRESOLVED'
 return dict(diagnostic_enabled=True,diagnostic_outcome=status,reconciliation=rec,declared_scope=scope,required_dimensions=list(dimensions),structural_evidence_established=any(c.dimension_assertions and c.claim_role=='STRUCTURAL_IDENTITY_ASSERTION' for c in claims),unresolved_claim_ids=[c.evidence_id for c in pkg.claims if c.unresolved_dependencies],retained_out_of_scope_claim_ids=[c.evidence_id for c in pkg.claims if c.evidence_id not in selected],record_terminology_fully_reconciled=scope=='TERMINOLOGY' and rec['complete_for_requested_dimensions'],sufficient_for_incoming_concept=False,eligibility_change='NOT_AUTHORIZED_OR_PERFORMED',canonical_admission='NOT_PERFORMED',external_corroboration='SEPARATE_NOT_ASSESSED')
