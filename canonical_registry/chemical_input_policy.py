"""A bounded chemical interpretation proof. Deepcopy retains it, JSON does not.

This is an in-process integrity check, not authentication against hostile code.
Only configured interpretation adapters issue it after chemical validation.
"""
from internal_structure_policy import digest

VERSION = "source-independent-chemical-1"
_SEAL = object()


class _Qualification:
    def __init__(self, package):
        self.seal = _SEAL
        self.digest = digest(package.to_dict())

    def __deepcopy__(self, memo):
        return self


def authorize(package):
    package._chemical_qualification = _Qualification(package)


def qualified(package):
    proof = getattr(package, "_chemical_qualification", None)
    return bool(isinstance(proof, _Qualification) and proof.seal is _SEAL
                and proof.digest == digest(package.to_dict()))
