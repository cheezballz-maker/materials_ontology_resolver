import copy,json,unittest,sqlite3,tempfile
from pathlib import Path
from chemistry import describe,exact_key
from form_characterizer import characterize,interpret
from identity_comparator import compare
from policy import decision
from resolver import Resolver,lookup
from providers import ChEBI
from test_registry import fixture
from registry_builder import populate

class FormTests(unittest.TestCase):
    def pair(self,a,b,status,dimension=None):
        r=compare(describe(a),describe(b));self.assertEqual(r['assessment'],status,r)
        if dimension:self.assertEqual(r['dimensions'][dimension],'DIFFERENT',r)
        return r
    def admit(self,s,name,assertion=None):return decision(*fixture(s),name,assertion,source_complete=True)
    def test_representation(self):
        self.pair('CCO','OCC','EXACT');self.pair('c1ccccc1','C1=CC=CC=C1','EXACT')
    def test_constitution(self):self.pair('CCO','COC','DISTINCT','connectivity')
    def test_stereo(self):
        l='N[C@@H](CCC(=O)O)C(=O)O';d='N[C@H](CCC(=O)O)C(=O)O'
        self.pair(l,d,'DISTINCT','stereochemistry')
        self.assertEqual(self.admit(l,'L-glutamic acid')['status'],'AUTO_ACCEPT')
        self.assertEqual(self.admit(d,'D-glutamic acid')['status'],'AUTO_ACCEPT')
        self.assertEqual(self.admit(l,'glutamic acid')['status'],'UNRESOLVED')
        self.assertEqual(self.admit('NC(CCC(=O)O)C(=O)O','glutamic acid')['status'],'UNRESOLVED')
        self.assertNotEqual(compare(describe(l),describe('NC(CCC(=O)O)C(=O)O'))['assessment'],'EXACT')
        self.pair('C/C=C/C','C/C=C\\C','DISTINCT','stereochemistry')
    def test_partial_and_ensemble(self):
        self.assertEqual(self.admit('C[C@H](O)C(O)C','(2R)-pentane-2,3-diol')['status'],'UNRESOLVED')
        self.assertEqual(self.admit('N[C@@H](C)C(=O)O','racemic alanine')['status'],'OUT_OF_SCOPE')
        self.assertEqual(self.admit('O=[Si]=O','silicon dioxide')['status'],'UNRESOLVED')
        self.assertEqual(self.admit('c1ccccc1-c1ccccc1','axial atropisomer')['status'],'UNRESOLVED')
        self.assertEqual(self.admit('c1ccccc1-c1ccccc1','(R)-biphenyl')['status'],'UNRESOLVED')
    def test_isotopes(self):
        self.pair('O','[2H]O[2H]','DISTINCT','isotope_specification')
        self.pair('[13CH3]CO','C[13CH2]O','DISTINCT','isotope_specification')
        self.pair('[13CH3]C','C[13CH3]','EXACT')
        self.assertEqual(self.admit('[2H]O[2H]','deuterium oxide')['status'],'AUTO_ACCEPT')
        self.assertEqual(self.admit('[13CH3]CO','labelled ethanol')['status'],'UNRESOLVED')
    def test_charge_and_resonance(self):
        self.pair('CC(=O)O','CC(=O)[O-]','DISTINCT','protonation_charge')
        self.pair('CC(=O)[O-]','CC([O-])=O','EXACT')
        # Distinguishable isotope oxygen sites make this nontrivial resonance test.
        self.pair('CC(=[18O])[O-]','CC([18O-])=O','EXACT')
        self.assertEqual(self.admit('CC(=O)[O-]','acetate')['status'],'AUTO_ACCEPT')
        self.pair('NCC(=O)O','[NH3+]CC(=O)[O-]','DISTINCT','protonation_charge')
    def test_salts(self):
        na='CC(=O)[O-].[Na+]';k='CC(=O)[O-].[K+]'
        self.pair(na,k,'DISTINCT','components')
        self.pair('CN','C[NH3+].[Cl-]','DISTINCT')
        self.assertEqual(self.admit(na,'sodium acetate')['status'],'UNRESOLVED')
        self.assertEqual(self.admit(k,'potassium acetate')['status'],'UNRESOLVED')
        self.assertEqual(self.admit('C[NH3+].[Cl-]','methylamine hydrochloride')['status'],'UNRESOLVED')
        self.assertEqual(self.admit('CN.Cl','methylamine hydrochloride')['status'],'UNRESOLVED')
        self.assertEqual(self.admit('CC(=O)[O-].[Na+].[Na+]','sodium acetate')['status'],'UNRESOLVED')
        self.assertEqual(self.admit('[K+].[K+].[O-]C(=O)CC(=O)[O-]','dipotassium malonate')['status'],'UNRESOLVED')
        self.assertEqual(interpret(describe('N[C@@H]1C[C@H](O)CC1'),'(1R,3R)-3-aminocyclopentan-1-ol')['specification'],'SPECIFIED')
    def test_hydrate_and_solvate(self):
        na='CC(=O)[O-].[Na+]';tri=na+'.O.O.O'
        self.pair(na,tri,'DISTINCT','components')
        self.assertEqual(self.admit(tri,'sodium acetate trihydrate')['status'],'UNRESOLVED')
        self.assertEqual(self.admit(tri,'hydrated sodium acetate')['status'],'UNRESOLVED')
        self.assertEqual(self.admit(na+'.O','sodium acetate trihydrate')['status'],'UNRESOLVED')
        self.assertEqual(self.admit('CCO.CS(C)=O','ethanol DMSO solvate',{'explicit_structure':True,'form_kind':'solvate','solvent_counts':{'DMSO':1}})['status'],'UNRESOLVED')
        self.assertEqual(self.admit('CCO.CS(C)=O','ethanol DMSO solvate')['status'],'UNRESOLVED')
        self.assertEqual(self.admit('CCO.CO','ethanol methanol')['status'],'UNRESOLVED')
    def test_tautomers(self):
        a,b=describe('O=c1cccc[nH]1'),describe('Oc1ccccn1')
        self.assertEqual(a['inchikey'],b['inchikey']);self.assertNotEqual(a['fixed_h_inchi'],b['fixed_h_inchi'])
        self.pair(a['smiles'],b['smiles'],'DISTINCT','tautomeric_form')
        for s,name in [(a['smiles'],'2-pyridone'),(b['smiles'],'2-hydroxypyridine')]:self.assertEqual(self.admit(s,name)['status'],'AUTO_ACCEPT')
    def test_conflicting_tautomer_is_not_admitted(self):
        a,o,e=fixture('Nc1nc(=S)ss1');b=fixture('N=c1nc(S)ss1')[2]['rows'][0]
        self.assertEqual(a['inchikey'],b['InChIKey']);e['rows'].append(b)
        name='5-Amino-3H-1,2,4-dithiazole-3-thione'
        for i,record in enumerate(e['rows']):
            record.update(provider='PubChem',CID=i+1,IUPACName=name,provenance={'record_id':str(i+1),'query_type':'name','query':name,'query_origin':'source_preferred_name','query_status':'SUCCESS'})
        r=decision(a,o,e,name,source_complete=True)
        self.assertEqual(r['status'],'UNRESOLVED');self.assertEqual(r['provider_routes'][0]['state'],'NON_DISCRIMINATING')
    def test_feature_immutability_and_components(self):
        d=describe('CC(=O)[O-].[Na+].O.O.O');before=copy.deepcopy(d);f=characterize(d)
        self.assertEqual(d,before);self.assertEqual(f['component_stoichiometry']['O'],3)
        f['component_stoichiometry']['O']=999;self.assertEqual(characterize(d)['component_stoichiometry']['O'],3)
    def test_lookup_no_alias_formula_or_key_merge(self):
        a,b=describe('O=c1cccc[nH]1'),describe('Oc1ccccn1')
        self.assertEqual(lookup(a,[('SUB_00000001',b)])['status'],'NO_MATCH')
        self.assertEqual(lookup(describe('CCO'),[('SUB_00000001',describe('COC'))])['status'],'NO_MATCH')
        self.assertEqual(lookup(a,[('SUB_00000001',a)])['status'],'EXACT')
        self.assertEqual(lookup(a,[('SUB_00000001',a),('SUB_00000002',a)])['status'],'UNRESOLVED')
    def test_provider_integrity(self):
        d,o,e=fixture('CCO');e['rows'][0]['InChI']=describe('COC')['inchi']
        self.assertEqual(decision(d,o,e,'ethanol',source_complete=True)['status'],'UNRESOLVED')
        self.assertEqual(decision(d,o,{'rows':[]},'ethanol')['status'],'UNRESOLVED')
    def test_slash_backslash_not_normalized(self):
        a=describe('F/C=C/F');b=describe('F/C=C\\F')
        self.assertEqual(a['original_input'],'F/C=C/F');self.assertEqual(b['original_input'],'F/C=C\\F')
        self.assertNotEqual(exact_key(a),exact_key(b))
    def test_comparator_complete_link_and_registry(self):
        db=sqlite3.connect(':memory:');db.executescript(Path('schema.sql').read_text())
        structures=['CCO','OCC','COC','O=c1cccc[nH]1','Oc1ccccn1','CC(=O)[O-].[Na+]','CC(=O)[O-].[K+]']
        records=[dict(i=i,name='test',d=describe(s),aliases=['shared name'],external={'rows':[]}) for i,s in enumerate(structures,1)]
        out=populate(db,records,[(r['i'],'EXACT','fixture') for r in records])
        self.assertEqual(out['canonical_substances'],6)
        self.assertEqual(out['mapping'][1],out['mapping'][2])
        self.assertNotEqual(out['mapping'][4],out['mapping'][5])
        self.assertNotEqual(out['mapping'][6],out['mapping'][7])
        self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
    def test_stable_id_reuse(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            self.assertTrue(Path(folder).resolve().is_relative_to(Path(__file__).resolve().parent))
            path=Path(folder)/'old.sqlite';old=sqlite3.connect(path);old.executescript(Path('schema.sql').read_text())
            old.execute("INSERT INTO substance_identity VALUES('SUB_00000100','ethanol','ACCEPTED')")
            old.execute("INSERT INTO substance_structure VALUES('SUB_00000100','SMILES','CCO')");old.commit();old.close()
            db=sqlite3.connect(':memory:');db.executescript(Path('schema.sql').read_text())
            rows=[dict(i=i,name='test',d=describe(s),aliases=[],external={'rows':[]}) for i,s in [(1,'OCC'),(2,'COC')]]
            result=populate(db,rows,[(1,'EXACT','test'),(2,'EXACT','test')],path)
            self.assertEqual(result['mapping'],{1:'SUB_00000100',2:'SUB_00000101'})

class ChebiTests(unittest.TestCase):
    def test_residue_alias_is_not_discrete_molecular_evidence(self):
        c=object.__new__(ChEBI);c.max_hits=8
        def get(url):
            if 'es_search' in url:return {'status':'SUCCESS','data':{'total':1,'results':[{'_source':{'chebi_accession':'CHEBI:1'}}]}}
            return {'status':'SUCCESS','url':url,'data':{'name':'amino acid residue','names':{'SYNONYM':[{'name':'amino acid'}]},'stars':3,'is_released':True,'default_structure':{'smiles':'*NCC(*)=O','is_r_group':False}}}
        c.get=get;r=c.name('amino acid')
        self.assertEqual(r['rows'],[])
        self.assertEqual(r['excluded_records'][0]['reason'],'NON_DISCRETE_WILDCARD_STRUCTURE')
        self.assertEqual(len(r['retrieval']),2)
    def test_exact_name_not_first_hit(self):
        d=describe('CCO');c=object.__new__(ChEBI);c.max_hits=8
        def get(url):
            if 'es_search' in url:return {'status':'SUCCESS','data':{'total':2,'results':[{'_source':{'chebi_accession':'CHEBI:1'}},{'_source':{'chebi_accession':'CHEBI:2'}}]}}
            name='ethanol derivative' if 'CHEBI:1' in url else 'ethanol'
            return {'status':'SUCCESS','url':url,'data':{'name':name,'stars':3,'is_released':True,'default_structure':{'smiles':'CCO','standard_inchi':d['inchi'],'standard_inchi_key':d['inchikey']}}}
        c.get=get;result=c.name('ethanol')
        self.assertEqual([x['ChEBIID'] for x in result['rows']],['CHEBI:2'])
    def test_fuzzy_search_truncation_is_not_chemical_ambiguity(self):
        c=object.__new__(ChEBI);c.max_hits=8;c.get=lambda url:{'status':'SUCCESS','data':{'total':9,'results':[]}}
        result=c.name('ambiguous')
        self.assertEqual(result['status'],'SUCCESS');self.assertTrue(result['search_truncated']);self.assertEqual(result['rows'],[])

if __name__=='__main__':unittest.main(verbosity=2)
