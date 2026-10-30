"""Source-only sampling. No resolver execution or prediction/diagnostic reads."""
import ast, hashlib, json, random, re, sys, unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import openpyxl

H=Path(__file__).resolve().parent; B=H.parent
SOURCE=B.parent.parent/'cuma/CUMA v1 (ENG Only).xlsx'
FRAMEWORK=Path(r'C:\Users\IT PatsnapSG\Downloads\Molecular_Substance_Identity_Framework_v1.md')
ONTOLOGY=B.parent.parent.parent/'13. Materials Ontology/Ontology/substance_ontology.ttl'
SEED=2026102802
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def norm(s):return ' '.join(unicodedata.normalize('NFC',s or '').split()).casefold()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')

assert not (H/'SAMPLE_FROZEN.json').exists(),'Never replace a frozen sample'
known=set(); names=set(); source_files=[]
old=read(B/'form_aware_holdout/steward/exclusions.json')
known.update(old['known_development_indices']);known.update(map(int,old['excluded_cuma']))
names.update(old['exclusion_names'])
for folder in ('blinded_validation','form_aware_holdout'):
    for p in sorted((B/folder).glob('packet_*/records.json')):
        source_files.append(p)
        for r in read(p):
            known.add(r['cuma_index']);names.update(norm(x) for x in [r['preferred_name']]+r['aliases'] if x)
# All development code string literals, including historical source snapshots,
# plus document table/name mentions: deliberately conservative lexical exclusion.
dev_files=list(B.glob('*.py'))+list((B/'evidence_upgrade/baseline').glob('*.py'))
for p in dev_files:
    for node in ast.walk(ast.parse(p.read_text(encoding='utf-8-sig'))):
        if isinstance(node,ast.Constant) and isinstance(node.value,str):names.add(norm(node.value))
for r in read(B/'reviewed_evidence.json'):names.update(norm(x) for x in r['names'])
docs=list(B.glob('*.md'))+[FRAMEWORK]+list((B/'evidence_upgrade').glob('*.md'))
for p in docs:
    s=p.read_text(encoding='utf-8-sig')
    known.update(int(x) for x in re.findall(r'\bCUMA\s+(\d{1,5})\b',s,re.I))
    known.update(int(x) for x in re.findall(r'^\|\s*(\d{1,5})\s*[/|]',s,re.M))
    names.update(norm(x.strip(' `*')) for line in s.splitlines() if line.startswith('|') for x in line.split('|') if x.strip())
    names.update(norm(x) for x in re.findall(r'`([^`\n]+)`',s))
known.update((9152,46724,52217))

records={};errors={}
w=openpyxl.load_workbook(SOURCE,read_only=True,data_only=True)
rows=iter(w.active.values);assert next(rows)[:3]==('No.','display_name_en','alias_list_en')
for row in rows:
    if not row or all(x is None for x in row):continue
    i,name,raw=row[:3];assert isinstance(i,int) and i not in records
    try:
        aliases=ast.literal_eval(raw) if raw else []
        assert isinstance(aliases,list) and all(isinstance(x,str) for x in aliases)
    except Exception as e:aliases=[];errors[i]={'raw_alias_cell':raw,'error':str(e)}
    records[i]={'cuma_index':i,'preferred_name':name,'aliases':aliases}
w.close()
# Add complete source claims for every known development index before overlap
# exclusion. No predictions or outcomes are consulted.
for i in known & records.keys():names.update(norm(x) for x in [records[i]['preferred_name']]+records[i]['aliases'] if x)
names.discard('')
excluded={}
for i,r in records.items():
    if i in known:excluded[i]='PRIOR_OR_CURATED_INDEX'
    elif any(norm(x) in names for x in [r['preferred_name']]+r['aliases']):excluded[i]='EXACT_DEVELOPMENT_NAME_OR_ALIAS_OVERLAP'
# Obvious duplicate preferred-name spellings: ignore whitespace and Unicode
# punctuation only, preserving letters, digits, locants and stereo signs.
def duplicate_key(s):return re.sub(r'\s+','',norm(s).translate(str.maketrans({'−':'-','–':'-','’':"'"})))
excluded_keys={duplicate_key(records[i]['preferred_name']) for i in excluded}
for i,r in records.items():
    if i not in excluded and duplicate_key(r['preferred_name']) in excluded_keys:excluded[i]='OBVIOUS_DUPLICATE_OF_EXCLUDED_SOURCE'
eligible={i:r for i,r in records.items() if i not in excluded}
patterns={
 'isotope':r'deuteri|triti|[-]d\d+\b|\b(?:13C|14C|15N|18O)\b',
 'stereo':r'\((?:\d*[RSZE])(?:[,\s]*\d*[RSZE])*\)|(?:^|\b)[DL]-|\b(?:cis|trans)-|\b(?:alanine|valine|serine|threonine|leucine|lactic acid|tartaric acid)\b',
 'salt':r'hydrochloride|hydrobromide|\b(?:sodium|potassium|lithium|calcium|magnesium)\b.*(?:ate|ide)|(?:sodium|potassium) salt',
 'hydrate':r'hydrat',
 'solvate':r'solvat|ethanolate|methanolate|(?:compd\.? with|compound with).*(?:ethanol|methanol|dimethyl sulfoxide|acetone|dimethylformamide|ethyl acetate|propan-2-ol|2-propanol)|(?:ethanol|methanol|dimethyl sulfoxide|acetone|dimethylformamide|ethyl acetate|propan-2-ol|2-propanol).*\([1-9]\s*:\s*[1-9]\)',
 'tautomer':r'[1-9]H-|pyridin.*one|pyrimidin.*(?:one|ol)|hydroxypyrid|uracil|pyrazol.*ol|imidazol.*ol|thiour|thione',
 'protonation_charge':r'aminium|ammonium|phosphonium|pyridinium|imidazolium|\([123][+-]\)|\b(?:cation|anion|zwitterion)\b',
 'difficult':r'<[^>]+>|\b(?:unknown|unidentified)\b|^[A-Z]{2,}[- ]?\d+',
 'out_of_scope':r'polymer|copolymer|poly\(|alloy|bronze|mixture|extract|resin|mineral|steel|quartz|bentonite|kaolin|glass',
}
def tags(r):
    s=r['preferred_name'] or '';out=[k for k,p in patterns.items() if re.search(p,' '.join([s]+r['aliases']) if k in ('solvate','isotope') else s,re.I)]
    if len(s)>160 and 'difficult' not in out:out.append('difficult')
    if len(s)<=45 and not out:out.append('straightforward')
    return out
labels={i:tags(r) for i,r in eligible.items()}

# Lexical neighbourhoods select records together, not chemical truth. These
# transformations are never used by adjudication, the resolver or scoring.
def masks(s):
    s=norm(s);out={'duplicate':duplicate_key(s)}
    out['stereo']=re.sub(r'\((?:\d*[rsze])(?:[,\s]*\d*[rsze])*\)|\b(?:[dl]|cis|trans)-','',s)
    out['isotope']=re.sub(r'-d\d+\b|\b(?:13c|14c|15n|18o)\b|\(?[\d,]*deuterio\)?','',s)
    out['salt']=re.sub(r'\b(?:mono|di|tri)?(?:hydrochloride|hydrobromide|sodium|potassium|lithium|calcium|magnesium)(?: salt)?\b','',s)
    out['hydrate']=re.sub(r'\b(?:hemi|mono|di|tri|tetra|penta|hexa|hepta|octa|nona|deca|sesqui)?hydrate\b','',s)
    out['solvate']=re.sub(r'\b(?:ethanol|methanol|acetone|ethanolate|methanolate|solvate)\b','',s)
    out['constitutional']=re.sub(r'(?<![a-z])\d+(?:,\d+)*-','',s)
    return {k:re.sub(r'[\s,]+','',v).strip('-()') for k,v in out.items()}
groups={k:defaultdict(list) for k in ('duplicate','stereo','isotope','salt','hydrate','solvate','constitutional')}
for i,r in eligible.items():
    for k,v in masks(r['preferred_name']).items():
        if len(v)>=6:groups[k][v].append(i)
rng=random.Random(SEED);chosen={};pairs=[];pair_pools={}
for kind,g in groups.items():
    pool=[sorted(v) for v in g.values() if 2<=len(v)<=20 and (kind=='duplicate' or len({norm(records[i]['preferred_name']) for i in v})>1)]
    pool.sort();rng.shuffle(pool);pair_pools[kind]=len(pool);n=0
    for v in pool:
        remaining=[i for i in v if i not in chosen]
        if len(remaining)<2:continue
        a,b=rng.sample(remaining,2);chosen[a]=chosen[b]='pair_'+kind
        pairs.append({'a':a,'b':b,'sampling_hint':kind,'chemical_relation':'UNADJUDICATED'});n+=1
        if n==5:break
targets=[('solvate',20),('isotope',30),('hydrate',35),('protonation_charge',25),('salt',50),('stereo',50),('tautomer',30),('out_of_scope',25),('difficult',25),('straightforward',80)]
pools={k:sum(k in t for t in labels.values()) for k,_ in targets}
for kind,target in targets:
    need=max(0,target-sum(kind in labels[i] for i in chosen))
    pool=sorted(i for i in eligible if i not in chosen and kind in labels[i]);rng.shuffle(pool)
    for i in pool[:min(need,400-len(chosen))]:chosen[i]=kind
pool=sorted(i for i in eligible if i not in chosen and 'straightforward' in labels[i]);rng.shuffle(pool)
for i in pool[:400-len(chosen)]:chosen[i]='straightforward_top_up'
assert len(chosen)==400
summary={'source_records':len(records),'excluded':len(excluded),'eligible':len(eligible),'selected':len(chosen),'seed':SEED,'candidate_tags':dict(Counter(k for i in chosen for k in labels[i])),'candidate_pair_groups':dict(Counter(p['sampling_hint'] for p in pairs)),'available_pools':pools,'available_pair_pools':pair_pools}
print(json.dumps(summary,indent=2))
if '--freeze' not in sys.argv:sys.exit(0)
(H/'steward').mkdir(exist_ok=True)
save(H/'steward/exclusions.json',dict(known_development_indices=sorted(known),excluded_cuma=excluded,exclusion_names=sorted(names),development_files=[str(p) for p in dev_files+docs+source_files],rule='Known indices; exact normalized preferred-name/alias overlap; obvious duplicate source name. No predicted outcome consulted.'))
save(H/'steward/eligible_population.json',dict(count=len(eligible),indices=sorted(eligible),source_sha256=sha(SOURCE)))
save(H/'steward/selection.json',dict(**summary,targets=targets,primary_strata=chosen,tags={i:labels[i] for i in chosen},pair_candidates=pairs,input_errors={i:errors[i] for i in chosen if i in errors}))
# Keep lexical pair members together to permit coherent independent source
# investigation, without passing pair hints or strata to adjudicators.
units=[[p['a'],p['b']] for p in pairs];paired={i for u in units for i in u}
units += [[i] for i in sorted(chosen) if i not in paired];rng.shuffle(units)
packets=[[],[],[]]
for unit in units:min(packets,key=len).extend(unit)
for n,ids in enumerate(packets,1):
    packet=H/f'packet_{n}';packet.mkdir()
    rng.shuffle(ids);save(packet/'records.json',[records[i] for i in ids])
    (packet/'Molecular_Substance_Identity_Framework_v1.md').write_bytes(FRAMEWORK.read_bytes())
supp=H/'supplemental';supp.mkdir()
save(supp/'records.json',[records[i] for i in (9152,46724,52217)])
(supp/'Molecular_Substance_Identity_Framework_v1.md').write_bytes(FRAMEWORK.read_bytes())
protected=list(B.glob('*.py'))+list(B.glob('*.java'))+list(B.glob('*.class'))+[B/'schema.sql',B/'reviewed_evidence.json',B/'IDENTITY_POLICY.md',FRAMEWORK,ONTOLOGY]
protected+=list(B.rglob('*.sqlite'))
for parent in ('blinded_validation','form_aware_holdout','evidence_upgrade','form_aware_evaluation'):
    protected+=list((B/parent).rglob('reference.json'))+list((B/parent).rglob('*FROZEN.json'))+list((B/parent).rglob('alias_attestations.json'))
save(H/'steward/protected_hashes.json',{str(p.resolve()):sha(p) for p in sorted(set(protected)) if p.exists()})
save(H/'SAMPLE_FROZEN.json',dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),**summary,indices=sorted(chosen),source_path=str(SOURCE.resolve()),source_sha256=sha(SOURCE),sampling_script_sha256=sha(__file__),selection_sha256=sha(H/'steward/selection.json'),eligible_sha256=sha(H/'steward/eligible_population.json'),exclusions_sha256=sha(H/'steward/exclusions.json'),packets={f'packet_{n}/records.json':sha(H/f'packet_{n}/records.json') for n in (1,2,3)},supplemental_sha256=sha(supp/'records.json'),protected_hashes_sha256=sha(H/'steward/protected_hashes.json'),prediction_data_used=False))
print('SAMPLE FROZEN. No adjudication or prediction has run.')
