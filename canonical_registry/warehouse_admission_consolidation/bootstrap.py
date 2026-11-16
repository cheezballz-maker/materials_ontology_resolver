import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
sys.path.insert(0,str(BASE/'real_world_normalization'))
exec((BASE/'real_world_normalization/bootstrap.py').read_text())
sys.path.insert(0,str(Path(__file__).resolve().parent))
