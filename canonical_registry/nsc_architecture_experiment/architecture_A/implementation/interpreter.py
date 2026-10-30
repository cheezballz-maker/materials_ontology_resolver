"""Pinned source-aware OPSIN adapter. Closure is not yet proven: fail closed."""
import base64, functools, hashlib, json, os, re, subprocess
from pathlib import Path
from shared.semantic_interface import SemanticInterpretation,SemanticValidation,make_claims,make_operation,make_constraint,validate_interpretation

ROOT=Path(__file__).resolve().parents[3]
PATTERN=re.compile(r'(?P<loc>1)-(?P<alkyl>methyl|ethyl|propyl|butyl)-(?P<h>1H)-(?P<parent>pyrazole|imidazole)')
dec=lambda s:base64.b64decode(s,validate=True).decode('utf8') if s else ''
@functools.lru_cache(maxsize=32)
def trace(name):
    try:
        home=ROOT/'source_aware_substitution_poc';build=json.loads((home/'build.json').read_text(encoding='utf8'))
        if hashlib.sha256((home/'substitution-instrumentation.patch').read_bytes()).hexdigest()!=build['patch_sha256']:return {'error':'PATCH_DIGEST_MISMATCH'}
        root=Path(build['temp_build']);jar=root/'opsin-core-2.9.0.jar'
        if hashlib.sha256(jar.read_bytes()).hexdigest()!='627ee5da4af551f9c4d1d766f545eb7cf519a344776e0bb677247a47abac0252':return {'error':'OPSIN_DIGEST_MISMATCH'}
        cp=os.pathsep.join(map(str,[root/'substitution-classes',root/'source/opsin-core/src/main/resources',jar]));encoded=base64.b64encode(name.encode()).decode()
        p=subprocess.run(['java','-Dprobe.trace=true','-cp',cp,'uk.ac.cam.ch.wwmm.opsin.Runner',encoded],capture_output=True,text=True,encoding='utf8',check=True,timeout=25)
        rows=[s.split('\t') for s in p.stdout.splitlines()];r=[x for x in rows if x[0]=='R'];ps=[x for x in rows if x[0]=='P'];ss=[x for x in rows if x[0]=='S'];hs=[x for x in rows if x[0]=='E']
        if len(r)!=1 or dec(r[0][1])!=name or r[0][2]!='SUCCESS' or dec(r[0][6]) or r[0][7]=='true' or len(ps)!=1 or ps[0][2]!='true' or len(ss)!=1 or len(hs)!=1:return {'error':'UNSUPPORTED_PARSE_OR_TRACE'}
        s,h=ss[0],hs[0];start,end=int(s[1]),int(s[2]);hstart,hend=int(h[1]),int(h[2])
        if name[start:end]!=dec(s[3]) or name[hstart:hend]!=dec(h[3]) or dec(h[4])!='indicatedHydrogen' or s[13:18]!=['true','true','true','true','false'] or h[11:13]!=['true','false'] or int(h[15])>=int(s[18]):return {'error':'PROVENANCE_UNPROVEN'}
        return {'status':'OBSERVED','locant_span':[start,end],'indicated_h_span':[hstart,hend],'target_atom':s[11],'attachment_atom':s[12],'smiles':dec(r[0][4]),'cml':dec(r[0][5]),'source_nodes':dec(s[7]),'substituent_xml':dec(s[8])}
    except Exception:return {'error':'TRACE_UNAVAILABLE'}

def interpret_name(name):
    m=PATTERN.fullmatch(name) if isinstance(name,str) else None
    if not m:return SemanticInterpretation(input_name=name,scope_status='OUT_OF_CONTRACT',unresolved_dependencies=['UNSUPPORTED_GRAMMAR'])
    evidence=trace(name)
    if evidence.get('status')!='OBSERVED':return SemanticInterpretation(input_name=name,scope_status='UNKNOWN',unresolved_dependencies=[evidence.get('error','TRACE_UNAVAILABLE')])
    # Trace locant and indicated-H token must cover the independently recognized
    # units; intervening substituent token provenance is checked below.
    nodes=evidence['source_nodes']
    if not nodes or m['alkyl'][:-2] not in nodes or ':yl;' not in nodes:
        return SemanticInterpretation(input_name=name,scope_status='UNKNOWN',unresolved_dependencies=['SUBSTITUENT_PROVENANCE_INCOMPLETE'])
    length={'methyl':1,'ethyl':2,'propyl':3,'butyl':4}[m['alkyl']]
    result=SemanticInterpretation(input_name=name,scope_status='IN_CONTRACT',source_claims=make_claims(name,m.span('loc'),m.span('alkyl'),m.span('h'),m.span('parent')),semantic_operations=[make_operation(m['parent'],m['alkyl'],length)],structural_constraints=[make_constraint(m['parent'],m['alkyl'],length)],unresolved_dependencies=['FINAL_OPERATION_CLOSURE_NOT_PROVEN'])
    validate_interpretation(result);return result
def validate_candidate(interpretation,candidate_structure,context=None):
    if interpretation.scope_status=='OUT_OF_CONTRACT':return SemanticValidation(result='OUT_OF_CONTRACT',reason_codes=['UNSUPPORTED_GRAMMAR'])
    if interpretation.scope_status!='IN_CONTRACT':return SemanticValidation(result='UNKNOWN',reason_codes=interpretation.unresolved_dependencies)
    validate_interpretation(interpretation)
    return SemanticValidation(result='UNKNOWN',operation_results=[{'operation_id':'op1','result':'UNKNOWN'}],evidence={'trace':'OBSERVED'},reason_codes=['FINAL_OPERATION_CLOSURE_NOT_PROVEN'])
