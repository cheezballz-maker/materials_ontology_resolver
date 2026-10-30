"""Controlled retrieval tests; fixtures are never loaded by the runtime resolver."""
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from rdkit import Chem
from chemistry import describe
from resolver import Resolver
from providers import GSRS,PubChem,ChEBI,cached_json
from evidence_retrieval import Acquisition,hypothesis_keys,identifier_keys,deduplicate,independent_lineages


def row(smiles,**fields):
    d=describe(smiles)
    return dict(SMILES=smiles,InChI=d['inchi'],InChIKey=d['inchikey'],**fields)


class Provider:
    def __init__(self,records=None):self.records=records or {};self.queries=[]
    def retrieve(self,kind,value):
        self.queries.append((kind,value))
        answer=self.records.get((kind,value),[])
        if isinstance(answer,dict):return copy.deepcopy(answer)
        return dict(status='SUCCESS',rows=copy.deepcopy(answer),query=value,url='https://test.invalid/record',retrieved_at=1)
    def name(self,value):return self.retrieve('name',value)


class Bridge:
    def __init__(self,names=None):self.names=names or {}
    def opsin(self,name):
        s=self.names.get(name)
        return dict(status='SUCCESS' if s else 'FAILURE',smiles=s,query=name,diagnostic='')
    def official(self,d):return dict(status='SUCCESS',agrees=True,inchi=d['inchi'],inchikey=d['inchikey'])


def engine(names=None,pub=None,chebi=None,gsrs=None):
    return Resolver(Bridge(names),pub or Provider(),chebi or Provider(),reviewed_evidence=Path('no_test_runtime_evidence.json'),gsrs=gsrs)


class RetrievalTests(unittest.TestCase):
    def test_identifier_corroboration_after_name_failure(self):
        s='CCOC(C)=O';d=describe(s);pub=Provider({('InChIKey',d['inchikey']):[row(s,CID=8857)]})
        r=engine({'ethyl ethanoate':s},pub).evaluate('ethyl ethanoate')
        self.assertEqual(r['status'],'AUTO_ACCEPT',r)
        self.assertIn(('InChIKey',d['inchikey']),pub.queries)
        self.assertEqual(r['evidence']['external']['rows'][0]['provenance']['query_origin'],'validated_hypothesis')
    def test_source_identifier_recovery_and_checksum(self):
        s='CCOC(C)=O';pub=Provider({('CASRegistryNumber','141-78-6'):[row(s,CID=8857)]})
        r=engine({'ethyl ethanoate':s},pub).evaluate('ethyl ethanoate',identifiers=[dict(identifier_type='CASRegistryNumber',identifier_value='141-78-6')])
        self.assertEqual(r['status'],'AUTO_ACCEPT')
        with self.assertRaises(ValueError):identifier_keys([dict(identifier_type='CASRegistryNumber',identifier_value='141-78-7')])
    def test_source_key_conflict_cannot_be_repaired(self):
        r=engine({'methanol':'CO'}).evaluate('methanol',identifiers=[dict(identifier_type='InChIKey',identifier_value=describe('CCO')['inchikey'])])
        self.assertEqual(r['status'],'CONFLICT');self.assertIn('SOURCE_IDENTIFIER_CONFLICT',r['reason_codes'])
    def test_complete_keys_keep_isotope_stereo_and_components(self):
        s='[13CH3][C@H](O)C(=O)[O-].[Na+].O.O';d=describe(s)
        keys=hypothesis_keys(d)
        self.assertEqual(next(k['value'] for k in keys if k['kind']=='SMILES'),d['smiles'])
        self.assertIn('[13CH3]',keys[1]['value']);self.assertEqual(keys[1]['value'].count('.'),3)
        with self.assertRaises(ValueError):hypothesis_keys(dict(d,inchikey=describe('CCO')['inchikey']))
    def test_stereo_search_alternatives_are_not_exact_evidence(self):
        s='N[C@H](C)C(=O)O';key=describe(s)['inchikey'];name='(R)-2-aminopropanoic acid'
        for returned,expected in [([row('NC(C)C(=O)O')],'UNRESOLVED'),([row(s),row('NC(C)C(=O)O')],'AUTO_ACCEPT')]:
            with self.subTest(expected=expected):
                r=engine({name:s},Provider({('InChIKey',key):returned})).evaluate(name)
                self.assertEqual(r['status'],expected)
                used=r['evidence']['external']['rows']
                self.assertTrue(all(x['SMILES']==s for x in used))
                self.assertTrue(any(not x['used_for_corroboration'] for x in r['evidence']['retrieval']['candidate_comparisons']))
    def test_isotope_not_removed_by_retrieval(self):
        s='[13CH3]CO';name='ethanol-1-13C';key=describe(s)['inchikey']
        for rs,status in [('CCO','UNRESOLVED'),(s,'AUTO_ACCEPT')]:
            r=engine({name:s},Provider({('InChIKey',key):[row(rs)]})).evaluate(name)
            self.assertEqual(r['status'],status);self.assertEqual(r['structure']['smiles'],describe(s)['smiles'])
    def test_salt_parent_never_substituted(self):
        s='CC(=O)[O-].[Na+]';name='sodium acetate';key=describe(s)['inchikey']
        for rs,status in [('CC(=O)O','UNRESOLVED'),(s,'AUTO_ACCEPT')]:
            r=engine({name:s},Provider({('InChIKey',key):[row(rs)]})).evaluate(name)
            self.assertEqual(r['status'],status);self.assertEqual(r['structure']['smiles'],describe(s)['smiles'])
    def test_hydrate_requires_all_water_components(self):
        s='CC(=O)[O-].[Na+].O.O.O';name='sodium acetate trihydrate';key=describe(s)['inchikey']
        r=engine({name:s},Provider({('InChIKey',key):[row('CC(=O)[O-].[Na+]')]})).evaluate(name)
        self.assertEqual(r['status'],'UNRESOLVED');self.assertEqual(r['structure']['components'],5)
    def test_solvate_requires_complete_form(self):
        s='CCO.CS(C)=O';key=describe(s)['inchikey']
        r=engine(pub=Provider({('InChIKey',key):[row('CCO')]})).evaluate('ethanol DMSO solvate',structure=s,assertion={'form_kind':'solvate','solvent_counts':{'DMSO':1}})
        self.assertEqual(r['status'],'UNRESOLVED');self.assertEqual(r['structure']['components'],2)
    def test_standard_key_is_not_fixed_tautomer_proof(self):
        a='O=c1cccc[nH]1';b='Oc1ccccn1';key=describe(a)['inchikey']
        self.assertEqual(key,describe(b)['inchikey'])
        r=engine({'2-pyridone':a},Provider({('InChIKey',key):[row(b)]})).evaluate('2-pyridone')
        self.assertEqual(r['status'],'UNRESOLVED')
        self.assertTrue(any('TAUTOMER_DIFFERENT' in x['comparison']['reason_codes'] for x in r['evidence']['retrieval']['candidate_comparisons'] if x.get('comparison')))
    def test_original_provider_disagreement_still_blocks(self):
        s='CCO';pub=Provider({('name','ethanol'):[row('COC')],('InChIKey',describe(s)['inchikey']):[row(s)]})
        r=engine({'ethanol':s},pub).evaluate('ethanol')
        self.assertEqual(r['status'],'CONFLICT');self.assertNotIn(('InChIKey',describe(s)['inchikey']),pub.queries)
    def test_invalid_identifier_returned_by_provider_blocks(self):
        s='CCO';bad=row(s);bad['InChIKey']=describe('CO')['inchikey']
        r=engine({'ethanol':s},Provider({('InChIKey',describe(s)['inchikey']):[bad]})).evaluate('ethanol')
        self.assertEqual(r['status'],'CONFLICT')
    def test_unknown_lineage_is_not_independence(self):
        s='CCO';name='common alcohol name';p=Provider({('name',name):[row(s,CID=1)]});c=Provider({('name',name):[row(s,ChEBIID='CHEBI:1')]})
        r=engine(pub=p,chebi=c).evaluate(name)
        self.assertEqual(r['status'],'UNRESOLVED');self.assertIn('EVIDENCE_LINEAGE_INDEPENDENCE_UNCONFIRMED',r['reason_codes'])
    def test_known_mirrors_and_multiple_queries_not_independent(self):
        s='CCO';name='common alcohol name';lineage=dict(independence='DOCUMENTED',lineage=['GSRS:upstream-record'])
        p=Provider({('name',name):[row(s,CID=1,provenance=lineage)]});c=Provider({('name',name):[row(s,ChEBIID='CHEBI:1',provenance=lineage)]})
        r=engine(pub=p,chebi=c).evaluate(name)
        self.assertEqual(r['status'],'UNRESOLVED');self.assertEqual(independent_lineages(r['evidence']['external']['rows']),1)
        rows=r['evidence']['external']['rows'];self.assertEqual(len(deduplicate(rows+rows)[0]),2)
    def test_parser_failure_recovered_by_validated_original_alias(self):
        # A punctuation-only spelling variant can independently preserve the
        # preferred claim; a different unparsed name cannot inherit this alias.
        name='ethyl-alcohol';alias='ethyl alcohol';s='CCO'
        p=Provider({('name',name):[row(s,CID=702)],('name',alias):[row(s,CID=702)]})
        r=engine({alias:s},p).evaluate(name,[alias,'methanol'])
        self.assertEqual(r['status'],'AUTO_ACCEPT');self.assertEqual(r['evidence']['claims'][0]['status'],'FAILURE')
        self.assertEqual(r['evidence']['local_source_support']['alias'],alias)
        self.assertTrue(r['evidence']['alias_decisions'][0]['accepted']);self.assertFalse(r['evidence']['alias_decisions'][1]['accepted'])
    def test_provider_generated_name_is_not_independent_local_source(self):
        p=Provider({('name','unparsed common name'):[row('CCO',IUPACName='ethanol')]})
        r=engine({'ethanol':'CCO'},p).evaluate('unparsed common name')
        self.assertEqual(r['status'],'UNRESOLVED');self.assertNotIn('local_source_support',r['evidence'])
    def test_bad_source_alias_does_not_repair_primary(self):
        p=Provider({('name','unparsed common name'):[row('CCO')],('name','ethyl alcohol'):[row('COC')]})
        r=engine({'ethyl alcohol':'CCO'},p).evaluate('unparsed common name',['ethyl alcohol'])
        self.assertEqual(r['status'],'UNRESOLVED');self.assertNotIn('local_source_support',r['evidence'])
    def test_no_arbitrary_text_or_incomplete_referent_fallback(self):
        p=Provider();r=engine(pub=p).evaluate('arbitrary invalid words')
        self.assertEqual(r['status'],'UNRESOLVED');self.assertNotIn('structure',r)
        r=engine({'ethanol':'CCO'},p).evaluate('(truncated chemical',['ethanol'])
        self.assertEqual(r['reason_codes'],['INCOMPLETE_SOURCE_REFERENT'])
    def test_no_secondary_semantics_override(self):
        p=Provider({('name','methylamine hydrochloride'):[row('C[NH3+].[Cl-]')]})
        r=engine({'methylamine hydrochloride':'CN.Cl'},p).evaluate('methylamine hydrochloride')
        self.assertEqual(r['status'],'UNRESOLVED');self.assertEqual(p.queries,[])
    def test_source_alias_cannot_supply_missing_primary_stereo(self):
        s='N[C@H](C)C(=O)O';p=Provider({('name','alanine'):[row(s)],('name','(R)-alanine'):[row(s)]})
        r=engine({'(R)-alanine':s},p).evaluate('alanine',['(R)-alanine'])
        self.assertEqual(r['status'],'UNRESOLVED');self.assertIn('STEREO_SOURCE_INTENT_UNSPECIFIED',r['reason_codes'])
    def test_gsrs_can_corroborate_validated_local_candidate(self):
        s='CCOC(C)=O';g=Provider({('name','ethyl ethanoate'):[row(s,UNII='0123456789')]})
        r=engine({'ethyl ethanoate':s},gsrs=g).evaluate('ethyl ethanoate')
        self.assertEqual(r['status'],'AUTO_ACCEPT')
        self.assertEqual(r['validated_rows'][0]['provider'],'GSRS')
    def test_source_alias_contradiction_stays_out_of_primary_evidence(self):
        p=Provider({('name','unparsed common name'):[row('CCO')],('name','ethyl alcohol'):[row('COC')]})
        r=engine({'ethyl alcohol':'CCO'},p).evaluate('unparsed common name',['ethyl alcohol'])
        self.assertEqual(r['status'],'UNRESOLVED')
        self.assertEqual([x['SMILES'] for x in r['evidence']['external']['rows']],['CCO'])
    def test_query_limit_and_deduplication(self):
        a=Acquisition(Provider(),Provider(),max_queries=1)
        k=dict(kind='name',value='ethanol',origin='source_preferred_name',asserts_source_identity=True)
        a.query('PubChem',k);a.query('PubChem',k);r=a.query('ChEBI',k)
        self.assertEqual(len(a.results),1);self.assertEqual(r['status'],'NOT_QUERIED')
    def test_truncated_discovery_cannot_claim_complete_corroboration(self):
        d=describe('CCO');p=Provider({('InChIKey',d['inchikey']):dict(status='INCOMPLETE',rows=[row('CCO')])})
        r=engine({'ethanol':'CCO'},p).evaluate('ethanol')
        self.assertEqual(r['status'],'UNRESOLVED')


class ProviderSafetyTests(unittest.TestCase):
    def record(self,s='CCO'):
        d=describe(s);m=Chem.MolFromSmiles(s)
        structure=dict(smiles=s,molfile=Chem.MolToMolBlock(m),_inchi=d['inchi'],_inchiKey=d['inchikey'],stereochemistry='ACHIRAL',atropisomerism='No',references=['r1'])
        moieties=[dict(smiles=Chem.MolToSmiles(x),countAmount=dict(average=1)) for x in Chem.GetMolFrags(m,asMols=True)]
        return dict(substanceClass='chemical',status='approved',definitionType='PRIMARY',definitionLevel='COMPLETE',uuid='00000000-0000-0000-0000-000000000001',approvalID='0123456789',structure=structure,moieties=moieties,names=[dict(name='ethanol',languages=['en'])],references=[dict(uuid='r1',citation='public primary record',docType='FDA_SRS')])
    def test_gsrs_complete_molecular_record(self):
        r=GSRS.record(self.record(),'https://test.invalid/gsrs')
        self.assertEqual(r['SMILES'],'CCO');self.assertEqual(r['gsrs_moiety_validation'],'COMPLETE_INTEGER_FORM_AGREES');self.assertEqual(len(r['structure_references']),1)
    def test_gsrs_ratio_no_assembly_or_salt_stripping(self):
        for change in ('fractional','mismatch','range','mixture'):
            r=self.record()
            if change=='fractional':r['moieties'][0]['countAmount']['average']=.5
            elif change=='mismatch':r['moieties'][0]['countAmount']['average']=2
            elif change=='range':r['moieties'][0]['countAmount']['high']=2
            else:r['substanceClass']='mixture'
            with self.subTest(change=change),self.assertRaises(ValueError):GSRS.record(r,'url')
    def test_gsrs_inconsistent_structures_and_key_rejected(self):
        for change in ('key','molfile','stereo'):
            r=self.record()
            if change=='key':r['structure']['_inchiKey']=describe('CO')['inchikey']
            elif change=='molfile':r['structure']['molfile']=Chem.MolToMolBlock(Chem.MolFromSmiles('CO'))
            else:r['structure']['stereochemistry']='RACEMIC'
            with self.subTest(change=change),self.assertRaises(ValueError):GSRS.record(r,'url')
    def test_chebi_identifier_does_not_require_original_name_equality(self):
        c=object.__new__(ChEBI);c.max_hits=8;d=describe('CCO')
        c.get=lambda url: {'status':'SUCCESS','url':url,'data':{'name':'ethanol','stars':3,'is_released':True,'default_structure':{'smiles':'CCO','standard_inchi':d['inchi'],'standard_inchi_key':d['inchikey']}}}
        r=c.retrieve('ChEBIID','CHEBI:16236');self.assertEqual(len(r['rows']),1)
    def test_http_cache_and_failure_budget(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            p=PubChem(folder,budget=1)
            with patch('urllib.request.urlopen',side_effect=URLError('unavailable')) as call:
                one=cached_json(p,'https://test.invalid/one');two=cached_json(p,'https://test.invalid/one');three=cached_json(p,'https://test.invalid/two')
            self.assertEqual(one,two);self.assertEqual(one['status'],'ERROR');self.assertEqual(three['status'],'NOT_QUERIED');self.assertEqual(call.call_count,1)
    def test_offline_never_requests(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            p=GSRS(folder,offline=True)
            with patch('urllib.request.urlopen') as call:r=p.name('ethanol')
            self.assertEqual(r['status'],'NOT_QUERIED');call.assert_not_called()


if __name__=='__main__':unittest.main(verbosity=2)
