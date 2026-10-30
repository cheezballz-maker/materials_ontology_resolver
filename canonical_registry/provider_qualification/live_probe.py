"""Bounded non-CUMA CTX probe; no credentials enter output or URLs."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from comptox import CompTox
from chemistry import describe
from evidence_retrieval import provenance
from evidence_model import assess
from form_characterizer import characterize

root=Path(__file__).resolve().parent
adapter=CompTox(root/'live_cache',budget=12,timeout=12)
cases=[('Toluene','Cc1ccccc1'),('Ethanol','CCO'),('Sodium acetate','CC(=O)[O-].[Na+]'),('Deuterium oxide','[2H]O[2H]'),('2-Pyridone','O=c1cccc[nH]1')]
rows=[]
for name,smiles in cases:
    result=adapter.name(name);candidate=describe(smiles)
    key=dict(kind='name',value=name,origin='source_preferred_name',asserts_source_identity=True)
    found=[]
    for row in result.get('rows',[]):
        row=provenance(row,result,key); a=assess(row,candidate);f=characterize(describe(row['SMILES']))
        details=[x.get('data',{}) for x in result.get('retrieval',[]) if isinstance(x.get('data'),dict) and x['data'].get('dtxsid')==row.get('DTXSID')]
        provider_fields=[k for k in ('smiles','smilesString','inchiString','inchikey') if any(v.get(k) for v in details)]
        found.append(dict(DTXSID=row.get('DTXSID'),DTXCID=row.get('DTXCID'),provider_fields=provider_fields,identifier_origin=row.get('identifier_origin'),features={k:f[k] for k in ('stereo_state','isotopes','charge_distribution','component_count','tautomer_sensitive')},qualification=a['state'],reason=a['reason'],comparison=a.get('comparison')))
    rows.append(dict(query=name,route='exact name',status=result['status'],records=found))
(root/'live_probe.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(dict(cases=len(rows),requests=adapter.calls,statuses=[r['status'] for r in rows])))
