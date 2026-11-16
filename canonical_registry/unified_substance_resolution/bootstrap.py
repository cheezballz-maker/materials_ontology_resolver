import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
sys.path.insert(0,str(BASE/'controlled_identity_reuse'))
exec((BASE/'controlled_identity_reuse/bootstrap.py').read_text())
sys.path.insert(0,str(Path(__file__).resolve().parent))
