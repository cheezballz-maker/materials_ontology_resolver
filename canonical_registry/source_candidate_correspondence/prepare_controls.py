"""Freeze independently specified references and expectations before runtime work."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
 for n in ('controls','evaluation'):(H/n).mkdir(exist_ok=True)
 if (H/'controls/benchmark_freeze.json').exists():raise SystemExit('Frozen controls already exist; no overwrite')
 refs=['https://iupac.qmul.ac.uk/BlueBook/P6.html','https://iupac.qmul.ac.uk/BlueBook/P7.html','https://iupac.qmul.ac.uk/BlueBook/P8.html','https://iupac.qmul.ac.uk/BlueBook/P9.html#P-93.1','https://www.rdkit.org/docs/source/rdkit.Chem.rdmolops.html']
 # Literal reference definitions are authored here, not generated from any
 # incoming record, normalized source structure, cache or parser result.
 definitions={
 'REF_ETHANOL':('ethanol','OCC'),'REF_ETHER':('dimethyl ether','COC'),
 'REF_BENZENE':('benzene Kekule','C1=CC=CC=C1'),
 'REF_NITRO':('nitrobenzene','c1ccc(cc1)[N+]([O-])=O'),
 'REF_R_BUTANOL':('specified butan-2-ol configuration A','CC[C@@H](O)C'),
 'REF_S_BUTANOL':('opposite butan-2-ol configuration B','CC[C@H](O)C'),
 'REF_UNSPEC_BUTANOL':('unspecified butan-2-ol','CCC(C)O'),
 'REF_ACID':('acetic acid','OC(=O)C'),'REF_ACETATE':('acetate','[O-]C(C)=O'),
 'REF_LACTAM':('explicit pyridone lactam','O=C1C=CC=CN1'),
 'REF_LACTIM':('explicit hydroxypyridine lactim','Oc1ncccc1'),
 'REF_C13_TERMINAL':('terminal carbon-13 ethanol','OC[13CH3]'),
 'REF_C13_CARBI':('carbinol carbon-13 ethanol','O[13CH2]C'),
 'REF_D2O':('explicit dideuterium oxide','[2H]O[2H]'),
 'REF_H1_WATER':('explicit protium water','[1H]O[1H]'),
 'REF_WATER':('conventionally unlabelled water','O'),
 'REF_METHYLAMINE':('methylamine','NC'),
 'REF_METHYLAMMONIUM_CHLORIDE':('defined 1:1 methylammonium chloride','[Cl-].[NH3+]C'),
 'REF_ETHANOL_WATER_1':('explicit 1:1 ethanol/water molecular composition','O.CCO'),
 'REF_ETHANOL_WATER_2':('explicit 1:2 ethanol/water molecular composition','O.O.CCO'),
 'REF_META_BROMOCHLORO':('1-bromo-3-chlorobenzene','Clc1cccc(Br)c1'),
 'REF_PARA_BROMOCHLORO':('1-bromo-4-chlorobenzene','Clc1ccc(Br)cc1'),
 'REF_METHANOL':('methanol','OC'),
 'REF_PROPANOL':('propan-1-ol','OCCC'),
 'REF_ISOPROPANOL':('propan-2-ol','OC(C)C'),
 'REF_DEUT_METHANOL':('carbon-monodeuterated methanol','OC[2H]'),
 'REF_E_BUTENE':('E-but-2-ene','C/C=C/C'),
 'REF_Z_BUTENE':('Z-but-2-ene','C/C=C\\C'),
 'REF_ZWITTERION':('explicit glycine zwitterion','[O-]C(=O)C[NH3+]'),
 'REF_NEUTRAL_GLYCINE':('explicit neutral glycine graph','OC(=O)CN'),
 'REF_METHANE':('methane','C'),'REF_METHYL_RADICAL':('methyl radical','[CH3]'),
 }
 inventory=[]
 for key,(name,smiles) in definitions.items():
  inventory.append(dict(candidate_substance_id=key,preferred_name=name,structure=smiles,identity_scope='DEFINED_MULTICOMPONENT_COMPOSITION' if '.' in smiles else 'DISCRETE_MOLECULAR',provenance=dict(definition_kind='INDEPENDENT_REFERENCE_DEFINITION',document='Frozen separately authored reference inventory; not from incoming source',references=refs,lineage_roots=['REFERENCE_INVENTORY:'+key],independence_status='ESTABLISHED_FOR_CONTROL_DEFINITION',derived_from_source_concepts=[],review_status='CHEMICAL_REVIEW_PENDING')))
 def claim(smiles=None,kind='structure',**kw):return dict(kind=kind,structure=smiles,**kw)
 S='CORRESPONDENCE_SUPPORTED';D='CORRESPONDENCE_DIFFERENT';U='CORRESPONDENCE_UNRESOLVED';X='SOURCE_CONFLICT'
 def case(i,label,source,candidates,expected,summary,dimensions=None,**kw):
  claims=source if isinstance(source,list) else [claim(source)]
  return dict(id=i,description=label,source=dict(source_concept_id='INCOMING:'+i,claims=claims,identity_scope=kw.pop('identity_scope','DEFINED_MULTICOMPONENT_COMPOSITION' if any('.' in (c.get('structure') or '') for c in claims) else 'DISCRETE_MOLECULAR'),link_status=kw.pop('link_status','ESTABLISHED'),link_kind=kw.pop('link_kind','EXPLICIT_SOURCE_ASSERTION'),provenance=dict(document='Separate incoming control definition',lineage_roots=['INCOMING_CONTROL:'+i],references=refs,review_status='CHEMICAL_REVIEW_PENDING')),candidate_ids=candidates,expected_candidate_statuses=expected,expected_set_summary=summary,expected_dimensions=dimensions or {},scientific_justification=label,evidence_independence='Reference inventory is independently authored literal input; no source-normalized graph is used to define candidates. Not blinded or human-certified.',review_status='CHEMICAL_REVIEW_PENDING',**kw)
 unique='UNIQUE_SUPPORTED_CANDIDATE';none='NO_SUPPORTED_CANDIDATE_IN_SET';unres='SOURCE_IDENTITY_UNRESOLVED';conf='SOURCE_IDENTITY_CONFLICT'
 dev=[
 case('D01','equivalent complete ethanol graph','CCO',['REF_ETHANOL'],[S],unique,{'constitution':'EXACT_COMPATIBLE'}),
 case('D02','conventional name with explicit independently annotated identity',[claim('CCO','annotated_name',original='ethyl alcohol',annotation_document='IUPAC functional-class alcohol nomenclature; complete identity annotation supplied as evidence')],['REF_ETHANOL'],[S],unique),
 case('D03','aromatic versus Kekule','c1ccccc1',['REF_BENZENE'],[S],unique),
 case('D04','equivalent nitro representation','O=[N+]([O-])c1ccccc1',['REF_NITRO'],[S],unique),
 case('D05','matching specified stereo','C[C@H](O)CC',['REF_R_BUTANOL'],[S],unique,{'stereochemistry':'EXACT_COMPATIBLE'}),
 case('D06','matching labelled carbon','[13CH3]CO',['REF_C13_TERMINAL'],[S],unique),
 case('D07','same defined multicomponent salt','C[NH3+].[Cl-]',['REF_METHYLAMMONIUM_CHLORIDE'],[S],unique),
 case('D08','constitutional isomer','CCO',['REF_ETHER'],[D],none,{'constitution':'EXACT_INCOMPATIBLE'}),
 case('D09','positional isomer','Brc1cccc(Cl)c1',['REF_PARA_BROMOCHLORO'],[D],none,{'constitution':'EXACT_INCOMPATIBLE'}),
 case('D10','opposite stereoisomer','C[C@H](O)CC',['REF_S_BUTANOL'],[D],none,{'stereochemistry':'EXACT_INCOMPATIBLE'}),
 case('D11','acid versus conjugate base','CC(=O)O',['REF_ACETATE'],[D],none,{'protonation_charge':'EXACT_INCOMPATIBLE'}),
 case('D12','explicit tautomer contrast','O=c1cccc[nH]1',['REF_LACTIM'],[D],none,{'tautomer':'EXACT_INCOMPATIBLE'}),
 case('D13','different carbon isotope position','[13CH3]CO',['REF_C13_CARBI'],[D],none,{'isotope':'EXACT_INCOMPATIBLE'}),
 case('D14','free compound versus salt','CN',['REF_METHYLAMMONIUM_CHLORIDE'],[D],none,{'components':'EXACT_INCOMPATIBLE'}),
 case('D15','explicit water component ratio','CCO.O',['REF_ETHANOL_WATER_2'],[D],none,{'component_stoichiometry':'EXACT_INCOMPATIBLE'}),
 case('D16','stereo unspecified source graph','CC(O)CC',['REF_R_BUTANOL'],[U],unres),
 case('D17','tautomer unspecified source constraint',[claim('Oc1ccccn1',unknown_dimensions=['tautomer'])],['REF_LACTIM'],[U],unres),
 case('D18','broad polymer family',[claim(None,'unknown',original='polyethylene family')],['REF_ETHANOL'],[U],unres,identity_scope='FAMILY'),
 case('D19','unsupported name',[claim(None,'name',original='unknown alkxq')],['REF_ETHANOL'],[U],unres),
 case('D20','unvalidated source identifier',[claim(None,'identifier',original='64-17-5')],['REF_ETHANOL'],[U],unres),
 case('D21','original-form standardization implications unresolved','CCO',['REF_ETHANOL'],[U],unres,link_status='UNESTABLISHED',link_kind='ORIGINAL_MATERIAL_TO_STANDARDIZED_RECORD'),
 case('D22','partial component identity',[claim('C[NH3+].[Cl-]',unknown_dimensions=['components','component_stoichiometry','hydration_solvation'])],['REF_METHYLAMMONIUM_CHLORIDE'],[U],unres),
 case('D23','two contradictory explicit source structures',[claim('CCO'),claim('COC')],['REF_ETHANOL'],[X],conf),
 case('D24','opposite exact source stereo claims',[claim('C[C@H](O)CC'),claim('C[C@@H](O)CC')],['REF_R_BUTANOL'],[X],conf),
 case('D25','incompatible independently mapped source identifiers',[claim('CCO','validated_identifier',original='control:identifierA'),claim('COC','validated_identifier',original='control:identifierB')],['REF_ETHANOL'],[X],conf),
 case('D26','conflicting annotated exact names',[claim('CCO','annotated_name',original='ethanol'),claim('COC','annotated_name',original='dimethyl ether')],['REF_ETHANOL'],[X],conf),
 case('D27','one supported among distinct candidates','CCO',['REF_ETHER','REF_ETHANOL','REF_METHANOL'],[D,S,D],unique),
 case('D28','duplicate equivalent reference candidate records','CCO',['REF_ETHANOL','REF_ETHANOL_DUPLICATE'],[S,S],'MULTIPLE_SUPPORTED_CANDIDATES'),
 case('D29','multiple unresolved candidate states','CC(O)CC',['REF_R_BUTANOL','REF_S_BUTANOL'],[U,U],unres),
 case('D30','no candidates supplied','CCO',[],[],none),
 case('D31','source-derived candidate must not corroborate','CCO',['SOURCE_DERIVED_DUPLICATE'],[U],unres),
 case('D32','explicit heavy versus explicitly protiated water','[2H]O[2H]',['REF_H1_WATER'],[D],none,{'isotope':'EXACT_INCOMPATIBLE'}),
 case('D33','heavy versus conventional unlabelled represented water','[2H]O[2H]',['REF_WATER'],[D],none,{'isotope':'EXACT_INCOMPATIBLE'}),
 case('D34','ordinary explicit versus implicit H representation','[H]O[H]',['REF_WATER'],[S],unique,{'constitution':'EXACT_COMPATIBLE','isotope':'EXACT_COMPATIBLE'}),
 case('D35','isotope scope unestablished in source name',[claim('O','annotated_name',original='water with isotope scope expressly unspecified',unknown_dimensions=['isotope'])],['REF_D2O'],[U],unres),
 case('D36','isotopic and constitutional distinction','[13CH3]CO',['REF_ETHER'],[D],none,{'constitution':'EXACT_INCOMPATIBLE','isotope':'EXACT_INCOMPATIBLE'}),
 case('D37','known reported association outside structural referent',[claim('CCO'),claim(None,'association',original='supplier search term')],['REF_ETHANOL'],[S],unique),
 case('D38','unknown potentially binding alias remains active',[claim('CCO'),claim(None,'unknown',original='potential exact alias')],['REF_ETHANOL'],[U],unres),
 case('D39','candidate-derived source observation is not source specificity',[claim('CCO',origin='CANDIDATE_DERIVED')],['REF_ETHANOL'],[U],unres),
 case('D40','dot components without entity scope','CCO.O',['REF_ETHANOL_WATER_1'],[U],unres,identity_scope='UNESTABLISHED_COMPONENT_KIND'),
 case('D41','registry key insufficient for tautomer',[claim('O=c1cccc[nH]1')],['REF_LACTIM'],[D],none),
 ]
 held=[
 case('H01','new constitutional contrast','CCCO',['REF_ISOPROPANOL'],[D],none),
 case('H02','alternate isotope-labelled graph encoding','[H]C([2H])([H])O',['REF_DEUT_METHANOL'],[S],unique),
 case('H03','equivalent isotope-labelled water encoding','O([2H])[2H]',['REF_D2O'],[S],unique),
 case('H04','same explicit lactam graph','O=c1cccc[nH]1',['REF_LACTAM'],[S],unique),
 case('H05','E versus Z stereochemistry','C/C=C/C',['REF_Z_BUTENE'],[D],none,{'stereochemistry':'EXACT_INCOMPATIBLE'}),
 case('H06','explicit neutral versus zwitterionic hydrogen placement','NCC(=O)O',['REF_ZWITTERION'],[D],none,{'protonation_charge':'EXACT_INCOMPATIBLE'}),
 case('H07','explicit hydration composition difference','CCO',['REF_ETHANOL_WATER_1'],[D],none),
 case('H08','same complete acetate resonance depiction','CC([O-])=O',['REF_ACETATE'],[S],unique),
 case('H09','no exact name to graph link','CCO',['REF_ETHANOL'],[U],unres,link_status='UNESTABLISHED',link_kind='ASSOCIATED_NAME_MEMBERSHIP'),
 case('H10','source conflict with no candidates',[claim('CO'),claim('CCO')],[],[],conf),
 case('H11','supported and unresolved candidate prevents unique conclusion','CCO',['REF_ETHANOL','UNQUALIFIED_CANDIDATE'],[S,U],'CANDIDATE_SET_AMBIGUOUS'),
 case('H12','specified source and stereo-unspecified candidate','C[C@H](O)CC',['REF_UNSPEC_BUTANOL'],[U],unres),
 case('H13','missing chemical provenance',[claim('CO',unverified=True)],['REF_METHANOL'],[U],unres),
 case('H14','electronic radical distinction','[CH3]',['REF_METHANE'],[D],none,{'electronic_state':'EXACT_INCOMPATIBLE'}),
 ]
 # Derived and duplicate candidate cases have explicit provenance semantics.
 dup=json.loads(json.dumps(inventory[0]));dup['candidate_substance_id']='REF_ETHANOL_DUPLICATE';dup['structure']='C(C)O';dup['provenance']['lineage_roots']=['REFERENCE_INVENTORY:ETHANOL_DUPLICATE'];inventory.append(dup)
 derived=json.loads(json.dumps(inventory[0]));derived['candidate_substance_id']='SOURCE_DERIVED_DUPLICATE';derived['provenance'].update(independence_status='SOURCE_DERIVED',derived_from_source_concepts=['INCOMING:D31'],lineage_roots=['INCOMING_CONTROL:D31']);inventory.append(derived)
 unknown=json.loads(json.dumps(inventory[0]));unknown['candidate_substance_id']='UNQUALIFIED_CANDIDATE';unknown['provenance']['independence_status']='UNESTABLISHED';unknown['provenance']['lineage_roots']=['UNESTABLISHED:CANDIDATE'];inventory.append(unknown)
 for name,o in [('candidate_reference_inventory.json',{'candidates':inventory,'review':'CHEMICAL_REVIEW_PENDING'}),('development_controls.json',{'cases':dev,'blinding':'PUBLIC_FROZEN_NOT_BLINDED'}),('heldout_controls.json',{'cases':held,'blinding':'PUBLIC_FROZEN_NOT_BLINDED'})]:write(H/'controls'/name,o)
 write(H/'controls/benchmark_freeze.json',{'phase':'PRE_IMPLEMENTATION','files':{n:sha(H/'controls'/n) for n in ('candidate_reference_inventory.json','development_controls.json','heldout_controls.json')}})
 previous=json.loads((B/'source_evidence_adapters/evaluation/protected_input_freeze.json').read_text())['files'];paths={Path(n) for n in previous}|set((B/'source_evidence_adapters').rglob('*.py'))|set((B/'source_evidence_adapters').rglob('*.json'))|{B/'SOURCE_EVIDENCE_ADAPTER_AND_CLAIM_ROLE_V1_REPORT.md',B/'SOURCE_INDEPENDENT_IDENTITY_EVIDENCE_RECONCILIATION_V1_REPORT.md',B/'CHARGE_DIMENSION_EVIDENCE_V1_REPORT.md'}
 write(H/'evaluation/protected_input_freeze.json',{'files':{str(p.resolve()):sha(p) for p in sorted(paths) if p.is_file()},'provider_calls_allowed':0})
 print(f'Frozen {len(dev)} development + {len(held)} public held-out cases and {len(inventory)} independently defined/reference-boundary candidates')
if __name__=='__main__':main()
