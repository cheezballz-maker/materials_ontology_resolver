"""Sampling steward only. Never imported by blinded adjudicators."""
import ast,hashlib,json,random,re,sqlite3
from pathlib import Path
import openpyxl
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
seed=20261027
rng=random.Random(seed)
w=openpyxl.load_workbook(BASE.parent.parent/'cuma/CUMA v1 (ENG Only).xlsx',read_only=True,data_only=True)
records={}
for row in list(w.active.values)[1:]:
    if row[0] is None: continue
    i,name,raw=row[:3]
    try: aliases=ast.literal_eval(raw) if raw else []
    except Exception: aliases=[]
    records[i]={'cuma_index':i,'preferred_name':name,'aliases':aliases}
w.close()
db=sqlite3.connect((BASE/'output/candidates.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
# Outcome-assisted sampling is confined to the steward; never expose these strata
# or any engine output to adjudicators. No reference judgments are assigned here.
accepted=[x[0] for x in db.execute("SELECT cuma_index FROM candidate WHERE status='EXACT'")]
conflicts=[x[0] for x in db.execute("SELECT cuma_index FROM candidate WHERE status='CONFLICT'")]
failures=set()
for i,raw in db.execute('SELECT cuma_index,evidence_json FROM candidate'):
    e=json.loads(raw)
    if e['claims'][0].get('status') in ['FAILURE','ERROR','INVALID']: failures.add(i)
selected={i:'admission_census' for i in accepted}
selected.update({i:'provider_conflict_census' for i in conflicts})
patterns={
'isotopic':r'(?i)(?:\b(?:deuter|triti)|-d\d+\b|\b(?:13C|14C|15N|18O)\b|isotope)',
'hydrate_solvate':r'(?i)(?:hydrat|solvat|hemihydrat)',
'stereochemical':r'(?i)(?:\([0-9,]*(?:R|S|E|Z)[,0-9RS EZ-]*\)|\b(?:cis|trans|racemic|racemate)\b|^[DL]-)',
'salt_charge':r'(?i)(?:hydrochloride|hydrobromide|ammonium|sodium|potassium|chloride|sulfate)',
'multicomponent':r'(?i)(?:adduct|complex|\(\d+:\d+\)|;|compound with)',
'tautomer':r'(?i)(?:[1-9]H-|hydroxypyrid|pyridin.*one|imidazol.*ol|hydroxynaphth)',
'excluded_material':r'(?i)(?:polymer|copolymer|poly\(|alloy|bronze|mixture|extract|resin|mineral|steel|quartz)',
}
groups={}
for i,r in records.items():
    k=re.sub(r'(?i)(?:hydrochloride|hydrobromide|hydrate|solvate|\([RS]\))','',r['preferred_name'] or '')
    k=re.sub(r'[^a-z0-9]','',k.lower())
    groups.setdefault(k,[]).append(i)
duplicates={i for v in groups.values() if len(v)>1 for i in v}
spec=[('isotopic',12),('hydrate_solvate',12),('stereochemical',20),('salt_charge',20),('multicomponent',12),('tautomer',12),('excluded_material',18),('opsin_failure',20),('duplicate_near_duplicate',15),('multiple_aliases',20),('straightforward',20)]
for category,n in spec:
    def matches(i,r):
        name=r['preferred_name'] or ''
        if category in patterns: return bool(re.search(patterns[category],name))
        if category=='opsin_failure': return i in failures
        if category=='duplicate_near_duplicate': return i in duplicates
        if category=='multiple_aliases': return len(r['aliases'])>=5
        return len(name)<=35 and not any(re.search(p,name) for p in patterns.values())
    pool=[i for i,r in records.items() if i not in selected and matches(i,r)]
    rng.shuffle(pool)
    selected.update({i:category for i in pool[:n]})
pool=[i for i in records if i not in selected];rng.shuffle(pool)
for i in pool[:300-len(selected)]: selected[i]='random_top_up'
assert len(selected)==300
ROOT.mkdir(exist_ok=True);(ROOT/'steward').mkdir(exist_ok=True)
(ROOT/'steward/selection.json').write_text(json.dumps({'seed':seed,'strata':selected},indent=2),encoding='utf-8')
hashes={str(p.name):hashlib.sha256(p.read_bytes()).hexdigest() for p in [BASE/'output/registry.sqlite',BASE/'output/candidates.sqlite']}
(ROOT/'steward/source_hashes.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
ids=list(selected);rng.shuffle(ids)
for n in range(3):
    packet=ROOT/f'packet_{n+1}';packet.mkdir(exist_ok=True)
    (packet/'records.json').write_text(json.dumps([records[i] for i in ids[n*100:(n+1)*100]],ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared 3 blinded packets of 100 source records each; prediction strata withheld.')
