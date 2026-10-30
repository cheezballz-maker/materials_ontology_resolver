"""Write specification fixtures only. Does not run a nomenclature engine."""
import hashlib
import json
from pathlib import Path

H = Path(__file__).resolve().parent
def write(name, value):
    (H/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf8')

refs = {
    'R1': ('IUPAC Blue Book P-13.1: substitutive operation', 'https://iupac.qmul.ac.uk/BlueBook/P1.html#P-13.1'),
    'R2': ('IUPAC Blue Book P-14.3.2: placement of locants', 'https://iupac.qmul.ac.uk/BlueBook/P1.html#P-14.3.2'),
    'R3': ('IUPAC Blue Book P-14.7.1: indicated hydrogen', 'https://iupac.qmul.ac.uk/BlueBook/P1.html#P-14.7'),
    'R4': ('IUPAC Blue Book P-22.2, Table 2.2: retained parent hydrides and numbering', 'https://iupac.qmul.ac.uk/BlueBook/P2.html'),
    'R5': ('IUPAC Blue Book P-29: substituent-group names', 'https://iupac.qmul.ac.uk/BlueBook/P2.html#P-29'),
}
grammar = '''(* NSC-001 v1, whole source name; grammar is case sensitive. *)
name             = substitution, "-", indicated_h, "-", parent ;
substitution     = "1-", normal_alkyl ;
normal_alkyl     = "methyl" | "ethyl" | "propyl" | "butyl" ;
indicated_h      = "1H" ;
parent           = "pyrazole" | "imidazole" ;
(* Semantic guards: one neutral mononuclear parent, N1 bears the source H,
   exactly one unbranched terminal alkyl bond at N1; no residual tokens. *)
(* Parsing is whole-input; no implicit whitespace, alternate spelling, primes,
   multipliers, suffixes, isotope/stereo notation, charge or salts. *)
'''
(H/'nomenclature_grammar.ebnf').write_text(grammar, encoding='utf8')
contract = {'contract_id':'NSC-001','version':'1.0','status':'FROZEN_SPECIFICATION_NOT_IMPLEMENTED',
 'purpose':'Compare a single explicitly locanted normal alkyl substitutive operation on an explicitly indicated-H parent; no whole identity admission.',
 'grammar_file':'nomenclature_grammar.ebnf','accepted_parents':['1H-pyrazole','1H-imidazole'],
 'accepted_substituents':[{'name':n,'linear_carbons':i} for i,n in enumerate(('methyl','ethyl','propyl','butyl'),1)],
 'guards':['source exactly one whole name','explicit locant 1 for substituent and indicated-H parent','neutral conventional mononuclear parent','one alkyl substituent bonded at parent N1','no other operations'],
 'interpretation':['The IUPAC parent locant and indicated-H define the parent hydride state before substitution.','Substitution formally exchanges one N1 hydrogen for a covalently bonded unbranched alkyl group; do not require the replaced hydrogen in the final structure.','Use independently validated numbered parent templates and exact alkyl templates, not parser atom IDs.'],
 'semantic_states':['SUPPORTED','DIFFERENT','UNKNOWN'],'grammar_states':['IN_CONTRACT','OUT_OF_CONTRACT','UNKNOWN'],
 'identity_admission':'NOT_ESTABLISHED','no_runtime_implementation':True,
 'negative_proof':'DIFFERENT only if the relevant constraint is established, the candidate is reliable and complete, and all chemically admissible correspondences violate it; graph mismatch alone is not a reason.',
 'completeness':'Operation only. Tautomer dimension and all other identity dimensions require independently justified completeness; no such result is promised here.',
 'nonclaims':['Excluded strings are not asserted chemically ambiguous.','Candidate isotope, stereo, charge, additional components or source conflict require separate assessment.','No synonym is validated by this contract alone.'],
 'references':refs}
write('nomenclature_support_contract.json',contract)
rule_data=[
 ('R1','Formal H-for-group substitution','A parent H is exchanged for the substituent, forming its attachment bond.','Only one N1 substitution; no suffix or additional operations.','1-methyl-1H-pyrazole'),
 ('R2','Locant placement','A locant immediately precedes the naming unit it modifies.','Only numeric 1 and unambiguous single parent ownership.','1-methyl-1H-imidazole'),
 ('R3','Indicated hydrogen','The source descriptor specifies a parent mancude-ring state; it is not a final hydrogen-count instruction.','One explicit 1H; added H and other H locants excluded.','1-methyl-1H-pyrazole'),
 ('R4','Retained heteromonocyclic parent','The defined parent and its numbering determine which atom is N1.','Only 1H-pyrazole and 1H-imidazole; extensions require independently reviewed numbered templates.','1-methyl-1H-imidazole'),
 ('R5','Normal alkyl groups','A methyl, ethyl, propyl or butyl prefix provides a terminal single attachment of a straight carbon chain.','Unbranched C1-C4 only; no unsupported alkyl naming variants.','1-ethyl-1H-imidazole')]
write('nomenclature_rule_catalog.json',{'rules':[{'rule_id':i,'construction':label,'authoritative_reference':{'title':refs[i][0],'url':refs[i][1]},'meaning':meaning,'structural_implications':meaning,'applicability_boundaries':limits,'independent_example':ex,'known_limitations':'Does not establish complete identity or all mobile-H states.'} for i,label,meaning,limits,ex in rule_data]})
schema={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'NSC source semantic constraints','type':'object','required':['contract_id','input_name','scope_status','parent','source_claims','operations','structural_constraints','completeness'],
 'properties':{'contract_id':{'const':'NSC-001'},'input_name':{'type':'string'},'scope_status':{'enum':['IN_CONTRACT','OUT_OF_CONTRACT','UNKNOWN']},
 'parent':{'type':['object','null'],'description':'Numbered chemically defined parent template, not parser identity; null if scope cannot establish parent.'},
 'source_claims':{'type':'array','items':{'$ref':'#/$defs/claim'}},'operations':{'type':'array','items':{'$ref':'#/$defs/claim'}},'structural_constraints':{'type':'array','items':{'$ref':'#/$defs/constraint'}},
 'completeness':{'type':'object','required':['operation','tautomer','identity'],'properties':{'operation':{'enum':['COMPLETE','PARTIAL','UNKNOWN']},'tautomer':{'enum':['COMPLETE','PARTIAL','UNKNOWN','NOT_APPLICABLE']},'identity':{'const':'NOT_ESTABLISHED'}},'additionalProperties':False}},
 '$defs':{'claim':{'type':'object','required':['semantic_type','source_span','owner','rule_id','value','dependencies'], 'properties':{'semantic_type':{'type':'string'},'source_span':{'type':'object','required':['start','end','text'],'properties':{'start':{'type':'integer','minimum':0},'end':{'type':'integer','minimum':0},'text':{'type':'string'}},'additionalProperties':False},'owner':{'type':'string'},'rule_id':{'enum':list(refs)},'value':{},'dependencies':{'type':'array','items':{'type':'string'}}},'additionalProperties':False},
 'constraint':{'type':'object','required':['semantic_type','owner','assertion','rule_id','applicability','dependencies','result'],'properties':{'semantic_type':{'type':'string'},'owner':{'type':'string'},'assertion':{'type':'object'},'rule_id':{'enum':list(refs)},'applicability':{'type':'string'},'dependencies':{'type':'array','items':{'type':'string'}},'result':{'enum':['SUPPORTED','DIFFERENT','UNKNOWN','NOT_EVALUATED']}},'additionalProperties':False}},'additionalProperties':False,
 'description':'Half-open Unicode-code-point spans in the original input; ownership is contract-local semantic fragment identity, not an OPSIN object ID. Validating the JSON schema does not validate chemistry.'}
write('semantic_constraint_schema.json',schema)
rules='https://iupac.qmul.ac.uk/BlueBook/P1.html#P-13.1'
pz='https://pubchem.ncbi.nlm.nih.gov/compound/70255'; iz='https://pubchem.ncbi.nlm.nih.gov/compound/MCTWTZJPVLRJOU-UHFFFAOYSA-N'; pz3='https://pubchem.ncbi.nlm.nih.gov/compound/1453-58-3'; ethiz='https://pubchem.ncbi.nlm.nih.gov/compound/1-Ethyl-1H-imidazole'
def case(i, name, candidate, grammar, expected, issue, ref, constraints, context=None):
    return {'id':i,'input_name':name,'candidate_structure':candidate,'candidate_format':'SMILES', 'expected_grammar_classification':grammar,'expected_source_constraints':constraints,'expected_comparison_result':expected,'scientific_justification':issue,'references':[rules,ref], 'evaluation_context':context or {}}
dev=[
 case('D01','1-methyl-1H-pyrazole','CN1C=CC=N1','IN_CONTRACT','SUPPORTED','N1 methyl replaces the indicated parent N1 hydrogen.',pz,['1H-pyrazole parent','N1-methyl']),
 case('D02','1-methyl-1H-imidazole','CN1C=CN=C1','IN_CONTRACT','SUPPORTED','N1 methyl on a differently numbered diazole parent.',iz,['1H-imidazole parent','N1-methyl']),
 case('D03','1-methyl-1H-pyrazole','CC1=CC=NN1','IN_CONTRACT','DIFFERENT','Candidate has carbon methyl and NH instead of N1 methyl; IUPAC locants and two independently documented structures establish the difference.',pz3,['1H-pyrazole parent','N1-methyl']),
 case('D04','1-methyl-1H-pyrazole','C1=CC(N(N1)C)=C1','IN_CONTRACT','UNKNOWN','Malformed candidate must not be used to infer a chemical contradiction.',pz,['1H-pyrazole parent','N1-methyl']),
 case('D05','methyl-1H-pyrazole','CN1C=CC=N1','OUT_OF_CONTRACT','UNKNOWN','The pilot requires an explicit substituent locant; exclusion alone does not decide chemical ambiguity.',pz,[]),
 case('D06','1-methyl-1H-pyrazole hydrochloride','CN1C=CC=N1.Cl','OUT_OF_CONTRACT','UNKNOWN','The source contains an unhandled salt construction.',pz,[]),
 case('D07','1-methyl-1H-pyrazol-3-one','CN1C=CC=N1','OUT_OF_CONTRACT','UNKNOWN','Suffix operation and added-H rules are excluded.',pz,[]),
 case('D08','1-methyl-1H-pyrazole','[2H]C1=CC=NN1C','IN_CONTRACT','UNKNOWN','Candidate has isotope specificity outside the comparison contract; do not silently discard it.',pz,['1H-pyrazole parent','N1-methyl']),
 case('D09','1-methyl-1H-pyrazole','CN1C=CC=N1','IN_CONTRACT','UNKNOWN','Missing candidate correspondence cannot establish an operation result.',pz,['1H-pyrazole parent','N1-methyl'],{'correspondence':'UNAVAILABLE'}),
 case('D10','1-methyl-1H-pyrazole','CN1C=CC=N1','IN_CONTRACT','SUPPORTED','Equivalent alternative Kekule/traversal serialization; structural mapping rather than string comparison.',pz,['1H-pyrazole parent','N1-methyl'],{'alternate_candidate':'CN1N=CC=C1'}),
 case('D11','1-methyl-1H-pyrazole','CN1C=CC=N1','IN_CONTRACT','SUPPORTED','The stated claim alone matches; separate record-level conflict prevents identity admission.',pz,['1H-pyrazole parent','N1-methyl'],{'second_source_name':'1-methyl-1H-imidazole','expected_record_resolution':'CONFLICT','second_claim_comparison':'DIFFERENT'}),
 case('D12','1-methyl-1H-pyrazole','CN1C=CC=N1','IN_CONTRACT','UNKNOWN','If candidate provenance leaves different operation outcomes under admissible mappings, do not pick one.',pz,['1H-pyrazole parent','N1-methyl'],{'correspondence':'SIMULATED_UNRESOLVED_SYMMETRY','mapping_predicates':[True,False]})]
hold=[
 case('H01','1-ethyl-1H-imidazole','CCN1C=CN=C1','IN_CONTRACT','SUPPORTED','N1 ethyl group replaces the indicated parent H.',ethiz,['1H-imidazole parent','N1-ethyl']),
 case('H02','1-ethyl-1H-imidazole','CN1C=CN=C1','IN_CONTRACT','DIFFERENT','Methyl and ethyl groups have different substituent connectivity; both candidate and source claim are explicit.',iz,['1H-imidazole parent','N1-ethyl']),
 case('H03','1-ethyl-1H-imidazole','CCN1C=CN=C1.Cl','IN_CONTRACT','UNKNOWN','The candidate has an additional component; salt composition is outside the pilot.',ethiz,['1H-imidazole parent','N1-ethyl']),
 case('H04','1-ethyl-1H-imidazole','CCN1C=CN=C1','IN_CONTRACT','UNKNOWN','Insufficient structural mapping cannot establish a result.',ethiz,['1H-imidazole parent','N1-ethyl'],{'correspondence':'UNAVAILABLE'}),
 case('H05','1-ethylimidazole','CCN1C=CN=C1','OUT_OF_CONTRACT','UNKNOWN','A conventional name without explicit 1H is outside this deliberately narrow grammar, even if it is chemically valid.',ethiz,[]),
 case('H06','1-ethyl-1H-imidazole','CCN1C=CN=C1','IN_CONTRACT','SUPPORTED','Equivalent atom traversal must not generate a false difference.',ethiz,['1H-imidazole parent','N1-ethyl'],{'alternate_candidate':'CCN1C=NC=C1'})]
write('independent_semantic_controls.json',{'version':'1.0','status':'FROZEN_EXPECTATIONS_NOT_EXECUTED','semantics':'Results apply only to the named operation; source conflicts are separately evaluated.','cases':dev})
write('heldout_semantic_controls.json',{'version':'1.0','status':'FROZEN_NOT_EXECUTED','selection':'Different parent/substituent combination and negative, scope, component, symmetry/traversal and missing-evidence checks. Public specification, not secret blind adjudication.','cases':hold})
write('architecture_comparison_requirements.json',{'shared_contract':'NSC-001 v1.0','same_inputs':'Use both frozen JSON control files unchanged; no candidate or source from either parser may set a reference label.',
 'evaluation':['Preserve original source span/ownership and compare source-derived constraints with separately supplied candidate.','Measure exact matches for grammar and operation labels; safety gate requires zero unsupported positive or negative assertions, including UNKNOWN and symmetry cases.','Demonstrate whole-input rejection, candidate correspondence completeness and no identity admission side effect.','Report coverage, false positive/negative and abstentions separately, with per-case and heldout outcomes.','Require independent chemical review of expected graph and symmetry items before acceptance.'],
 'A':{'requires':['Pinned version','source token ownership','semantic parent template/candidate correspondence','bounded transformation closure or independently validated final-structure proof','fail-closed clones, normalization, warning and alternatives'],'note':'Full internal operation logging is not a contract requirement.'},
 'B':{'requires':['independently implemented whole-name grammar','reviewed numbered parent and alkyl templates','separately supplied candidate graph','symmetry-aware comparison','fail-closed unsupported transformations'],'note':'Independent rules must not copy candidate parser results as source evidence.'},
 'release':'Specification only. No resolver flag, provider change or evidence gate change.'})
extensions=[('additional substitution','numbered parent and locant mapping','multiple positions, multipliers and precedence','all symmetry-aware attachment mappings','ownership and equivalent positions','high'),('added-H and suffixes','parent and operation composition','P-14.7.2 and functional suffix transformations','affected atom/bond and H states','mobile-H completeness','high'),('functional-class names','source spans and claims','class-specific names and conventional variants','role-specific structure mapping','polysemy','medium'),('charge and protonation','atom-mapped constraints','ionic nomenclature and source scope','charged graph and proton assignments','acid/base defaults','high'),('salts and stoichiometry','typed components','counterions and composition','component multiset and stoichiometry','hydration and unknown composition','high'),('stereo','claim scopes','R/S, E/Z and relative stereochemistry','stereo-aware all-isomorphism','unspecified versus relative stereo','high'),('isotopes','locant ownership','isotopic descriptor syntax and conventional scope','isotopic atom mapping','unlabelled isotope convention','medium'),('validated aliases','independent claim scopes','systematic and conventional naming rules','full-form identity correspondence','broad aliases and source provenance','high')]
write('nomenclature_extension_roadmap.json',{'extensions':[{'class':c,'reusable_components':a,'additional_semantics':b,'structural_comparison':d,'limitations':e,'expected_practical_value':f} for c,a,b,d,e,f in extensions], 'value':'qualitative estimates, not measured recoveries'})
names=['nomenclature_support_contract.json','nomenclature_grammar.ebnf','semantic_constraint_schema.json','nomenclature_rule_catalog.json','architecture_comparison_requirements.json','independent_semantic_controls.json','heldout_semantic_controls.json','nomenclature_extension_roadmap.json']
write('nomenclature_contract_freeze.json',{'purpose':'Contract and shared controls frozen before 81-case applicability review.','sha256':{n:hashlib.sha256((H/n).read_bytes()).hexdigest() for n in names}})
print('FROZEN',len(names))
