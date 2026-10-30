"""Independent source-to-constraint compilation; no candidate structure input."""
from shared.semantic_interface import SemanticInterpretation
def compile_source(name,parsed):
    claims=[];ops=[];constraints=[]
    def claim(i,kind,owner,rule,span):
        a,b=span;claims.append({'claim_id':i,'source_span':{'start':a,'end':b},'source_text':name[a:b],'claim_type':kind,'semantic_owner':owner,'rule_id':rule})
    claim('parent','SOURCE_EXPLICIT_PARENT','benzene','R4',parsed['parent_span'])
    for i,g in enumerate(parsed['groups'],1):
        lid,pid,mid=f'loc{i}',f'prefix{i}',f'mult{i}'
        claim(lid,'SOURCE_EXPLICIT_LOCANTS','benzene','R2',g['locant_span']);claim(pid,'SOURCE_EXPLICIT_SUBSTITUENT','benzene','R5',g['prefix_span'])
        ids=['parent',lid,pid]
        if g['multiplier_span']:
            claim(mid,'SOURCE_EXPLICIT_MULTIPLICITY','benzene','R3',g['multiplier_span']);ids.append(mid)
        oid=f'op{i}';params={'parent':'benzene','positions':g['locants'],'substituent':g['prefix']}
        ops.append({'operation_id':oid,'operation_type':'SUBSTITUTE_PARENT_H','source_claim_ids':ids,'rule_ids':['R1','R2','R3','R4','R5'],'semantic_owner':'benzene','parameters':params,'dependencies':ids})
        constraints.append({'constraint_id':f'k{i}','constraint_type':'RING_SUBSTITUENT_POSITIONS','source_claim_ids':ids,'rule_ids':['R1','R2','R3','R4','R5'],'semantic_owner':'benzene','structural_assertion':params,'dependencies':[oid],'applicability_conditions':['single neutral benzene component','all source operations consumed','no unsupported structure attributes']})
    return SemanticInterpretation(input_name=name,scope_status='IN_CONTRACT',source_claims=claims,semantic_operations=ops,structural_constraints=constraints,contract_id='NSC-002',contract_version='1.0')
