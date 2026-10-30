"""Source-only holdout steward. Never reads a prediction or diagnostic table."""
import ast,hashlib,json,random,re,unicodedata
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import openpyxl
H=Path(__file__).resolve().parent;B=H.parent
SOURCE=B.parent.parent/'cuma/CUMA v1 (ENG Only).xlsx'
FRAMEWORK=Path(r'C:\Users\IT PatsnapSG\Downloads\Molecular_Substance_Identity_Framework_v1.md')
ONTOLOGY=B.parent.parent.parent/'13. Materials Ontology/Ontology/substance_ontology.ttl'
SEED=2026102702
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def norm(s):return ' '.join(unicodedata.normalize('NFC',s or '').split()).casefold()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
assert not (H/'SAMPLE_FROZEN.json').exists(),'Never replace a frozen sample'
previous=[]
for n in (1,2,3):previous+=json.loads((B/f'blinded_validation/packet_{n}/records.json').read_text(encoding='utf-8'))
known={r['cuma_index'] for r in previous}
names={norm(s) for r in previous for s in [r['preferred_name']]+r['aliases'] if s}
dev_files=[B/'test_registry.py',B/'test_forms.py',B/'evaluate.py',B/'reviewed_evidence.json']
for p in dev_files[:3]:
    tree=ast.parse(p.read_text(encoding='utf-8'))
    names.update(norm(node.value) for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str))
for row in json.loads(dev_files[3].read_text()):names.update(norm(n) for n in row['names'])
# Conservative lexical exclusion of named framework/development examples, including
# forms whose CUMA IDs were never recorded in the original small engineering set.
names.update(map(norm,['water','heavy water','glutamic acid','L-glutamic acid','D-glutamic acid','sodium acetate','potassium acetate','sodium acetate trihydrate','methylamine','methylamine hydrochloride','acetate','2-pyridone','2-hydroxypyridine','cisplatin','transplatin','ferrocene','ferrocenium','caffeine','oxalic acid','anatase','rutile','but-2-ene','glycine','alanine','ethanol','ethyl alcohol','benzene','dimethyl ether','acetone','acetic acid']))
for p in list(B.glob('*.md'))+[FRAMEWORK]:
    txt=p.read_text(encoding='utf-8-sig')
    known.update(int(x) for x in re.findall(r'\bCUMA\s+(\d{1,5})\b',txt,re.I))
    for field in re.findall(r'^\|\s*(\d{1,5})\s*[/|]',txt,re.M):known.add(int(field))
records={};errors={}
w=openpyxl.load_workbook(SOURCE,read_only=True,data_only=True)
rows=iter(w.active.values);assert next(rows)[:3]==('No.','display_name_en','alias_list_en')
for row in rows:
    if not row or all(v is None for v in row):continue
    i,name,raw=row[:3];assert isinstance(i,int) and i not in records
    try:
        aliases=ast.literal_eval(raw) if raw else []
        assert isinstance(aliases,list) and all(isinstance(a,str) for a in aliases)
    except Exception as ex:aliases=[];errors[i]={'raw_alias_cell':raw,'error':str(ex)}
    records[i]={'cuma_index':i,'preferred_name':name,'aliases':aliases}
w.close()
excluded={}
for i,r in records.items():
    if i in known:excluded[i]='KNOWN_DEVELOPMENT_INDEX'
    elif any(norm(s) in names for s in [r['preferred_name']]+r['aliases']):excluded[i]='DEVELOPMENT_NAME_OR_ALIAS_OVERLAP'
patterns={
 'solvate':r'solvat|ethanolate|methanolate|(?:compd\.? with|compound with).*(?:ethanol|methanol|dimethyl sulfoxide|acetone)',
 'hydrate':r'hydrat',
 'isotope':r'deuteri|triti|[-]d\d+\b|\b(?:13C|14C|15N|18O)\b',
 'protonation_charge':r'aminium|ammonium|phosphonium|pyridinium|imidazolium|\([123][+-]\)|\b(?:cation|anion|zwitterion)\b',
 'salt':r'hydrochloride|hydrobromide|\b(?:sodium|potassium|lithium|calcium|magnesium)\b.*(?:ate|ide)|(?:sodium|potassium) salt',
 'stereo':r'\((?:\d*[RSZE])(?:[,\s]*\d*[RSZE])*\)|(?:^|\b)[DL]-|\b(?:cis|trans)-',
 'potentially_unspecified_stereo':r'\b(?:alanine|valine|leucine|isoleucine|serine|threonine|proline|lysine|phenylalanine|tryptophan|tyrosine|glutamine|asparagine|cysteine|methionine|histidine|arginine|lactic acid|tartaric acid|malic acid)\b|[23]-hydroxy(?:but|pent|hex)|[23]-amino(?:but|pent|hex)',
 'tautomer':r'[1-9]H-|pyridin.*one|pyrimidin.*(?:one|ol)|hydroxypyrid|uracil|pyrazol.*ol|imidazol.*ol|thiour|thione',
 'multicomponent':r'compd\.? with|compound with|\b[1-9]\s*:\s*[1-9]\b|adduct|complex',
 'out_of_scope':r'polymer|copolymer|poly\(|alloy|bronze|mixture|extract|resin|mineral|steel|quartz|bentonite|kaolin|glass',
 'difficult':r'<[^>]+>|\b(?:unknown|unidentified)\b|^[A-Z]{2,}[- ]?\d+',
}
def tags(r):
    name=r['preferred_name'] or '';alltext=' '.join([name]+r['aliases']);out=[]
    for key,p in patterns.items():
        text=alltext if key in ('solvate','isotope') else name
        if re.search(p,text,re.I):out.append(key)
    if 'stereo' in out and 'potentially_unspecified_stereo' in out:out.remove('potentially_unspecified_stereo')
    if len(name)>160 and 'difficult' not in out:out.append('difficult')
    if len(name)<=45 and not out:out.append('straightforward')
    return out
eligible={i:r for i,r in records.items() if i not in excluded}
labels={i:tags(r) for i,r in eligible.items()}
quotas=[('solvate',40),('hydrate',50),('isotope',30),('protonation_charge',25),('salt',35),('stereo',35),('potentially_unspecified_stereo',30),('tautomer',25),('multicomponent',20),('out_of_scope',20),('difficult',20),('straightforward',30)]
rng=random.Random(SEED);chosen={};pools={}
for category,n in quotas:
    pool=sorted(i for i in eligible if i not in chosen and category in labels[i]);pools[category]=len(pool);rng.shuffle(pool)
    chosen.update({i:category for i in pool[:n]})
# Rare source strata may not meet quota. Allocate half the shortfall to hydrates,
# then fill from ordinary names; never synthesize records or relabel alkoxides.
shortfall=360-len(chosen)
for category,n in [('hydrate',(shortfall+1)//2),('straightforward',360)]:
    pool=sorted(i for i in eligible if i not in chosen and category in labels[i]);rng.shuffle(pool)
    chosen.update({i:category for i in pool[:min(n,360-len(chosen))]})
assert len(chosen)==360 and not set(chosen)&known
ids=sorted(chosen);rng.shuffle(ids)
for n in (1,2,3):
    packet=H/f'packet_{n}';packet.mkdir()
    save(packet/'records.json',[records[i] for i in ids[(n-1)*120:n*120]])
    (packet/'Molecular_Substance_Identity_Framework_v1.md').write_bytes(FRAMEWORK.read_bytes())
save(H/'steward/exclusions.json',dict(known_development_indices=sorted(known),excluded_cuma=excluded,exclusion_names=sorted(names),development_files=[str(p) for p in dev_files]))
save(H/'steward/selection.json',dict(seed=SEED,quotas=quotas,available_at_selection=pools,primary_strata=chosen,tags={i:labels[i] for i in chosen},input_errors={i:errors[i] for i in chosen if i in errors}))
protected=list(B.glob('*.py'))+list(B.glob('*.java'))+[B/'RegistryBridge.class',B/'schema.sql',B/'reviewed_evidence.json',B/'IDENTITY_POLICY.md',B/'output/registry.sqlite',B/'output/candidates.sqlite',FRAMEWORK,ONTOLOGY]
protected += list((B/'blinded_validation').glob('packet_*/reference.json'))+list((B/'blinded_validation').glob('packet_*/alias_attestations.json'))
protected += list((B/'blinded_validation').glob('packet_*/*FROZEN.json'))
protected += list((B/'form_aware_evaluation/validated').glob('*.sqlite'))
save(H/'steward/protected_hashes.json',{str(p.resolve()):sha(p) for p in protected if p.exists()})
save(H/'SAMPLE_FROZEN.json',dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),seed=SEED,records=360,indices=sorted(chosen),source_path=str(SOURCE.resolve()),source_sha256=sha(SOURCE),sampling_script_sha256=sha(__file__),selection_sha256=sha(H/'steward/selection.json'),exclusions_sha256=sha(H/'steward/exclusions.json'),packets={f'packet_{n}/records.json':sha(H/f'packet_{n}/records.json') for n in (1,2,3)},prediction_data_used=False))
print(json.dumps({'records':360,'source_records':len(records),'excluded_records':len(excluded),'primary_strata':dict(Counter(chosen.values())),'available_pools':pools,'solvate_candidates':[(i,records[i]['preferred_name']) for i in chosen if 'solvate' in labels[i]]},indent=2))
