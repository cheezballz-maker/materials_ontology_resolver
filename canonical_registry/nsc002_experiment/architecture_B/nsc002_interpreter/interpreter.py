from shared.semantic_interface import SemanticInterpretation,SemanticValidation
from .grammar import recognize
from .semantic_rules import compile_source
from .schema_validation import validate
from .candidate_comparison import compare
def interpret_name(source_name):
    parsed=recognize(source_name)
    if parsed is None:return SemanticInterpretation(input_name=source_name,scope_status='OUT_OF_CONTRACT',contract_id='NSC-002',contract_version='1.0',unresolved_dependencies=['WHOLE_NAME_OUT_OF_CONTRACT'])
    result=compile_source(source_name,parsed);validate(result);return result
def validate_candidate(interpretation,candidate_structure,context=None):
    if interpretation.scope_status!='IN_CONTRACT':return SemanticValidation(result='OUT_OF_CONTRACT',reason_codes=['WHOLE_NAME_OUT_OF_CONTRACT'])
    validate(interpretation);outcome,reason,evidence=compare(interpretation.semantic_operations,candidate_structure,context)
    return SemanticValidation(result=outcome,operation_results=[{'operation_ids':[op['operation_id'] for op in interpretation.semantic_operations],'result':outcome,'scope':'joint_ring_pattern'}],reason_codes=[reason],evidence=evidence)
