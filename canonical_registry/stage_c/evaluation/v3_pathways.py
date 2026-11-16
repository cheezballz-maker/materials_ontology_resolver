"""Verify isolated provider pathways with frozen real records and no registry writes."""

import argparse
from collections import Counter
from contextlib import ExitStack

from rdkit import rdBase

from canonical_registry.authoritative_lookup.lookup import IdentityLookup
from canonical_registry.authoritative_lookup.sources import cosing_input, read, write
from canonical_registry.cosing_pilot.staged_assessment import _bridge
from canonical_registry.identity_sufficiency.contract import Evaluator
from ..captures import inputs
from ..v3_authority import ROOT, MultiAuthority, retained_source_input
from ..source_identity_safety import SourceIdentitySafety


def main(*, safety=False):
    cases = {"ANISOLE": {"PubChem", "ChEBI"}, "HYDROGEN PEROXIDE": {"ChEBI"},
             "2,5-XYLENOL": {"ChEBI"}, "CYCLOHEXYL PHENETHYL ETHER": {"PubChem"}}
    cohort, _, _ = inputs(ROOT)
    selected = {}
    for row in cohort:
        if row["parent"]["inci"] in cases:
            selected.setdefault(row["parent"]["inci"], row)
    results = []
    with ExitStack() as stack, rdBase.BlockLogs():
        bridge = _bridge(stack)
        for provider in ("PubChem", "ChEBI"):
            evaluator = Evaluator(bridge.official)
            lookup = MultiAuthority(IdentityLookup(evaluator, {}), bridge.opsin)
            for index in (lookup.index, lookup.names):
                for k, values in index.items():
                    index[k] = [(authority, graph) for authority, graph in values if authority.authority == provider]
            if safety:
                lookup = SourceIdentitySafety(lookup, evaluator, read(ROOT.parent / "safety_closure" / "identifier_reference.json"))
            for name, providers in cases.items():
                if provider not in providers:
                    continue
                row = selected[name]
                source = retained_source_input(row, cosing_input(row))
                decision, receipt, diagnostics = lookup.evaluate(source, [], 0)
                assert decision["eligibility"] == "CANDIDATE_READY" and receipt["authority"] == provider, (name, diagnostics)
                results.append({"designation": name, "provider": provider, "source": row["concept_id"],
                                "decision": decision, "receipt": receipt})
    output = ROOT.parent / "safety_closure" if safety else ROOT
    write(output / "isolated_pathways.json", results)
    print(dict(Counter(r["provider"] for r in results)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safety-closure", action="store_true")
    main(safety=parser.parse_args().safety_closure)
