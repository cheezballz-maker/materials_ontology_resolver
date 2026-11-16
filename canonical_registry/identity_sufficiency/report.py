"""Summarize evidence qualification results from the frozen artifacts."""

from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

from canonical_registry.cosing_pilot.full_capture import read
from .evaluate import DATA

REPORT = DATA.parents[1]/"CHEMICAL_IDENTITY_EVIDENCE_SUFFICIENCY_V1_REPORT.md"
VERDICT = "CHEMICAL_IDENTITY_EVIDENCE_SUFFICIENCY_V1_CONDITIONAL"
READY = "CANDIDATE_READY"
NEEDS = "NEEDS_MORE_EVIDENCE"
OUT = "NOT_APPLICABLE_TO_EXACT_MOLECULAR_RESOLUTION"
HOLD = "REVIEW_HOLD"


def generate():
    data = "identity_sufficiency/data/"
    metrics = read(DATA/"metrics.json")
    output = read(DATA/"eligibility.json")
    pool = read(DATA/"candidate_pool.json")
    inventory = read(DATA/"cosing_inventory_metrics.json")
    refs = read(DATA/"frozen_reference.json")
    tests = ElementTree.parse(DATA/"tests.xml").getroot()[0].attrib
    direct = Counter(x["evidence_pathway"] for x in pool)
    ready = {kind:{r["name"]:r["decision"] for r in records if r["decision"]["eligibility"]==READY}
             for kind,records in output.items()}
    pairs = {k:all(ready["cosing"][k]["specificity"][v]==ready["gsrs"][k]["specificity"][v]
                  for v in ("inchi","inchikey","fixed_h_inchi","smiles"))
             for k in sorted(ready["cosing"].keys()&ready["gsrs"].keys())}
    if not all(pairs.values()):
        raise ValueError("Cross-source structural qualification disagreed")
    lines = ["# Chemical Identity Evidence Sufficiency v1","",
        f"The shared evaluator qualified {len(pool)} bounded source records for a subsequent molecular match attempt. "
        "The CosIng inventory screen found three candidate-ready concepts with revision-bound authority receipts. "
        "The verdict is conditional because positive cases are development controls and much of the inventory lacks whole-referent evidence. "
        "Canonical matching was outside the run.","",
        "## The prior zero-candidate result","",
        "The prior screen required a retained preferred-name graph and a retained typed graph together. It then required the typed source row "
        "to supply a verified whole-ingredient binding. The alias capture stored original alias IDs, values, types, source labels and timestamps. "
        "The structural and formula claims were labelled PUBCHEM, and the capture supplied no field binding the source graph to the whole "
        "ingredient. A PUBCHEM label alone could not provide that missing role. Keeping this authority safeguard is necessary. The universal "
        "name-parser requirement was avoidable when a separate qualified evidence pathway established the same chemical referent.",
        "WATER previously received an existing-target proposal to SUB_00000562 in the pinned development registry. The pilot used its earlier "
        "name-based eligibility and admission checks plus a complete downstream lookup. The later handoff had both a preferred-name graph and "
        "reported typed structure for WATER, but its stricter source-binding check failed. In this run, the exact source designation and revision, "
        "matching singleton EC and CAS claims, ECHA chemical definition and separate NIST structure support C. The earlier proposal was read "
        "from its report. No target was queried or confirmed here. [Organization pilot](COSING_CANONICAL_ORGANIZATION_PILOT_V1_REPORT.md), "
        "[Stage B handoff](COSING_STAGE_B_COMPLETION_AND_STAGE_C_HANDOFF_V1_REPORT.md), "
        "[ECHA water record](https://echa.europa.eu/substance-information/-/substanceinfo/100.028.902), "
        "[NIST water](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185)","",
        "## Shared policy and source adapters","",
        "The evaluator separates structure validity, material scope, authority and revision-bound correspondence. Path A uses a validated native "
        "whole structure, B uses an explicit nomenclature link with a separate graph, and C uses a qualified identifier relationship with a "
        "defined structural referent. It compares strict molecular forms, holds conflicts and requires official InChI agreement. Explicit "
        "source-defined molecular stereo underspecification is the supported ChemicalConcept branch. [Reusable specification](CHEMICAL_IDENTITY_EVIDENCE_SUFFICIENCY_CONTRACT_V1.md)","",
        "The CosIng adapter preserves original claims and Stage B scope and conflict results. Its three curated receipts are limited to the "
        "record revisions, source conditions and authority evidence in the frozen artifact. AQUA uses its explicit definition of Water and "
        "the independent structural reference. GLYCERIN uses its exact designation and ECHA EC/CAS definition with the NIST structure. "
        "These receipts are individual evidence reviews. The adapter does not apply them to unreviewed records with similar names or identifiers. "
        f"[Frozen authority receipts]({data}authority_receipts.json), "
        "[ECHA glycerol](https://echa.europa.eu/substance-information/-/substanceinfo/100.000.263), "
        "[NIST glycerin](https://webbook.nist.gov/cgi/cbook.cgi?ID=C56815)","",
        "The GSRS adapter uses the FDA-derived warehouse record type and native ingredient role. The sample includes 78 warehouse records "
        "with 955 original alias and 363 identifier rows, plus one supplemental ALCOHOL record with an archived native GSRS definition. "
        "All companion rows were verified against their parent keys. IONIC MOIETY and MOLECULAR FRAGMENT remain component roles. Native "
        "ALCOHOL passed the retained GSRS validation for an approved complete primary chemical definition, referenced structure, "
        "molfile and SMILES agreement and integer moieties. FDA UNII records for WATER and GLYCERIN provide specific identifier scope, "
        "and their warehouse structures agree with the independent NIST structural definitions. The FDA-derived source label establishes "
        "neither a pharmaceutical application nor the defining field role of other warehouse graphs. "
        f"[Observed Trino schemas]({data}gsrs_schemas.json), [Bounded SQL]({data}gsrs_inventory.sql), "
        "[GSRS API and schema](https://gsrs.ncats.nih.gov/api-documentation), "
        "[FDA WATER](https://precision.fda.gov/uniisearch/srs/unii/059QF0KO0R), "
        "[FDA GLYCERIN](https://precision.fda.gov/uniisearch/srs/unii/PDC6A3C0OX)","",
        "## Bounded evaluation","",
        "| Source and group | Records | Ready | More evidence | Outside exact scope | Review hold |",
        "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for source in ("cosing","gsrs"):
        for group,stats in sorted(metrics["groups"][source]["by_group"].items()):
            c = stats["statuses"]
            lines.append(f"| {source} · {group} | {stats['total']} | {c.get(READY,0)} | {c.get(NEEDS,0)} | {c.get(OUT,0)} | {c.get(HOLD,0)} |")
    lines += ["",f"The real candidates used A for {direct['A_DIRECT_STRUCTURE']}, B for {direct['B_NOMENCLATURE']} and C for "
              f"{direct['C_IDENTIFIER']} records. All qualified for the Substance pathway. WATER and GLYCERIN agreed across the two source "
              "adapters on strict graph, full key and fixed-H identity. Their source records and evidence receipts remain separate. The "
              "graph-grounded ChemicalConcept branch passed controlled tests. No real cohort record supplied that branch's explicit partial scope.",
              f"The frozen references recorded {sum(len(x['disagreements']) for x in metrics['groups'].values())} outcome disagreements. "
              "The held-out groups are fresh to this contract, and their labels primarily capture prior scope decisions or available source role. "
              "They are provisional comparators and contained no independently verified positive controls. The six real positives were "
              "authority-backed development cases. The results support tested safety behavior without estimating general precision or recall. "
              f"[Frozen reference]({data}frozen_reference.json), [Per-record packets, decisions and previous diagnostics]({data}eligibility.json)","",
              "| Example | Evidence and decision |","| --- | --- |",
              "| WATER | Previous binding gap was real. Source designation, EC/CAS and independent structural evidence support identifier-mediated readiness. |",
              "| AQUA | One retained imported typed graph and no preferred-name graph in the prior assessment. Its explicit source definition and independent structural reference support nomenclature-mediated readiness. |",
              "| GLYCERIN | Prior parser and typed candidates agreed, but their presence left scope unqualified. Revision-bound EC/CAS and structure receipts support readiness. |",
              "| UREA | Stage B recorded conflicting structural dimensions. The CosIng record stays held. Source reconciliation is needed before an exact path. |",
              "| SODIUM CHLORIDE | The Stage B preferred-name graph and reported identifiers leave original structural authority and complete form unqualified. A native or identifier-scoped complete salt definition could establish readiness. |",
              "| CI 74160 and DIRECT RED 80 | Existing processing holds and reported dye structure claims leave the whole referent unresolved. No molecular candidate was promoted. |",
              "| TITANIUM DIOXIDE | Structural conflict and whole-scope guard remain active. An inorganic name or formula cannot establish a discrete source graph. |",
              "| GSRS polymer, mixture and structurally diverse records | Native record-type scope supports abstention from exact molecular routing. Ionic moieties remain component evidence until the referent role is established. |",
              "| Controlled stereochemical forms | Opposite stereo, protonation, isotope and hydrate differences hold. Explicit graph-grounded open stereo can route to the existing ChemicalConcept pathway. |","",
              "The per-record artifact identifies original claims, candidate evidence, previous reason, applied scope and authority, supported "
              "specificity and final pathway. Unbound but structurally plausible GSRS and CosIng records are the main false-rejection review "
              "population. A native definition, a verified nomenclature relationship or an authoritative identifier bridge could qualify "
              "some of these records. Present evidence does not support counting those abstentions as chemical false negatives.","",
              "## Inventory applicability","",
              "The inventory screen reused the frozen Stage B evidence after the bounded safety checks. It applied the shared policy to all "
              "30,360 concepts and made no additional external adjudications. Only the three reviewed receipts could supply new grants. "
              "The counts measure the availability of qualified evidence in this snapshot.","",
              "| Operational status | Concepts |","| --- | ---: |"]
    lines.extend(f"| {name} | {inventory['statuses'].get(name,0):,} |" for name in (READY,NEEDS,OUT,HOLD))
    lines += ["",f"The inventory routes {inventory['resolution_paths'].get('SUBSTANCE',0)} Substance candidates and "
              f"{inventory['resolution_paths'].get('CHEMICAL_CONCEPT',0)} ChemicalConcept candidates. Evidence-route counts and "
              "the full hold and rejection reasons are in the metrics. Scope and authority gaps remain the primary acquisition targets. "
              "Structural conflicts require evidence reconciliation before routing. "
              f"[Inventory metrics and transitions]({data}cosing_inventory_metrics.json), "
              f"[Per-concept inventory decisions]({data}cosing_inventory_eligibility.jsonl)","",
              "## Verification and downstream scope","",
              f"The focused contract and retained handoff tests ran {tests['tests']} cases with {tests['failures']} failures and "
              f"{tests['errors']} errors. All {len(refs['protected_before'])} protected-file digests matched before and after. "
              "The run changed no canonical registry, ontology, Stage B assessment, source binding or ingredient-equivalence history. "
              "An independent specialist review was unavailable. The highest-value next evidence is a revision-bound whole-ingredient "
              "role for additional defined molecules and complete form evidence for salts, stereo and partial molecular concepts.","",
              "A first separately authorized Stage C run can use the three CosIng candidates in a bounded, read-only existing-ID attempt "
              "under unchanged matching and admission policy. GSRS candidates are cross-source validation controls. No identity assignment "
              "or ingredient equivalence follows from this pool. "
              f"[Qualified candidate pool]({data}candidate_pool.json), [Tests]({data}tests.xml), "
              f"[Metrics and protected checksums]({data}metrics.json)",""]
    if (DATA/"audit.json").exists():
        lines += [f"The artifact audit checked the input and decision schemas, source links and protected digests for the bounded packets and inventory decisions. "
                  f"[Artifact audit]({data}audit.json)",""]
    lines += [
              "## Reproduction","",
              "The source packets and reference are already frozen. The freeze command refuses to replace them.","",
              "~~~powershell",
              "python -B -m pytest -q canonical_registry/identity_sufficiency/test_contract.py canonical_registry/cosing_pilot/test_stage_b_handoff.py --junitxml canonical_registry/identity_sufficiency/data/tests.xml",
              "python -B -m canonical_registry.identity_sufficiency.evaluate evaluate",
              "python -B -m canonical_registry.identity_sufficiency.evaluate inventory",
              "python -B -m canonical_registry.identity_sufficiency.report",
              "~~~","",VERDICT,""]
    REPORT.write_text("\n".join(lines),encoding="utf-8")
    print(VERDICT)


if __name__=="__main__":
    generate()
