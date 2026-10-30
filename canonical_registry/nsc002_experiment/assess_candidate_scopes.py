"""Coverage-opportunity triage only; no molecular parsing or identity replay."""
import collections,hashlib,json,re
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
scope=H/'NSC-002/provisional_candidate_scopes.json';freeze=read(H/'NSC-002/provisional_scope_freeze.json');assert hashlib.sha256(scope.read_bytes()).hexdigest()==freeze['sha256']
records=read(ROOT/'NOMENCLATURE_FALSE_HOLD_TAXONOMY.json');assert len(records)==81
group=re.compile(r'(\d(?:,\d)*)-(di|tri)?(bromo|chloro|fluoro|iodo|nitro)(?:-|(?=benzene))',re.I)
def c_exact(text):
 if not text.isascii() or not text.lower().endswith('benzene'):return False
 pos=0;locants=[];groups=[]
 while pos<len(text)-7:
  m=group.match(text,pos)
  if not m:return False
  loc=[int(x) for x in m[1].split(',')];mult={None:1,'di':2,'tri':3}.get(m[2].lower() if m[2] else None)
  if len(loc)!=mult or any(x<1 or x>6 for x in loc):return False
  locants.extend(loc);groups.append(m[3].lower());pos=m.end()
 return pos==len(text)-7 and 1<=len(groups)<=3 and len(set(locants))==len(locants) and len(set(groups))==len(groups)
def assess(which,text):
 if not text:return ('INSUFFICIENT_EVIDENCE','Source text unavailable.')
 t=text.strip()
 if which=='A':
  if re.fullmatch(r'[13]H-pyrimidin-[24]-one',t,re.I):return ('FULL_NAME_APPLICABLE','Complete provisional grammar; no structural or chemical adjudication.')
  if re.search(r'\([13]H\)-one|[13]H-pyrimidin|pyrimidin.*one',t,re.I):return ('POTENTIALLY_APPLICABLE_REQUIRES_EXTENSION','Possible H/suffix context; ownership and additional operations are not closed.')
 if which=='B':
  if re.fullmatch(r'pyridin-1-ium|1-(?:methyl|ethyl)pyridin-1-ium',t,re.I):return ('FULL_NAME_APPLICABLE','Complete provisional grammar; counterion and form evidence still needed.')
  if re.search(r'pyridin(?:ium|.*ium)|pyridinium',t,re.I):return ('POTENTIALLY_APPLICABLE_REQUIRES_EXTENSION','Possible cation language, no proven component ownership.')
 if which=='C':
  if c_exact(t):return ('FULL_NAME_APPLICABLE','Complete provisional grammar; source and candidate consistency not validated.')
  if re.search(r'(?:bromo|chloro|fluoro|iodo|nitro)',t,re.I) and re.search(r'benzen|phenyl',t,re.I):return ('POTENTIALLY_APPLICABLE_REQUIRES_EXTENSION','Possible substituted phenyl or benzene; whole-source ownership and other operations unproven.')
 return ('OUT_OF_SCOPE','No whole-name or bounded lexical opportunity for this candidate scope.')
priority={'FULL_NAME_APPLICABLE':4,'PARTIAL_OPERATION_APPLICABLE':3,'POTENTIALLY_APPLICABLE_REQUIRES_EXTENSION':2,'OUT_OF_SCOPE':1,'INSUFFICIENT_EVIDENCE':0}
out=[]
for x in records:
 claims=[('preferred_name',x.get('preferred_name'))]+[('alias',y.get('text')) for y in x.get('aliases',[])]
 row={'cuma_index':x['record_id'],'preferred_name':x.get('preferred_name'),'primary_blocker':x['primary_blocker'],'additional_requirements':x.get('secondary_blockers',[]),'other_source_claims_not_adjudicated':True,'candidates':{}}
 for k in ('A','B','C'):
  evaluated=[(role,text,*assess(k,text)) for role,text in claims if text]
  if evaluated:
   role,text,status,reason=max(evaluated,key=lambda a:priority[a[2]])
  else:role,text,status,reason='none',None,'INSUFFICIENT_EVIDENCE','No saved source strings.'
  row['candidates'][k]={'classification':status,'matched_role':role,'matched_source':text,'reason':reason,'whole_record_eligible':False}
 out.append(row)
counts={k:dict(collections.Counter(r['candidates'][k]['classification'] for r in out)) for k in ('A','B','C')}
payload={'method':'Candidate scopes frozen before this assessment. Text-only applicability on preferred names and saved aliases, including source role; no provider queries, structural validation, or identity recovery. Partial operation support is never inferred from a substring.','scope_freeze_sha256':freeze['sha256'],'records':out,'counts':counts,'recovered':0}
(H/'NSC-002/candidate_scope_comparison.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps({'counts':counts,'full_matches':{k:[(x['cuma_index'],x['candidates'][k]['matched_source']) for x in out if x['candidates'][k]['classification']=='FULL_NAME_APPLICABLE'] for k in ('A','B','C')}},indent=2))
