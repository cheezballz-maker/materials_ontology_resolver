"""Measure native operations inside the existing form feature calculation."""

from collections import Counter
from itertools import combinations
from time import perf_counter
from unittest.mock import patch

from .full_capture import read, write
from .stage_b_v3_cohort import OUTPUT

CASES = ("DIRECT RED 23", "PERFLUORODECALIN", "UREA", "CUPRIC OXIDE")


def measure(output):
    from canonical_registry.nomenclature_interpretation.molecular import reconcile_graphs
    from form_characterizer import _features
    from rdkit import Chem, rdBase
    from rdkit.Chem.MolStandardize import rdMolStandardize

    selected = {row["name"]:row for row in read(OUTPUT/"corrected_predictions.json")["predictions"]
                if row["name"] in CASES}
    result = []
    with rdBase.BlockLogs():
        for name in CASES:
            interpretation = selected[name]["trace"]["interpretation"]
            claims = [a["value"] for a in interpretation["assertions"]+interpretation["withheld_assertions"]
                      if a["category"]=="STRUCTURAL"]
            graphs = {a["smiles"]:a for a in claims}
            for graph in graphs.values():
                timings, calls = Counter(), Counter()

                def timed(label, fn, *args, **kwargs):
                    start = perf_counter()
                    try:
                        return fn(*args, **kwargs)
                    finally:
                        timings[label] += perf_counter()-start
                        calls[label] += 1

                resonance = Chem.ResonanceMolSupplier
                enumerator = rdMolStandardize.TautomerEnumerator

                class Tautomer:
                    def __init__(self):
                        self.native = enumerator()

                    def __getattr__(self, key):
                        return getattr(self.native, key)

                    def Enumerate(self, mol):
                        return timed("tautomer_enumerate",self.native.Enumerate,mol)

                def contributors(*args):
                    supplier = timed("resonance_supplier",resonance,*args)
                    iterator = timed("resonance_iter",iter,supplier)
                    while True:
                        try:
                            value = timed("resonance_next",next,iterator)
                        except StopIteration:
                            return
                        yield value

                mol = Chem.MolFromSmiles(graph["smiles"])
                _features.cache_clear()
                with patch.object(Chem,"ResonanceMolSupplier",contributors), patch.object(
                    rdMolStandardize,"TautomerEnumerator",Tautomer
                ), patch.object(Chem,"FindPotentialStereo",side_effect=lambda m, fn=Chem.FindPotentialStereo:
                                timed("find_potential_stereo",fn,m)), patch.object(
                    Chem,"MolToSmiles",side_effect=lambda *a, fn=Chem.MolToSmiles, **k: timed("mol_to_smiles",fn,*a,**k)
                ), patch.object(Chem,"SanitizeMol",side_effect=lambda *a, fn=Chem.SanitizeMol, **k:
                                timed("sanitize_mol",fn,*a,**k)), patch.object(
                    Chem,"MolFromSmiles",side_effect=lambda *a, fn=Chem.MolFromSmiles, **k:timed("parse_smiles",fn,*a,**k)
                ), patch.object(Chem,"GetMolFrags",side_effect=lambda *a, fn=Chem.GetMolFrags, **k:
                                timed("get_fragments",fn,*a,**k)), patch.object(
                    Chem,"RemoveHs",side_effect=lambda *a, fn=Chem.RemoveHs, **k:timed("remove_hs",fn,*a,**k)):
                    start = perf_counter()
                    features = _features(graph["smiles"])
                    elapsed = perf_counter()-start
                print(name,mol.GetNumAtoms(),round(elapsed,4),dict(timings),flush=True)
                result.append({"name":name,"atoms":mol.GetNumAtoms(),"bonds":mol.GetNumBonds(),
                    "components":features["component_count"],"resonance_forms":len(features["resonance_forms"]),
                    "tautomer_diagnostic_count":features["tautomer_diagnostic_count"],"seconds":elapsed,
                    "native_seconds":dict(timings),"native_calls":dict(calls)})
            for left,right in combinations(claims,2):
                start = perf_counter()
                _,relation = reconcile_graphs(left,right)
                result.append({"name":name,"warm_comparison_seconds":perf_counter()-start,"relation":relation})
    write(output,{"rdkit":rdBase.rdkitVersion,"records":result})


def stereo_probe(output):
    import cProfile
    import pstats
    from canonical_registry.nomenclature_interpretation.molecular import reconcile_graphs
    from rdkit import rdBase

    row = next(p for p in read(OUTPUT/"corrected_predictions.json")["predictions"]
               if p["name"]=="PERFLUORODECALIN")
    interpretation = row["trace"]["interpretation"]
    graphs = [a["value"] for a in interpretation["assertions"]+interpretation["withheld_assertions"]
              if a["category"]=="STRUCTURAL"]
    with rdBase.BlockLogs(), cProfile.Profile() as profile:
        start = perf_counter()
        comparisons = [reconcile_graphs(a,b)[1] for a,b in combinations(graphs,2)]
        elapsed = perf_counter()-start
    stats = pstats.Stats(profile)
    functions = [{"path":name[0].split("canonical_registry")[-1],"line":name[1],"function":name[2],
                  "calls":value[1],"self_seconds":value[2],"cumulative_seconds":value[3]}
                 for name,value in sorted(stats.stats.items(),key=lambda x:-x[1][2])[:15]]
    write(output,{"name":row["name"],"seconds":elapsed,"comparisons":comparisons,"hotspots":functions})


if __name__=="__main__":
    import argparse
    import subprocess
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    parser.add_argument("--worker",action="store_true",help=argparse.SUPPRESS)
    parser.add_argument("--stereo",action="store_true")
    options = parser.parse_args()
    if options.worker:
        (stereo_probe if options.stereo else measure)(options.output)
    else:
        arguments = ["--stereo"] if options.stereo else []
        subprocess.run([sys.executable,"-B","-m",__spec__.name,str(options.output),"--worker",*arguments],
                       timeout=15 if options.stereo else 220,check=True)
