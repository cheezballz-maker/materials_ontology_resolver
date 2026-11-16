"""Unified read-only resolution and optional marked disposable persistence."""
import argparse,json,socket,sys
from dataclasses import asdict
from pathlib import Path
import bootstrap
from providers import Bridge
from fixture_registry import FixturePermit,create_fixture,connect
from unified_resolver import SubstanceResolver
from registry_matching_models import RetrievalPolicy

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True,type=Path);p.add_argument('--source-type',choices=('pubchem','chebi','qualified'));p.add_argument('--registry',type=Path,default=Path(__file__).resolve().parent.parent/'output/registry.sqlite');p.add_argument('--persist',action='store_true');p.add_argument('--permit-file',type=Path,help='Private *.permit.json capability: created once, reused for subsequent calls');p.add_argument('--output',type=Path);p.add_argument('--verbosity',choices=('full','summary'),default='full');p.add_argument('--indexed-only',action='store_true');p.add_argument('--max-candidates',type=int);p.add_argument('--no-official-validation',action='store_true');p.add_argument('--allow-creation',action='store_true');p.add_argument('--creation-permit-file',type=Path,help='Separate private *.permit.json capability, disposable creation only');a=p.parse_args()
 if a.allow_creation and (not a.persist or not a.creation_permit_file):p.error('--allow-creation requires --persist and a separate --creation-permit-file')
 if a.creation_permit_file and not a.creation_permit_file.name.endswith('.permit.json'):p.error('Creation capability must use private *.permit.json suffix')
 paths=[p.resolve() for p in (a.output,a.permit_file,a.creation_permit_file) if p]
 if len(paths)!=len(set(paths)):p.error('Result and private capability paths must all differ')
 creation=None
 if a.output and (a.output.exists() or a.output.suffix!='.json'):p.error('Output must be a new .json file')
 if a.output and a.permit_file and a.output.resolve()==a.permit_file.resolve():p.error('Result output and private capability file must be different paths')
 record=json.loads(a.input.read_text(encoding='utf-8-sig'));source=a.source_type or record.get('source_type') or record.get('provider','qualified').lower();registry=a.registry
 socket.create_connection=lambda *args,**kw: (_ for _ in ()).throw(RuntimeError('LIVE_PROVIDER_NETWORK_DISABLED'))
 if a.persist:
  if not a.permit_file or not a.permit_file.name.endswith('.permit.json'):p.error('--persist requires a private *.permit.json capability path')
  if a.permit_file.exists():
   raw=json.loads(a.permit_file.read_text());registry=FixturePermit(Path(raw['path']),raw['fixture_id'],raw['token']);d=connect(registry);d.close()
  else:
   if a.allow_creation:
    if a.creation_permit_file.exists():p.error('Existing creation capability needs its original association capability')
    sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'canonical_substance_creation'))
    from creation_authorization import create_creation_fixture
    creation=create_creation_fixture(a.registry);registry=creation.association
    a.creation_permit_file.write_text(json.dumps({'fixture_id':registry.fixture_id,'path':str(registry.path),'creation_token':creation.creation_token},indent=2)+'\n',encoding='utf8')
   else:registry=create_fixture(a.registry)
   a.permit_file.write_text(json.dumps({**asdict(registry),'path':str(registry.path)},indent=2)+'\n',encoding='utf8')
 if a.allow_creation and creation is None:
  sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'canonical_substance_creation'))
  from creation_authorization import CreationPermit,connect_creation
  if not a.creation_permit_file.exists():p.error('Association-only fixtures cannot be upgraded; supply a fresh pair of capability paths')
  raw=json.loads(a.creation_permit_file.read_text())
  if raw['fixture_id']!=registry.fixture_id or Path(raw['path']).resolve()!=registry.path.resolve():p.error('Capabilities refer to different fixtures')
  creation=CreationPermit(registry,raw['creation_token']);d=connect_creation(creation);d.close()
 bridge=None if a.no_official_validation else Bridge()
 try:result=SubstanceResolver(official_validator=bridge.official if bridge else None).resolve(record,source,registry,persist_association=a.persist,retrieval_policy=RetrievalPolicy(exhaustive=not a.indexed_only,max_candidates=a.max_candidates),diagnostic_verbosity=a.verbosity,allow_creation=a.allow_creation,creation_authorization=creation)
 finally:
  if bridge:bridge.close()
 output=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
 if a.output:a.output.write_text(output,encoding='utf8')
 else:print(output,end='')
 print(f"{result['resolution_status']}; canonical={result['canonical_substance_id']}; association={result['association']['status']}",file=sys.stderr)
 return 2 if result.get('error') else 0
if __name__=='__main__':raise SystemExit(main())
