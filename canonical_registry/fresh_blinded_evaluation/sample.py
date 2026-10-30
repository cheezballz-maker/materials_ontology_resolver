"""Source-only unbiased sample, with conservative historical leakage exclusions."""
import ast,hashlib,json,random,re,unicodedata
from pathlib import Path
import openpyxl
H=Path(__file__).resolve().parent;B=H.parent;SOURCE=B.parent.parent/'cuma/CUMA v1 (ENG Only).xlsx';SEED=2026102901
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
norm=lambda s:' '.join(unicodedata.normalize('NFC',s or '').split()).casefold()
dup=lambda s:re.sub(r'\s+','',norm(s).translate(str.maketrans({'−':'-','–':'-','’':"'"})))
assert (B/'FRESH_BLINDED_EVALUATION_FREEZE.json').exists() and not (H/'SAMPLE_FROZEN.json').exists()
prev=read(B/'second_form_aware_holdout/steward/exclusions.json')
known=set(prev['known_development_indices'])|set(map(int,prev['excluded_cuma']))|{9152,46724,52217,5684,5997,23839,30142,5}
names=set(prev['exclusion_names']);source_packets=[]
for folder in ('blinded_validation','form_aware_holdout','second_form_aware_holdout'):
 for p in sorted((B/folder).glob('packet_*/records.json')):
    source_packets.append(str(p.relative_to(B)))
    for row in read(p):
        known.add(row['cuma_index']);names.update(norm(x) for x in [row['preferred_name']]+row['aliases'] if x)
for p in B.glob('test_*.py'):
 for node in ast.walk(ast.parse(p.read_text(encoding='utf-8-sig'))):
    if isinstance(node,ast.Constant) and isinstance(node.value,str):names.add(norm(node.value))
for p in B.glob('*.md'):
 s=p.read_text(encoding='utf-8-sig')
 known.update(int(x) for x in re.findall(r'\bCUMA\s+(\d{1,5})\b',s,re.I))
 known.update(int(x) for x in re.findall(r'^\|\s*(\d{1,5})\s*(?:[/| ]|$)',s,re.M))
 names.update(norm(x.strip(' `*')) for line in s.splitlines() if line.startswith('|') for x in line.split('|') if x.strip())
 names.update(norm(x) for x in re.findall(r'`([^`\n]+)`',s))
records={};w=openpyxl.load_workbook(SOURCE,read_only=True,data_only=True);rows=iter(w.active.values)
assert next(rows)[:3]==('No.','display_name_en','alias_list_en')
for row in rows:
 if not row or all(x is None for x in row):continue
 i,name,raw=row[:3];assert isinstance(i,int) and i not in records
 try:
    aliases=ast.literal_eval(raw) if raw else [];assert isinstance(aliases,list) and all(isinstance(x,str) for x in aliases);error=None
 except Exception as e:aliases=[];error={'message':str(e),'raw_alias_cell':raw}
 records[i]=dict(cuma_index=i,preferred_name=name,aliases=aliases,input_error=error)
w.close()
for i in known & records.keys():names.update(norm(x) for x in [records[i]['preferred_name']]+records[i]['aliases'] if x)
names.discard('');excluded={}
for i,r in records.items():
 if i in known:excluded[i]='PRIOR_OR_TARGETED_INDEX'
 elif any(norm(x) in names for x in [r['preferred_name']]+r['aliases'] if x):excluded[i]='EXACT_NORMALIZED_HISTORICAL_NAME_OR_ALIAS'
keys={dup(records[i]['preferred_name']) for i in excluded}
for i,r in records.items():
 if i not in excluded and dup(r['preferred_name']) in keys:excluded[i]='OBVIOUS_DUPLICATE_OF_EXCLUDED_SOURCE'
eligible=sorted(set(records)-set(excluded));chosen=sorted(random.Random(SEED).sample(eligible,min(400,len(eligible))))
sample=[records[i] for i in chosen];out=H/'fresh_sample.json';out.write_text(json.dumps(sample,ensure_ascii=False,indent=2),encoding='utf-8')
manifest=dict(seed=SEED,sampling='simple random sample without replacement from eligible CUMA rows; no capability enrichment',source_sha256=sha(SOURCE),source_records=len(records),excluded_count=len(excluded),eligible_count=len(eligible),sample_size=len(sample),sample_sha256=sha(out),sample_indices=chosen,prior_packet_files=source_packets,exclusion_rules=['all previously curated/excluded IDs','all IDs in three prior holdout packets','IDs mentioned in current reports and known historical cases','exact normalized name/alias overlap with known cases, test string literals or report claims','obvious duplicate preferred name of excluded records'],duplicate_handling='Each eligible source row has equal probability; sample duplicates are retained and never selected deliberately.',exclusion_counts={reason:list(excluded.values()).count(reason) for reason in set(excluded.values())})
(H/'SAMPLE_FROZEN.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({k:manifest[k] for k in ('source_records','excluded_count','eligible_count','sample_size','seed','exclusion_counts')},indent=2))
