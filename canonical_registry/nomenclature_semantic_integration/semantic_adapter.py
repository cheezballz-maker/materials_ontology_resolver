"""Experimental, fail-closed 2.9.0 trace adapter; never promotes admission.

The pinned instrumented process runs once per input, so the POC's static
state is process-local. A mapped token is *not* a validated final constraint:
operation and complete mobile-H lineage are not present in the POC trace.
"""
import base64,hashlib,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent
TRACE=H/'opsin-2.9.0-trace.jar';RELEASE=H/'opsin-core-2.9.0-jar-with-dependencies.jar'
EXPECTED_RELEASE='627ee5da4af551f9c4d1d766f545eb7cf519a344776e0bb677247a47abac0252'
EXPECTED_TRACE='58708f2907c661806f2d67811cc3bb77f2b48f29e7d0d78d1cff4da956045be5'
def _sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def _decode(s):return base64.b64decode(s,validate=True).decode('utf8') if s else ''
def trace(name,timeout=12):
 """Return explicit token evidence with UNKNOWN constraint; never a policy decision."""
 def fallback(reason):return {'status':'UNRESOLVED','constraint':'UNKNOWN','reason':reason,'claims':[]}
 try:
  if not isinstance(name,str) or not name:return fallback('INVALID_INPUT')
  if not name.isascii():return fallback('ORIGINAL_SPAN_NORMALIZATION_UNVERIFIED')
  if _sha(RELEASE)!=EXPECTED_RELEASE or _sha(TRACE)!=EXPECTED_TRACE:return fallback('ARTIFACT_DIGEST_MISMATCH')
  encoded=base64.b64encode(name.encode('utf8')).decode('ascii')
  cp=str(TRACE)+__import__('os').pathsep+str(RELEASE)
  p=subprocess.run(['java','-Dprobe.trace=true','-cp',cp,'uk.ac.cam.ch.wwmm.opsin.Runner',encoded],capture_output=True,text=True,encoding='utf8',timeout=timeout,check=True)
  lines=[line.split('\t') for line in p.stdout.splitlines()];r=[x for x in lines if x[0]=='R']
  if len(r)!=1 or _decode(r[0][1])!=name:return fallback('PARSE_RESULT_UNTRUSTWORTHY')
  rec=r[0];status=rec[2];warnings=_decode(rec[6]);ambiguous=rec[7]=='true'
  if status!='SUCCESS' or warnings or ambiguous:return fallback('OPSIN_WARNING_OR_FAILURE')
  alternatives=[x for x in lines if x[0]=='P']
  if len(alternatives)!=1 or alternatives[0][2]!='true':return fallback('ALTERNATIVE_PARSE_UNVERIFIED')
  cml=_decode(rec[5]);root=ET.fromstring(cml);ns={'c':'http://www.xml-cml.org/schema'}
  atoms={a.get('id'):a for a in root.findall('.//c:atom',ns)};claims=[]
  for e in (x for x in lines if x[0]=='E'):
   start,end=int(e[1]),int(e[2]);token,kind,locant,owner=map(_decode,e[3:7]);atom='a'+e[7]
   explicit=start>=0 and end<=len(name) and name[start:end]==token
   mapped=explicit and e[11]=='true' and e[12]=='false' and atom in atoms and any(a.get('value')==locant for a in atoms[atom].findall('c:label',ns))
   claims.append(dict(source_span=[start,end] if explicit else None,source_text=token if explicit else None,semantic_type={'indicatedHydrogen':'INDICATED_HYDROGEN','addedHydrogen':'ADDED_INDICATED_HYDROGEN'}.get(kind,'UNKNOWN'),fragment=owner,fragment_id=e[14],locant=locant,cml_atom=atom,operation_stage='PARENT_LOCANTED_FEATURE',explicit_or_generated='EXPLICIT' if explicit else 'GENERATED_OR_UNMAPPED',mapping_status='MAPPED_BOUNDED' if mapped else 'UNRESOLVED',operations='NOT_CAPTURED',constraint='UNKNOWN',reason='OPERATION_AND_MOBILE_H_COVERAGE_UNPROVEN' if mapped else 'SOURCE_OR_FRAGMENT_LINEAGE_UNRESOLVED'))
  return {'status':'TRACE_ONLY','constraint':'UNKNOWN','reason':'OPERATION_AND_MOBILE_H_COVERAGE_UNPROVEN','engine_version':'2.9.0','smiles':_decode(rec[4]),'same_result_cml':cml,'claims':claims}
 except Exception:
  return fallback('TRACE_FAILURE')
