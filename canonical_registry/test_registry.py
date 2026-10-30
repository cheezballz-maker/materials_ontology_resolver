import json
import sqlite3
import unittest
from pathlib import Path
from chemistry import describe,exact_key,normalize_name,comparison_views,related
from policy import reconcile,scope
from providers import Bridge

# Explicit, manually inspectable expectations; provider rows below are controlled fixtures,
# never used to admit actual CUMA records.
PAIRS=[
 ('traversal','CCO','OCC',True),('kekule','c1ccccc1','C1=CC=CC=C1',True),
 ('constitutional isomers','CCO','COC',False),
 ('enantiomers','N[C@@H](C)C(=O)O','N[C@H](C)C(=O)O',False),
 ('unspecified stereo','NC(C)C(=O)O','N[C@H](C)C(=O)O',False),
 ('geometric isomers','F/C=C/F','F/C=C\\F',False),
 ('salt parent','CN','C[NH3+].[Cl-]',False),
 ('protonation','CN','C[NH3+]',False),
 ('hydrate','CCO','CCO.O',False),('solvate','CCO','CCO.CO',False),
 ('tautomer','O=c1cccc[nH]1','Oc1ccccn1',False),
 ('isotope','CCO','[13CH3]CO',False),('radical','C','[CH3]',False),
 ('zwitterion','NCC(=O)O','[NH3+]CC(=O)[O-]',False),
 ('component multiplicity','CO.O','CO.O.O',False)]

def fixture(smiles):
    d=describe(smiles)
    # Controlled GSRS-like adapter output after its complete-moiety checks.
    return d,{'status':'SUCCESS','agrees':True},{'rows':[{'provider':'GSRS','SMILES':smiles,'InChI':d['inchi'],'InChIKey':d['inchikey'],'UNII':'0123456789','record_id':d['smiles'],'gsrs_moiety_validation':'COMPLETE_INTEGER_FORM_AGREES',
        'provenance':{'record_id':d['smiles'],'query_type':'UNII','query':'0123456789','query_origin':'source_identifier','query_status':'SUCCESS'}}]}

class ChemistryTests(unittest.TestCase):
    def test_identity_boundaries(self):
        for label,a,b,same in PAIRS:
            with self.subTest(label=label): self.assertEqual(exact_key(describe(a))==exact_key(describe(b)),same)
    def test_invalid_suffix(self):
        for x in ['CN hydrochloride','CCO arbitrary text','CCO\tethanol','CCO |foo|','not-a-chemical','C1CC','*']:
            with self.subTest(x=x),self.assertRaises(ValueError): describe(x)
    def test_inchi_suffix(self):
        x=describe('CCO')['inchi']; self.assertEqual(describe(x,'inchi')['inchikey'],describe('CCO')['inchikey'])
        for suffix in [' arbitrary','/garbage','garbage']:
            with self.subTest(suffix=suffix),self.assertRaises(ValueError): describe(x+suffix,'inchi')
    def test_parent_views_do_not_mutate(self):
        d=describe('C[NH3+].[Cl-]'); before=json.dumps(d,sort_keys=True); comparison_views(d)
        self.assertEqual(before,json.dumps(d,sort_keys=True)); self.assertNotEqual(exact_key(d),exact_key(describe('CN')))
    def test_normalization(self): self.assertEqual(normalize_name('  methylamine  hydrochloride '),'methylamine hydrochloride')
    def test_standard_inchi_is_not_merge_key(self):
        a,b=describe('O=c1cccc[nH]1'),describe('Oc1ccccn1')
        self.assertEqual(a['inchikey'],b['inchikey']); self.assertNotEqual(exact_key(a),exact_key(b))
    def test_decisions(self):
        d,o,e=fixture('CCO')
        self.assertEqual(reconcile(d,o,e,'ethanol',source_complete=True)[0],'AUTO_ACCEPT')
        self.assertEqual(reconcile(d,o,{},'ethanol')[0],'UNRESOLVED')
        self.assertEqual(reconcile(None,None,{},'invalid arbitrary name')[0],'UNRESOLVED')
        self.assertEqual(reconcile(d,{'agrees':False},e,'ethanol')[0],'UNRESOLVED')
        self.assertEqual(reconcile(d,o,e,'polymer mixture')[0],'OUT_OF_SCOPE')
        e['rows'][0]['InChIKey']=describe('C')['inchikey']
        self.assertEqual(reconcile(d,o,e,'ethanol',source_complete=True)[0],'UNRESOLVED')
    def test_ambiguous_provider(self):
        d,o,e=fixture('CCO'); e['rows']+=fixture('COC')[2]['rows']
        self.assertEqual(reconcile(d,o,e,'ethanol',source_complete=True)[0],'UNRESOLVED')
    def test_complex_forms_abstain(self):
        for s in ['C[NH3+].[Cl-]','CCO.O','[13CH3]CO','N[C@H](C)C(=O)O','[CH3]']:
            with self.subTest(s=s): self.assertEqual(reconcile(*fixture(s),'test name')[0],'UNRESOLVED')
    def test_no_transitive_merge(self):
        a,b,c=describe('CCO'),describe('OCC'),describe('COC')
        self.assertEqual(exact_key(a),exact_key(b)); self.assertNotEqual(exact_key(b),exact_key(c))
    def test_minimal_schema(self):
        db=sqlite3.connect(':memory:'); db.executescript(Path('schema.sql').read_text())
        self.assertEqual(len(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()),5)
        with self.assertRaises(sqlite3.IntegrityError): db.execute("INSERT INTO substance_reconciliation VALUES(1,NULL,'EXACT','bad')")

class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.b=Bridge()
    @classmethod
    def tearDownClass(cls): cls.b.close()
    def test_opsin_and_official(self):
        for name,s in [('ethanol','CCO'),('ethyl alcohol','CCO'),('benzene','c1ccccc1'),('methylamine hydrochloride','CN.Cl')]:
            with self.subTest(name=name):
                r=self.b.opsin(name); self.assertEqual(r['status'],'SUCCESS'); d=describe(r['smiles'])
                self.assertEqual(exact_key(d),exact_key(describe(s))); self.assertTrue(self.b.official(d)['agrees'])
    def test_invalid_name_no_fallback(self): self.assertEqual(self.b.opsin('arbitrary_invalid_chemical_zzzz')['status'],'FAILURE')

if __name__=='__main__': unittest.main(verbosity=2)
