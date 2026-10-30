import json,pathlib,hashlib,datetime,collections
from rdkit import Chem,rdBase
from rdkit.Chem import inchi
D=pathlib.Path(__file__).resolve().parent
def cache(provider,name):
 p=D/'source_cache'/(provider+'_'+hashlib.sha256(name.encode()).hexdigest()[:20]+'.json')
 return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
def evidence(provider,url,query,record_id,lineage,independence,note):return dict(provider=provider,url=url,query=query,record_id=record_id,lineage=lineage,independence=independence,note=note)
def main():
 rows=json.loads((D/'records.json').read_text(encoding='utf-8-sig'));out=[]
 paper='https://pstorage-acs-6854636.s3.amazonaws.com/4166524/ml300049d_si_001.pdf'
 patent='https://patents.google.com/patent/WO2019020790A1/en'
 isotope='https://www.fishersci.co.uk/shop/products/n-methyl-d3-n-nitroso-p-toluenesulfonamide-cdn-2/30310445'
 for row in rows:
  i=row['cuma_index'];op=cache('opsin',row['preferred_name']);pc=cache('pubchem',row['preferred_name'])
  ev=[evidence('OPSIN',op['url'],row['preferred_name'],'name parser','OPSIN/Cambridge','Independent nomenclature algorithm, not experimental corroboration','Full name parsed; graph, substitutions and CIP assignment independently inspected. Raw parser alone is not identity proof.')]
  ev.append(evidence('PubChem',pc['url'],row['preferred_name'],'name search','NCBI/PubChem','Single aggregated database lineage','Name search returned HTTP '+str(pc.get('status_code'))+'; retrieval failures and retry history retained in cache.'))
  if i==9152:
   reason='The ACS primary synthesis identifies the resolved (2S) Cbz-protected azetidine/Boc-protected piperidine alcohol as compound 29 (SI pages 11–12), separately from its (2R) enantiomer. The intact OPSIN graph has both carbamates, the 3-hydroxyazetidine linkage and one S piperidine stereocentre. PubChem name miss is not a chemical ambiguity.'
   ev.append(evidence('ACS Medicinal Chemistry Letters supporting information',paper,'exact preferred name, compound 29','ml300049d SI compound 29','Rice et al., ml300049d experimental synthesis','Primary synthetic report independent of OPSIN; no reliance on database synonym membership','Resolved S and R products are separately described after Mosher ester separation; S intermediate isolated before hydrogenolysis.'))
  elif i==46724:
   reason='The original (3S) descriptor belongs to the benzodiazepine stereocentre, as established by the primary patent preparation of compound D. Both independently parsed complete systematic names produce the same S lactam methyl propionate graph. A PubChem alias hit lacks stereochemistry and is retained only as a related unspecified candidate, not used to erase S.'
   ev.append(evidence('WIPO patent via Google Patents',patent,'methyl 3-[(3S)-7-bromo-2-oxo-5-(pyridin-2-yl)-2,3-dihydro-1H-1,4-benzodiazepin-3-yl]propanoate','WO2019020790A1 compound D example 3','WO2019020790 family','Primary patent independent of name parser; related patent family versions are one lineage','Preparation and isolated product explicitly retain 3S; methyl ester, 7-bromo and 5-pyridin-2-yl positions verified.'))
   ev.append(evidence('Japan MHLW chemical announcement','https://anzeninfo.mhlw.go.jp/kag_det/kag_116130.html','308242-23-1','116130 / CAS 308242-23-1','MHLW 2012 chemical announcement','Independent regulatory listing; submitted structural origin may overlap commercial registrants','Japanese systematic name explicitly describes 3S methyl propanoate species.'))
  else:
   reason='Conflicting chemical intent: the literal preferred name parses to an unlabeled N-phenyl nitrosotosylamide (C13 framework), while every substantive alias specifies N-methyl-d3 Diazald (C8 framework). Manufacturer isotope-reference material confirms the latter structure. The public marketplace hit for the preferred name itself mixes the N-phenyl heading with methyl-d3 CAS/details. No authoritative evidence resolves which referent this source intended; do not silently substitute methyl-d3 or admit parser-only phenyl structure.'
   ev.append(evidence('CDN Isotopes / Fisher product record',isotope,'N-Methyl-d3-N-nitroso-p-toluenesulfonamide','CDN / 30310445','CDN isotope reference material','Manufacturer structural evidence independent of OPSIN; Fisher syndicates CDN and is not a second independent lineage','Complete isotope SMILES [2H]C([2H])([2H])N(N=O)S(=O)(=O)c1ccc(C)cc1 shows N-CD3, not N-phenyl.'))
   ev.append(evidence('Guidechem marketplace','https://www.guidechem.com/trade/n-phenyl-n-nitroso-p-toluenesu-id4487198.html','N-Phenyl-N-nitroso-p-toluenesulfonamide','CAS 42366-72-3 mixed listing','Guidechem supplier listing','Uncertain commercial lineage; low authority and internally contradictory','Heading says N-phenyl but details say DIAZALD(R)-N-METHYL-D3; not independent exact-form confirmation.'))
  status='CONFLICT' if i==52217 else 'EXACT'
  dim=dict(constitution='SPECIFIED' if status=='EXACT' else 'CONFLICT: N-phenyl versus N-CD3',stereo='SPECIFIED: S absolute configuration' if status=='EXACT' else 'NOT_APPLICABLE',isotope='Conventional unlabeled scope' if status=='EXACT' else 'CONFLICT: unlabeled versus site-specific deuterium',protonation_charge='Neutral, no salt',components='Single covalent component',component_stoichiometry='1',hydration_solvation='No hydrate or solvate specified',tautomer='Named lactam retained; no tautomer canonicalization' if i==46724 else 'Named covalent form retained')
  aliases=[]
  for pos,a in enumerate(row['aliases']):
   if i==46724: j='SAME';why='Full independent name parse matches the 3S lactam methyl ester; primary compound-D synthesis corroborates exact constitution and stereochemistry.';urls=[patent,cache('opsin',a)['url']]
   elif a=='98 ATOM % D': j='UNRESOLVED';why='Isotope enrichment percentage alone identifies neither a molecular skeleton nor label positions.';urls=[isotope]
   else:j='DIFFERENT';why='The named N-methyl-d3 nitrosotosylamide has N-CD3 rather than the preferred literal N-phenyl substituent; constitution and isotope scope differ, regardless of unresolved record intent.';urls=[isotope,op['url']]
   aliases.append(dict(alias_position=pos,alias=a,judgment=j,reason=why,evidence_urls=urls))
  entry=dict(cuma_index=i,preferred_name=row['preferred_name'],expected_status=status,reason=reason,abstention_basis=None,expected_smiles=None,expected_inchi=None,expected_inchikey=None,dimensions=dim,form_categories=['stereo'] if status=='EXACT' else ['isotope'],evidence=ev,alias_judgments=aliases)
  if status=='EXACT':
   params=Chem.SmilesParserParams();params.parseName=False;params.allowCXSMILES=False
   m=Chem.MolFromSmiles(op['response']['smiles'],params);assert m
   Chem.SanitizeMol(m);entry['expected_smiles']=Chem.MolToSmiles(m,True);entry['expected_inchi']=inchi.MolToInchi(m);entry['expected_inchikey']=inchi.InchiToInchiKey(entry['expected_inchi'])
   entry['validation']={'rdkit_version':rdBase.rdkitVersion,'strict_full_input':True,'assigned_centres':Chem.FindMolChiralCenters(m,includeUnassigned=True),'fixed_h_inchi':inchi.MolToInchi(m,options='/FixedH')}
   assert all(x[1]=='S' for x in entry['validation']['assigned_centres'])
  out.append(entry)
 (D/'reference.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 method={'predictions_seen':False,'scope':'Only this supplemental packet, independent from packet_3 counts','record_count':3,'alias_position_base':0,'rdkit_version':rdBase.rdkitVersion,'method':'Original records preserved. Public PubChem and OPSIN independently queried. Primary synthetic literature checked for two stereodefined compounds. Full strict SMILES parsed, graph/CIP checked, Standard and Fixed-H InChI generated. Parser-only evidence never promoted to EXACT.','limitations':['PubChem returned 404 for complete preferred names; one successful alias lookup lost specified stereochemistry.','OPSIN is nomenclature computation, not experimental confirmation. Multiple pages of one publication or a supplier syndication are one lineage.','52217 remains a source-intent conflict; all isotope aliases judged against the literal preferred name, not silently adopted as the subject.','TLS EOF errors, HTTP 403 for a malformed question-mark alias, and 404 parsing misses are preserved with retry history.'],'qa':{'complete_records':True,'alias_occurrences_preserved':True,'strict_smiles':True,'identifier_roundtrip':True}}
 (D/'methodology.json').write_text(json.dumps(method,indent=2)+'\n',encoding='utf-8')
 print(collections.Counter(x['expected_status'] for x in out))
if __name__=='__main__':main()
