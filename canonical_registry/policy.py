"""Form-aware admission policy, separate from providers and ID allocation."""
import re
from chemistry import describe
from form_characterizer import interpret
from identity_comparator import compare

OOS=re.compile(r'\b(polymer|copolymer|alloy|bronze|steel|mixture|extract|preparation|resin|glass|ceramic|mineral|bentonite|kaolin|quartz|racemic|racemate)\b|\bpoly\(',re.I)
def scope(name):return 'OUT_OF_SCOPE' if OOS.search(name or '') else None
def eligible(d,name,assertion=None):return not scope(name) and interpret(d,name,assertion)['specification']=='SPECIFIED'

def validate_external(external):
    validated=[]
    for row in external.get('rows',[]):
        try:
            d=describe(row.get('SMILES') or row.get('IsomericSMILES') or '')
            if d['inchi']!=row.get('InChI') or d['inchikey']!=row.get('InChIKey'):return [],'PROVIDER_IDENTIFIER_CONFLICT'
            validated.append((d,row))
        except (ValueError,RuntimeError):return [],'PROVIDER_STRUCTURE_INVALID'
    return validated,None

def decision(local,official,external,name,assertion=None,source_profile=None,source_complete=None):
    from evidence_model import assess,availability,qualifying_lineage,aggregate_route,route_key,CONTRADICTS,CORROBORATES,NON_DISCRIMINATING
    result=dict(status='UNRESOLVED',reason_codes=[],comparisons=[],validated_rows=[])
    def finish(status,code):result.update(status=status,reason_codes=[code]);return result
    if scope(name):return finish('OUT_OF_SCOPE','EXCLUDED_MATERIAL_FAMILY')
    if not local:return finish('UNRESOLVED','NO_VALIDATED_CANDIDATE')
    form=interpret(local,name,assertion,source_profile);result['form']=form
    typed=bool((assertion or {}).get('explicit_structure'))
    complete=typed if source_complete is None else bool(source_complete)
    assessed=[assess(row,local) for row in external.get('rows',[])]
    if not complete:
        for a in assessed:
            if a['state'] in (CORROBORATES,CONTRADICTS):
                a.update(state=NON_DISCRIMINATING,reason='SOURCE_SPECIFICITY_UNESTABLISHED')
    result['evidence_states']=assessed or [dict(state=availability(external.get('status','NOT_QUERIED')),reason='NO_USABLE_PROVIDER_RECORD')]
    groups={}
    for a in assessed:groups.setdefault(route_key(a),[]).append(a)
    route_states={key:aggregate_route(items) for key,items in groups.items()}
    result['provider_routes']=[dict(provider=k[0],route=k[1],query=k[2],query_origin=k[3],state=route_states[k],record_ids=[a.get('record_id') for a in items],per_record_states=[dict(record_id=a.get('record_id'),state=a['state'],reason=a.get('reason')) for a in items]) for k,items in groups.items()]
    for row,a in zip(external.get('rows',[]),assessed):
        result['comparisons'].append(dict(provider=row.get('provider','PubChem'),comparison=a.get('comparison'),evidence_state=a['state']))
    if form['reason_codes']:result['reason_codes']=form['reason_codes'];return result
    if not official or not official.get('agrees') or official.get('status') not in ('SUCCESS','WARNING'):return finish('UNRESOLVED','OFFICIAL_INCHI_NOT_CONFIRMED')
    if not complete:return finish('UNRESOLVED','SOURCE_INTERPRETATION_INCOMPLETE')
    if CONTRADICTS in route_states.values():return finish('CONFLICT','VERIFIED_SOURCE_IDENTITY_CONTRADICTION')
    valid=[row for row,a in zip(external.get('rows',[]),assessed) if route_states[route_key(a)]==CORROBORATES and qualifying_lineage(a) and row.get('corroboration',True)]
    result['validated_rows']=valid
    if not typed and not valid:return finish('UNRESOLVED','NO_QUALIFYING_CORROBORATION')
    return finish('AUTO_ACCEPT','SOURCE_STRUCTURE_VALIDATED' if typed else 'INDEPENDENT_EXACT_FORM_CORROBORATION')

def reconcile(local,official,external,name,assertion=None,source_complete=None):
    r=decision(local,official,external,name,assertion,source_complete=source_complete)
    return r['status'],';'.join(r['reason_codes'])
