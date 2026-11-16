"""Verify frozen source and canonical inputs, allowing a regenerated derived index."""

from canonical_registry.identity_sufficiency.evaluate import _guards
from .sources import DATA, ROOT, read

DERIVED_CACHE = ROOT / "enrichment" / "local" / "chemical_index.sqlite"


def current_baseline():
    frozen = read(DATA / "freeze.json")["protected_before"]
    current = _guards()
    changes = {k: {"freeze": frozen.get(k), "current": current.get(k)}
               for k in set(frozen) | set(current) if frozen.get(k) != current.get(k)}
    if set(changes) - {str(DERIVED_CACHE)}:
        raise ValueError("Protected source or canonical input changed since freeze")
    return current, changes
