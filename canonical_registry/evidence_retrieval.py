"""Bounded evidence acquisition, not identity policy or source-specific knowledge.

Original claims and hypothesis-derived discovery are separate. Discovery does
not corroborate source identity; source-linked contradictory claims may veto.
All comparisons use the unchanged identity comparator. No validation fixtures,
registry records, source indices, or parent transformations are consulted.
"""
import copy
import re
from chemistry import describe, normalize_name
from identity_comparator import compare
from policy import validate_external


def complete_name(name):
    """Detect visibly incomplete delimiters, without repairing a source name."""
    stack=[];pairs={')':'(',']':'[','}':'{'}
    for c in name:
        if c in '([{':stack.append(c)
        elif c in pairs:
            if not stack or stack.pop()!=pairs[c]:return False
    return not stack and not name.rstrip().endswith(',')


def identifier_keys(identifiers,candidate=None):
    keys=[]
    for item in identifiers:
        kind=item.get('identifier_type');value=item.get('identifier_value')
        if not isinstance(value,str) or not value or value!=value.strip():raise ValueError('INVALID_SOURCE_IDENTIFIER')
        valid=False
        if kind=='InChIKey':
            valid=bool(re.fullmatch('[A-Z]{14}-[A-Z]{10}-[A-Z]',value))
            if valid and candidate and value!=candidate['inchikey']:raise ValueError('SOURCE_IDENTIFIER_CONFLICT')
        elif kind=='InChI':
            d=describe(value,'inchi');valid=True
            # InChI is a retrieval key, not a fixed-tautomer reconstruction.
            if candidate and value!=candidate['inchi']:raise ValueError('SOURCE_IDENTIFIER_CONFLICT')
        elif kind=='PubChemCID':valid=bool(re.fullmatch('[1-9][0-9]*',value))
        elif kind=='ChEBIID':valid=bool(re.fullmatch('CHEBI:[1-9][0-9]*',value))
        elif kind=='UNII':valid=bool(re.fullmatch('[A-Z0-9]{10}',value))
        elif kind=='DTXSID':valid=bool(re.fullmatch('DTXSID[0-9]+',value))
        elif kind=='DTXCID':valid=bool(re.fullmatch('DTXCID[0-9]+',value))
        elif kind=='CASRegistryNumber':
            valid=bool(re.fullmatch('[1-9][0-9]{1,6}-[0-9]{2}-[0-9]',value))
            if valid:
                digits=value.replace('-','');valid=sum((i+1)*int(x) for i,x in enumerate(reversed(digits[:-1])))%10==int(digits[-1])
        elif kind=='ECNumber':
            valid=bool(re.fullmatch('[0-9]{3}-[0-9]{3}-[0-9]',value))
            if valid:
                digits=value.replace('-','');valid=sum((i+1)*int(x) for i,x in enumerate(digits[:-1]))%11==int(digits[-1])
        else:raise ValueError('UNSUPPORTED_SOURCE_IDENTIFIER_TYPE')
        if not valid:raise ValueError('INVALID_SOURCE_IDENTIFIER')
        key=dict(kind=kind,value=value,origin='source_identifier',asserts_source_identity=True)
        if key not in keys:keys.append(key)
    if len(keys)>8:raise ValueError('SOURCE_IDENTIFIER_LIMIT')
    return keys


def hypothesis_keys(candidate):
    # Revalidate the descriptor; keys retain the full graph, including fragments.
    d=describe(candidate['smiles'])
    if (d['inchi'],d['inchikey'])!=(candidate['inchi'],candidate['inchikey']):raise ValueError('CANDIDATE_IDENTIFIER_CONFLICT')
    return [dict(kind=k,value=v,origin='validated_hypothesis',asserts_source_identity=False)
            for k,v in [('InChIKey',d['inchikey']),('SMILES',d['smiles']),('InChI',d['inchi'])]]


def provenance(row,result,key):
    r=copy.deepcopy(row);provider=r.get('provider') or result.get('provider','unknown')
    family='GSRS' if provider in ('GSRS','FDA GSRS','NCATS GSRS') else provider
    record=str(r.get('record_id') or r.get('UNII') or r.get('ChEBIID') or r.get('CID') or r.get('url') or result.get('url','unknown'))
    raw_times=[x.get('retrieved_at') for x in result.get('retrieval',[]) if x.get('retrieved_at')]
    prior=r.get('provenance',{})
    lineage=set(prior.get('lineage',[]))|{family+':'+record}
    if family=='CompTox':lineage.add('DSSTox:'+record)
    # Known upstream references join families; mere database multiplicity never
    # proves independence. The raw reference documents remain in the audit.
    for ref in r.get('structure_references',[]):
        citation=(ref.get('citation','')+' '+ref.get('docType','')).lower()
        if 'pubchem' in citation:lineage.add('PubChem:upstream')
        if 'chebi' in citation:lineage.add('ChEBI:upstream')
        if 'srs' in citation:lineage.add('GSRS:upstream')
    r['provider']=family
    r['provenance']=dict(provider=provider,family=family,record_id=record,retrieved_via=result.get('provider'),
        query=key['value'],query_type=key['kind'],query_origin=key['origin'],
        query_status=result.get('status'),
        retrieved_at=result.get('retrieved_at') or (raw_times[-1] if raw_times else None),
        url=r.get('url') or result.get('url'),lineage=sorted(lineage),
        independence=prior.get('independence','UNDETERMINED'),
        source_dependence_classification=prior.get('source_dependence_classification','SOURCE_DEPENDENCE_UNKNOWN'),
        note='Repeated lookups/mirrors are one record; cross-provider independence is not inferred.')
    return r


def deduplicate(rows):
    retained=[];seen=set();duplicates=[]
    for r in rows:
        p=r.get('provenance',{});signature=(p.get('family'),p.get('query_type'),p.get('query'),p.get('query_origin'),p.get('record_id'),r.get('SMILES'),r.get('InChI'),r.get('InChIKey'))
        if signature in seen:duplicates.append(p);continue
        seen.add(signature);retained.append(r)
    return retained,duplicates


def independent_lineages(rows):
    """Conservative external-only gate; absent lineage proof cannot be a vote.

    Adapters in this increment retain provenance but do not claim independent
    experimental origins. A future audited normalized evidence adapter may supply
    DOCUMENTED independence. Never infer it from provider brand or record count.
    """
    groups=[]
    for r in rows:
        p=r.get('provenance',{})
        if p.get('independence')!='DOCUMENTED':continue
        origins=set(p.get('lineage',[]));family=p.get('family')
        if not origins:continue
        joined=[g for g in groups if origins & g['origins'] or family in g['families'] or any(x.startswith(f+':') for x in origins for f in g['families']) or any(x.startswith(family+':') for x in g['origins'])]
        for g in joined:origins|=g['origins'];groups.remove(g)
        groups.append({'origins':origins,'families':{family}|set().union(*(g['families'] for g in joined))})
    return len(groups)


class Acquisition:
    def __init__(self,pubchem,chebi,gsrs=None,max_queries=16,comptox=None):
        self.providers={'PubChem':pubchem,'ChEBI':chebi}
        if gsrs:self.providers['GSRS']=gsrs
        if comptox:self.providers['CompTox']=comptox
        self.max_queries=max_queries;self.results=[];self.seen={};self.candidate_diagnostics=[];self.blocked_queries=[]
    def query(self,provider,key,purpose='primary'):
        token=(provider,key['kind'],key['value'],purpose)
        if token in self.seen:return self.seen[token]
        if len(self.results)>=self.max_queries:
            self.blocked_queries.append(dict(provider=provider,retrieval_key=key,purpose=purpose,reason='PER_REFERENT_QUERY_LIMIT'))
            return dict(provider=provider,status='NOT_QUERIED',diagnostic='PER_REFERENT_QUERY_LIMIT',rows=[])
        adapter=self.providers[provider]
        result=copy.deepcopy(adapter.name(key['value']) if key['kind']=='name' else adapter.retrieve(key['kind'],key['value']))
        result['provider']=provider;result['retrieval_key']=key;result['purpose']=purpose
        result['rows']=[provenance(r,result,key) for r in result.get('rows',[])]
        self.results.append(result);self.seen[token]=result
        return result
    def source_name(self,name):
        key=dict(kind='name',value=name,origin='source_preferred_name',asserts_source_identity=True)
        for p in ('PubChem','ChEBI'):self.query(p,key)
        if 'CompTox' in self.providers:self.query('CompTox',key)
    def source_identifiers(self,keys):
        supported={'PubChem':{'PubChemCID','InChIKey','InChI','CASRegistryNumber','ECNumber'},'ChEBI':{'ChEBIID','InChIKey','InChI','CASRegistryNumber','ECNumber'},'GSRS':{'UNII','CASRegistryNumber'},'CompTox':{'InChIKey','CASRegistryNumber','DTXSID','DTXCID'}}
        for key in keys:
            for p in self.providers:
                if key['kind'] in supported[p]:self.query(p,key)
    def external(self,candidate=None):
        rows=[];diagnostics=[]
        for result in self.results:
            if result['purpose']!='primary':continue
            for row in result.get('rows',[]):
                validated,error=validate_external({'rows':[row]})
                if error:
                    # Retain invalid provider rows so the existing policy rejects them.
                    rows.append(row);diagnostics.append(dict(provenance=row['provenance'],assessment='INVALID',reason=error));continue
                d=validated[0][0];cmp=compare(candidate,d) if candidate else None
                claimed=result['retrieval_key']['asserts_source_identity']
                if claimed or cmp is None or cmp['assessment']=='EXACT':rows.append(row)
                diagnostics.append(dict(provenance=row['provenance'],asserts_source_identity=claimed,comparison=cmp,used_for_corroboration=bool(claimed),retained_for_comparison=claimed or cmp is None or cmp['assessment']=='EXACT',structure=d['smiles']))
        rows,duplicates=deduplicate(rows);self.candidate_diagnostics=diagnostics
        return dict(rows=rows,status='SUCCESS' if rows else 'NOT_QUERIED',duplicates=duplicates)
    def expand(self,name,candidate,identifiers=()):
        self.source_identifiers(identifiers)
        keys=hypothesis_keys(candidate)
        # A complete-key lookup first; structure/InChI are bounded alternatives.
        for p in ('PubChem','ChEBI'):self.query(p,keys[0])
        if 'GSRS' in self.providers:self.query('GSRS',dict(kind='name',value=name,origin='source_preferred_name',asserts_source_identity=True))
        exact_by_provider=set()
        for r in self.results:
            for row in r.get('rows',[]):
                validated,error=validate_external({'rows':[row]})
                if not error and compare(candidate,validated[0][0])['assessment']=='EXACT':exact_by_provider.add(r['provider'])
        if 'PubChem' not in exact_by_provider:
            self.query('PubChem',keys[1]);self.query('PubChem',keys[2])
        if 'GSRS' in self.providers and 'GSRS' not in exact_by_provider:self.query('GSRS',keys[1])
        # A provider name may retrieve another record only after graph validation.
        if 'ChEBI' not in exact_by_provider:
            names=[]
            for r in self.results:
                for row in r.get('rows',[]):
                    v,error=validate_external({'rows':[row]})
                    n=row.get('IUPACName')
                    if not error and n and compare(candidate,v[0][0])['assessment']=='EXACT' and n not in names:names.append(n)
            if names:self.query('ChEBI',dict(kind='name',value=names[0],origin='validated_exact_provider_name',asserts_source_identity=False))
        return self.external(candidate)
    def source_alias_support(self,name,aliases,candidate,claim):
        """Validate a source-supplied alternative claim; never generate an alias.

        Original name/identifier evidence anchors the hypothesis. A warning-free
        original alias supplies independent local nomenclature, but is usable only
        after exact graph comparison AND its own external name attestation. Provider
        generated names are never treated as independent local source evidence.
        """
        attempts=0
        for alias in aliases[:64]:
            if attempts>=3:break
            c=claim(alias);d=c.get('structure')
            if c.get('status')!='SUCCESS' or not d or compare(candidate,d)['assessment']!='EXACT':continue
            from form_characterizer import interpret
            if interpret(d,alias)['specification']!='SPECIFIED':continue
            attempts+=1
            key=dict(kind='name',value=alias,origin='source_alias_claim_validation',asserts_source_identity=False)
            result=self.query('PubChem',key,purpose='alias_validation')
            validated,error=validate_external(result)
            from evidence_model import assess,aggregate_route,CORROBORATES
            if result['status']=='SUCCESS' and validated and not error and aggregate_route([assess(r,candidate) for v,r in validated])==CORROBORATES:
                return dict(kind='VALIDATED_SOURCE_ALIAS',alias=alias,claim=c,attestation=result,
                            explanation='Original source alias parsed warning-free and independently corroborated; original preferred referent form gate remains unchanged.')
        return None
    def audit(self,assessments=()):
        from evidence_model import aggregate_route,route_key
        states=[]
        for q in self.results:
            k=q['retrieval_key'];matching=[a for a in assessments if route_key(a)==(q['provider'],k['kind'],k['value'],k['origin'])]
            state=aggregate_route(matching,q['status'],bool(q.get('rows')))
            states.append(dict(provider=q['provider'],route=k['kind'],query=k,state=state,
                record_ids=[r.get('provenance',{}).get('record_id') for r in q.get('rows',[])],
                per_record_states=[dict(record_id=a.get('record_id'),state=a['state'],reason=a.get('reason')) for a in matching]))
        return dict(version=1,queries=self.results,candidate_comparisons=self.candidate_diagnostics,
                    query_count=len(self.results),query_limit=self.max_queries,blocked_queries=self.blocked_queries,
                    provider_states=states,
                    independence_rule='No independent votes inferred from mirrors or unknown aggregate lineage')
