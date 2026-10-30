"""Bounded public-provider characterization, with independently chosen examples."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from providers import PubChem,ChEBI,GSRS
from chemistry import describe
from evidence_retrieval import provenance
from evidence_model import assess
from form_characterizer import characterize
H=Path(__file__).resolve().parent
cases=[('ethanol','CCO'),('(R)-butan-2-ol','C[C@@H](O)CC'),('acetate','CC(=O)[O-]'),('sodium acetate','CC(=O)[O-].[Na+]'),('deuterium oxide','[2H]O[2H]'),('2-pyridone','O=c1cccc[nH]1')]
providers=[PubChem(H/'probe_pubchem',budget=6),ChEBI(H/'probe_chebi',budget=18,max_hits=2),GSRS(H/'probe_gsrs',budget=18,max_hits=2)]
output=[]
for adapter in providers:
    for name,s in cases:
        result=adapter.name(name); candidate=describe(s)
        key=dict(kind='name',value=name,origin='source_preferred_name',asserts_source_identity=True)
        found=[]
        for raw in result.get('rows',[]):
            row=provenance(raw,result,key);audit=assess(row,candidate)
            try:
                f=characterize(describe(row.get('SMILES') or row.get('IsomericSMILES') or ''))
                features={k:f[k] for k in ('stereo_state','isotopes','charge_distribution','component_count','tautomer_sensitive')}
            except (ValueError,RuntimeError):features=None
            found.append(dict(record_id=audit['record_id'],fields=[k for k in ('SMILES','IsomericSMILES','InChI','InChIKey') if row.get(k)],features=features,qualification=audit['state'],reason=audit['reason']))
        output.append(dict(provider=type(adapter).__name__,query=name,status=result['status'],records=found,excluded=result.get('excluded_records',[])))
        (H/'provider_probe.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
print('Completed',len(output),'bounded public-provider cases')
