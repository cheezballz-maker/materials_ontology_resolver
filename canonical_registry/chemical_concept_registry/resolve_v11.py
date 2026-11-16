"""CLI demonstration; all concept writes are restricted to marked fixtures."""
import argparse,json,uuid
from pathlib import Path
from registry import BASE,FIXTURES,Registry,initialize
from unified_chemical import UnifiedChemicalResolver
from providers import Bridge

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--smiles');p.add_argument('--name');p.add_argument('--inchikey')
    p.add_argument('--fixture',help='Existing marked fixture filename; otherwise creates a disposable fixture')
    p.add_argument('--read-only-concepts',action='store_true')
    p.add_argument('--request-key',default='cli-'+uuid.uuid4().hex)
    a=p.parse_args()
    if not (a.smiles or a.name):p.error('supply --smiles and/or --name')
    registry=Registry(FIXTURES/a.fixture) if a.fixture else initialize(FIXTURES/('v11_cli_'+uuid.uuid4().hex+'.sqlite'))
    bridge=Bridge() if a.name else None
    try:
        source={k:v for k,v in {'smiles':a.smiles,'name':a.name,'inchikey':a.inchikey}.items() if v}
        result=UnifiedChemicalResolver(registry,BASE/'output/registry.sqlite',name_adapter=bridge).resolve(source,request_key=a.request_key,create_concept=not a.read_only_concepts)
        print(json.dumps({'fixture':str(registry.path),'result':result},indent=2,ensure_ascii=False))
    finally:
        if bridge:bridge.close()
if __name__=='__main__':main()
