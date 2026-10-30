"""Lexical observations only: never establish source identity or eligibility.

IUPAC P-14.7 distinguishes indicated from added indicated hydrogen. A token
alone cannot establish grammatical ownership, atom mapping, or tautomer form.
"""
import re

TOKEN=re.compile(r'(?<![A-Za-z0-9])(\d+[a-z]?)H(?=\s*(?:[-,)]))')

def indicated_hydrogen_tokens(name):
    if not isinstance(name,str):return []
    return [dict(token=m.group(0),locant=m.group(1),span=[m.start(),m.end()],
                 grammatical_scope='UNVERIFIED',candidate_atom='UNMAPPED',
                 source_tautomer_support='NOT_ESTABLISHED') for m in TOKEN.finditer(name)]
