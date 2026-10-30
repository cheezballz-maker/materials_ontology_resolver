from shared.semantic_interface import SemanticInterpretation,SemanticValidation,make_claims,validate_interpretation
from shared.structural_comparator import compare_candidate
from .grammar import recognize
from .parent_definitions import ALKYL
from .semantic_operations import compose
from .constraint_generation import generate
def interpret_name(name):
    m=recognize(name)
    if not m:return SemanticInterpretation(input_name=name,scope_status='OUT_OF_CONTRACT',unresolved_dependencies=['UNSUPPORTED_GRAMMAR'])
    parent,alkyl=m['parent'],m['alkyl'];length=ALKYL[alkyl]
    ops,cons=generate(parent,alkyl,length)
    result=SemanticInterpretation(input_name=name,scope_status='IN_CONTRACT',source_claims=make_claims(name,m.span('loc'),m.span('alkyl'),m.span('h'),m.span('parent')),semantic_operations=ops,structural_constraints=cons)
    validate_interpretation(result);return result
def validate_candidate(interpretation,candidate_structure,context=None):
    if interpretation.scope_status!='IN_CONTRACT':return SemanticValidation(result='OUT_OF_CONTRACT',reason_codes=['UNSUPPORTED_GRAMMAR'])
    validate_interpretation(interpretation);op=interpretation.semantic_operations[0]['parameters']
    expected=compose(op['parent'],op['chain_length'])
    result,reason,evidence=compare_candidate(expected,candidate_structure,context or {})
    return SemanticValidation(result=result,operation_results=[{'operation_id':'op1','result':result}],evidence=evidence,reason_codes=[reason])
