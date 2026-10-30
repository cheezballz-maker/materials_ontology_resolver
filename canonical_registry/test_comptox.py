import io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from comptox import CompTox,ROOT
from chemistry import describe
from evidence_model import assess,NON_DISCRIMINATING
from evidence_retrieval import provenance

class CompToxTests(unittest.TestCase):
    def test_exact_search_and_detail_are_candidates_not_identity_proof(self):
        docs=[json.dumps([{'dtxsid':'DTXSID7021360','dtxcid':'DTXCID501360','searchValue':'toluene','smiles':'Cc1ccccc1','isMarkush':False}]).encode(),
              json.dumps({'dtxsid':'DTXSID7021360','dtxcid':'DTXCID501360','smiles':'Cc1ccccc1'}).encode()]
        class Resp(io.BytesIO):
            def __enter__(self):return self
            def __exit__(self,*x):self.close()
        def response(request,timeout):
            self.assertEqual(request.get_header('X-api-key'),'test-only-secret')
            self.assertNotIn('test-only-secret',request.full_url)
            return Resp(docs.pop(0))
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence_scope_remediation') as tmp,patch('comptox.configured_key',return_value='test-only-secret'),patch('comptox.urllib.request.urlopen',side_effect=response):
            p=CompTox(tmp);result=p.retrieve('name','toluene')
            self.assertEqual(result['status'],'SUCCESS');self.assertEqual(result['rows'][0]['DTXSID'],'DTXSID7021360')
            self.assertEqual(assess(result['rows'][0],describe('Cc1ccccc1'))['state'],NON_DISCRIMINATING)
            self.assertNotIn('test-only-secret',json.dumps(result))
            for f in Path(tmp).glob('*.json'):self.assertNotIn('test-only-secret',f.read_text())
    def test_missing_key_and_offline_are_unavailable(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence_scope_remediation') as tmp,patch('comptox.configured_key',return_value=''):
            self.assertEqual(CompTox(tmp).name('ethanol')['status'],'NOT_QUERIED')
            self.assertEqual(CompTox(tmp,offline=True).name('ethanol')['status'],'NOT_QUERIED')
    def test_no_fuzzy_or_formula_query(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence_scope_remediation') as tmp:
            self.assertEqual(CompTox(tmp,offline=True).retrieve('formula','C2H6O')['status'],'UNSUPPORTED')
    def test_case_only_match_and_inconsistent_detail_are_not_no_match_or_proof(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence_scope_remediation') as tmp:
            p=CompTox(tmp,offline=True)
            p._get=lambda path:{'status':'SUCCESS','data':[{'dtxsid':'DTXSID7021360','searchValue':'Toluene','smiles':'Cc1ccccc1'}]}
            self.assertEqual(p.name('toluene')['status'],'NON_DISCRIMINATING')
            def get(path):
                if '/search/equal/' in path:return {'status':'SUCCESS','data':[{'dtxsid':'DTXSID7021360','searchValue':'Toluene','smiles':'Cc1ccccc1'}]}
                return {'status':'SUCCESS','data':{'smiles':'Cc1ccccc1','inchikey':'WRONG'}}
            p._get=get
            self.assertEqual(p.name('Toluene')['status'],'NON_DISCRIMINATING')
    def test_dsstox_provenance_is_not_claimed_independent(self):
        r=provenance({'provider':'CompTox','record_id':'DTXSID7021360'}, {'provider':'CompTox'},
                     {'value':'Toluene','kind':'name','origin':'source_preferred_name'})
        self.assertIn('DSSTox:DTXSID7021360',r['provenance']['lineage'])
        self.assertEqual(r['provenance']['independence'],'UNDETERMINED')

if __name__=='__main__':unittest.main()
