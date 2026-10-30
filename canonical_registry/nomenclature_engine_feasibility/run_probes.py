"""Bounded public OPSIN probes, no network, no resolver or OPSIN mutation."""
import base64,json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
from rdkit import Chem
H=Path(__file__).resolve().parent;B=H.parent
sys.path.insert(0,str(B))
from chemistry import describe
from source_form import assess
jar=B.parent/'opsin-master/opsin-cli/target/opsin-cli-3.0-SNAPSHOT-jar-with-dependencies.jar'
def spec(name,issue,expect,source):return dict(input_name=name,selection_reason=issue,expected_source_claim=expect,grounding=source)
blue='https://iupac.qmul.ac.uk/BlueBook/P1.html';stereo='https://goldbook.iupac.org/terms/view/S05984';ionic='https://iupac.qmul.ac.uk/BlueBook/P7.html';taut='https://goldbook.iupac.org/terms/view/T06252'
cases=[
spec('1H-pyrazole','indicated H','Ring hydrogen locant 1 is explicitly written, subject to grammar scope.',blue),
spec('2H-pyrazole','indicated H contrast','Ring hydrogen locant 2 is explicitly written, subject to grammar scope.',blue),
spec('pyridin-2(1H)-one','added indicated H and lactam','Added indicated H and carbonyl suffix are explicit; inspect full molecule.',blue),
spec('pyridin-2-ol','lactim versus lactam','Hydroxy and lactam names are graph-distinct tautomeric descriptions.',taut),
spec('ethanoic acid','neutral acid','Acid functional group is specified; do not assume unrelated charge sites.',ionic),
spec('sodium ethanoate','ionic counterion','Source names an anionic acid derivative and sodium; exact component counts require validation.',ionic),
spec('ethane-1,2-diamine dihydrochloride','stoichiometric salt','Source uses dihydrochloride; trace counts and protonation independently.',ionic),
spec("2,2'-bipyridine",'primed repeated locants','Locants have distinct primed spelling; graph numbering can be generated.',blue),
spec('2-(2-hydroxyphenyl)ethanol','repeated 2 locants nested','The nested locant and parent locant require fragment scope.',blue),
spec('(2R)-butan-2-ol','specific stereo preferred','Explicit R at locant 2.',stereo),
spec('butan-2-ol','less-specific stereo alias','Name does not specify R or S.',stereo),
spec('(2S)-butan-2-ol','opposite stereo','Explicit S differs from R.',stereo),
spec('ethanol','specific alias control','Ethyl alcohol is a reported synonym; comparator must not use alias alone.', 'https://pubchem.ncbi.nlm.nih.gov/compound/ethanol'),
spec('methanol','specific incompatible alias control','Methanol has different molecular constitution from ethanol.', 'https://pubchem.ncbi.nlm.nih.gov/compound/methanol'),
spec('ethanol absolutely unconsumed garbage','malformed text','A valid name followed by arbitrary text is not a complete chemical name.',blue),
spec('triazine','unlocanted heterocycle ambiguity/default','Source does not supply ring-heteroatom locants; inspect warnings and generated numbering.',blue),
]
extra=[(17504,'1-methyl 2-aminoterephthalate'),(4373,'3-Methyl-4-phenylpyrazole'),(30832,'Benzyl acetoacetate'),(5684,'1,1-Cyclopropane dimethanol cyclic sulphate'),(5997,'1-N-BOC-1,2-TRANS-CYCLOHEXYLDIAMINE'),(30142,'D-glucose 6-phosphate disodiumsalt dihydrate'),(5,'5-Amino-3H-1,2,4-dithiazole-3-thione')]
for i,n in extra:cases.append(dict(**spec(n,'historical source safety probe','Existing policy requires abstention; no probe grants EXACT.',blue),record_id=i))
extra81=[(8165,'2-ethyl-5-nitroaniline'),(18118,'1-phenyl-6,7-dihydro-1H-indol-4(5H)-one'),(11113,'Dimethyl terephthalate')]
for i,n in extra81:cases.append(dict(**spec(n,'representative diagnostic hold','Explore output only; a graph or locant does not establish source support.',blue),record_id=i))
subprocess.run(['javac','-cp',str(jar),'-d',str(H),str(H/'Probe.java')],check=True)
payload=''.join(base64.b64encode(c['input_name'].encode()).decode()+'\n' for c in cases)
p=subprocess.run(['java','-cp',str(H)+';'+str(jar),'Probe'],input=payload,text=True,capture_output=True,timeout=120,check=True)
lines=p.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases),p.stderr)
keys=['version','status','message','warnings','ambiguity_flag','stereo_ignored','smiles','cxsmiles','cml','standard_inchi','nonstandard_inchi']
for c,line in zip(cases,lines):
    fields=line.split('\t')
    if fields[0]=='ERROR':c['raw_output']={'error':base64.b64decode(fields[1]).decode()};continue
    assert len(fields)==len(keys)
    raw={k:base64.b64decode(v).decode('utf8') for k,v in zip(keys,fields)};c['raw_output']=raw
    labels=[]
    if raw['cml']:
        root=ET.fromstring(raw['cml']);ns={'c':'http://www.xml-cml.org/schema'}
        for a in root.findall('.//c:atom',ns):
            ls=[l.get('value') for l in a.findall('c:label',ns) if l.get('dictRef','').endswith(':locant')]
            if ls:labels.append(dict(cml_atom=a.get('id'),element=a.get('elementType'),locants=ls))
    c['cml_locants']=labels
    m=Chem.MolFromSmiles(raw['cxsmiles']) if raw['cxsmiles'] else None
    c['rdkit_cx_atom_properties']=[dict(index=a.GetIdx(),properties={p:a.GetProp(p) for p in a.GetPropNames(includePrivate=False)}) for a in m.GetAtoms() if list(a.GetPropNames(includePrivate=False))] if m else []
    c['engine']='OPSIN local installed 3.0-SNAPSHOT, default configuration';c['mapping']='public atom locants / CML only; source owner and raw spans not established';c['explicit_vs_default']='not distinguished by public output';c['safe_conclusion']='Candidate and output labels are observations only; no source identity or eligibility inferred.'
    c['limitations']='No descriptor-to-fragment ownership, raw source span, complete alternative-parse enumeration or source-atom correspondence established.'
byname={x['input_name']:x for x in cases}
alias_tests=[]
for alias in ('butan-2-ol','(2S)-butan-2-ol'):
    preferred='(2R)-butan-2-ol';a=byname[preferred]['raw_output']['smiles'];b=byname[alias]['raw_output']['smiles'];da,db=describe(a),describe(b)
    result=assess(preferred,dict(status='SUCCESS',structure=da),[(alias,dict(status='SUCCESS',structure=db))],da)
    alias_tests.append(dict(preferred=preferred,alias=alias,source_form_status=result['status'],reason_codes=result['reason_codes'],source_claim_conflicts=result['source_claim_conflicts'],qualification='local helper experiment only; no final resolver admission',grounding=stereo))
out={'local_engine_jar':str(jar),'probe_count':len(cases),'cases':cases,'alias_pair_tests':alias_tests,'stderr':p.stderr,'network_requests':0}
(B/'engine_probe_results.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf8')
print('Saved',len(cases),'public OPSIN probes')
