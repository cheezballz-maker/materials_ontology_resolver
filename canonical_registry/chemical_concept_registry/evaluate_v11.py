"""Bounded frozen-pilot v1.1 study; all concept writes use a new fixture."""
import csv,hashlib,json,sqlite3,sys,time,uuid
from collections import Counter
from pathlib import Path
from rdkit import Chem,RDLogger
RDLogger.DisableLog('rdApp.*')
from constraints import molecular,ProposalError
from registry import initialize,FIXTURES,BASE,sha
from unified_chemical import UnifiedChemicalResolver
sys.path.insert(0,str(BASE/'unified_substance_resolution'))
from unified_resolver import SubstanceResolver
from warehouse_sample_adapter import TrustedWarehouseAdapter
from providers import Bridge
from registry_matching_models import RetrievalPolicy
from registry_identity_adapter import RegistrySnapshot

ROOT=Path(__file__).resolve().parent
PILOT=BASE/'warehouse_admission_consolidation/output/normalized_pilot.sqlite'
SEED=BASE/'output/registry.sqlite'
ONTOLOGY=Path(r'C:\Users\IT PatsnapSG\OneDrive - Patsnap\13. PatSnap\13. Materials Ontology\Ontology\substance_ontology.ttl')
OLD_FIXTURE=Path(json.loads((ROOT/'evaluation.json').read_text(encoding='utf8'))['fixture_database'])
P=BASE/'real_world_normalization/pilot_readonly_20261103'
META=json.loads((P/'sampling_manifest.json').read_text(encoding='utf8'))
packets={p['source_record_id']:p for p in (json.loads(line) for line in (P/'sampled_records.jsonl').read_text(encoding='utf8').splitlines())}
with (BASE/'chemical_concept_feasibility/record_evaluation.csv').open(encoding='utf-8-sig',newline='') as f: old={r['source_record_id']:r for r in csv.DictReader(f)}
with sqlite3.connect(PILOT.resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as db:
    states={sid:json.loads(result) for sid,result in db.execute('select original_substance_id,result_json from warehouse_pilot')}
rows=[]
for sid,prior in old.items():
    raw=packets[sid]['record'];sm=raw.get('isometric_smiles') or raw.get('jchem_smiles') or ''
    mol=Chem.MolFromSmiles(sm) if sm else None
    elements=set(a.GetSymbol() for a in mol.GetAtoms()) if mol else set()
    rows.append({'sid':sid,'prior':prior,'raw':raw,'smiles':sm,'elements':elements,'old_status':states[sid]['resolution_status']})
def order(row):return hashlib.sha256(('v11-eval-20261104:'+row['sid']).encode()).hexdigest()
rows.sort(key=order)
chosen=[];used=set();shortfalls={}
def take(label,n,pred):
    found=0
    for r in rows:
        if found>=n:break
        if r['sid'] not in used and pred(r):
            chosen.append((label,r));used.add(r['sid']);found+=1
    shortfalls[label]=n-found
take('previously_supported_open',10,lambda r:r['prior']['current_tool_test'].startswith('REPRESENTATION_SUPPORTED'))
take('fluorinated',10,lambda r:'F' in r['elements'])
take('chlorine_bromine_iodine',6,lambda r:bool({'Cl','Br','I'} & r['elements']))
take('sulfur',8,lambda r:'S' in r['elements'])
take('phosphorus_silicon_boron',5,lambda r:bool({'P','Si','B'} & r['elements']))
take('exact_pilot_admission',8,lambda r:r['old_status']=='NEW_SUBSTANCE_CREATED')
take('contradictory_claims',5,lambda r:r['prior']['meaning_category']=='CONFLICTING_ASSERTIONS')
take('multicomponent',5,lambda r:'.' in r['smiles'])
take('over_64',3,lambda r:r['prior']['current_tool_test']=='STEREO_ENUMERATION_LIMIT')
take('other_abstention',65-len(chosen),lambda r:r['old_status']!='NEW_SUBSTANCE_CREATED')
assert len(chosen)>=60
guards=[PILOT,SEED,ONTOLOGY,OLD_FIXTURE]
before={str(p):sha(p) for p in guards}
path=FIXTURES/('v11_eval_'+uuid.uuid4().hex+'.sqlite');registry=initialize(path)
bridge=Bridge(timeout=5);adapter=TrustedWarehouseAdapter(batch_file=P/'sampled_records.json',expected_sha256=META['source_json_sha256'])
router=UnifiedChemicalResolver(registry,RegistrySnapshot(PILOT),name_adapter=bridge,substance_resolver=SubstanceResolver(official_validator=bridge.official))
out=[]
try:
 for i,(stratum,r) in enumerate(chosen,1):
    result=router.resolve(packets[r['sid']],source_adapter=adapter,request_key='warehouse-v11:'+r['sid'],retrieval_policy=RetrievalPolicy(exhaustive=False,max_candidates=8,allow_exploratory_names=False))
    item=dict(source_id=r['sid'],stratum=stratum,name=r['raw'].get('substance_master_name_en',''),smiles=r['smiles'],elements=sorted(r['elements']),previous_pilot_outcome=r['old_status'],v1_capability=r['prior']['current_tool_test'],prior_assessment=r['prior']['meaning_category'],outcome=result['outcome'],concept_id=result['concept_id'],substance_id=result['substance_id'],diagnostics=result['diagnostics'],interpretation=result['interpretation'],validation=result['validation'],substance_comparisons=result['substance_comparisons'],concept_comparisons=result['concept_comparisons'],elapsed_seconds=result['elapsed_seconds'],evidence=result['evidence'],justification='Automated bounded interpretation only; no independent expert adjudication.')
    out.append(item)
    print(i,stratum,result['outcome'],result['elapsed_seconds'],flush=True)
finally:bridge.close()
after={str(p):sha(p) for p in guards}
assert before==after
with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
    integrity=db.execute('pragma integrity_check').fetchone()[0];fk=db.execute('pragma foreign_key_check').fetchall()
    concepts=db.execute('select count(*) from concept').fetchone()[0]
payload=dict(cohort_size=len(out),selection_seed='v11-eval-20261104',shortfalls=shortfalls,fixture_database=str(path),fixture_concept_count=concepts,fixture_integrity=integrity,fixture_foreign_key_errors=fk,protected_hashes_before=before,protected_hashes_after=after,outcomes=dict(Counter(x['outcome'] for x in out)),records=out)
(ROOT/'evaluation_v11.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print('DONE',json.dumps(payload['outcomes']),flush=True)
