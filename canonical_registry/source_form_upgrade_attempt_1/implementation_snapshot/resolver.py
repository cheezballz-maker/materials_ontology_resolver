"""Reusable source-independent evidence orchestration and exact registry lookup."""
import json
from pathlib import Path
from chemistry import describe,normalize_name,comparison_views
from form_characterizer import interpret,characterize
from identity_comparator import compare
from policy import decision,scope,validate_external
from source_form import assess as assess_source_form,source_claim

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
    def __init__(self,bridge,pubchem,chebi,reviewed_evidence=None,gsrs=None):
        self.bridge=bridge;self.pubchem=pubchem;self.chebi=chebi;self.gsrs=gsrs;self.claim_cache={}
        path=Path(reviewed_evidence) if reviewed_evidence else Path(__file__).with_name('reviewed_evidence.json')
        self.reviewed=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
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
        from evidence_retrieval import Acquisition,complete_name,identifier_keys,independent_lineages
        ev=dict(name=name,source_identifiers=list(identifiers),claims=[],providers=[],alias_decisions=[])
        def finish(status,code,local=None,form=None):
            r=dict(status=status,reason_codes=[code],evidence=ev)
            if local:r['structure']=local
            if form:r['form']=form
            return r
        if not isinstance(name,str) or not name.strip():return finish('INVALID','MISSING_NAME')
        if scope(name):return finish('OUT_OF_SCOPE','EXCLUDED_MATERIAL_FAMILY')
        if not complete_name(name):return finish('UNRESOLVED','INCOMPLETE_SOURCE_REFERENT')
        intent=dict(assertion or {})
        if structure is not None:
            try:local=describe(structure,input_type)
            except ValueError as e:
                ev['error']=str(e);return finish('INVALID','INVALID_STRUCTURE')
            intent['explicit_structure']=True
            primary=dict(status='SUCCESS',original=name,structure=local,origin='explicit typed source structure')
        else:primary=self.claim(name);local=primary.get('structure')
        ev['claims'].append(primary)
        ev['source_form']=dict(claims=[source_claim(name,primary)],status='NOT_YET_ASSESSED')
        try:keys=identifier_keys(identifiers,local)
        except ValueError as e:return finish('CONFLICT' if str(e)=='SOURCE_IDENTIFIER_CONFLICT' else 'INVALID',str(e),local)
        if primary.get('status')=='WARNING':return finish('UNRESOLVED','NAME_PARSER_WARNING_REQUIRES_REVIEW')
        if local:
            form=interpret(local,name,intent)
            if form['reason_codes']:
                return dict(status='UNRESOLVED',reason_codes=form['reason_codes'],form=form,evidence=ev,structure=local)
        acquisition=Acquisition(self.pubchem,self.chebi,self.gsrs)
        acquisition.source_name(name);acquisition.source_identifiers(keys)
        external=acquisition.external(local)
        if not local:
            validated,error=validate_external(external)
            if error:
                ev['providers']=acquisition.results;ev['external']=external;ev['retrieval']=acquisition.audit()
                return finish('CONFLICT',error)
            if not validated and self.gsrs:
                acquisition.query('GSRS',dict(kind='name',value=name,origin='source_preferred_name',asserts_source_identity=True))
                external=acquisition.external();validated,error=validate_external(external)
            if error or not validated:
                ev['providers']=acquisition.results;ev['external']=external;ev['retrieval']=acquisition.audit()
                return finish('CONFLICT' if error else 'UNRESOLVED',error or 'NO_VALIDATED_CANDIDATE')
            local=validated[0][0];ev['candidate_origin']='provisional external hypothesis; not identity acceptance'
            try:identifier_keys(identifiers,local)
            except ValueError as e:
                ev['external']=external;return finish('CONFLICT',str(e),local)
        # Existing policy handles all original-claim contradictions before any
        # retrieval expansion. No provider result may repair or replace a graph.
        external=acquisition.external(local)
        reviewed=[]
        for item in self.reviewed:
            if normalize_name(name).casefold() in {normalize_name(n).casefold() for n in item['names']}:
                reviewed.append(item)
        ev['reviewed_evidence']=reviewed
        def with_reviewed(ext):
            ext=dict(ext,rows=list(ext['rows']))
            for item in reviewed:
                for c in item['claims']:
                    d=describe(c['smiles']);ext['rows'].append(dict(SMILES=d['smiles'],InChI=d['inchi'],InChIKey=d['inchikey'],provider='Reviewed evidence',corroboration=False,url=c['url'],source=c['source']))
            return ext
        official=self.bridge.official(local);ev['official_inchi']=official
        initial=decision(local,official,with_reviewed(external),name,intent)
        local_support=primary.get('status')=='SUCCESS'
        expand_codes={'EXTERNAL_EVIDENCE_INCOMPLETE','NO_EXTERNAL_CORROBORATION'}
        can_expand=initial['status']=='AUTO_ACCEPT' or (initial['status']=='UNRESOLVED' and set(initial['reason_codes'])<=expand_codes)
        if can_expand and (initial['status']!='AUTO_ACCEPT' or not local_support):
            external=acquisition.expand(name,local,keys)
            # Alternative original source names are individually validated claims,
            # never presumed synonyms and never provider-generated local evidence.
            if not local_support:
                support=acquisition.source_alias_support(name,list(aliases),local,self.claim)
                if support:ev['local_source_support']=support;local_support=True
        external=with_reviewed(acquisition.external(local))
        result=decision(local,official,external,name,intent)
        if result['status']=='AUTO_ACCEPT' and not local_support and independent_lineages(result['validated_rows'])<2:
            result.update(status='UNRESOLVED',reason_codes=['EVIDENCE_LINEAGE_INDEPENDENCE_UNCONFIRMED'])
        # A corroborated candidate does not establish that the original source
        # intended its constitution, stereochemistry or ring/anomeric form.
        # Examine individual original claims before allowing any admission.
        alias_claims=[(alias,self.claim(alias)) for alias in aliases] if result['status']=='AUTO_ACCEPT' else []
        if result['status']=='AUTO_ACCEPT':
            source=assess_source_form(name,primary,alias_claims,local,intent,ev.get('local_source_support'))
            ev['source_form']=source
            if source['status']!='SUPPORTED':result.update(status=source['status'],reason_codes=source['reason_codes'])
        result.update(structure=local,evidence=ev)
        ev['providers']=acquisition.results;ev['external']=external
        ev['comparison_views']=comparison_views(local);ev['dimension_comparisons']=result['comparisons'];ev['form']=result.get('form')
        curated_names={normalize_name(v).casefold() for row in external['rows'] if row.get('provider')=='ChEBI' for v in row.get('names',[])}
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
                        elif normalize_name(alias).casefold() in curated_names:
                            accepted=True;attestation='ChEBI exact-form record name plus independent OPSIN structure'
                        else:
                            key=dict(kind='name',value=alias,origin='source_alias_claim_validation',asserts_source_identity=False)
                            ap=acquisition.query('PubChem',key,purpose='alias_validation')
                            ad=decision(d,official,ap,alias)
                            accepted=ad['status']=='AUTO_ACCEPT';attestation=ap
                        if accepted:reason='ALIAS_STRUCTURE_AND_EXTERNAL_NAME_CORROBORATED'
            ev['alias_decisions'].append(dict(alias=alias,accepted=accepted,reason=reason,comparison=cmp,attestation=attestation))
        ev['retrieval']=acquisition.audit()
        return result
