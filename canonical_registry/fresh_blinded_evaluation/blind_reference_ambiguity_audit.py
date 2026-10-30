"""Read-only check of independent reference responses, without prediction access."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from rdkit import Chem
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
refs={r['cuma_index']:r for r in read(H/'reference_adjudication.json')}
sources=[('packet_1/independent_public_lookups.json',lambda x:x.get('pubchem',{}).get('body')),('packet_2/independent_lookup.json',lambda x:x.get('pubchem',{}).get('body')),('packet_3/public_lookup_results.json',lambda x:x.get('sources',{}).get('pubchem',{}).get('body'))]
flags=[];checked=0
for name,body in sources:
    for r in read(H/name):
        i=r['cuma_index']
        if refs[i]['reference_status']!='EXACT_REFERENCE_AVAILABLE':continue
        try:props=json.loads(body(r) or '{}').get('PropertyTable',{}).get('Properties',[])
        except (ValueError,TypeError):continue
        if not props:continue
        checked+=1;graphs=set()
        for p in props:
            s=p.get('SMILES') or p.get('IsomericSMILES');m=Chem.MolFromSmiles(s or '')
            if m:graphs.add(Chem.MolToSmiles(m,isomericSmiles=True,canonical=True))
        if len(props)>1:
            flags.append(dict(cuma_index=i,record_count=len(props),unique_parsed_graphs=len(graphs),different_graphs=len(graphs)>1))
out=dict(created_utc=datetime.now(timezone.utc).isoformat(),predictions_inspected=False,reference_labels_modified=False,exact_responses_checked=checked,multiple_record_responses=flags,note='A truncated or incomplete response cannot exclude additional records; missing responses are not evidence of uniqueness.')
p=H/'BLIND_SOURCE_AMBIGUITY_AUDIT.json';p.write_text(json.dumps(out,indent=2),encoding='utf-8')
print('Exact responses checked:',checked,'multiple-record responses:',len(flags),'different graphs:',sum(x['different_graphs'] for x in flags))
