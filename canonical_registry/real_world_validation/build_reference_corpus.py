"""Freeze real records + public documentary labels before the new interface runs.

Only RDKit file parsing/serialization is used to load original NIST molecular
files. No resolver/comparator or previous prediction is used to assign labels.
"""
import hashlib,html,json,re
from pathlib import Path
from rdkit import Chem
H=Path(__file__).resolve().parent;B=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,o):p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
 if (H/'reference_corpus/benchmark_freeze.json').exists():raise SystemExit('Reference corpus frozen; no overwrite')
 pubchem={};chebi={};provenance={}
 for folder in ('output/http_cache','evaluation/http_cache','systematic_nomenclature_upgrade_final/run/http_cache','provider_qualification/probe_pubchem','fresh_blinded_evaluation/run/http_cache'):
  for p in sorted((B/folder).glob('*.json')):
   raw=read(p)
   if 'pubchem.ncbi.nlm.nih.gov/rest/pug/compound/' not in raw.get('url',''):continue
   rows=raw.get('rows',raw.get('data',{}).get('PropertyTable',{}).get('Properties',[]))
   for index,row in enumerate(rows):
    if row.get('CID') and row.get('SMILES'):
     cid=str(row['CID']);ref='PubChem:'+cid
     if cid not in pubchem:
      pubchem[cid]=dict(source_name='PubChem',source_record_type='COMPOUND',record_id=cid,record=row,structure=row['SMILES'])
      provenance[ref]=dict(payload_path=str(p.resolve()),payload_sha256=sha(p),url=raw['url'],retrieved_at=raw.get('retrieved_at'),cached_row_path=f'$.rows[{index}]',lineage_roots=['PubChem:COMPOUND:'+cid],upstream_structure_origin='UNAVAILABLE_IN_PROPERTY_PAYLOAD',role='SAVED_RESOLVER_PROVIDER_RESPONSE_NOT_NEW_QUERY')
 for p in sorted((B/'fresh_blinded_evaluation/run/chebi_cache').glob('*.json')):
  raw=read(p);r=raw.get('data') or {}
  if raw.get('status')!='SUCCESS' or not isinstance(r,dict) or not r.get('chebi_accession'):continue
  accession=r['chebi_accession'];chebi[accession]=dict(source_name='ChEBI',source_record_type='CHEMICAL_ENTITY',record_id=accession,record=r,structure=(r.get('default_structure') or {}).get('smiles'))
  provenance['ChEBI:'+accession]=dict(payload_path=str(p.resolve()),payload_sha256=sha(p),url=raw['url'],retrieved_at=raw.get('retrieved_at'),lineage_roots=['ChEBI:CHEMICAL_ENTITY:'+accession],curator=r.get('created_by'),record_modified=r.get('modified_on'),names_metadata=r.get('names'),upstream_structure_origin='NOT_ESTABLISHED_BY_CACHED_METADATA',role='SAVED_RESOLVER_PROVIDER_RESPONSE_NOT_NEW_QUERY')
 nist={}
 for r in read(H/'validation_material/retrieval_manifest.json')['records']:
  if r['status']!='SUCCESS' or not r.get('molfile'):continue
  p=Path(r['molfile']['path']);m=Chem.MolFromMolBlock(p.read_text(encoding='utf8'),sanitize=True,removeHs=False,strictParsing=True)
  if m is None:raise ValueError('NIST_MOLFILE_NOT_PARSED:'+r['description'])
  ref=r['reference_id'];nist[r['description']]=dict(source_name='NIST_VALIDATION_MATERIAL',source_record_type='DOCUMENTED_MOLECULAR_FILE',record_id=ref,record=r,structure=Chem.MolToSmiles(m,canonical=True,isomericSmiles=True),raw_molfile_path=str(p.resolve()),raw_molfile_sha256=sha(p))
  provenance[ref]={**r,'lineage_roots':[ref],'upstream_structure_origin':'NIST authoritative record; specific graph generator ancestry not established','role':'PUBLIC_VALIDATION_MATERIAL_NOT_QUALIFYING_PROVIDER_CORROBORATION'}
 def source(cid):return pubchem[cid]
 E='CHEMICALLY_EQUIVALENT';D='CHEMICALLY_DIFFERENT';U='CHEMICALLY_UNRESOLVED'
 refs={'isotope':'https://iupac.qmul.ac.uk/BlueBook/P8.html','stereo':'https://iupac.qmul.ac.uk/BlueBook/P9.html#P-93.1','charge':'https://iupac.qmul.ac.uk/BlueBook/P7.html','nomenclature':'https://iupac.qmul.ac.uk/BlueBook/P6.html','tautomer':'https://iupac.qmul.ac.uk/BlueBook/P1.html#P-14.7'}
 cases=[]
 def add(i,cid,ref,category,expected,why,group,*,scope='DISCRETE_MOLECULAR',reference_scope=None,mode='STRUCTURAL_FIELD_REFERENT',quality='INDEPENDENT_DOCUMENTARY_GROUNDING',eligible=True):
  s=source(cid) if not cid.startswith('CHEBI:') else chebi[cid];sref=s['source_name']+':'+s['record_id'];r=ref;rref=r['record_id'] if r['source_name']=='NIST_VALIDATION_MATERIAL' else r['source_name']+':'+r['record_id']
  key='RW'+str(i).zfill(2);parts='development_reference' if group in ('ethanol_ether','benzene','pyridine','bromomethane') else 'frozen_evaluation'
  support=[provenance[sref]['url'],provenance[rref]['url'],refs.get(category,refs['nomenclature'])]
  cases.append(dict(case_id=key,chemical_identity_description=why,category=category,partition=parts,identity_group=group,source_record=s,source_record_provenance=provenance[sref],reference_identity=r,reference_provenance=provenance[rref],source_structure=s['structure'],reference_structure=r['structure'],source_identity_scope=scope,reference_identity_scope=reference_scope or ('DEFINED_MULTICOMPONENT_COMPOSITION' if '.' in r['structure'] else 'DISCRETE_MOLECULAR'),incoming_concept_mode=mode,applicable_identity_dimensions=['constitution','stereochemistry','tautomer','protonation_charge','isotope','components','component_stoichiometry','hydration_solvation','electronic_state'],expected_correspondence=expected,expected_independence_status='INDEPENDENCE_UNESTABLISHED',scientific_justification=why,supporting_references=support,review_status=quality,documentary_annotation_status='COMPLETED_FROM_ORIGINAL_FIELDS_AND_DOCUMENTARY_CHEMISTRY' if eligible else 'REFERENCE_REVIEW_PENDING',qualified_expert_review='NOT_PERFORMED',accuracy_population_eligible=eligible,label_origin='Documentary identity descriptions, explicit molecular files and chemical definitions; never resolver prediction',selection_bias='Purposive chemical coverage; not random, blind or a population-precision study'))
 add(1,'702',nist['ethanol'],'constitution',E,'Cached ethanol is a two-carbon alcohol; NIST ethanol molecular file independently supplies that C-C-O structure and neutral OH form.','ethanol_ether')
 add(2,'8254',nist['dimethyl_ether'],'constitution',E,'Cached dimethyl ether and the NIST dimethyl-ether molecular file both explicitly supply C-O-C ether constitution.','ethanol_ether')
 add(3,'241',nist['benzene'],'resonance',E,'Actual PubChem benzene Kekule field and NIST benzene molecular file denote the same aromatic ring; traversal/Kekule depiction is not a new molecular identity.','benzene')
 add(4,'1049',nist['pyridine'],'constitution',E,'The source pyridine ring and NIST pyridine molecular file specify the same five-carbon/one-nitrogen heteroaromatic ring.','pyridine')
 add(5,'6323',nist['bromomethane'],'constitution',E,'PubChem bromomethane and the NIST methyl-bromide molecular file specify the same neutral C-Br molecule.','bromomethane')
 add(6,'6344',nist['dichloromethane'],'constitution',E,'PubChem dichloromethane and the NIST molecular file specify the same unlabelled CH2Cl2 structure.','dichloromethane')
 add(7,'180',nist['acetone'],'tautomer',E,'Both original records explicitly depict the carbonyl form of acetone; the reference is the molecular file, not an equality of normalized InChI.','acetone')
 add(8,'176',nist['acetic_acid'],'charge',E,'Both source and NIST molecular file explicitly specify the neutral carboxylic acid form, not its conjugate base.','acetate')
 add(9,'24602',nist['heavy_water'],'isotope',E,'The source and NIST deuterium-oxide molecular file explicitly label both hydrogen atoms as mass 2.','water')
 add(10,'160586',nist['dichloromethane_d2'],'isotope',E,'Both authentic molecular records specify methylene chloride with two deuterium atoms.','dichloromethane')
 add(11,'522220',nist['acetone_d6'],'isotope',E,'The source and NIST molecular file specify six deuteria on the acetone methyl groups.','acetone')
 add(12,'84682',nist['r_butanol'],'stereo',E,'Source IUPAC name specifies (2R)-butan-2-ol; NIST C14898794 explicitly names the R form and supplies its stereochemical molecular file.','butanol')
 add(13,'702',nist['dimethyl_ether'],'constitution',D,'Ethanol has C-C-O alcohol constitution; the independently supplied NIST ether has C-O-C constitution. Equal formula cannot identify them.','ethanol_ether')
 add(14,'160586',nist['dichloromethane'],'isotope',D,'The source deliberately labels two hydrogen atoms as deuterium while the reference is ordinary unlabelled dichloromethane.','dichloromethane')
 add(15,'522220',nist['acetone'],'isotope',D,'Perdeuterated acetone and ordinary acetone differ in deliberate isotope substitution; labels cannot be stripped.','acetone')
 add(16,'24602',nist['water'],'isotope',D,'Dideuterium oxide and conventional unlabelled water are distinct represented isotope forms; unlabelled does not assert pure protium.','water')
 add(17,'84682',nist['s_butanol'],'stereo',D,'The source R configuration and the explicitly named NIST S-but-2-ol reference are opposite enantiomers.','butanol')
 add(18,'7245',nist['p_chlorophenol'],'positional',D,'The source 2-chlorophenol has adjacent Cl/OH; NIST 4-chlorophenol places them para. The substitution positions independently establish constitutional difference.','chlorophenol')
 add(19,'31372',nist['acetic_acid'],'components',D,'The source explicitly supplies sodium plus acetate in 1:1 ionic composition; the NIST neutral acid file contains no sodium counterion.','acetate',scope='DEFINED_MULTICOMPONENT_COMPOSITION')
 add(20,'31372',nist['sodium_acetate_trihydrate'],'stoichiometry',D,'The source explicitly supplies anhydrous sodium acetate composition; the NIST trihydrate record and molecular file supply three additional water molecules. Composition-level distinction only, not a polymorph claim.','acetate',scope='DEFINED_MULTICOMPONENT_COMPOSITION')
 add(21,'175',nist['acetic_acid'],'charge',D,'The source acetate graph has a negatively charged carboxylate and lacks the acid proton; NIST explicitly supplies neutral acetic acid.','acetate')
 add(22,'636405',chebi['CHEBI:59213'],'tautomer',D,'Independent inspection of original fields: PubChem explicitly names/depicts 6-methyl-4-oxo-1H-pyridine (N-H/C=O); ChEBI names/depicts 4-hydroxy-6-methylpyridine (ring n/O-H). The represented proton/bond arrangement differs even though Standard InChI shares a mobile-H projection. This label is based on those raw fields, not the previously reported resolver result.','cefpiramide')
 add(23,'95444',pubchem['820607'],'stereo',U,'The authentic source indanol graph specifies neither of its stereogenic centers. It cannot select the independently specified (1R,2R) reference.','indanol')
 add(24,'50989996',pubchem['820608'],'stereo',U,'Source (1S)-2-bromoindan-1-ol leaves C2 configuration unspecified; a fully specified (1S,2S) reference is a narrower identity.','indanol')
 add(25,'CHEBI:61358',nist['ethanol'],'broad',U,'ChEBI explicitly identifies a polymer and supplies no default molecular graph. It does not denote one ethanol-like molecular Substance.','polymer',scope='FAMILY')
 add(26,'702',nist['ethanol'],'source_binding',E,'The actual source graph and NIST graph remain equivalent, but this incoming concept selects the source-generated name field alone. Its binding must be assessed independently and cannot inherit the record graph merely from membership.','ethanol_ether',mode='ASSOCIATED_NAME_REFERENT')
 add(27,'71601',nist['benzene_d6_corrected'],'isotope',E,'Both original molecular records explicitly specify six deuteria on the benzene ring.','benzene')
 add(28,'71601',nist['benzene'],'isotope',D,'The source benzene-d6 and conventional unlabelled NIST benzene differ in deliberate isotope composition.','benzene')
 add(29,'31372',nist['sodium_acetate'],'representation',None,'NIST sodium-acetate molfile explicitly uses an O-Na bond while its Standard InChI projects ionic components. The incoming record is already ionic. No exact chemical-equivalence/difference reference label is assigned without validating that metal-bond depiction convention.','acetate',scope='DEFINED_MULTICOMPONENT_COMPOSITION',quality='REVIEW_PENDING',eligible=False)
 add(30,'50989996',pubchem['820607'],'stereo',D,'The source explicitly fixes indanol C1 as S; the reference fixes C1 as R and C2 as R. Unspecified source C2 cannot make an S-at-C1 identity equal to an R-at-C1 identity. The known C1 incompatibility alone excludes this reference.','indanol')
 add(31,'CHEBI:59213',chebi['CHEBI:59214'],'charge',D,'ChEBI explicitly defines 59214 as the anion obtained by loss of the carboxylic-acid proton from 59213 and supplies reciprocal conjugate-acid/base relations and structures. The expected difference is documentary, not generated by the comparator.','cefpiramide')
 for c in cases:
  if c['incoming_concept_mode']=='ASSOCIATED_NAME_REFERENT':c['expected_source_identity_correspondence']='SOURCE_IDENTITY_UNRESOLVED'
  elif c['expected_correspondence']==E:c['expected_source_identity_correspondence']='SOURCE_IDENTITY_CORRESPONDENCE_SUPPORTED'
  elif c['expected_correspondence']==D:c['expected_source_identity_correspondence']='SOURCE_IDENTITY_DIFFERENT'
  else:c['expected_source_identity_correspondence']='SOURCE_IDENTITY_UNRESOLVED'
  # A concrete unqualified metal depiction is deliberately not a golden label.
  if not c['accuracy_population_eligible']:c['expected_source_identity_correspondence']=None
 for c in cases:
  for record,prov in [(c['source_record'],c['source_record_provenance']),(c['reference_identity'],c['reference_provenance'])]:
   assert Path(prov.get('payload_path',prov.get('path'))).exists()
 manifest=dict(version='1.0',population='Purposive actual cached provider records and separately acquired NIST primary molecular files; no synthetic candidate definitions',case_count=len(cases),partitions={k:sum(c['partition']==k for c in cases) for k in ('development_reference','frozen_evaluation')},split='Chemical identity families grouped; development families ethanol/ether, benzene, pyridine, bromomethane. No source identity duplicated across partitions.',annotation_policy='Expected labels are documentary assertions from original names/graphs/curated definitions, not resolver outputs; REVIEW_PENDING cases excluded from accuracy; no qualified expert review or blinding claimed.',blinding='NOT_BLINDED',qualified_expert_reviewed_cases=0,known_dependent_fields='Every source computed InChI/key/name is dependent on its own source graph. Cross-record upstream structure independence remains unestablished.',unvalidated_categories=['Isotopically unspecified real source-name scope: no sufficiently documented incoming name found; retained frozen controls only','Genuine within-record contradictory identity assertions: no independently established real example selected; historical controls only','General charged-resonance equivalence beyond actual aromatic/Kekule equivalence: not independently validated'],public_validation_retrieval='validation_material/retrieval_manifest.json; not production provider evidence or automatic independent corroboration')
 adjudication={c['case_id']:dict(expected_correspondence=c['expected_correspondence'],expected_source_identity_correspondence=c['expected_source_identity_correspondence'],expected_independence_status=c['expected_independence_status'],justification=c['scientific_justification'],review_status=c['review_status'],accuracy_population_eligible=c['accuracy_population_eligible'],label_revision_history=[]) for c in cases}
 for name,obj in [('corpus_manifest.json',manifest),('reference_cases.json',{'cases':cases}),('provenance_records.json',provenance),('reference_adjudication.json',adjudication)]:write(H/'reference_corpus'/name,obj)
 write(H/'reference_corpus/benchmark_freeze.json',{'phase':'BEFORE_DIAGNOSTIC_INTERFACE_IMPLEMENTATION_AND_RESOLVER_EXECUTION','files':{n:sha(H/'reference_corpus'/n) for n in ('corpus_manifest.json','reference_cases.json','provenance_records.json','reference_adjudication.json')},'material_hashes':{str(p.resolve()):sha(p) for p in sorted((H/'validation_material').glob('*')) if p.is_file() and p.suffix in ('.html','.mol')},'labels_generated_by_resolver':False})
 print(json.dumps(manifest,indent=2));print('Corpus frozen without running resolver/comparator')
if __name__=='__main__':main()
