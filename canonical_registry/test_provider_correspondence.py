import unittest
from chemistry import describe
from evidence_model import assess,aggregate_route,CORROBORATES,CONTRADICTS,NON_DISCRIMINATING,PROVIDER_RECORD_AMBIGUOUS,UNAVAILABLE
from evidence_retrieval import provenance,deduplicate
from policy import decision
from test_evidence_retrieval import engine,Provider
from test_provider_qualification import row

def routed(smiles,query,kind='name',origin='source_preferred_name',cid=123):
    r=row(smiles,name=query,kind=kind,origin=origin,value=query);r['CID']=cid
    if kind=='InChIKey':r['InChIKey']=describe(smiles)['inchikey']
    return r

class CorrespondenceTests(unittest.TestCase):
    def test_candidate_key_is_discovery_only(self):
        d=describe('CCO');p=Provider({('InChIKey',d['inchikey']):[routed('CCO',d['inchikey'],kind='InChIKey',origin='validated_hypothesis')]})
        r=engine({'ethanol':'CCO'},p,Provider()).evaluate('ethanol')
        self.assertEqual(r['status'],'UNRESOLVED');self.assertEqual(r['reason_codes'],['NO_QUALIFYING_CORROBORATION'])
        self.assertTrue(all(not a['used_for_corroboration'] for a in r['evidence']['retrieval']['candidate_comparisons'] if a['provenance']['query_origin']=='validated_hypothesis'))
    def test_source_key_can_corroborate(self):
        d=describe('CCO');r=routed('CCO',d['inchikey'],kind='InChIKey',origin='source_identifier')
        self.assertEqual(assess(r,d)['state'],CORROBORATES)
    def test_exact_returned_name(self):self.assertEqual(assess(routed('CCO','ethanol'),describe('CCO'))['state'],CORROBORATES)
    def test_ambiguity_order_independent(self):
        good=assess(routed('CCO','ethanol',cid=1),describe('CCO'));bad=assess(routed('CO','ethanol',cid=2),describe('CCO'))
        for items in ([good,bad],[bad,good]):self.assertEqual(aggregate_route(items),PROVIDER_RECORD_AMBIGUOUS)
    def test_identical_records_and_nondiscriminating(self):
        a=assess(routed('CCO','ethanol',cid=1),describe('CCO'));b=assess(routed('OCC','ethanol',cid=2),describe('CCO'))
        self.assertEqual(aggregate_route([a,b]),CORROBORATES)
        self.assertEqual(aggregate_route([a,dict(state=NON_DISCRIMINATING)]),CORROBORATES)
    def test_distinct_route_survives_dedup_and_ambiguity(self):
        source=describe('CCO');good=routed('CCO','ethanol',cid=1);bad=routed('CO','ethanol',cid=2)
        exact=routed('CCO','1',kind='PubChemCID',origin='source_identifier',cid=1)
        rows,discarded=deduplicate([good,bad,exact]);self.assertEqual(len(rows),3)
        result=decision(source,{'status':'SUCCESS','agrees':True},{'rows':rows},'ethanol',source_complete=True)
        self.assertEqual(result['status'],'AUTO_ACCEPT')
        self.assertEqual({a['route']:a['state'] for a in result['provider_routes']},{'name':PROVIDER_RECORD_AMBIGUOUS,'PubChemCID':CORROBORATES})
    def test_ambiguous_only_cannot_accept_or_conflict(self):
        d=describe('CCO');rows=[routed('CCO','ethanol',cid=1),routed('CO','ethanol',cid=2)]
        r=decision(d,{'status':'SUCCESS','agrees':True},{'rows':rows},'ethanol',source_complete=True)
        self.assertEqual(r['status'],'UNRESOLVED');self.assertEqual(r['provider_routes'][0]['state'],PROVIDER_RECORD_AMBIGUOUS)
    def test_typed_structure_ambiguity_neutral(self):
        d=describe('CCO');rows=[routed('CCO','ethanol',cid=1),routed('CO','ethanol',cid=2)]
        r=decision(d,{'status':'SUCCESS','agrees':True},{'rows':rows},'ethanol',{'explicit_structure':True},source_complete=True)
        self.assertEqual(r['status'],'AUTO_ACCEPT')
    def test_unavailable(self):self.assertEqual(aggregate_route([],status='ERROR'),UNAVAILABLE)

if __name__=='__main__':unittest.main()
