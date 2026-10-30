"""Post-freeze evaluation only. No resolver invocation or provider requests."""
import json,sys,sqlite3,hashlib
from collections import Counter,defaultdict
from datetime import datetime,timezone
from itertools import combinations
from pathlib import Path
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors
H=Path(__file__).resolve().parent;B=H.parent;sys.path.insert(0,str(B))
from form_aware_holdout.score_holdout import metrics,same,nonadmissible
from freeze_and_prepare import read,save,sha,protect

def molecule(s):
    p=Chem.SmilesParserParams();p.parseName=False;p.allowCXSMILES=False
    m=Chem.MolFromSmiles(s,p)
    if m is None:raise ValueError('Invalid full structure')
    return m

def raw_valid(row):
    try:
        s=row.get('SMILES') or row.get('IsomericSMILES');m=molecule(s)
        return s if Chem.MolToInchi(m)==row.get('InChI') and Chem.MolToInchiKey(m)==row.get('InChIKey') else None
    except Exception:return None

def dominant(reason,ref,ev,kind):
    if kind=='CONFIRMED_FALSE_POSITIVE_EXACT':return 'unsafe admission'
    if kind=='CONFIRMED_WRONG_ALIAS':return 'unsafe alias promotion'
    s=reason.upper();forms=ref.get('form_categories',[])
    if 'INCOMPLETE_SOURCE' in s:return 'source-name ambiguity'
    if 'INVALID' in s or 'MALFORMED' in s:return 'invalid input' if 'PROVIDER' not in s else 'provider disagreement'
    if 'LINEAGE' in s or 'INDEPENDENT' in s:return 'evidence dependence/provenance'
    if 'ISOTOPE' in s:return 'isotope position unknown'
    if 'STEREO_SOURCE' in s:return 'stereo source intent'
    if 'STEREO' in s:return 'stereo interpretation'
    if 'TAUTOMER' in s:return 'tautomer conflict'
    if 'HYDRATION' in s:return 'hydration stoichiometry'
    if 'COORDINATION' in s or 'ELECTRONIC' in s:return 'coordination/electronic-state unsupported'
    if 'EXTENDED' in s or 'ELEMENT_UNSUPPORTED' in s:return 'extended material unsupported'
    if 'COMPONENT' in s or 'COUNTERION' in s:
        return 'solvate scope' if 'solvate' in forms else 'hydration stoichiometry' if 'hydrate' in forms else 'salt semantics' if 'salt' in forms else 'component stoichiometry'
    if 'PROTONATION' in s or 'CHARGE' in s:return 'protonation/charge ambiguity'
    if 'PARSER_WARNING' in s:return 'parser warning'
    if 'PROVIDER' in s or 'DIMENSION_CONFLICT' in s:return 'provider disagreement'
    if 'EXCLUDED' in s or 'ENSEMBLE' in s:return 'ensemble/scope classification'
    if 'DIMENSION_UNKNOWN' in s:return 'unresolved identity dimension'
    if 'EVIDENCE' in s or 'CORROBORATION' in s:return 'evidence retrieval incomplete'
    if 'NO_VALIDATED_CANDIDATE' in s:return 'parser failure and retrieval incomplete'
    return 'reference uncertainty' if kind=='UNVERIFIED_ADMISSION' else 'source-name ambiguity'

def route_audit(row,ev):
    queries=ev.get('retrieval',{}).get('queries',[]);used=ev.get('decision',{}).get('validated_rows',[])
    paths=set();lineages=[]
    for r in used:
        p=r.get('provenance',{});lineages.append(p)
        if p.get('query_type')=='InChIKey':paths.add('full InChIKey')
        if p.get('query_type') in ('InChI','SMILES'):paths.add('InChI/complete structure')
        if r.get('provider')=='GSRS':paths.add('GSRS')
        if p.get('query_origin')=='source_identifier':paths.add('supplied identifier')
        if p.get('query_origin')=='validated_exact_provider_name':paths.add('validated provider name')
    if ev.get('local_source_support'):paths.add('validated original alias')
    original=[q for q in queries if q['provider'] in ('PubChem','ChEBI') and q.get('purpose')=='primary' and q.get('retrieval_key',{}).get('origin')=='source_preferred_name']
    initialrows=[r for q in original for r in q.get('rows',[])];primary=(ev.get('claims') or [{}])[0]
    counter='UNKNOWN';explanation='Insufficient recorded pre-expansion evidence for causal inference.'
    if len(original)==2 and row['predicted_status']=='EXACT':
        if any(q['provider']=='ChEBI' and q['status']=='INCOMPLETE' for q in original):
            counter='WOULD_REMAIN_UNRESOLVED';explanation='Original ChEBI name evidence was incomplete.'
        elif not initialrows:
            counter='WOULD_REMAIN_UNRESOLVED';explanation='Original PubChem/ChEBI name path supplied no corroborating structure.'
        elif primary.get('status')!='SUCCESS' and not {'PubChem','ChEBI'}<={r.get('provider') for r in initialrows}:
            counter='WOULD_REMAIN_UNRESOLVED';explanation='Primary name did not parse; the older external-only path lacked both PubChem and ChEBI support.'
        elif all(raw_valid(r) and same(raw_valid(r),row['predicted_smiles'][0]) for r in initialrows):
            counter='OLDER_NAME_PATH_SUFFICIENT';explanation='Original name evidence already matches the admitted graph; form/official checks are unchanged. Additional routes are not shown necessary.'
    comparisons=ev.get('retrieval',{}).get('candidate_comparisons',[])
    related=[c for c in comparisons if (c.get('comparison') or {}).get('assessment') in ('DISTINCT','UNRESOLVED')]
    return dict(cuma_index=row['cuma_index'],preferred_name=row['preferred_name'],predicted_status=row['predicted_status'],reference_verdict=row['exact_verdict'],supporting_increment_routes=sorted(paths),older_path_counterfactual=counter,counterfactual_basis=explanation,counterfactual_method='Saved trace inference, not another resolver execution',lineage=lineages,source_alias_support=ev.get('local_source_support',{}).get('alias'),query_routes=[dict(provider=q['provider'],kind=q['retrieval_key']['kind'],origin=q['retrieval_key']['origin'],status=q['status']) for q in queries],near_or_conflicting_discoveries=related,blocking_contradiction=row['predicted_status']=='CONFLICT')

def pair_relation(a,b):
    if a['expected_status']!= 'EXACT' or b['expected_status']!='EXACT':return 'REFERENCE_NOT_FULLY_ASSESSABLE'
    x,y=a['expected_smiles'],b['expected_smiles']
    if same(x,y):return 'EXACT_REFERENCE_IDENTITY'
    ma,mb=molecule(x),molecule(y)
    sa,sb=Chem.Mol(ma),Chem.Mol(mb);Chem.RemoveStereochemistry(sa);Chem.RemoveStereochemistry(sb)
    if Chem.MolToSmiles(sa)==Chem.MolToSmiles(sb):return 'STEREOCHEMICAL_DIFFERENCE'
    ia,ib=Chem.Mol(ma),Chem.Mol(mb)
    for m in (ia,ib):
        for atom in m.GetAtoms():atom.SetIsotope(0)
    if Chem.MolToSmiles(ia)==Chem.MolToSmiles(ib):return 'ISOTOPE_DIFFERENCE'
    ca=Counter(Chem.MolToSmiles(f) for f in Chem.GetMolFrags(ma,asMols=True));cb=Counter(Chem.MolToSmiles(f) for f in Chem.GetMolFrags(mb,asMols=True))
    da,db=ca-cb,cb-ca;changed=set(da)|set(db)
    if changed and changed<= {'O'}:return 'HYDRATION_NUMBER_DIFFERENCE'
    if len(ca)>1 or len(cb)>1:return 'COMPONENT_OR_CHARGE_DIFFERENCE'
    if a['expected_inchikey']==b['expected_inchikey']:return 'DISTINCT_GRAPH_WITH_SHARED_STANDARD_KEY'
    if rdMolDescriptors.CalcMolFormula(ma)==rdMolDescriptors.CalcMolFormula(mb):return 'CONSTITUTIONAL_OR_OTHER_FORM_DIFFERENCE'
    return 'DISTINCT_REFERENCE_IDENTITIES'

def pair_row(a,b,hint=None):
    admitted=a['predicted_status']==b['predicted_status']=='EXACT';co=admitted and a['substance_id']==b['substance_id'];rel=pair_relation(a,b)
    return dict(a=a['cuma_index'],b=b['cuma_index'],name_a=a['preferred_name'],name_b=b['preferred_name'],sampling_hint=hint,reference_relation=rel,expected_a=a['expected_status'],expected_b=b['expected_status'],predicted_a=a['predicted_status'],predicted_b=b['predicted_status'],both_admitted=admitted,coassigned=co,result='FALSE_MERGE' if co and rel not in ('REFERENCE_NOT_FULLY_ASSESSABLE','EXACT_REFERENCE_IDENTITY') else 'UNASSESSED_COASSIGNMENT' if co and rel=='REFERENCE_NOT_FULLY_ASSESSABLE' else 'CORRECT_EXACT_CLUSTER' if co else 'BOTH_ADMITTED_DISTINCT' if admitted else 'ONE_WITHHELD' if (a['predicted_status']=='EXACT')!=(b['predicted_status']=='EXACT') else 'BOTH_WITHHELD')

def main():
    protect();frozen=read(H/'ADJUDICATION_FROZEN.json');sf=read(H/'SCORING_PROTOCOL_FROZEN.json')
    for p,v in frozen['files'].items():assert sha(H/p)==v,p
    for p,v in sf['files'].items():assert sha(H/p)==v,p
    assert read(H/'RUN_FINISHED.json')['returncode']==0
    assert not (H/'METRICS_FROZEN.json').exists(),'Never silently rescore frozen results'
    refs={};source={}
    for n in (1,2,3):
        refs.update({r['cuma_index']:r for r in read(H/f'packet_{n}/reference.json')})
        source.update({r['cuma_index']:r for r in read(H/f'packet_{n}/records.json')})
    cand=sqlite3.connect((H/'predictions/candidates.sqlite').as_uri()+'?mode=ro',uri=True);reg=sqlite3.connect((H/'predictions/registry.sqlite').as_uri()+'?mode=ro',uri=True)
    rows=[];aliases=[];disagreements=[];routes=[];qcounts=Counter();http=defaultdict(Counter);failurequeries=[]
    for i,name,rawaliases,status,reason,raw in cand.execute('SELECT * FROM candidate ORDER BY cuma_index'):
        ref=refs[i];ev=json.loads(raw);orig=source[i];assert name==orig['preferred_name'] and json.loads(rawaliases)==orig['aliases']
        sid,rs,rr=reg.execute('SELECT substance_id,resolution_status,reason FROM substance_reconciliation WHERE cuma_index=?',(i,)).fetchone();assert (status,reason)==(rs,rr)
        structures=[x[0] for x in reg.execute("SELECT structure_value FROM substance_structure WHERE substance_id=? AND structure_type='SMILES'",(sid,))]
        verdict=av=kind=None
        if status=='EXACT':
            assert structures
            verdict=('CORRECT' if all(same(s,ref['expected_smiles']) for s in structures) else 'INCORRECT') if ref['expected_status']=='EXACT' else 'INCORRECT' if nonadmissible(ref) else 'UNVERIFIED'
            if verdict=='INCORRECT':kind='CONFIRMED_FALSE_POSITIVE_EXACT'
            elif verdict=='UNVERIFIED':kind='UNVERIFIED_ADMISSION'
        else:
            av='EXCESSIVE' if ref['expected_status']=='EXACT' else 'CORRECT' if nonadmissible(ref) else 'UNVERIFIED'
            if av=='EXCESSIVE':kind='REFERENCE_EXACT_WITHHELD'
            elif status!=ref['expected_status']:kind='NONADMISSION_STATUS_DISAGREEMENT' if av=='CORRECT' else 'REFERENCE_UNCERTAINTY'
        row=dict(cuma_index=i,preferred_name=name,expected_status=ref['expected_status'],expected_smiles=ref.get('expected_smiles'),expected_inchikey=ref.get('expected_inchikey'),predicted_status=status,predicted_smiles=structures,substance_id=sid,exact_verdict=verdict,abstention_verdict=av,reference_nonadmissible=nonadmissible(ref),reference_reason=ref['reason'],reference_abstention_basis=ref.get('abstention_basis'),reference_categories=ref['form_categories'],resolver_reason=reason,disagreement_type=kind,dominant_cause=dominant(reason,ref,ev,kind) if kind else None,evidence=ref['evidence'],dimensions=ref['dimensions'])
        rows.append(row)
        if kind:disagreements.append(row)
        routes.append(route_audit(row,ev))
        for q in ev.get('retrieval',{}).get('queries',[]):
            key=q['retrieval_key'];qcounts[(q['provider'],key['kind'],key['origin'],q['purpose'],q['status'])]+=1
            for rawq in q.get('retrieval',[q]):
                if rawq.get('url') and rawq.get('status')!='NOT_QUERIED':http[q['provider']][rawq['url']]+=1
            if q['status'] not in ('SUCCESS',):failurequeries.append(dict(cuma_index=i,provider=q['provider'],kind=key['kind'],origin=key['origin'],status=q['status'],diagnostic=q.get('diagnostic')))
        refaliases={a['alias_position']:a for a in ref['alias_judgments']};positions=defaultdict(list);seen=Counter()
        for j,a in enumerate(orig['aliases']):positions[a].append(j)
        for a in ev.get('alias_decisions',[]):
            j=positions[a['alias']][seen[a['alias']]];seen[a['alias']]+=1
            if not a.get('accepted'):continue
            ar=refaliases[j];v='UNVERIFIED'
            if verdict=='CORRECT' and ar['judgment'] in ('SAME','DIFFERENT'):v='CORRECT' if ar['judgment']=='SAME' else 'INCORRECT'
            elif verdict=='INCORRECT' and ref['expected_status']=='EXACT' and ar['judgment']=='SAME':v='INCORRECT'
            item=dict(cuma_index=i,alias_position=j,alias=a['alias'],reference_judgment=ar['judgment'],verdict=v,reference_reason=ar['reason'],evidence_urls=ar.get('evidence_urls',[]));aliases.append(item)
            if v=='INCORRECT':disagreements.append(dict(**item,disagreement_type='CONFIRMED_WRONG_ALIAS',dominant_cause='unsafe alias promotion'))
    assert len(rows)==400
    overall=metrics(rows,aliases);forms={}
    for tag in ['straightforward','stereo','isotope','protonation_charge','salt','hydrate','solvate','tautomer','multicomponent','out_of_scope']:
        subset=[r for r in rows if tag in r['reference_categories']];ids={r['cuma_index'] for r in subset}
        forms[tag]=metrics(subset,[a for a in aliases if a['cuma_index'] in ids])
    by={r['cuma_index']:r for r in rows};selection=read(H/'steward/selection.json')
    near=[pair_row(by[p['a']],by[p['b']],p['sampling_hint']) for p in selection['pair_candidates']]
    coassigned=[];reference_exact_pairs=[]
    for a,b in combinations(rows,2):
        if a['predicted_status']==b['predicted_status']=='EXACT' and a['substance_id']==b['substance_id']:coassigned.append(pair_row(a,b))
        if a['expected_status']==b['expected_status']=='EXACT' and a['expected_inchikey']==b['expected_inchikey'] and same(a['expected_smiles'],b['expected_smiles']):reference_exact_pairs.append(pair_row(a,b))
    summary=read(H/'predictions/summary.json');usage={}
    for provider,folder,budget,countkey in [('PubChem','http_cache',2400,'pubchem_requests'),('ChEBI','chebi_cache',4000,'chebi_requests'),('GSRS','gsrs_cache',800,'gsrs_requests')]:
        cache=list((H/'predictions'/folder).glob('*.json'));data=[read(p) for p in cache]
        assert len(cache)==summary[countkey],(provider,'fresh request/cache discrepancy')
        usage[provider]=dict(http_requests=summary[countkey],budget=budget,budget_fraction=summary[countkey]/budget,cache_entries=len(cache),cache_statuses=dict(Counter(x['status'] for x in data)),cached_failure_reasons=dict(Counter(x.get('diagnostic','unspecified') for x in data if x['status']=='ERROR')),recorded_http_observations=sum(http[provider].values()),observed_cache_hits=sum(n-1 for n in http[provider].values()),cache_hit_method='Repeated recorded URLs in a fresh-cache run; does not count in-memory query deduplication')
    supplemental=[];prior={x['cuma_index']:x for x in read(B/'evidence_upgrade/new_unverified_admissions.json')}
    for r in read(H/'supplemental/reference.json'):
        old=prior[r['cuma_index']];v=('confirmed correct' if all(same(s,r['expected_smiles']) for s in old['predicted_smiles']) else 'contradicted') if r['expected_status']=='EXACT' else 'contradicted' if nonadmissible(r) else 'still unresolved'
        supplemental.append(dict(cuma_index=r['cuma_index'],preferred_name=r['preferred_name'],review=v,reference_status=r['expected_status'],reason=r['reason'],independent_structure=r.get('expected_smiles'),previous_prediction=old['predicted_smiles'],evidence=r['evidence'],excluded_from_holdout_metrics=True))
    taxonomy=Counter(r['dominant_cause'] for r in disagreements);losses=Counter(r['dominant_cause'] for r in rows if r['disagreement_type']=='REFERENCE_EXACT_WITHHELD')
    outputs={'metrics.json':overall,'comparison.json':rows,'alias_comparison.json':aliases,'by_reference_form.json':forms,'disagreements.json':disagreements,'near_form_pairs.json':near,'coassigned_pairs.json':coassigned,'reference_exact_pairs.json':reference_exact_pairs,'retrieval_routes.json':routes,'provider_usage.json':dict(providers=usage,query_modes=[dict(provider=p,kind=k,origin=o,purpose=u,status=s,count=n) for (p,k,o,u,s),n in sorted(qcounts.items())],non_success_queries=failurequeries),'supplemental_review.json':supplemental,'taxonomy.json':dict(disagreements=dict(taxonomy),confirmed_identity_losses=dict(losses))}
    for name,data in outputs.items():save(H/name,data)
    cand.close();reg.close()
    save(H/'METRICS_FROZEN.json',dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),evaluation_type='second fresh blinded holdout',files={name:sha(H/name) for name in outputs},prediction_hashes={name:sha(H/'predictions'/name) for name in ('registry.sqlite','candidates.sqlite')},adjudication_sha256=sha(H/'ADJUDICATION_FROZEN.json'),scoring_protocol_sha256=sha(H/'SCORING_PROTOCOL_FROZEN.json'),gaps_ranked=False))
    print(json.dumps(overall,indent=2))

if __name__=='__main__':main()
