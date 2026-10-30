"""Bounded public documentary material, never resolver-provider evidence.

Only fixed NIST WebBook pages and their explicitly linked 2D molecular files are
read. No PubChem/ChEBI request, production client, credential or cache is touched.
"""
import datetime,hashlib,html,json,re,urllib.request,urllib.parse
from pathlib import Path
H=Path(__file__).resolve().parent
REFERENCES={
 'ethanol':'C64175','dimethyl_ether':'C115106','acetone':'C67641','acetic_acid':'C64197','benzene':'C71432','pyridine':'C110861','bromomethane':'C74839','dichloromethane':'C75092','dichloromethane_d2':'C1665005','benzene_d6':'C107643','benzene_d6_corrected':'C1076433','acetone_d6':'C666524','heavy_water':'C7789200','water':'C7732185','r_butanol':'C14898794','s_butanol':'C4221992','sodium_acetate':'C127093','sodium_acetate_trihydrate':'C6131904','o_chlorophenol':'C95578','p_chlorophenol':'C106489','pyridone_2':'C142086','hydroxypyridine_2':'C142082'}
def main():
 out=H/'validation_material';out.mkdir(exist_ok=True);records=[]
 def fetch(url,target):
  if target.exists():return target.read_bytes(),'LOCAL_VALIDATION_MATERIAL_CACHE'
  u=urllib.parse.urlparse(url)
  if u.scheme!='https' or u.hostname!='webbook.nist.gov':raise ValueError('OUTSIDE_VALIDATION_REFERENCE_ALLOWLIST')
  req=urllib.request.Request(url,headers={'User-Agent':'ChemicalCorrespondencePublicReferenceValidation/1.0'})
  with urllib.request.urlopen(req,timeout=12) as response:data=response.read(2_000_000)
  target.write_bytes(data);return data,'PUBLIC_VALIDATION_MATERIAL_DOWNLOAD'
 for name,ident in REFERENCES.items():
  url='https://webbook.nist.gov/cgi/cbook.cgi?ID='+ident+'&Units=SI';row=dict(reference_id='NIST:'+ident,description=name,url=url,role='PUBLIC_VALIDATION_MATERIAL_ONLY',production_provider_evidence=False,independent_corroboration_by_download=False,retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
  try:
   p=out/(name+'.html');raw,route=fetch(url,p);s=raw.decode('utf8',errors='replace');plain=html.unescape(re.sub('<[^>]+>',' ',s));plain=' '.join(plain.split());row.update(path=str(p.resolve()),sha256=hashlib.sha256(raw).hexdigest(),retrieval_route=route,status='SUCCESS')
   values=[html.unescape(x).strip() for x in re.findall(r'<span\s+class="inchi-text">(.*?)</span>',s,re.S)];row['inchi']=next((x for x in values if x.startswith('InChI=')),None)
   title=re.search(r'<title>(.*?)</title>',s,re.S|re.I);row['title']=html.unescape(title.group(1)).strip() if title else None
   row['inchikey']=next((x for x in values if re.fullmatch(r'[A-Z]{14}-[A-Z]{10}-[A-Z]',x)),None)
   if not row['inchi']:row['status']='NO_QUALIFIED_IDENTITY_FIELDS'
   links=re.findall(r'href=["\']([^"\']+)["\']',s,re.I);mol=next((html.unescape(link) for link in links if 'Str2File=' in link),None)
   if mol:
    molurl=urllib.parse.urljoin(url,mol);mp=out/(name+'.mol')
    try:
     data,mroute=fetch(molurl,mp);row['molfile']=dict(url=molurl,path=str(mp.resolve()),sha256=hashlib.sha256(data).hexdigest(),retrieval_route=mroute)
    except Exception as exc:row['molfile_error']=str(exc)
  except Exception as exc:row.update(status='UNAVAILABLE',error=type(exc).__name__+': '+str(exc))
  records.append(row);print(name,row['status'],row.get('inchi',''),flush=True)
 (out/'retrieval_manifest.json').write_text(json.dumps({'purpose':'Separate public validation material, not resolver-provider queries or qualifying corroboration','fixed_page_limit':len(REFERENCES),'maximum_molfile_downloads':len(REFERENCES),'records':records},indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
