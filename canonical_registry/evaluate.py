"""Version 2 engineering evaluation; the 300 frozen reference labels are untouched."""
import json
from pathlib import Path
from chemistry import describe
from providers import Bridge,PubChem,ChEBI,ROOT
from resolver import Resolver
from identity_comparator import compare
from test_registry import PAIRS

CASES=[('ethanol','CCO',True),('ethyl alcohol','CCO',True),('acetone','CC(C)=O',True),('benzene','c1ccccc1',True),('acetic acid','CC(=O)O',True),
 ('dimethyl ether','COC',True),('methylamine hydrochloride','CN.Cl',False),('methylammonium','C[NH3+]',True),
 ('(S)-alanine','N[C@@H](C)C(=O)O',True),('alanine',None,False),('ethanol monohydrate',None,False),
 ('deuterium oxide','[2H]O[2H]',True),('polyethylene',None,False),('poly(ethylene)',None,False),('silicon bronze',None,False),
 ('ethanol mixture',None,False),('arbitrary_invalid_chemical_zzzz',None,False),('CN hydrochloride',None,False)]

def run():
    out=ROOT/'form_aware_evaluation/engineering'; out.mkdir(parents=True,exist_ok=True)
    b=Bridge(); p=PubChem(out/'http_cache',budget=40); chebi=ChEBI(out/'chebi_cache',budget=80); engine=Resolver(b,p,chebi); records=[]
    alias_cases=[('ethyl alcohol',True),('acetone',False),('methylamine hydrochloride',False),('arbitrary_invalid_chemical_zzzz',False)]
    try:
        for name,gold,expected in CASES:
            result=engine.evaluate(name); d=result.get('structure'); status=result['status']; accepted=status=='AUTO_ACCEPT'
            correct=bool(accepted and gold and compare(d,describe(gold))['assessment']=='EXACT')
            records.append(dict(name=name,gold_smiles=gold,expected_admission=expected,status=status,correct_identity=correct,reason=result['reason_codes'],evidence=dict(local={'structure':d},analysis=result)))
        alias_resolution=engine.evaluate('ethanol',[name for name,expected in alias_cases])
    finally: b.close()
    admissions=[r for r in records if r['status']=='AUTO_ACCEPT']
    # Alias promotion evaluation against an externally corroborated ethanol identity.
    aliases=[]
    promoted={r['alias'] for r in alias_resolution['evidence'].get('alias_decisions',[]) if r['accepted']}
    for name,expected in alias_cases:
        actual=name in promoted
        aliases.append(dict(alias=name,expected=expected,promoted=actual))
    pair_results=[dict(label=label,expected_same=same,predicted_same=compare(describe(a),describe(b))['assessment']=='EXACT',a=a,b=b) for label,a,b,same in PAIRS]
    negatives=[r for r in pair_results if not r['expected_same']]
    alias_promoted=[r for r in aliases if r['promoted']]
    metrics=dict(records=len(records),automatic_admissions=len(admissions),admission_precision=sum(r['correct_identity'] for r in admissions)/len(admissions) if admissions else None,alias_precision=sum(r['expected'] for r in alias_promoted)/len(alias_promoted) if alias_promoted else None,false_merge_rate=sum(r['predicted_same'] for r in negatives)/len(negatives),abstention_rate=1-len(admissions)/len(records),coverage=len(admissions)/len(records),expected_admission_mismatches=sum((r['status']=='AUTO_ACCEPT')!=r['expected_admission'] for r in records),limitations='Small explicit engineering gold set; not a representative CUMA precision estimate or independent expert adjudication.')
    result=dict(metrics=metrics,cases=records,alias_cases=aliases,pairs=pair_results)
    (out/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(metrics,indent=2))
    if any(not r['correct_identity'] for r in admissions) or metrics['false_merge_rate'] or any(not r['expected'] for r in alias_promoted): raise SystemExit('Precision gate failed')

if __name__=='__main__': run()
