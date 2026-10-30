"""Independent exact NSC-001 recognizer; original code-point spans retained."""
import re
PATTERN=re.compile(r'(?P<loc>1)-(?P<alkyl>methyl|ethyl|propyl|butyl)-(?P<h>1H)-(?P<parent>pyrazole|imidazole)')
def recognize(name):
    return PATTERN.fullmatch(name) if isinstance(name,str) else None
