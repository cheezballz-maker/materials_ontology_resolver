"""Read-only matching integrates existing evidence and hardened chemistry."""
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
for name in ('','nsc_architecture_experiment','nsc002_experiment','charge_dimension_evidence','identity_reconciliation','source_evidence_adapters','source_candidate_correspondence','real_world_validation','chemical_correspondence_hardening'):
 p=BASE/name
 if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.path.insert(0,str(HERE))
