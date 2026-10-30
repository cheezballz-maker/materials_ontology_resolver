"""Whole-name NSC-002 grammar. Match spans refer to original input."""
import re
GROUP=re.compile(r'(\d(?:,\d)*)-(di|tri)?(bromo|chloro|fluoro|iodo|nitro)(?:-|(?=benzene))',re.I|re.ASCII)
def recognize(name):
    if not isinstance(name,str) or not name.isascii() or not name.lower().endswith('benzene'):return None
    pos=0; groups=[]; positions=[]; end=len(name)-7
    while pos<end:
        m=GROUP.match(name,pos)
        if not m:return None
        locants=[int(x) for x in m.group(1).split(',')];prefix=m.group(3).lower();mult=(m.group(2) or '').lower()
        if len(locants)!={'':1,'di':2,'tri':3}[mult] or any(x not in range(1,7) for x in locants):return None
        groups.append({'locants':locants,'prefix':prefix,'locant_span':m.span(1),'prefix_span':m.span(3),'multiplier_span':m.span(2) if mult else None})
        positions.extend(locants);pos=m.end()
    if pos!=end or not 1<=len(groups)<=3 or len(set(positions))!=len(positions) or len(set(g['prefix'] for g in groups))!=len(groups):return None
    return {'groups':groups,'parent_span':(end,len(name))}
