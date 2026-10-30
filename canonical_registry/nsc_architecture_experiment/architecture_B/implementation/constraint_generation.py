from shared.semantic_interface import make_operation,make_constraint
def generate(parent,alkyl,length):return [make_operation(parent,alkyl,length)],[make_constraint(parent,alkyl,length)]
