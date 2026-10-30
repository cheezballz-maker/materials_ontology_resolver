"""One-time, pre-implementation benchmark and protected-input freeze. No network."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent; B=H.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
 for n in ('controls','evaluation'):(H/n).mkdir(exist_ok=True)
 target=H/'controls/benchmark_freeze.json'
 if target.exists():raise SystemExit('Already frozen: refusing to replace controls')
 refs=['https://support.nlm.nih.gov/knowledgebase/article/KA-03387/en-us','https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest','https://pmc.ncbi.nlm.nih.gov/articles/PMC11181558/','https://iupac.qmul.ac.uk/BlueBook/P7.html','https://iupac.qmul.ac.uk/BlueBook/P8.html','https://iupac.qmul.ac.uk/BlueBook/P9.html#P-93.1']
 def field(kind,value,**kw):return dict(kind=kind,value=value,**kw)
 def case(i,title,fields,candidate,expected,scope='RECORD_STRUCTURE',dims=None,role=None,why=None,roots=None):
  return dict(id=i,description=title,input_source_record=dict(source='IndependentControls',record_id=i,fields=fields),candidate=candidate,scope=scope,required_dimensions=dims or ['constitution'],expected_result=expected,expected_first_role=role or 'STRUCTURAL_IDENTITY_ASSERTION',expected_dependency_roots=roots,chemical_justification=why or title,field_provenance='Annotated synthetic typed source fields with explicit document and payload pointer; not real database records.',review_status='CHEMICAL_REVIEW_PENDING',references=refs)
 S=lambda s:field('structure',s)
 C='RECONCILED_COMPATIBLE';U='RECONCILIATION_UNRESOLVED';X='RECONCILIATION_CONFLICT'
 dev=[
 case('D01','neutral graph',[S('CCO')],'OCC',C),
 case('D02','specified stereo',[S('C[C@H](O)CC')],'C[C@H](O)CC',C,dims=['stereochemistry']),
 case('D03','unspecified stereo',[S('CC(O)CC')],'C[C@H](O)CC',U,dims=['stereochemistry']),
 case('D04','isotope label retained',[S('[13CH3]CO')],'CCO',X,dims=['isotope']),
 case('D05','tautomer not normalized',[S('O=c1cccc[nH]1')],'Oc1ccccn1',X,dims=['tautomer']),
 case('D06','acid vs base',[S('CC(=O)O')],'CC(=O)[O-]',X,dims=['protonation_charge']),
 case('D07','salt components retained',[S('C[NH3+].[Cl-]')],'CN',X,dims=['components']),
 case('D08','explicit water component, no phase inference',[S('CCO.O')],'CCO',X,dims=['hydration_solvation']),
 case('D09','record identifier has no graph proof',[field('record_identifier','123')],'CCO',U,role='REFERENCE_CROSS_LINK'),
 case('D10','computed key dependent',[S('CCO'),field('derived_key','LFQSCWFLJHTTHZ-UHFFFAOYSA-N',depends_on=0)],'CCO',C,roots=1),
 case('D11','independent supplied InChI retains limited dimensions',[field('inchi','InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3',independent=True)],'CCO',C,role='STRUCTURAL_IDENTIFIER'),
 case('D12','CAS-like synonym is unvalidated',[S('CCO'),field('association','64-17-5')],'CCO',U,scope='TERMINOLOGY'),
 case('D13','qualified identifier with explicit independent graph',[S('CCO'),field('validated_mapping','external:test',smiles='COC',mapping_document='control:explicit-independent-association',independent=True)],'CCO',X),
 case('D14','NSC001 source interpretation compatible',[S('Cn1cccn1'),field('name','1-methyl-1H-pyrazole')],'Cn1cccn1',C,scope='TERMINOLOGY'),
 case('D15','NSC002 source interpretation contradiction',[S('Brc1ccc(Cl)cc1'),field('name','1-bromo-3-chlorobenzene')],'Brc1ccc(Cl)cc1',X,scope='TERMINOLOGY'),
 case('D16','explicitly broad annotated stereo name',[S('C[C@H](O)CC'),field('annotated_name','butan-2-ol',state='UNSPECIFIED',dimension='stereochemistry',framework='CC(O)CC')],'C[C@H](O)CC',C,scope='TERMINOLOGY',dims=['stereochemistry']),
 case('D17','broad claim alone cannot select stereo',[field('annotated_name','butan-2-ol',state='UNSPECIFIED',dimension='stereochemistry',framework='CC(O)CC')],'C[C@H](O)CC',U,scope='TERMINOLOGY',dims=['stereochemistry'],role='PARTIAL_IDENTITY_ASSERTION'),
 case('D18','unverified depositor synonym retained but separate scope',[S('CCO'),field('association','arbitrary supplier label')],'CCO',C),
 case('D19','same association unresolved in terminology',[S('CCO'),field('association','arbitrary supplier label')],'CCO',U,scope='TERMINOLOGY'),
 case('D20','unparseable binding name not metadata',[S('CCO'),field('name','nonsense alkxq')],'CCO',U,scope='TERMINOLOGY'),
 case('D21','generated unsupported name is dependent, not proof',[S('CCO'),field('generated_name','ethanol',depends_on=0)],'CCO',C,roots=1),
 case('D22','unknown source role remains active',[S('CCO'),field('unknown','potential identity name')],'CCO',U),
 case('D23','two independent structures contradict',[S('CCO'),S('COC')],'CCO',X,roots=2),
 case('D24','dependent source graph has one root',[S('CCO'),field('structure','OCC',depends_on=0)],'CCO',C,roots=1),
 case('D25','missing provenance',[field('structure','CCO',missing_provenance=True)],'CCO',U,role='UNKNOWN_ROLE'),
 case('D26','circular derivation cannot corroborate',[field('structure','CCO',depends_on=1),field('structure','OCC',depends_on=0)],'CCO',U),
 case('D27','incorrect derived key is unresolved inconsistency',[S('CCO'),field('derived_key','LCGLNKUTAGEVQW-UHFFFAOYSA-N',depends_on=0)],'CCO',U),
 case('D28','NSC002 neutral nitro charge producer',[field('name','1-chloro-2-nitrobenzene',charge=True)],'Clc1ccccc1[N+](=O)[O-]',C,scope='TERMINOLOGY',dims=['constitution','protonation_charge'],role='PARTIAL_IDENTITY_ASSERTION'),
 case('D29','unsupported charge stays unknown',[field('name','nitrobenzene',charge=True)],'c1ccccc1[N+](=O)[O-]',U,scope='TERMINOLOGY',dims=['protonation_charge'],role='CHEMICAL_NAME_ASSERTION'),
 case('D30','valid structure prefix garbage rejected',[S('CCO arbitrary')],'CCO',U),
 case('D31','candidate-derived name cannot corroborate',[field('name','1-bromo-3-chlorobenzene',candidate_derived=True)],'Brc1cccc(Cl)c1',U,scope='TERMINOLOGY',role='PARTIAL_IDENTITY_ASSERTION'),
 ]
 held=[
 case('H01','other constitutional isomer',[S('CCCO')],'CC(C)O',X),
 case('H02','other isotope',[S('[2H]O[2H]')],'O',X,dims=['isotope']),
 case('H03','component multiplicity',[S('[Na+].[Na+].[O-]C(=O)C(=O)[O-]')],'[Na+].[O-]C(=O)C(=O)O',X,dims=['components']),
 case('H04','other conjugate base',[S('O=C(O)c1ccccc1')],'O=C([O-])c1ccccc1',X,dims=['protonation_charge']),
 case('H05','NSC002 repeated substituent',[field('name','1,3-dibromobenzene')],'Brc1cccc(Br)c1',C,scope='TERMINOLOGY',role='PARTIAL_IDENTITY_ASSERTION'),
 case('H06','missing dependency',[field('structure','CO',depends_on=9)],'CO',U),
 case('H07','identifier mapping without route cannot assert graph',[field('validated_mapping','arbitrary',smiles='CO',independent=True)],'CO',U,role='STRUCTURAL_IDENTIFIER'),
 case('H08','documented metadata alone proves nothing',[field('metadata','solvent')],'CO',U,role='NONBINDING_METADATA'),
 case('H09','specified enantiomers contradict',[S('N[C@@H](C)C(=O)O')],'N[C@H](C)C(=O)O',X,dims=['stereochemistry']),
 case('H10','source scope does not establish incoming match',[S('CCO')],'CCO',U,scope='INCOMING_CONCEPT'),
 ]
 for n,x in [('development_controls.json',dev),('heldout_controls.json',held)]:write(H/'controls'/n,{'cases':x,'blinding':'PUBLIC_FROZEN_NOT_BLINDED','review_status':'CHEMICAL_REVIEW_PENDING'})
 write(target,{'phase':'PRE_IMPLEMENTATION','files':{n:sha(H/'controls'/n) for n in ('development_controls.json','heldout_controls.json')}})
 # Protect production, previous experiments, reference contracts and raw evaluated cache.
 prior=json.loads((B/'identity_reconciliation/evaluation/pre_implementation_hashes.json').read_text())['files']
 paths={B/n for n in prior}|set(B.glob('*.py'))|set((B/'identity_reconciliation').rglob('*.py'))|set((B/'identity_reconciliation').rglob('*.json'))
 for d in ('fresh_blinded_evaluation/run/http_cache','fresh_blinded_evaluation/run/chebi_cache'):
  paths|=set((B/d).glob('*.json'))
 external=json.loads((B/'FRESH_BLINDED_EVALUATION_FREEZE.json').read_text())['external_hashes']
 paths|={Path(x['path']) for x in external.values()}
 write(H/'evaluation/protected_input_freeze.json',{'files':{str(p.resolve()):sha(p) for p in sorted(paths) if p.is_file()},'provider_calls_permitted':0})
 print('Frozen 31 development and 10 public held-out controls; protected inputs snapshotted')
if __name__=='__main__':main()
