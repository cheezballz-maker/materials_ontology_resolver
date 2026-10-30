"""Paths for isolated diagnostics; no provider/client initialization."""
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
for p in (BASE,BASE/'nsc_architecture_experiment',BASE/'nsc002_experiment',BASE/'charge_dimension_evidence',BASE/'identity_reconciliation',BASE/'source_evidence_adapters'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
