import unittest, uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from constraints import molecular, compare, ProposalError, EQUIVALENT, DISTINCT, BROADER, UNRESOLVED
from registry import initialize, FIXTURES, BASE
from unified_chemical import UnifiedChemicalResolver, reconcile_graphs
from chemistry import describe

class NameFixture:
    def __init__(self, values): self.values=values
    def opsin(self,name):
        return {'status':'SUCCESS','smiles':self.values[name],'diagnostic':'synthetic graph assertion'} if name in self.values else {'status':'FAILURE'}

class V11Tests(unittest.TestCase):
    def setUp(self):
        self.path=FIXTURES/('v11test_'+uuid.uuid4().hex+'.sqlite')
        self.reg=initialize(self.path)
        self.router=UnifiedChemicalResolver(self.reg,BASE/'output/registry.sqlite',name_adapter=NameFixture({'broad':'CC(O)F','R':'C[C@H](O)F','S':'C[C@@H](O)F','ethanol':'CCO'}))
    def tearDown(self):
        for suffix in ('','-journal','-wal','-shm'):
            p=Path(str(self.path)+suffix)
            if p.exists():p.unlink()
    def test_expansion_and_rejections(self):
        for smiles in ['CC(O)F','CC(O)Cl','CC(O)Br','CC(O)I','CC(O)CS','CC(O)CP(=O)(O)O','CC(O)C[Si](C)(C)C','CC(O)CB(O)O']:
            with self.subTest(smiles=smiles):
                p=molecular(smiles);self.assertEqual(p['stereo_state'],'UNASSIGNED_IN_REPRESENTATION');self.assertEqual(len(p['isomers']),2)
                with self.assertRaises(ProposalError):molecular(smiles+'.Cl')
        for smiles in ['[13CH3]C(O)F','CC(O)F.Cl','[NH3+]C(C)C(=O)[O-]','Cl[Pt@SP1](Cl)(N)N','CC(O)[Fe]','CC(O)F garbage']:
            with self.subTest(smiles=smiles),self.assertRaises(ProposalError):molecular(smiles)
    def test_traversal_and_open_stereo(self):
        a=molecular('CC(O)F');b=molecular('FC(O)C')
        self.assertEqual(compare(a,b),EQUIVALENT)
        self.assertEqual(reconcile_graphs(describe('CC(O)F'),describe('C[C@H](O)F'))[1],'RIGHT_MORE_SPECIFIC')
        self.assertEqual(reconcile_graphs(describe('C[C@@H](O)F'),describe('C[C@H](O)F'))[1],'CONFLICTING_STEREOCHEMISTRY')
        self.assertEqual(compare(molecular('CC(O)C(O)CC'),molecular('C[C@@H](O)C(O)CC')),BROADER)
        self.assertEqual(compare(molecular('C[C@@H](O)C(O)CC'),molecular('C[C@H](O)C(O)CC')),DISTINCT)
        self.assertGreaterEqual(len(molecular('CC=CCC(O)C')['isomers']),4)
        self.assertEqual(compare(molecular('C/C=C/CC(O)C'),molecular('C/C=C\\CC(O)C')),DISTINCT)
    def test_routing_idempotency_and_conflict(self):
        a=self.router.resolve({'smiles':'CC(O)F'},request_key='first')
        b=self.router.resolve({'smiles':'FC(O)C'},request_key='second')
        c=self.router.resolve({'smiles':'CC(O)F'},request_key='first')
        self.assertEqual([a['outcome'],b['outcome'],c['outcome']],['CHEMICAL_CONCEPT_CREATED','CHEMICAL_CONCEPT_REUSED','CHEMICAL_CONCEPT_REUSED'])
        self.assertEqual(a['concept_id'],b['concept_id']);self.assertEqual(b['concept_id'],c['concept_id'])
        with self.assertRaisesRegex(ValueError,'IDEMPOTENCY_CONFLICT'):
            self.reg.create_or_reuse({'kind':'molecular','smiles':'CC(O)F'},'CC(O)F','first',evidence={'different':'source claim'})
        self.assertEqual(self.router.resolve({'name':'R','smiles':'C[C@@H](O)F'},request_key='bad')['outcome'],'CONFLICT')
        self.assertEqual(self.router.resolve({'name':'R','smiles':'CC(O)F'},request_key='specific')['outcome'],'UNRESOLVED') # exact requires qualified Substance adapter
        self.assertEqual(self.router.resolve({'name':'ethanol','smiles':'CC(O)F'},request_key='constitution')['outcome'],'CONFLICT')
        self.assertEqual(self.router.resolve({'smiles':'CC(O)F','inchi_key':'WRONG'},request_key='badkey')['outcome'],'CONFLICT')
        self.assertEqual(self.router.resolve({'smiles':'CC(O)F','inchikey':describe('CC(O)F')['inchikey'],
                                             'inchi_key':describe('CCO')['inchikey']},request_key='two-keys')['outcome'],'CONFLICT')
        self.assertEqual(self.router.resolve({'smiles':'CC(O)F.Cl'},request_key='salt')['outcome'],'UNRESOLVED')
        self.assertEqual(self.router.resolve({'smiles':'CCO'},request_key='exact')['outcome'],'UNRESOLVED')
    def test_rollback_and_concurrency(self):
        proposal={'kind':'molecular','smiles':'CC(O)F'}
        with self.assertRaises(RuntimeError):self.reg.create_or_reuse(proposal,'CC(O)F','fail',fail_after_insert=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            rs=list(pool.map(lambda k:self.reg.create_or_reuse(proposal,'CC(O)F',k),['r1','r2']))
        self.assertEqual(sorted(r['outcome'] for r in rs),['CREATED','REUSED'])
        self.assertEqual(len({r['concept_id'] for r in rs}),1)
    def test_64_budget(self):
        with self.assertRaisesRegex(ProposalError,'STEREO_ENUMERATION_LIMIT'):
            molecular('CC(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C')

    def test_frozen_regression_corpus(self):
        import json
        for c in json.loads((Path(__file__).parent/'v11_regression_corpus.json').read_text(encoding='utf8'))['cases']:
            with self.subTest(case=c['id']):
                try:molecular(c['smiles']);actual='SUPPORTED'
                except ProposalError as exc:actual=exc.code
                self.assertEqual(actual,c['expect'])

    def test_real_exact_match_pipeline_and_adapter_binding(self):
        import sys
        sys.path.insert(0,str(BASE/'unified_substance_resolution'))
        from evaluate_pipeline import SyntheticAdapter
        from unified_resolver import SubstanceResolver
        from providers import Bridge
        from registry_matching_models import RetrievalPolicy
        bridge=Bridge()
        try:
            router=UnifiedChemicalResolver(self.reg,BASE/'canonical_registry_matching/fixtures/D01.sqlite',substance_resolver=SubstanceResolver(official_validator=bridge.official))
            matched=router.resolve({'case':'D01','smiles':'CCO'},source_adapter=SyntheticAdapter(),request_key='exact')
            self.assertEqual(matched['outcome'],'EXACT_SUBSTANCE_MATCH',matched)
            self.assertEqual(matched['substance_id'],'FIX_1')
            bounded=router.resolve({'case':'D01','smiles':'CCO'},source_adapter=SyntheticAdapter(),request_key='bounded',retrieval_policy=RetrievalPolicy(exhaustive=False,max_candidates=1,allow_exploratory_names=False))
            self.assertEqual(bounded['outcome'],'SUBSTANCE_SEARCH_INCOMPLETE',bounded)
            self.assertFalse(bounded['substance_search']['retrieval']['search_complete'])
            self.assertIsNone(bounded['substance_id'])
            truncated=router.resolve({'case':'D01','smiles':'CCO'},source_adapter=SyntheticAdapter(),request_key='truncated',retrieval_policy=RetrievalPolicy(exhaustive=True,max_candidates=1,allow_exploratory_names=False,strategy='exhaustive'))
            self.assertEqual(truncated['outcome'],'SUBSTANCE_SEARCH_INCOMPLETE',truncated)
            self.assertIn('CANDIDATE_RETRIEVAL_TRUNCATED',truncated['diagnostics'])
            mismatch=router.resolve({'case':'D01','smiles':'CCN'},source_adapter=SyntheticAdapter(),request_key='mismatch')
            self.assertEqual(mismatch['outcome'],'UNRESOLVED')
            self.assertIn('QUALIFIED_GRAPH_DOES_NOT_ESTABLISH_SAME_EXACT_IDENTITY',mismatch['diagnostics'])
            self.assertIsNone(mismatch['substance_id'])
            no_match_router=UnifiedChemicalResolver(self.reg,BASE/'canonical_registry_matching/fixtures/D02.sqlite',substance_resolver=SubstanceResolver(official_validator=bridge.official))
            no_match=no_match_router.resolve({'case':'D02','smiles':'CC[C@@H](C)O'},source_adapter=SyntheticAdapter(),request_key='no-match')
            self.assertEqual(no_match['outcome'],'EXACT_SUBSTANCE_NOT_IN_REGISTRY',no_match)
            self.assertIsNone(no_match['substance_id'])
        finally:bridge.close()

    def test_stereo_refinement_retains_name_derived_admission(self):
        import sys
        sys.path.insert(0,str(BASE/'unified_substance_resolution'))
        from evaluate_pipeline import SyntheticAdapter
        from unified_resolver import SubstanceResolver
        from providers import Bridge
        from test_provider_qualification import row
        exact='CC[C@H](C)O'
        name='(2S)-butan-2-ol'
        class Adapter(SyntheticAdapter):
            def adapt(self, packet):
                adapted=super().adapt(packet)
                adapted.incoming.name=name
                if packet.get('corroboration'):
                    evidence=row(exact,name=name)
                    evidence['provenance']['source_dependence_classification']='SOURCE_INDEPENDENT'
                    adapted.incoming.external_evidence={'status':'SUCCESS','rows':[evidence]}
                return adapted
        bridge=Bridge()
        try:
            # Select the real systematic name for the exact registry control.
            for candidate in ('(2R)-butan-2-ol','(2S)-butan-2-ol'):
                parsed=bridge.opsin(candidate)
                if parsed['status']=='SUCCESS' and describe(parsed['smiles'])['smiles']==describe(exact)['smiles']:
                    name=candidate
                    break
            else:self.fail('OPSIN did not establish the reference stereoisomer')
            router=UnifiedChemicalResolver(self.reg,BASE/'canonical_registry_matching/fixtures/D02.sqlite',
                name_adapter=bridge,substance_resolver=SubstanceResolver(official_validator=bridge.official))
            packet={'case':'D02','smiles':'CCC(C)O','override_graph':'CCC(C)O','name':name}
            uncorroborated=router.resolve(packet,source_adapter=Adapter())
            self.assertEqual(uncorroborated['outcome'],'UNRESOLVED',uncorroborated)
            self.assertIn('substance_search',uncorroborated,uncorroborated)
            self.assertFalse(uncorroborated['substance_search']['admission_eligible'])
            supported=router.resolve({**packet,'corroboration':True},source_adapter=Adapter())
            self.assertEqual(supported['outcome'],'EXACT_SUBSTANCE_MATCH',supported)
            self.assertEqual(supported['substance_id'],'FIX_1')
        finally:bridge.close()

    def test_stale_snapshot_and_unsupported_exact_are_withheld(self):
        import sys, sqlite3, shutil
        from contextlib import closing
        sys.path.insert(0,str(BASE/'unified_substance_resolution'))
        from evaluate_pipeline import SyntheticAdapter
        from unified_resolver import SubstanceResolver
        from registry_identity_adapter import RegistrySnapshot
        path=self.path.with_suffix('.snapshot.sqlite')
        try:
            shutil.copyfile(BASE/'canonical_registry_matching/fixtures/D01.sqlite',path)
            snapshot=RegistrySnapshot(path)
            router=UnifiedChemicalResolver(self.reg,snapshot,substance_resolver=SubstanceResolver())
            unsupported=router.resolve({'case':'D01','smiles':'[CH3]','override_graph':'[CH3]'},source_adapter=SyntheticAdapter())
            self.assertEqual(unsupported['outcome'],'UNRESOLVED')
            self.assertFalse(unsupported['substance_id'] or unsupported['concept_id'])
            with closing(sqlite3.connect(path)) as conn, conn:
                conn.execute("UPDATE substance_identity SET preferred_name='changed' WHERE substance_id='FIX_1'")
            stale=router.resolve({'case':'D01','smiles':'CCO'},source_adapter=SyntheticAdapter())
            self.assertEqual(stale['outcome'],'UNRESOLVED',stale)
            self.assertIn('REGISTRY_SNAPSHOT_CHANGED',stale['substance_search']['error']['message'])
            self.assertFalse(stale['substance_id'] or stale['concept_id'])
        finally:
            path.unlink(missing_ok=True)

    def test_name_failure_and_ambiguity_do_not_authorize_an_identity(self):
        for status in ('FAILURE','WARNING'):
            class Adapter:
                def opsin(self,name):
                    return {'status':status,'smiles':'CC(O)F','diagnostic':'control'}
            router=UnifiedChemicalResolver(self.reg,BASE/'output/registry.sqlite',name_adapter=Adapter())
            r=router.resolve({'smiles':'CC(O)F','name':'ambiguous label'},request_key=status)
            self.assertEqual(r['outcome'],'UNRESOLVED')
            self.assertIsNone(r['concept_id'])

    def test_qualified_complete_secondary_structure(self):
        import sys
        sys.path.insert(0,str(BASE/'unified_substance_resolution'))
        from evaluate_pipeline import SyntheticAdapter
        from unified_resolver import SubstanceResolver
        from evidence_adapter_contract import structural_field
        from providers import Bridge
        class Adapter(SyntheticAdapter):
            def adapt(self, packet):
                record=super().adapt(packet)
                incoming=record.incoming.concept
                c=structural_field(incoming.evidence_package,'secondary',packet['isometric_smiles'],'$.isometric_smiles')
                incoming.binding['evidence_ids'].append(c.evidence_id)
                return record
        bridge=Bridge()
        try:
            router=UnifiedChemicalResolver(self.reg,BASE/'canonical_registry_matching/fixtures/D02.sqlite',
                                            substance_resolver=SubstanceResolver(official_validator=bridge.official))
            packet={'case':'D02','smiles':'CCC(C)O','override_graph':'CCC(C)O','isometric_smiles':'CC[C@H](C)O'}
            r=router.resolve(packet,source_adapter=Adapter())
            self.assertEqual(r['outcome'],'EXACT_SUBSTANCE_MATCH',r)
            self.assertEqual(r['substance_id'],'FIX_1')
        finally:bridge.close()

if __name__=='__main__':unittest.main()
