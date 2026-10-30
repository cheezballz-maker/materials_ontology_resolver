"""Describe source input only; labels are lexical and not chemistry judgments."""
import collections,json,re
from pathlib import Path
H=Path(__file__).resolve().parent;r=json.loads((H/'fresh_sample.json').read_text(encoding='utf-8'))
groups=collections.Counter(x['preferred_name'] for x in r)
tags={'stereo_notation':r'\((?:\d*[RSZE])|\b(?:cis|trans)-|\b[DL]-','salt_term':r'hydrochloride|hydrobromide|\bsodium\b|\bpotassium\b|\bcalcium\b','hydrate_term':r'hydrat','isotope_term':r'deuteri|triti|\b(?:13C|14C|15N|18O)\b','mixture_polymer_term':r'\b(?:polymer|mixture|copolymer|alloy)\b'}
out=dict(sample_size=len(r),alias_occurrences=sum(len(x['aliases']) for x in r),records_with_aliases=sum(bool(x['aliases']) for x in r),multiple_aliases=sum(len(x['aliases'])>1 for x in r),malformed_alias_cells=sum(bool(x['input_error']) for x in r),duplicate_preferred_name_groups=sum(n>1 for n in groups.values()),lexical_tags={k:sum(bool(re.search(v,x['preferred_name'] or '',re.I)) for x in r) for k,v in tags.items()})
(H/'sample_summary.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
