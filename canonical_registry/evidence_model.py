"""Deterministic record qualification: evidence states are not votes."""
from chemistry import describe
from form_characterizer import characterize
from identity_comparator import compare
from provider_capabilities import PROFILES

CORROBORATES='CORROBORATES';CONTRADICTS='CONTRADICTS';NO_MATCH='NO_MATCH';UNAVAILABLE='UNAVAILABLE';NON_DISCRIMINATING='NON_DISCRIMINATING'
PROVIDER_RECORD_AMBIGUOUS='PROVIDER_RECORD_AMBIGUOUS'
STATES=(CORROBORATES,CONTRADICTS,NO_MATCH,UNAVAILABLE,NON_DISCRIMINATING,PROVIDER_RECORD_AMBIGUOUS)
DIMENSIONS=('connectivity','stereochemistry','isotope_specification','protonation_charge','electronic_state','tautomeric_form','components','component_stoichiometry')

def availability(status,has_rows=False):
    if status in ('ERROR','TIMEOUT','NOT_QUERIED','CACHE_MISSING','RATE_LIMITED','SERVICE_UNAVAILABLE','UNAVAILABLE'):
        return UNAVAILABLE
    if status in ('NO_MATCH','SUCCESS') and not has_rows:return NO_MATCH
    return NON_DISCRIMINATING

def aggregate_route(assessments,status='SUCCESS',has_rows=None):
    """Aggregate one provider + exact route + source query without voting."""
    states={a['state'] for a in assessments}
    if CORROBORATES in states and CONTRADICTS in states:return PROVIDER_RECORD_AMBIGUOUS
    if CONTRADICTS in states:return CONTRADICTS
    if CORROBORATES in states:return CORROBORATES
    if NON_DISCRIMINATING in states:return NON_DISCRIMINATING
    return availability(status,bool(assessments) if has_rows is None else has_rows)

def route_key(audit):
    p=audit.get('provenance') or {}
    return (p.get('retrieved_via') or audit.get('provider'),p.get('query_type'),p.get('query'),p.get('query_origin'))

def correspondence(row,p,profile,desc):
    kind=p.get('query_type'); value=p.get('query'); origin=p.get('query_origin')
    if p.get('query_status')!='SUCCESS' or kind not in profile.accepted_exact_lookup_routes or not value:return None
    if kind=='name':
        if origin not in ('source_preferred_name','source_alias_claim_validation'):return None
        names=list(row.get('names') or [])+[row.get('IUPACName'),row.get('matched_search_value')]
        return 'EXACT_RETURNED_NAME' if value in names else None
    fields={'PubChemCID':'CID','ChEBIID':'ChEBIID','UNII':'UNII','DTXSID':'DTXSID','DTXCID':'DTXCID','CASRegistryNumber':'CASRN'}
    if kind=='InChIKey':
        if origin!='source_identifier':return None
        return 'EXACT_FULL_INCHIKEY' if value==desc['inchikey'] and value==row.get('InChIKey') else None
    if origin!='source_identifier':return None
    return 'EXACT_SOURCE_IDENTIFIER' if str(row.get(fields.get(kind),''))==value else None

def assess(row,candidate):
    p=row.get('provenance') or {};profile=PROFILES.get(row.get('provider'))
    audit=dict(provider=row.get('provider'),provenance=p,record_id=p.get('record_id'),state=NON_DISCRIMINATING,comparison=None,reason=None)
    if not profile:
        audit['reason']='PROVIDER_PROFILE_UNAVAILABLE';return audit
    if not any(row.get(k) for k in profile.record_identifier_types):
        audit['reason']='PROVIDER_RECORD_IDENTIFIER_MISSING';return audit
    if profile.provider_name=='GSRS' and row.get('gsrs_moiety_validation')!='COMPLETE_INTEGER_FORM_AGREES':
        audit['reason']='GSRS_MOIETY_FORM_UNVALIDATED';return audit
    try:
        d=describe(row.get('SMILES') or row.get('IsomericSMILES') or '')
        if row.get('InChI') and d['inchi']!=row['InChI']:raise ValueError('identifier mismatch')
        if row.get('InChIKey') and d['inchikey']!=row['InChIKey']:raise ValueError('identifier mismatch')
    except (ValueError,RuntimeError,TypeError):
        audit['reason']='INVALID_OR_INCONSISTENT_PROVIDER_STRUCTURE';return audit
    cmp=compare(candidate,d);audit['comparison']=cmp;audit['structure']=d['smiles']
    basis=correspondence(row,p,profile,d);audit['correspondence_basis']=basis
    if not basis:
        audit['reason']='SOURCE_CLAIM_CORRESPONDENCE_UNVERIFIED';return audit
    dependence=p.get('source_dependence_classification',profile.source_independence_default)
    if dependence not in ('SOURCE_INDEPENDENT','SOURCE_DEPENDENCE_UNKNOWN','SOURCE_DEPENDENCE_KNOWN'):
        dependence='SOURCE_DEPENDENCE_UNKNOWN'
    audit['source_dependence_classification']=dependence
    if dependence=='SOURCE_DEPENDENCE_KNOWN':
        audit['reason']='DIRECT_SOURCE_DEPENDENCE';return audit
    a,b=characterize(candidate),characterize(d)
    required=['connectivity','protonation_charge','electronic_state','tautomeric_form']
    if a['stereo_state']!='NOT_APPLICABLE' or b['stereo_state']!='NOT_APPLICABLE':required.append('stereochemistry')
    if a['isotopes'] or b['isotopes']:required.append('isotope_specification')
    if a['component_count']>1 or b['component_count']>1:required.extend(('components','component_stoichiometry'))
    audit['required_dimensions']=sorted(required)
    audit['represented_dimensions']=sorted(required)
    if a['tautomer_sensitive'] and profile.tautomer_representation_behavior!='EXPLICIT_GRAPH':
        audit['reason']='TAUTOMER_FORM_NOT_DISCRIMINATED';return audit
    if (a['component_count']>1 or a['charge_distribution'] or b['component_count']>1 or b['charge_distribution']) and profile.known_structure_standardization_behavior!='VALIDATED_COMPLETE_MOIETIES':
        audit['reason']='CHARGE_OR_COMPONENT_FORM_NOT_DISCRIMINATED';return audit
    if a['stereo_state'] in ('PARTIAL','UNSPECIFIED') or b['stereo_state'] in ('PARTIAL','UNSPECIFIED'):
        audit['reason']='STEREO_NOT_FULLY_SPECIFIED';return audit
    if cmp['assessment']=='DISTINCT':
        if basis=='EXACT_FULL_INCHIKEY':audit['reason']='HYPOTHESIS_LOOKUP_DIFFERENT_FORM';return audit
        audit.update(state=CONTRADICTS,reason='VERIFIED_INCOMPATIBLE_FORM');return audit
    if cmp['assessment']!='EXACT':audit['reason']='COMPARISON_UNRESOLVED';return audit
    audit.update(state=CORROBORATES,reason='EXACT_FORM_VALIDATED');return audit

def qualifying_lineage(audit):
    return bool(audit.get('state')==CORROBORATES and audit.get('source_dependence_classification') in ('SOURCE_INDEPENDENT','SOURCE_DEPENDENCE_UNKNOWN'))
