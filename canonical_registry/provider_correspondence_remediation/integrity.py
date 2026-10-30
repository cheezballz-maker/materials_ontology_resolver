import base64,hashlib,json,os,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path.insert(0,str(B))
from comptox import configured_key
from providers import DEFAULT_JAR
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
old=read(B/'evidence_scope_remediation_result/IMPLEMENTATION_FROZEN.json');prior=read(B/'evidence_scope_remediation_result/classpath.json');f=read(H/'frozen.json')
cp=str(B)+';'+str(DEFAULT_JAR)
cmd=['java','-Xlog:class+load=info','-cp',cp,'RegistryBridge']
request='name\t'+base64.b64encode(b'(R)-butan-2-ol').decode()+'\n'
r=subprocess.run(cmd,input=request,text=True,capture_output=True,timeout=30)
loaded=[line for line in (r.stdout+'\n'+r.stderr).splitlines() if 'uk.ac.cam.ch.wwmm.opsin.NameToStructure source:' in line or 'uk.ac.cam.ch.wwmm.opsin.StereochemistryHandler source:' in line]
key=configured_key();hits=[]
for p in H.rglob('*'):
    if p.is_file() and p.suffix in ('.json','.log','.md','.py','.txt') and key and key.encode() in p.read_bytes():hits.append(str(p.relative_to(H)))
report=B/'PROVIDER_CORRESPONDENCE_REMEDIATION_REPORT.md'
if report.exists() and key and key.encode() in report.read_bytes():hits.append(report.name)
shadow=list(B.glob('uk/ac/cam/ch/wwmm/opsin/*.class'))
snapshots={}
for folder,manifest,subdir in [('explicit_multicomponent_upgrade_release2','SCORING_FROZEN.json','run'),('stereo_locant_upgrade_complete','SCORING_FROZEN.json','run'),('grounding_remediation_final_scored','SCORING_FROZEN.json','run'),('second_form_aware_holdout','METRICS_FROZEN.json','predictions'),('evidence_scope_remediation_result','SCORING_FROZEN.json','run')]:
    base=B/folder;data=read(base/manifest)
    snapshots[folder]=all(sha(base/subdir/name)==digest for name,digest in data['prediction_hashes'].items())
checks=dict(opsin_jar_unchanged=sha(DEFAULT_JAR)==prior['jar_sha256'],runtime_files_match_freeze=all(sha(B/k)==v for k,v in f['files'].items()),
    bridge_source_unchanged=sha(B/'RegistryBridge.java')==old['runtime_hashes']['RegistryBridge.java'],bridge_class_unchanged=sha(B/'RegistryBridge.class')==old['runtime_hashes']['RegistryBridge.class'],
    ontology_unchanged=sha(old['ontology_path'])==old['ontology_sha256'],schema_unchanged=sha(B/'schema.sql')==old['runtime_hashes']['schema.sql'],
    prior_registry_unchanged=sha(B/'provider_qualification/run/registry.sqlite')==f['prior_registry_sha256'],prior_candidate_unchanged=sha(B/'provider_qualification/run/candidates.sqlite')==f['prior_candidate_sha256'],
    historical_prediction_snapshots_unchanged=all(snapshots.values()),
    diagnostic_shadow_classes_absent=not shadow,classpath_verified=len(loaded)==2 and all(DEFAULT_JAR.name in x for x in loaded),
    java_injection_environment_absent=not any(os.environ.get(k) for k in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS')),
    key_configured=bool(key),secret_absent_from_new_text_files=not hits)
out=dict(checks=checks,hashes=dict(opsin_jar=sha(DEFAULT_JAR),ontology=sha(old['ontology_path']),schema=sha(B/'schema.sql')),historical_prediction_snapshots=snapshots,class_load_lines=loaded,secret_file_hits=hits)
(H/'integrity.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(checks,indent=2));sys.exit(0 if all(checks.values()) else 1)
