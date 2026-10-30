"""Development scoring only; frozen reference files never enter the resolver."""
import json,hashlib,sqlite3
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
from form_aware_holdout.score_holdout import metrics,same,nonadmissible

B=Path(__file__).resolve().parent;H=B/'evidence_upgrade';F=B/'form_aware_holdout'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):(H/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def protected_check():
    baseline=read(H/'BASELINE.json');allowed={'providers.py','resolver.py','pipeline.py','verify.py','registry_builder.py','README.md'}
    protected=[];changed=[]
    for path,digest in baseline['files'].items():
        p=Path(path)
        if p.parent==B and p.name in allowed:
            if sha(p)!=digest:changed.append(p.name)
        else:
            assert sha(p)==digest,path;protected.append(path)
    for path,digest in read(H/'IMPLEMENTATION_FROZEN.json')['runtime_hashes'].items():assert sha(B/path)==digest,path
    return dict(protected_unchanged=protected,allowed_changed=changed)

def main():
    protection=protected_check();refs={};originals={}
    for n in (1,2,3):
        refs.update({r['cuma_index']:r for r in read(F/f'packet_{n}/reference.json')})
        originals.update({r['cuma_index']:r for r in read(F/f'packet_{n}/records.json')})
    baseline={r['cuma_index']:r for r in read(F/'comparison.json')}
    run=H/'run';db=sqlite3.connect((run/'candidates.sqlite').as_uri()+'?mode=ro',uri=True);reg=sqlite3.connect((run/'registry.sqlite').as_uri()+'?mode=ro',uri=True)
    rows=[];aliases=[];safety=[];query_modes=Counter();query_results=Counter();http=Counter();allqueries=[]
    for i,name,rawaliases,status,reason,raw in db.execute('SELECT * FROM candidate ORDER BY cuma_index'):
        r=refs[i];ev=json.loads(raw);orig=originals[i];before=baseline[i]
        assert name==orig['preferred_name'] and json.loads(rawaliases)==orig['aliases']
        sid,rs,rr=reg.execute('SELECT substance_id,resolution_status,reason FROM substance_reconciliation WHERE cuma_index=?',(i,)).fetchone();assert (rs,rr)==(status,reason)
        structures=[x[0] for x in reg.execute("SELECT structure_value FROM substance_structure WHERE substance_id=? AND structure_type='SMILES'",(sid,))]
        verdict=av=None
        if status=='EXACT':
            assert structures
            verdict=('CORRECT' if all(same(s,r['expected_smiles']) for s in structures) else 'INCORRECT') if r['expected_status']=='EXACT' else 'INCORRECT' if nonadmissible(r) else 'UNVERIFIED'
        else:av='EXCESSIVE' if r['expected_status']=='EXACT' else 'CORRECT' if nonadmissible(r) else 'UNVERIFIED'
        queries=ev.get('retrieval',{}).get('queries',[])
        for q in queries:
            key=q['retrieval_key'];query_modes[(q['provider'],key['kind'],key['origin'],q['purpose'])]+=1;query_results[(q['provider'],q['status'])]+=1
            allqueries.append(dict(cuma_index=i,provider=q['provider'],kind=key['kind'],origin=key['origin'],purpose=q['purpose'],status=q['status']))
            for rawq in q.get('retrieval',[]):
                if rawq.get('diagnostic'):http[(q['provider'],rawq['diagnostic'])]+=1
        row=dict(cuma_index=i,preferred_name=name,expected_status=r['expected_status'],expected_smiles=r.get('expected_smiles'),expected_inchikey=r.get('expected_inchikey'),predicted_status=status,substance_id=sid,predicted_smiles=structures,exact_verdict=verdict,abstention_verdict=av,reference_nonadmissible=nonadmissible(r),reference_categories=r['form_categories'],reference_reason=r['reason'],reference_abstention_basis=r.get('abstention_basis'),baseline_status=before['predicted_status'],baseline_reason=before['resolver_reason'],baseline_verdict=before['exact_verdict'],reason=reason,local_source_support=ev.get('local_source_support',{}).get('kind'),support_alias=ev.get('local_source_support',{}).get('alias'),evidence=r['evidence'])
        rows.append(row)
        positions=defaultdict(list)
        for j,a in enumerate(orig['aliases']):positions[a].append(j)
        seen=Counter();refaliases={a['alias_position']:a for a in r['alias_judgments']}
        for a in ev.get('alias_decisions',[]):
            j=positions[a['alias']][seen[a['alias']]];seen[a['alias']]+=1
            if not a.get('accepted'):continue
            assert reg.execute('SELECT 1 FROM substance_alias WHERE substance_id=? AND alias=?',(sid,a['alias'])).fetchone()
            ar=refaliases[j];v='UNVERIFIED'
            if verdict=='CORRECT' and ar['judgment'] in ('SAME','DIFFERENT'):v='CORRECT' if ar['judgment']=='SAME' else 'INCORRECT'
            elif verdict=='INCORRECT' and r['expected_status']=='EXACT' and ar['judgment']=='SAME':v='INCORRECT'
            aliases.append(dict(cuma_index=i,alias_position=j,alias=a['alias'],reference_judgment=ar['judgment'],verdict=v,reference_reason=ar['reason'],evidence_urls=ar.get('evidence_urls',[])))
        if status=='EXACT' and before['predicted_status']!='EXACT':
            dec=ev['decision'];form=dec['form'];chosen=dec['structure'];support=ev.get('local_source_support')
            initial=ev['claims'][0].get('structure') or (support or {}).get('claim',{}).get('structure')
            comparisons=dec['comparisons']
            facts=dict(source_form_specified=form['specification']=='SPECIFIED',source_name_preserved=name==orig['preferred_name'],all_used_dimensions_equivalent=bool(comparisons) and all(all(v in ('EQUIVALENT','NOT_APPLICABLE') for v in c['comparison']['dimensions'].values()) for c in comparisons),official_inchi_agrees=ev['official_inchi']['agrees'],local_support_graph_preserved=bool(initial) and same(initial['smiles'],chosen['smiles']),canonical_graph_preserved=all(same(s,chosen['smiles']) for s in structures),no_original_form_gate_reasons=not form['reason_codes'])
            assert all(facts.values()),(i,facts)
            methods=sorted({(x.get('provider'),x.get('provenance',{}).get('query_type'),x.get('provenance',{}).get('query_origin')) for x in dec['validated_rows']})
            safety.append(dict(**row,engine_guard_verdict='PASS',independent_reference_verdict=verdict,guards=facts,form_categories=form['categories'],form_features={k:form['features'][k] for k in ['component_stoichiometry','stereo_state','isotopes','charge','hydrogen_count','elements']},source_form_assertion=form.get('source_assertion'),retrieval_capabilities=methods,query_trace=[q for q in allqueries if q['cuma_index']==i],new_identity_structure=chosen['smiles'],new_identity_inchikey=chosen['inchikey'],note='Guard PASS is internal evidence consistency; an UNVERIFIED frozen reference remains unverified. No isotope/stereo/proton/tautomer/component transformation was applied to the validated support graph.'))
    assert len(rows)==360
    after=metrics(rows,aliases);before=read(F/'metrics.json')
    forms={}
    for tag in ['straightforward','stereo','isotope','protonation_charge','salt','hydrate','solvate','tautomer','multicomponent','out_of_scope']:
        subset=[r for r in rows if tag in r['reference_categories']];ids={r['cuma_index'] for r in subset};forms[tag]=metrics(subset,[a for a in aliases if a['cuma_index'] in ids])
    recovered=[r for r in safety if r['exact_verdict']=='CORRECT'];unverified=[r for r in safety if r['exact_verdict']=='UNVERIFIED'];revoked=[r for r in rows if r['baseline_status']=='EXACT' and r['predicted_status']!='EXACT'];conflicts=[r for r in rows if r['predicted_status']=='CONFLICT' and r['baseline_status']!='CONFLICT']
    changed_identities=[r for r in rows if r['baseline_status']==r['predicted_status']=='EXACT' and not all(same(s,t) for s in r['predicted_smiles'] for t in baseline[r['cuma_index']]['predicted_smiles'])]
    save('before_metrics.json',before);save('after_metrics.json',after);save('comparison.json',rows);save('alias_comparison.json',aliases);save('after_by_form.json',forms)
    for name,value in [('new_admission_safety.json',safety),('confirmed_recoveries.json',recovered),('new_unverified_admissions.json',unverified),('revoked_admissions.json',revoked),('new_conflicts.json',conflicts),('changed_retained_identities.json',changed_identities)]:save(name,value)
    save('provider_usage.json',dict(query_modes=[dict(provider=p,kind=k,origin=o,purpose=purpose,count=n) for (p,k,o,purpose),n in sorted(query_modes.items())],query_results=[dict(provider=p,status=s,count=n) for (p,s),n in sorted(query_results.items())],http_diagnostics=[dict(provider=p,diagnostic=d,count=n) for (p,d),n in sorted(http.items())]))
    manifest=dict(scored_at_utc=datetime.now(timezone.utc).isoformat(),evaluation_type='development re-evaluation',protection=protection,reference_hashes={str(p.relative_to(F)):sha(p) for p in F.glob('packet_*/reference.json')},prediction_hashes={f:sha(run/f) for f in ['registry.sqlite','candidates.sqlite']},scorer_sha256=sha(Path(__file__)),frozen_metric_implementation_sha256=sha(F/'score_holdout.py'),new_admissions=len(safety),confirmed_recoveries=len(recovered),new_unverified_admissions=len(unverified),revoked_admissions=len(revoked),new_conflicts=len(conflicts),changed_retained_identities=len(changed_identities))
    save('SCORING_MANIFEST.json',manifest);db.close();reg.close()
    print(json.dumps(dict(after=after,changes={k:manifest[k] for k in ['new_admissions','confirmed_recoveries','new_unverified_admissions','revoked_admissions','new_conflicts','changed_retained_identities']}),indent=2))

if __name__=='__main__':main()
