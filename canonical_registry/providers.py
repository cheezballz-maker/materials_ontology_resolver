"""Evidence adapters: no canonical identity decisions or ID allocation."""
import base64
import hashlib
import json
import queue
import subprocess
import threading
import time
import urllib.request
import urllib.parse
from pathlib import Path
from rdkit import Chem
from chemistry import parse

ROOT=Path(__file__).resolve().parent
DEFAULT_JAR=ROOT.parent/'opsin-master/opsin-cli/target/opsin-cli-3.0-SNAPSHOT-jar-with-dependencies.jar'

class Bridge:
    def __init__(self,jar=DEFAULT_JAR,timeout=10):
        self.jar=Path(jar); self.timeout=timeout; self.p=None
        self.digest=hashlib.sha256(self.jar.read_bytes()).hexdigest()
        subprocess.run(['javac','-cp',str(self.jar),str(ROOT/'RegistryBridge.java')],check=True,capture_output=True,timeout=30)
    def close(self):
        if self.p:
            self.p.kill(); self.p.wait()
            for stream in (self.p.stdin,self.p.stdout,self.p.stderr): stream.close()
            self.p=None
    def request(self,kind,value):
        if self.p is None:
            self.q=queue.Queue()
            self.p=subprocess.Popen(['java','-Xmx512m','-cp',str(ROOT)+';'+str(self.jar),'RegistryBridge'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
            p,q=self.p,self.q
            threading.Thread(target=lambda: [q.put(x.rstrip('\n')) for x in p.stdout],daemon=True).start()
            # Drain stderr to prevent a blocked JVM, retaining transport diagnostics.
            self.stderr=[]
            threading.Thread(target=lambda: [self.stderr.append(x.rstrip()) for x in p.stderr],daemon=True).start()
        try:
            self.p.stdin.write(kind+'\t'+base64.b64encode(value.encode()).decode()+'\n'); self.p.stdin.flush()
            parts=self.q.get(timeout=self.timeout).split('\t')
            return [parts[0]]+[base64.b64decode(v).decode() for v in parts[1:]]
        except Exception as e:
            self.close(); return ['ERROR','',str(e) or 'timeout']
    def opsin(self,name):
        r=self.request('name',name)
        return dict(provider='OPSIN',query=name,status=r[0],smiles=r[1],diagnostic=r[2],version=r[3] if len(r)>3 else 'unreported',jar_name=self.jar.name,jar_sha256=self.digest)
    def opsin_cml(self,name):
        r=self.request('name_cml',name)
        return dict(provider='OPSIN',query=name,status=r[0],cml=r[1],diagnostic=r[2],version=r[3] if len(r)>3 else 'unreported')
    def official(self,d):
        r=self.request('mol',Chem.MolToMolBlock(parse(d['smiles'])))
        return dict(provider='Official InChI via JNA',status=r[0],inchi=r[1],diagnostic=r[2],inchikey=r[3] if len(r)>3 else '',version=r[4] if len(r)>4 else '',agrees=len(r)>3 and r[1]==d['inchi'] and r[3]==d['inchikey'])

class PubChem:
    def __init__(self,cache,budget=120,offline=False):
        self.cache=Path(cache); self.cache.mkdir(parents=True,exist_ok=True)
        self.budget=budget; self.offline=offline; self.calls=0; self.last=0
    def name(self,name):
        url='https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/'+urllib.parse.quote(name,safe='')+'/property/SMILES,InChI,InChIKey,IUPACName/JSON'
        file=self.cache/(hashlib.sha256(url.encode()).hexdigest()+'.json')
        if file.exists(): return json.loads(file.read_text(encoding='utf-8'))
        if self.offline or self.calls>=self.budget: return dict(provider='PubChem',query=name,status='NOT_QUERIED',reason='offline or request budget')
        self.calls+=1; time.sleep(max(0,0.3-(time.monotonic()-self.last))); self.last=time.monotonic()
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'CanonicalSubstancePOC/1.0'})
            with urllib.request.urlopen(req,timeout=15) as response:
                data=json.load(response)
            out=dict(provider='PubChem',query=name,url=url,status='SUCCESS',retrieved_at=time.time(),rows=data.get('PropertyTable',{}).get('Properties',[]))
        except Exception as e:
            out=dict(provider='PubChem',query=name,url=url,status='ERROR',diagnostic=str(e),retrieved_at=time.time())
        file.write_text(json.dumps(out,ensure_ascii=False),encoding='utf-8')
        return out

    def retrieve(self,kind,value):
        """Complete identity keys only; PubChem standardization is not our equality."""
        if kind=='name':return self.name(value)
        base='https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/'
        fields='/property/SMILES,InChI,InChIKey,IUPACName/JSON'
        if kind in ('CASRegistryNumber','ECNumber'):return self.name(value)
        if kind=='PubChemCID':path='cid/'+urllib.parse.quote(value,safe='')
        elif kind=='InChIKey':path='inchikey/'+urllib.parse.quote(value,safe='')
        elif kind=='InChI':path='inchi'
        elif kind=='SMILES':
            url=base+'fastidentity/smiles/'+urllib.parse.quote(value,safe='')+'/cids/JSON?identity_type=same_stereo_isotope&MaxRecords=9'
            raw=cached_json(self,url)
            out=dict(provider='PubChem',query=value,query_type=kind,url=url,status=raw['status'],rows=[],retrieval=[raw])
            if raw['status']!='SUCCESS':return out
            ids=raw['data'].get('IdentifierList',{}).get('CID',[])
            if len(ids)>8:out['status']='INCOMPLETE';out['diagnostic']='IDENTITY_RESULT_LIMIT';return out
            if not ids:return out
            props=cached_json(self,base+'cid/'+','.join(map(str,ids))+fields);out['retrieval'].append(props);out['status']=props['status']
            out['rows']=props.get('data',{}).get('PropertyTable',{}).get('Properties',[])
            return out
        else:return dict(provider='PubChem',query=value,status='UNSUPPORTED',rows=[])
        url=base+path+fields+('?' + urllib.parse.urlencode({'inchi':value}) if kind=='InChI' else '')
        raw=cached_json(self,url)
        rows=raw.get('data',{}).get('PropertyTable',{}).get('Properties',[])
        return dict(provider='PubChem',query=value,query_type=kind,url=url,status='INCOMPLETE' if len(rows)>8 else raw['status'],rows=rows[:8],retrieval=[raw])

class ChEBI:
    """Bounded exact-name corroboration using released three-star full records."""
    BASE='https://www.ebi.ac.uk/chebi/backend/api/public/'
    def __init__(self,cache,budget=500,offline=False,max_hits=8):
        self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True)
        self.budget=budget;self.offline=offline;self.max_hits=max_hits;self.calls=0;self.last=0
    def get(self,url):
        file=self.cache/(hashlib.sha256(url.encode()).hexdigest()+'.json')
        if file.exists():return json.loads(file.read_text(encoding='utf-8'))
        if self.offline or self.calls>=self.budget:return dict(status='NOT_QUERIED',url=url)
        self.calls+=1;time.sleep(max(0,0.3-(time.monotonic()-self.last)));self.last=time.monotonic()
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CanonicalSubstancePOC/2.0'}),timeout=15) as response:data=json.load(response)
            result=dict(status='SUCCESS',url=url,retrieved_at=time.time(),data=data)
        except Exception as e:result=dict(status='ERROR',url=url,retrieved_at=time.time(),diagnostic=str(e))
        file.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8');return result
    @staticmethod
    def names(record):
        import html,re
        from chemistry import normalize_name
        values=[record.get('name',''),record.get('ascii_name','')]
        values += [r.get('name','') for rows in record.get('names',{}).values() for r in rows if r.get('language_code') in (None,'en')]
        return sorted({normalize_name(html.unescape(re.sub(r'<[^>]+>','',v))) for v in values if v})
    def name(self,name):
        from chemistry import normalize_name
        url=self.BASE+'es_search/?term='+urllib.parse.quote(name,safe='')+'&size='+str(self.max_hits)+'&page=1'
        search=self.get(url);out=dict(provider='ChEBI',query=name,url=url,status=search['status'],rows=[],retrieval=[search])
        if search['status']!='SUCCESS':return out
        data=search['data']
        if data.get('total',0)>self.max_hits:
            out['search_truncated']=True
            out['diagnostic']='Bounded fuzzy retrieval; only exact-name full records corroborate. This is not evidence of chemical ambiguity or exhaustive database coverage.'
        for hit in data.get('results',[]):
            accession=hit.get('_source',{}).get('chebi_accession')
            if not accession:continue
            full=self.get(self.BASE+'compound/'+accession+'/');out['retrieval'].append(full)
            if full['status']!='SUCCESS':out['status']='INCOMPLETE';continue
            r=full['data'];names=self.names(r)
            if normalize_name(name) not in set(names):
                # A case-only candidate is an ambiguity, never an exact-name
                # assertion; do not silently discard potentially conflicting evidence.
                if normalize_name(name).casefold() in {v.casefold() for v in names}:
                    out['status']='INCOMPLETE'
                    out.setdefault('excluded_records',[]).append(dict(accession=accession,reason='NAME_CASE_VARIANT_UNVERIFIED',url=full['url']))
                continue
            s=r.get('default_structure') or {}
            if r.get('stars')!=3 or not r.get('is_released') or not s.get('smiles') or s.get('is_r_group'):continue
            # Some residue/class records carry wildcard atoms despite is_r_group=False.
            # They describe open-ended entities, not competing discrete molecules.
            # Keep the full response above, with an explicit exclusion diagnostic.
            if '*' in s['smiles']:
                out.setdefault('excluded_records',[]).append(dict(accession=accession,reason='NON_DISCRETE_WILDCARD_STRUCTURE',url=full['url']))
                continue
            out['rows'].append(dict(provider='ChEBI',ChEBIID=accession,SMILES=s['smiles'],InChI=s.get('standard_inchi'),InChIKey=s.get('standard_inchi_key'),names=names,url=full['url'],name_match=True,definition=r.get('definition'),source_dependence='Curated record; upstream data may overlap PubChem'))
        return out

    def retrieve(self,kind,value):
        if kind=='name':return self.name(value)
        if kind not in ('ChEBIID','InChIKey','InChI','CASRegistryNumber','ECNumber'):return dict(provider='ChEBI',query=value,status='UNSUPPORTED',rows=[])
        out=dict(provider='ChEBI',query=value,query_type=kind,status='SUCCESS',rows=[],retrieval=[])
        if kind=='ChEBIID':ids=[value]
        else:
            url=self.BASE+'es_search/?'+urllib.parse.urlencode({'term':value,'size':self.max_hits,'page':1})
            search=self.get(url);out.update(url=url,status=search['status']);out['retrieval'].append(search)
            if search['status']!='SUCCESS':return out
            if search['data'].get('total',0)>self.max_hits:out['status']='INCOMPLETE';out['diagnostic']='IDENTIFIER_RESULT_LIMIT'
            ids=[h.get('_source',{}).get('chebi_accession') for h in search['data'].get('results',[])[:self.max_hits]]
        for accession in ids:
            if not accession:continue
            full=self.get(self.BASE+'compound/'+accession+'/');out['retrieval'].append(full)
            if full['status']!='SUCCESS':out['status']='INCOMPLETE';continue
            r=full['data'];s=r.get('default_structure') or {}
            if r.get('stars')!=3 or not r.get('is_released') or not s.get('smiles') or s.get('is_r_group') or '*' in s.get('smiles',''):continue
            out['rows'].append(dict(provider='ChEBI',ChEBIID=accession,SMILES=s['smiles'],InChI=s.get('standard_inchi'),InChIKey=s.get('standard_inchi_key'),names=self.names(r),url=full['url'],definition=r.get('definition'),source_dependence='Curated record; upstream structure provenance not independently established'))
        return out


def cached_json(adapter,url):
    """Bounded read-only HTTP, including negative caching and explicit budgets."""
    file=adapter.cache/(hashlib.sha256(url.encode()).hexdigest()+'.json')
    if file.exists():return json.loads(file.read_text(encoding='utf-8'))
    if adapter.offline or adapter.calls>=adapter.budget:return dict(status='NOT_QUERIED',url=url,diagnostic='OFFLINE_OR_REQUEST_BUDGET')
    adapter.calls+=1;time.sleep(max(0,0.3-(time.monotonic()-adapter.last)));adapter.last=time.monotonic()
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CanonicalSubstancePOC/3.0'}),timeout=15) as response:
            data=json.load(response)
        result=dict(status='SUCCESS',url=url,retrieved_at=time.time(),data=data)
    except Exception as e:result=dict(status='ERROR',url=url,retrieved_at=time.time(),diagnostic=str(e))
    file.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8');return result


class GSRS:
    """NCATS public GSRS chemical records; FDA/NCATS mirrors are one lineage.

    No mixture/protein/polymer assembly, ratio expansion, salt conversion or
    inference from names. The complete supplied molfile must agree with SMILES,
    InChI and declared integer moieties. Unsupported records remain diagnostics.
    """
    BASE='https://gsrs.ncats.nih.gov/ginas/app/api/v1/'
    def __init__(self,cache,budget=200,offline=False,max_hits=4):
        self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True)
        self.budget=budget;self.offline=offline;self.max_hits=max_hits;self.calls=0;self.last=0
    def get(self,url):return cached_json(self,url)
    @staticmethod
    def record(r,url):
        from collections import Counter
        from chemistry import describe,normalize_name
        from identity_comparator import compare
        if r.get('substanceClass')!='chemical' or r.get('status')!='approved' or r.get('deprecated') or r.get('definitionType')!='PRIMARY' or r.get('definitionLevel')!='COMPLETE':raise ValueError('GSRS_RECORD_SCOPE_UNSUPPORTED')
        s=r.get('structure') or {}
        if s.get('stereochemistry') not in ('ACHIRAL','ABSOLUTE') or s.get('atropisomerism') not in (None,'No') or s.get('opticalActivity') in ('PLUS_MINUS','UNSPECIFIED'):raise ValueError('GSRS_STEREO_SCOPE_UNSUPPORTED')
        d=describe(s.get('smiles',''));block=s.get('molfile','')
        if not block.rstrip().endswith('M  END'):raise ValueError('GSRS_MOLFILE_INCOMPLETE')
        m=Chem.MolFromMolBlock(block,sanitize=True,removeHs=False,strictParsing=True)
        if m is None or compare(d,describe(Chem.MolToSmiles(m,isomericSmiles=True)))['assessment']!='EXACT':raise ValueError('GSRS_MOLFILE_SMILES_CONFLICT')
        if d['inchi']!=s.get('_inchi') or d['inchikey']!=s.get('_inchiKey'):raise ValueError('GSRS_IDENTIFIER_CONFLICT')
        counts=Counter(Chem.MolToSmiles(x,isomericSmiles=True) for x in Chem.GetMolFrags(parse(d['smiles']),asMols=True))
        moieties=Counter()
        for part in r.get('moieties',[]):
            amount=part.get('countAmount') or {};n=amount.get('average')
            if not isinstance(n,(int,float)) or n<1 or n!=int(n) or any(amount.get(k) is not None for k in ('low','high','lowLimit','highLimit','nonNumericValue')):raise ValueError('GSRS_MOIETY_RATIO_UNSUPPORTED')
            pd=describe(part.get('smiles',''));moieties[pd['smiles']]+=int(n)
        if not moieties or counts!=moieties:raise ValueError('GSRS_COMPLETE_FORM_MOIETY_CONFLICT')
        refids=set(s.get('references',[]));refs=[x for x in r.get('references',[]) if x.get('uuid') in refids]
        names=sorted({normalize_name(x['name']) for x in r.get('names',[]) if x.get('name') and not x.get('deprecated') and ('en' in x.get('languages',[]) or not x.get('languages'))})
        return dict(provider='GSRS',UNII=r.get('approvalID'),record_id=r['uuid'],SMILES=s['smiles'],InChI=s['_inchi'],InChIKey=s['_inchiKey'],names=names,url=url,structure_references=refs,source_dependence='FDA/NCATS GSRS family; structure-reference provenance retained, independence from aggregators unresolved',gsrs_moiety_validation='COMPLETE_INTEGER_FORM_AGREES')
    def name(self,name):return self.retrieve('name',name)
    def retrieve(self,kind,value):
        import re
        from chemistry import normalize_name
        literal=lambda v:re.sub(r'([+\-!(){}\[\]^"~*?:\\/])',r'\\\1',v)
        if kind=='name':q='root_names_name:"^'+literal(value)+'$"'
        elif kind=='UNII':q='root_approvalID:'+literal(value)
        elif kind=='CASRegistryNumber':q='root_codes_code:"^'+literal(value)+'$"'
        elif kind=='SMILES':q=None
        else:return dict(provider='GSRS',query=value,status='UNSUPPORTED',rows=[])
        params={'q':q if q is not None else value,'top':self.max_hits,'skip':0}
        if kind=='SMILES':params.update(type='exact',sync='true')
        url=self.BASE+('substances/structureSearch?' if kind=='SMILES' else 'substances/search?')+urllib.parse.urlencode(params)
        raw=self.get(url);out=dict(provider='GSRS',query=value,query_type=kind,url=url,status=raw['status'],rows=[],retrieval=[raw],excluded_records=[])
        if raw['status']!='SUCCESS':return out
        data=raw['data']
        if data.get('total',0)>self.max_hits:out['status']='INCOMPLETE';out['diagnostic']='GSRS_RESULT_LIMIT'
        if 'content' not in data:out['status']='INCOMPLETE';out['diagnostic']='GSRS_SEARCH_NOT_COMPLETE';return out
        for hit in data['content'][:self.max_hits]:
            uuid=hit.get('uuid','')
            if not re.fullmatch(r'[0-9a-fA-F-]{36}',uuid):continue
            full=self.get(self.BASE+'substances('+uuid+')?view=full');out['retrieval'].append(full)
            if full['status']!='SUCCESS':out['status']='INCOMPLETE';continue
            r=full['data']
            names={normalize_name(x.get('name','')) for x in r.get('names',[]) if not x.get('deprecated')}
            if kind=='name' and normalize_name(value) not in names:
                if normalize_name(value).casefold() in {n.casefold() for n in names}:
                    out['status']='INCOMPLETE'
                    out['excluded_records'].append(dict(record_id=uuid,reason='NAME_CASE_VARIANT_UNVERIFIED',url=full['url']))
                continue
            if kind=='UNII' and r.get('approvalID')!=value:continue
            if kind=='CASRegistryNumber' and not any(x.get('codeSystem')=='CAS' and x.get('code')==value for x in r.get('codes',[])):continue
            try:out['rows'].append(self.record(r,full['url']))
            except (ValueError,RuntimeError) as e:out['excluded_records'].append(dict(record_id=uuid,reason=str(e),url=full['url']))
        return out
