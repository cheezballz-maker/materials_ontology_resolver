"""Freeze implementation and prepare a cache-controlled development replay."""
import hashlib,json,shutil,sqlite3,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path

B=Path(__file__).resolve().parent.parent;H=B/'stereo_locant_upgrade_final';P=B/'second_form_aware_holdout'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')

assert not (H/'IMPLEMENTATION_FROZEN.json').exists()
run=H/'run';run.mkdir()
adjud=read(P/'ADJUDICATION_FROZEN.json');old=read(P/'METRICS_FROZEN.json')
for p,v in adjud['files'].items():assert sha(P/p)==v,p
for p,v in old['files'].items():assert sha(P/p)==v,p
for p,v in old['prediction_hashes'].items():assert sha(P/'predictions'/p)==v,p
tests=subprocess.run([sys.executable,'-m','unittest','test_registry','test_forms','test_evidence_retrieval','test_source_form','test_name_interpretation','test_systematic_notation','test_stereo_propagation','-v'],cwd=B,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
(H/'tests.log').write_text(tests.stdout,encoding='utf-8');assert tests.returncode==0,'Tests failed; see tests.log'
selection=read(P/'steward/selection.json');errors=selection['input_errors'];rows=[]
for n in (1,2,3):rows+=read(P/f'packet_{n}/records.json')
assert len(rows)==400 and len({r['cuma_index'] for r in rows})==400
db=sqlite3.connect(run/'candidates.sqlite')
db.execute('CREATE TABLE candidate(cuma_index INTEGER PRIMARY KEY,name TEXT,aliases TEXT,status TEXT,diagnostic TEXT,evidence_json TEXT)')
for r in rows:db.execute('INSERT INTO candidate VALUES(?,?,?,?,?,?)',(r['cuma_index'],r['preferred_name'],json.dumps(r['aliases'],ensure_ascii=False),'UNRESOLVED','Original frozen source input',json.dumps({'claims':[],'input_error':errors.get(str(r['cuma_index']))})))
db.commit();db.close()
cache={}
for folder in ('http_cache','chebi_cache','gsrs_cache'):
    source=B/'systematic_nomenclature_upgrade_final/run'/folder;target=run/folder;shutil.copytree(source,target)
    files=sorted(p.name for p in source.glob('*.json'))
    assert files==sorted(p.name for p in target.glob('*.json'))
    for name in files:assert sha(source/name)==sha(target/name)
    cache[folder]={'entries':len(files),'manifest_sha256':hashlib.sha256(''.join(n+sha(source/n) for n in files).encode()).hexdigest()}
runtime=['chemistry.py','form_characterizer.py','identity_comparator.py','policy.py','evidence_retrieval.py','providers.py','resolver.py','source_form.py','name_interpretation.py','systematic_notation.py','pipeline.py','registry_builder.py','schema.sql','verify.py','RegistryBridge.java','RegistryBridge.class','reviewed_evidence.json']
tests_files=['test_registry.py','test_forms.py','test_evidence_retrieval.py','test_source_form.py','test_name_interpretation.py','test_systematic_notation.py','test_stereo_propagation.py']
manifest=dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),records=400,run_kind='development re-evaluation, not an independent holdout',
  frozen_reference_manifest_sha256=sha(P/'ADJUDICATION_FROZEN.json'),frozen_metrics_manifest_sha256=sha(P/'METRICS_FROZEN.json'),
  baseline_prediction_hashes=old['prediction_hashes'],runtime_hashes={f:sha(B/f) for f in runtime},test_hashes={f:sha(B/f) for f in tests_files},tests_log_sha256=sha(H/'tests.log'),
  original_input_sha256=sha(run/'candidates.sqlite'),source_cache=cache,offline=True,new_network_requests_allowed=0,
  ontology_path=str(B.parent.parent.parent/'13. Materials Ontology/Ontology/substance_ontology.ttl'),
  framework_path='C:/Users/IT PatsnapSG/Downloads/Molecular_Substance_Identity_Framework_v1.md',
  reference_labels_modified=False,old_registry_modified=False)
for k in ['ontology','framework']:manifest[k+'_sha256']=sha(manifest[k+'_path'])
save(H/'IMPLEMENTATION_FROZEN.json',manifest)
print('Frozen implementation; 400 original source records and baseline provider caches prepared. Tests passed.')
