"""Bounded EPA CTX retrieval; qualification is a separate deterministic step."""
import hashlib,json,os,re,time,urllib.parse,urllib.request,urllib.error
from pathlib import Path
from chemistry import describe

ROOT=Path(__file__).resolve().parent
BASE='https://comptox.epa.gov/ctx-api/'

def configured_key():
    value=os.environ.get('CTX_API_KEY','').strip()
    if value:return value
    p=ROOT/'.env.local'
    if not p.exists():return ''
    try:
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.startswith('CTX_API_KEY='):
                return line.split('=',1)[1].strip().strip('"\'')
    except OSError:return ''
    return ''

def redact(obj,key):
    if isinstance(obj,str):return obj.replace(key,'[REDACTED]') if key else obj
    if isinstance(obj,list):return [redact(x,key) for x in obj]
    if isinstance(obj,dict):return {redact(k,key):redact(v,key) for k,v in obj.items()}
    return obj

class CompTox:
    def __init__(self,cache,budget=20,offline=False,timeout=15,max_hits=8):
        self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True)
        self.budget=budget;self.offline=offline;self.timeout=timeout;self.max_hits=max_hits;self.calls=0;self.last=0
    def _get(self,path):
        url=BASE+path;file=self.cache/(hashlib.sha256(url.encode()).hexdigest()+'.json')
        if file.exists():return json.loads(file.read_text(encoding='utf-8'))
        if self.offline:return dict(status='NOT_QUERIED',reason='OFFLINE_OR_CACHE_MISSING',url=url)
        key=configured_key()
        if not key:return dict(status='NOT_QUERIED',reason='KEY_NOT_CONFIGURED',url=url)
        if self.calls>=self.budget:return dict(status='NOT_QUERIED',reason='REQUEST_BUDGET',url=url)
        self.calls+=1;time.sleep(max(0,0.3-(time.monotonic()-self.last)));self.last=time.monotonic()
        try:
            req=urllib.request.Request(url,headers={'accept':'application/json','x-api-key':key,'User-Agent':'CanonicalSubstancePOC/1.0'})
            with urllib.request.urlopen(req,timeout=self.timeout) as response:data=json.load(response)
            result=dict(status='SUCCESS',data=redact(data,key),url=url,retrieved_at=time.time())
        except urllib.error.HTTPError as e:
            result=dict(status='NO_MATCH' if e.code==404 else 'RATE_LIMITED' if e.code==429 else 'ERROR',reason='HTTP_'+str(e.code),url=url)
        except Exception:
            result=dict(status='ERROR',reason='REQUEST_FAILED',url=url)
        # Never cache a credential or an exception containing a credential.
        if result['status'] in ('SUCCESS','NO_MATCH'):file.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
        return result
    def name(self,name):return self.retrieve('name',name)
    def retrieve(self,kind,value):
        if kind not in ('name','CASRegistryNumber','InChIKey','DTXSID','DTXCID'):
            return dict(provider='CompTox',status='UNSUPPORTED',query_type=kind,rows=[])
        if kind in ('DTXSID','DTXCID'):
            if not re.fullmatch(kind+r'\d+',value):return dict(provider='CompTox',status='ERROR',reason='INVALID_IDENTIFIER',rows=[])
            mode='by-dtxsid' if kind=='DTXSID' else 'by-dtxcid'
            raw=self._get('chemical/detail/search/'+mode+'/'+urllib.parse.quote(value,safe='')+'?projection=chemicalstructure')
            hits=[raw.get('data')] if raw.get('data') else []
        else:
            raw=self._get('chemical/search/equal/'+urllib.parse.quote(value,safe='')+'?top='+str(self.max_hits+1))
            hits=raw.get('data',[]) if isinstance(raw.get('data'),list) else []
        out=dict(provider='CompTox',query=value,query_type=kind,url=raw.get('url'),status=raw['status'],rows=[],retrieval=[raw])
        if raw['status']=='NO_MATCH' or (raw['status']=='SUCCESS' and not hits):out['status']='NO_MATCH';return out
        if raw['status']!='SUCCESS':return out
        if len(hits)>self.max_hits:out.update(status='INCOMPLETE',reason='RESULT_LIMIT');return out
        relevant_unusable=False
        for hit in hits:
            if not isinstance(hit,dict) or hit.get('isMarkush'):continue
            sid=hit.get('dtxsid');cid=hit.get('dtxcid');s=hit.get('smiles')
            if not sid or not re.fullmatch(r'DTXSID\d+',str(sid)):continue
            if kind in ('name','CASRegistryNumber','InChIKey') and hit.get('searchValue')!=value:
                if isinstance(hit.get('searchValue'),str) and hit['searchValue'].casefold()==value.casefold():relevant_unusable=True
                continue
            relevant_unusable=True
            detail=self._get('chemical/detail/search/by-dtxsid/'+urllib.parse.quote(sid,safe='')+'?projection=chemicalstructure');out['retrieval'].append(detail)
            d={}
            if detail['status']=='SUCCESS' and isinstance(detail.get('data'),dict):
                d=detail['data'];s=d.get('smiles') or d.get('smilesString') or s;cid=d.get('dtxcid') or cid
            if not s:continue
            try:desc=describe(s)
            except (ValueError,RuntimeError):continue
            provider_inchi=(d.get('inchiString') or '').strip();provider_key=(d.get('inchikey') or '').strip()
            if (provider_inchi and provider_inchi!=desc['inchi']) or (provider_key and provider_key!=desc['inchikey']):continue
            out['rows'].append(dict(provider='CompTox',DTXSID=sid,DTXCID=cid,record_id=sid,SMILES=s,matched_search_value=hit.get('searchValue'),CASRN=hit.get('searchValue') if kind=='CASRegistryNumber' else None,
                InChI=desc['inchi'],InChIKey=desc['inchikey'],identifier_origin='provider_verified' if provider_inchi and provider_key else 'locally_generated_not_provider_assertion',
                url=detail.get('url'),source_dependence='DSSTox; upstream independence and form preservation unverified'))
        if not out['rows']:out['status']='NON_DISCRIMINATING' if relevant_unusable else 'NO_MATCH'
        return out
