"""Reusable source-independent evidence orchestration and exact registry lookup."""
from chemistry import describe,normalize_name,comparison_views
from form_characterizer import interpret,characterize
from identity_comparator import compare
from policy import decision,scope,validate_external
from source_form import assess as assess_source_form,source_claim
from name_interpretation import interpret_preferred,normalized_parse_query
from systematic_notation import descriptors
from composition_constraints import extract as extract_composition,check as check_composition

def lookup(candidate,identities):
    """Complete in-memory identity search. Candidate sufficiency precedes this API.

    identities: iterable of (canonical ID, validated descriptor). No alias lookup
    or Standard-InChI-only match may assert exact identity.
    """
    f=characterize(candidate)
    if f['stereo_state'] in ('UNSPECIFIED','PARTIAL') or f['advanced_stereo']:
        return dict(status='UNRESOLVED',reason='STEREO_UNSPECIFIED',candidate_ids=[])
    matches=[];unknown=[]
    for sid,d in identities:
        c=compare(candidate,d)
        if c['assessment']=='EXACT':matches.append(sid)
        elif c['assessment']=='UNRESOLVED':unknown.append(sid)
    if len(set(matches))==1:return dict(status='EXACT',substance_id=matches[0])
    if matches or unknown:return dict(status='UNRESOLVED',reason='AMBIGUOUS_OR_UNKNOWN_REGISTRY_COMPARISON',candidate_ids=matches+unknown)
    return dict(status='NO_MATCH',substance_id=None)

class Resolver:
    def __init__(self,bridge,pubchem,chebi,reviewed_evidence=None,gsrs=None,comptox=None,semantic_adapter=None):
        self.bridge=bridge;self.pubchem=pubchem;self.chebi=chebi;self.gsrs=gsrs;self.comptox=comptox;self.claim_cache={}
        # Experimental evidence only: no adapter claim may alter admission.
        self.semantic_adapter=semantic_adapter
        # Deprecated argument retained for callers; case fixtures are not runtime policy.
    def resolve(self,name,identities,**kwargs):
        """Public outcomes only; NO_MATCH never allocates an ID automatically."""
        evidence=self.evaluate(name,**kwargs)
        if evidence['status']!='AUTO_ACCEPT':return dict(status='UNRESOLVED',admissible=False,may_admit_new=False,analysis=evidence)
        found=lookup(evidence['structure'],identities)
        return dict(**found,admissible=found['status']!='UNRESOLVED',may_admit_new=found['status']=='NO_MATCH',analysis=evidence)
    def claim(self,name):
        if name in self.claim_cache:return self.claim_cache[name]
        if not isinstance(name,str) or not name.strip():return dict(status='INVALID',original=name)
        q=normalize_name(name)
        if scope(q):return dict(status='OUT_OF_SCOPE',original=name)
        if len(q)>1000:return dict(status='UNRESOLVED',original=name,reason='NAME_LENGTH_BUDGET')
        r=self.bridge.opsin(q);r['original']=name
        if r['status']=='SUCCESS':
            try:r['structure']=describe(r['smiles'])
            except ValueError as e:r.update(status='INVALID',diagnostic=str(e))
        self.claim_cache[name]=r;return r
    def evaluate(self,name,aliases=(),structure=None,input_type='smiles',assertion=None,identifiers=()):
        from evidence_retrieval import Acquisition,complete_name,identifier_keys
        ev=dict(name=name,source_identifiers=list(identifiers),claims=[],providers=[],alias_decisions=[],local_eligibility=dict(status='NOT_ELIGIBLE',reason_codes=['NO_COMPLETE_SOURCE_CANDIDATE']))
        def finish(status,code,local=None,form=None):
            r=dict(status=status,reason_codes=[code],evidence=ev)
            if local:r['structure']=local
            if form:r['form']=form
            return r
        if not isinstance(name,str) or not name.strip():return finish('INVALID','MISSING_NAME')
        if scope(name) or not complete_name(name):
            ev['name_interpretation'],ev['source_name_profile']=interpret_preferred(name,dict(status='NOT_PARSED'),aliases)
            ev['source_name_profile']['composition_constraints']=extract_composition(name,assertion)
            return finish('OUT_OF_SCOPE','EXCLUDED_MATERIAL_FAMILY') if scope(name) else finish('UNRESOLVED','INCOMPLETE_SOURCE_REFERENT')
        intent=dict(assertion or {})
        if structure is not None:
            try:local=describe(structure,input_type)
            except ValueError as e:
                ev['error']=str(e)
                if str(e).startswith('InChI generation failed:'):
                    return finish('UNRESOLVED','UNSUPPORTED_STRUCTURE_CAPABILITY')
                return finish('INVALID','INVALID_STRUCTURE')
            intent['explicit_structure']=True
            primary=dict(status='SUCCESS',original=name,structure=local,origin='explicit typed source structure')
        else:primary=self.claim(name);local=primary.get('structure')
        ev['claims'].append(primary)
        name_claim=self.claim(name) if structure is not None else primary
        alternate=None
        if name_claim.get('status')!='SUCCESS':
            alternate_query=normalized_parse_query(name)
            if alternate_query:alternate=self.claim(alternate_query)
        selected=name_claim if name_claim.get('status')=='SUCCESS' else (alternate or name_claim)
        cml=None
        if selected.get('status')=='SUCCESS' and descriptors(name) and hasattr(self.bridge,'opsin_cml'):
            cml=self.bridge.opsin_cml(selected.get('query') or selected.get('original') or name)
        ev['name_interpretation'],ev['source_name_profile']=interpret_preferred(name,name_claim,aliases,alternate,cml_result=cml)
        constraints=extract_composition(name,intent,local if primary.get('status')=='SUCCESS' else None,
            'SOURCE_TYPED_STRUCTURE' if structure is not None else 'SOURCE_NAME_PARSE')
        ev['source_name_profile']['composition_constraints']=constraints
        if structure is not None and name_claim.get('structure') and compare(name_claim['structure'],local)['assessment']=='DISTINCT':
            ev['name_interpretation'].update(status='CONFLICTING',diagnostic='NAME_CONFLICT')
        ev['source_form']=dict(claims=[source_claim(name,primary)],status='NOT_YET_ASSESSED')
        try:keys=identifier_keys(identifiers,local)
        except ValueError as e:return finish('CONFLICT' if str(e)=='SOURCE_IDENTIFIER_CONFLICT' else 'INVALID',str(e),local)
        if primary.get('status')=='WARNING':return finish('UNRESOLVED','NAME_PARSER_WARNING_REQUIRES_REVIEW')
        if self.semantic_adapter is not None:
            try:ev['nomenclature_semantics']=self.semantic_adapter.trace(name)
            except Exception:ev['nomenclature_semantics']=dict(status='UNRESOLVED',constraint='UNKNOWN',reason='TRACE_FAILURE',claims=[])
        alias_claims=[]
        if local:
            comp=check_composition(constraints,local);ev['composition_comparison']=comp
            if comp['status']=='CONFLICT':return finish('CONFLICT',';'.join(comp['reason_codes']),local)
            form=interpret(local,name,intent,ev['source_name_profile'])
            alias_claims=[(alias,self.claim(alias)) for alias in aliases]
            preliminary=assess_source_form(name,primary,[],local,intent,None,ev['source_name_profile'])
            source=assess_source_form(name,primary,alias_claims,local,intent,None,ev['source_name_profile'])
            ev['preliminary_source_form']=preliminary;ev['source_form']=source
            local_reasons=list(source['reason_codes'])
            if not intent.get('explicit_structure') and ev['name_interpretation']['status']!='ESTABLISHED':local_reasons.append('SOURCE_INTERPRETATION_INCOMPLETE')
            if ev['name_interpretation']['status']=='CONFLICTING':local_reasons.append('NAME_CONFLICT')
            if comp['status']=='UNRESOLVED':local_reasons.append('MULTICOMPONENT_SOURCE_INCOMPLETE')
            local_reasons.extend(x for x in form['reason_codes'] if x not in local_reasons)
            if source['status']!='SUPPORTED' and not local_reasons:local_reasons.append('SOURCE_FORM_UNRESOLVED')
            if local_reasons:
                ev['claims'].extend(c for a,c in alias_claims)
                ev['alias_decisions']=[dict(alias=a,accepted=False,reason='SUBJECT_NOT_ADMITTED',comparison=None,attestation=None) for a,c in alias_claims]
                ev['local_eligibility']=dict(status='NOT_ELIGIBLE',reason_codes=local_reasons)
                return dict(status='CONFLICT' if source['status']=='CONFLICT' or ev['name_interpretation']['status']=='CONFLICTING' else 'UNRESOLVED',reason_codes=local_reasons,form=form,evidence=ev,structure=local,evidence_states=[])
            if form['reason_codes']:
                return dict(status='UNRESOLVED',reason_codes=form['reason_codes'],form=form,evidence=ev,structure=local)
            official=self.bridge.official(local);ev['official_inchi']=official
            if not official or not official.get('agrees') or official.get('status') not in ('SUCCESS','WARNING'):
                ev['claims'].extend(c for a,c in alias_claims)
                ev['alias_decisions']=[dict(alias=a,accepted=False,reason='SUBJECT_NOT_ADMITTED',comparison=None,attestation=None) for a,c in alias_claims]
                ev['local_eligibility']=dict(status='NOT_ELIGIBLE',reason_codes=['OFFICIAL_INCHI_NOT_CONFIRMED'])
                return dict(status='UNRESOLVED',reason_codes=['OFFICIAL_INCHI_NOT_CONFIRMED'],form=form,evidence=ev,structure=local,evidence_states=[])
            ev['local_eligibility']=dict(status='DETERMINISTIC_LOCAL_EXACT_ELIGIBLE',reason_codes=[])
        acquisition=Acquisition(self.pubchem,self.chebi,self.gsrs,comptox=self.comptox)
        acquisition.source_name(name);acquisition.source_identifiers(keys)
        external=acquisition.external(local)
        if not local:
            # Invalid external records are non-discriminating candidate evidence,
            # not proof that the source makes a contradictory claim.
            validated=[]
            for row in external.get('rows',[]):
                part,error=validate_external({'rows':[row]})
                if not error:validated.extend(part)
            if not validated and self.gsrs:
                acquisition.query('GSRS',dict(kind='name',value=name,origin='source_preferred_name',asserts_source_identity=True))
                external=acquisition.external();validated=[]
                for row in external.get('rows',[]):
                    part,error=validate_external({'rows':[row]})
                    if not error:validated.extend(part)
            if not validated:
                ev['providers']=acquisition.results;ev['external']=external;ev['retrieval']=acquisition.audit()
                return finish('UNRESOLVED','NO_VALIDATED_CANDIDATE')
            local=validated[0][0];ev['candidate_origin']='provisional external hypothesis; not identity acceptance'
            comp=check_composition(constraints,local);ev['composition_comparison']=comp
            if comp['status']=='CONFLICT':
                ev['providers']=acquisition.results;ev['external']=external;ev['retrieval']=acquisition.audit()
                return finish('CONFLICT',';'.join(comp['reason_codes']),local)
            try:identifier_keys(identifiers,local)
            except ValueError as e:
                ev['external']=external;return finish('CONFLICT',str(e),local)
        # Existing policy handles all original-claim contradictions before any
        # retrieval expansion. No provider result may repair or replace a graph.
        external=acquisition.external(local)
        official=ev.get('official_inchi') or self.bridge.official(local);ev['official_inchi']=official
        # A parser's success is not enough: check source-form specificity before
        # allowing a provider difference to count as a genuine contradiction.
        preliminary_source=ev.get('preliminary_source_form') or assess_source_form(name,primary,[],local,intent,None,ev['source_name_profile'])
        ev['preliminary_source_form']=preliminary_source
        source_complete=bool(ev['local_eligibility']['status']=='DETERMINISTIC_LOCAL_EXACT_ELIGIBLE' and
            (structure is not None or (primary.get('status')=='SUCCESS' and ev['name_interpretation']['status']=='ESTABLISHED')))
        initial=decision(local,official,external,name,intent,ev['source_name_profile'],source_complete)
        local_support=primary.get('status')=='SUCCESS'
        expand_codes={'NO_QUALIFYING_CORROBORATION'}
        can_expand=initial['status']=='AUTO_ACCEPT' or (initial['status']=='UNRESOLVED' and set(initial['reason_codes'])<=expand_codes)
        if can_expand and (initial['status']!='AUTO_ACCEPT' or not local_support):
            external=acquisition.expand(name,local,keys)
            # Alternative original source names are individually validated claims,
            # never presumed synonyms and never provider-generated local evidence.
            if not local_support:
                support=acquisition.source_alias_support(name,list(aliases),local,self.claim)
                if support:ev['local_source_support']=support;local_support=True
        external=acquisition.external(local)
        result=decision(local,official,external,name,intent,ev['source_name_profile'],source_complete)
        # A corroborated candidate does not establish that the original source
        # intended its constitution, stereochemistry or ring/anomeric form.
        # Examine individual original claims before allowing any admission.
        alias_claims=alias_claims or ([(alias,self.claim(alias)) for alias in aliases] if result['status']=='AUTO_ACCEPT' else [])
        if result['status']=='AUTO_ACCEPT':
            source=assess_source_form(name,primary,alias_claims,local,intent,ev.get('local_source_support'),ev['source_name_profile'])
            ev['source_form']=source
            if source['status']!='SUPPORTED':result.update(status=source['status'],reason_codes=source['reason_codes'])
        # Retrieval and aliases cannot supply the meaning of an unknown name.
        if result['status']=='AUTO_ACCEPT' and (ev['name_interpretation']['status']=='CONFLICTING' or (structure is None and ev['name_interpretation']['status']!='ESTABLISHED')):
            n=ev['name_interpretation']
            result.update(status='CONFLICT' if n['status']=='CONFLICTING' else 'UNRESOLVED',reason_codes=[n['diagnostic']])
        if result['status']=='AUTO_ACCEPT' and ev.get('composition_comparison',{}).get('status')=='UNRESOLVED':
            result.update(status='UNRESOLVED',reason_codes=['MULTICOMPONENT_SOURCE_INCOMPLETE'])
        result.update(structure=local,evidence=ev)
        ev['providers']=acquisition.results;ev['external']=external
        ev['comparison_views']=comparison_views(local);ev['dimension_comparisons']=result['comparisons'];ev['form']=result.get('form')
        curated_names={v for row in result['validated_rows'] if row.get('provider')=='ChEBI' for v in row.get('names',[])}
        for pos,alias in enumerate(aliases):
            claim=alias_claims[pos][1] if alias_claims else self.claim(alias);ev['claims'].append(claim);d=claim.get('structure')
            accepted=False;reason='SUBJECT_NOT_ADMITTED';cmp=None;attestation=None
            if result['status']=='AUTO_ACCEPT':
                reason='ALIAS_NOT_INDEPENDENTLY_CORROBORATED'
                if d and interpret(d,alias)['specification']=='SPECIFIED':
                    cmp=compare(local,d)
                    if cmp['assessment']=='EXACT':
                        alias_form=assess_source_form(alias,claim,[],d)
                        if alias_form['status']!='SUPPORTED':
                            reason='ALIAS_SOURCE_SPECIFICITY_UNSUPPORTED'
                        elif alias in curated_names:
                            accepted=True;attestation='ChEBI exact-form record name plus independent OPSIN structure'
                        else:
                            key=dict(kind='name',value=alias,origin='source_alias_claim_validation',asserts_source_identity=False)
                            ap=acquisition.query('PubChem',key,purpose='alias_validation')
                            ad=decision(d,official,ap,alias,source_complete=True)
                            accepted=ad['status']=='AUTO_ACCEPT';attestation=ap
                        if accepted:reason='ALIAS_STRUCTURE_AND_EXTERNAL_NAME_CORROBORATED'
            ev['alias_decisions'].append(dict(alias=alias,accepted=accepted,reason=reason,comparison=cmp,attestation=attestation))
        ev['retrieval']=acquisition.audit(result.get('evidence_states',[]))
        return result
