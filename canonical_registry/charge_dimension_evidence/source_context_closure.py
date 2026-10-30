from architecture_B.nsc002_interpreter.interpreter import interpret_name,validate_candidate
def assess(name,aliases,candidate):
    claims=[];dependencies=[];checks=[];assertions=[];op='UNKNOWN'
    for index,text in enumerate([name]+list(aliases)):
        identity=f'source{index}';interpretation=interpret_name(text)
        checks.append({'source_claim_id':identity,'original':text,'scope':interpretation.scope_status})
        for c in interpretation.source_claims:
            claims.append({**c,'claim_id':identity+':'+c['claim_id'],'original':text})
        if interpretation.scope_status!='IN_CONTRACT':dependencies.append(identity+':SOURCE_CONTEXT_OUT_OF_SCOPE');continue
        has_nitro=any(x['parameters']['substituent']=='nitro' for x in interpretation.semantic_operations)
        result=validate_candidate(interpretation,candidate)
        checks[-1].update(result=result.result,reason_codes=result.reason_codes)
        if index==0 and has_nitro and result.result=='SUPPORTED':op='SUPPORTED'
        if not has_nitro or result.result!='SUPPORTED':dependencies.append(identity+':SOURCE_CANDIDATE_NOT_CLOSED');continue
        assertions.append({'source_claim_id':identity,'meaning':'Complete source context specifies only neutral benzene, supported halo substituents and N-attached nitro; no other functional sites in this grammar.','provenance':'NOMENCLATURE_ESTABLISHED','rule':'IUPAC-P74.2.2.1.10','source_claim_ids':[x['claim_id'] for x in claims if x['claim_id'].startswith(identity+':')]})
    return {'claims':claims,'checks':checks,'assertions':assertions,'unresolved':dependencies,'operation_result':op,'complete':op=='SUPPORTED' and not dependencies}
