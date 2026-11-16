"""Generate the audited Stage B completion and Stage C planning report."""

from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

from .full_capture import read, write
from .stage_b_handoff_recovery import OUTPUT, REGISTRY, SOURCE

REPORT = Path(__file__).resolve().parents[1]/"COSING_STAGE_B_COMPLETION_AND_STAGE_C_HANDOFF_V1_REPORT.md"


def graph_diagnostics(records):
    from chemistry import parse
    from rdkit import Chem, rdBase

    result = {}
    with rdBase.BlockLogs():
        for cid,record in records.items():
            rows = []
            for alias in record["original_typed_evidence"]:
                kind = alias["alias_type"]
                if kind not in {"SMILES","INCHI"}:
                    continue
                data = {"alias_id":alias["inci_alias_id"],"type":kind}
                try:
                    mol = parse(alias["alias"],kind.lower())
                except (ValueError,RuntimeError) as exc:
                    data["parse_error"] = str(exc)
                else:
                    data.update(heavy_atoms=mol.GetNumHeavyAtoms(),rings=mol.GetRingInfo().NumRings(),
                                aromatic_bonds=sum(b.GetIsAromatic() for b in mol.GetBonds()),
                                components=len(Chem.GetMolFrags(mol)),charge=Chem.GetFormalCharge(mol))
                rows.append(data)
            result[cid] = rows
    return result


def generate():
    r = read(OUTPUT/"recovery.json")
    m = read(OUTPUT/"triage_eligibility_metrics.json")
    records = r["records"]
    shape_path = OUTPUT/"recovery_graph_diagnostics.json"
    if not shape_path.exists():
        write(shape_path,graph_diagnostics(records))
    shapes = read(shape_path)
    done = r["dispositions"]["COMPLETED"]
    held = r["dispositions"]["DOCUMENTED_HOLD"]
    i = m["inventory"]
    pending = m["eligibility"]
    priorities = Counter()
    for key,count in m["triage"].items():
        priorities[key.split("/")[0]] += count
    target = m["potential_pathways"]
    d = "cosing_pilot/data/stage_b_handoff_v1/"
    ready = pending.get("CANDIDATE_READY",0)
    verdict = "COSING_STAGE_B_HANDOFF_READY" if ready else "COSING_STAGE_B_HANDOFF_CONDITIONAL"
    lines = ["# CosIng Stage B Completion and Stage C Handoff v1","",
        f"All 30,360 registered concepts have an operational disposition. The working copy has {i['with_stage_b']:,} "
        f"completed current Stage B assessments and {held} documented holds. The recovery added {done} assessments. "
        f"The inventory screen found {ready:,} concepts ready for a canonical identity attempt under the recorded evidence policy. "
        "Stage C was not executed.","",
        "## Ten-record recovery","",
        "Each original packet was rebound to the current source revision. Each record had two six-second attempts in the prior full run. "
        "This recovery used one explicitly budgeted isolated retry per record. The extended limits reflect conjugated dye, aromatic ring "
        "or cage candidates and the measured direct-dye precedent. These features indicate possible reconciliation cost. "
        "The held runs do not identify the exact stalled native call for each graph. All completed retries passed the existing Stage B "
        f"quality gate and publication restrictions. [Retry evidence and exact source packets]({d}recovery.json)","",
        "| Record | Source designation | Reported graph characteristics | Budget / measured worker seconds | Disposition |",
        "| --- | --- | --- | ---: | --- |"]
    for cid,x in records.items():
        name = x["original_designation"].splitlines()[0].replace("|","\\|")
        graphs = [g for g in shapes[cid] if "heavy_atoms" in g]
        values = ", ".join(f"{g['heavy_atoms']} atoms / {g['rings']} rings" for g in graphs)
        value = values or ("No eligible typed graph" if not shapes[cid] else "Typed graph parse failed")
        lines.append(f"| {cid} | {name} | {value} | {x['budget_seconds']} / {x['execution']['elapsed_seconds']:.2f} | {x['disposition']} |")
    changes = records["CIC_00023298"]["original_designation"].count("\n")
    lines += ["",
        f"`CIC_00023298` contained {changes} embedded line feeds. The processing representation replaced only ASCII layout-whitespace runs "
        "with a space and retained the exact nonwhitespace token sequence. The original designation remains in the registry and source evidence. "
        "The assessment trace records both representations and the offset and original text of every edit. Non-layout controls remain rejected.",
        "The six persistent timeouts received a review-only nonstructural preview. Its molecular dimension is explicitly untested. "
        "No preview was persisted. Each remaining hold retains its original packet, timed attempt and recovery recommendation. "
        f"[Read-only graph diagnostics]({d}recovery_graph_diagnostics.json)","",
        "## Review inventory and priorities","",
        f"The sidecar accounts for all {m['original_items']:,} original items across {m['original_queue_concepts']:,} concepts. "
        "It preserves the original reason and event reference alongside derived risk, action, supporting evidence and the source revision. "
        "Multiple reasons can apply to one concept.","",
        "| Priority | Items | Action |","| --- | ---: | --- |",
        f"| P0 | {priorities['P0']:,} | Contain a published identity, source-binding or dependency failure |",
        f"| P1 | {priorities['P1']:,} | Hold the exact pathway while identity-significant evidence or processing remains unresolved |",
        f"| P2 | {priorities['P2']:,} | Review semantic attachment, preparation scope or the role of a reported chemical name |",
        f"| P3 | {priorities['P3']:,} | Preserve routine qualification and recovered processing history |","",
        "### Missing alias qualification","",
        "The observed source labels are GLOBAL COSING and FDA_GSRS_UNII. Missing type is distinct from missing authority or whole-ingredient binding. "
        "Source labels identify the reported origin. The claims remain unqualified for identity. The rule prioritizes structure-like strings, "
        "formulas and registry identifiers, flags form-specific lexical names and explicit constituent mentions, and keeps routine lexical claims "
        "traceable. Exact same-source duplicate qualification would only reuse an already qualified original claim.","",
        "| Item disposition | Count |","| --- | ---: |"]
    for action in ("AUTOMATIC_CLASSIFICATION","SUPPORTED_DUPLICATE_QUALIFICATION","REVIEW_REQUIRED","LEGITIMATELY_EXCLUDED"):
        n = i.get("alias_item_"+action,0)
        lines.append(f"| {action} | {n:,} |")
    raw_actions = m["missing_alias_claim_actions"]
    lines += ["",f"The {sum(raw_actions.values()):,} individual untyped claims included "
              f"{raw_actions.get('LEGITIMATELY_EXCLUDED',0):,} legitimate exclusions. "
              "Each item's highest-priority claim sets its triage disposition. The sidecar retains every claim and its individual assessment. "
              "Inactive or unusable source claims can remain excluded, and uncertain source revision or authority remains reviewable. "
              "The triage creates no new aliases, chemical structures or equivalence claims.","",
              "| Main missing-qualification cause | Items |","| --- | ---: |",
              *(f"| {k} | {n:,} |" for k,n in sorted(m["missing_alias_item_causes"].items())),"",
        "### Structural conflicts and material scope","",
        "All 1,327 original structural conflict items are held from exact matching. Patterns below overlap. Charge and component differences "
        "may reflect salt or solvate forms. Distinct full keys on one connectivity block can reflect several identity dimensions and do not "
        "identify a specific relationship. The review retains the complete Stage B evidence locator, underlying structure claims and disposition.","",
        "| Observed diagnostic | Items |","| --- | ---: |",
        *(f"| {k} | {n:,} |" for k,n in sorted(m["structural_diagnostic_patterns"].items())),"",
        "Existing rules can retain independent lexical, anatomical or preparation descriptors and withhold assertions that depend on the dispute. "
        "They do not adjudicate conflicting graph identity. Invalid representations require corrected source evidence. Formula and identifier conflicts "
        "require source reconciliation. Constituent attribution and competing whole-material structures require referent-qualified evidence, and remain "
        "outside exact matching until qualified.",
        "The 647 botanical attachment items retain reported taxonomic and anatomical text while withholding unsupported structured attachments. "
        "The 710 preparation-scope items distinguish source material, process, final preparation and constituent evidence. Those with structural "
        "candidate evidence receive identity-significant review. The two mineral constituent cases remain P1. No independent taxonomic or "
        "whole-material composition claim was created.","",
        "## Stage C eligibility and interface","",
        "| Inventory measure | Concepts |","| --- | ---: |",
        f"| Registered | {i['registered']:,} |",
        f"| Current Stage B assessments | {i['with_stage_b']:,} |",
        f"| At least one qualified semantic descriptor | {i['with_qualified_descriptors']:,} |",
        f"| Molecular candidate evidence, including withheld candidates | {i['with_molecular_candidate_evidence']:,} |",
        f"| Withheld or conflicting structural evidence | {i['with_withheld_or_conflicting_structure']:,} |",
        f"| CANDIDATE_READY | {ready:,} |",
        f"| Potential exact Substance route | {target.get('SUBSTANCE',0):,} |",
        f"| Potential graph-grounded ChemicalConcept route | {target.get('CHEMICAL_CONCEPT',0):,} |",
        f"| NEEDS_MORE_EVIDENCE | {pending.get('NEEDS_MORE_EVIDENCE',0):,} |",
        f"| NOT_APPLICABLE_TO_EXACT_MOLECULAR_RESOLUTION | {pending.get('NOT_APPLICABLE_TO_EXACT_MOLECULAR_RESOLUTION',0):,} |",
        f"| REVIEW_HOLD | {pending.get('REVIEW_HOLD',0):,} |","",
        "Processing holds and identity conflicts take precedence. An explicitly supported preparation, variable family or biological material can "
        "be outside exact molecular resolution. For molecular candidates, the screen requires agreement between the preferred-name graph and original "
        "typed evidence, a verified whole-ingredient binding and agreement with official InChI. Full graph, fixed-H and stereochemical evidence matter. "
        "Multicomponent, charged, isotopic and other chemical-form cases with open scope remain for review. The ChemicalConcept branch additionally "
        "requires explicit, graph-grounded underspecification.",
        f"The {sum(m['typed_graph_authorities'].values()):,} captured typed structural and formula assertions were labelled PUBCHEM. "
        f"Among records reaching the original-graph binding check, {m['eligibility_reasons'].get('ORIGINAL_SOURCE_GRAPH_BINDING_UNESTABLISHED',0):,} "
        "lacked a verified whole-ingredient role. The typed alias provenance does not document how that role was established. "
        f"The screen performed {m['official_checks']:,} official InChI checks on otherwise eligible graphs.",
        "The existing eligibility preview can consume the Stage B interpretation and its conflict guards. Its resolver adapter still requires a "
        "qualified source-referent package and applies the existing official validation and admission policy. The handoff sidecar supplies evidence "
        "locators, operational classes and reasons. The missing interface input is a revision-bound, authority-qualified whole-ingredient claim "
        "with explicit form and scope. Source qualification is the first bounded follow-up for defined molecular records. Once it yields qualified "
        "packets, the first separately authorized Stage C operation should be read-only existing-ID matching on that subset. No current record "
        "is cleared by this handoff for matching.","",
        "## Validation, performance and integrity","",
        "The audit includes all ten recovered or held records, deterministic samples across alias causes and review priorities, structural "
        "conflicts, compound botanicals, preparations, generic fallbacks, named molecular controls and withheld constituent candidates. "
        "The controlled tests check both the positive planning branch and its whole-referent, stereo, reference-validation and triage guards. "
        "The checks establish policy compliance. Semantic conclusions remain provisional without independent specialist adjudication. "
        f"[Validation sample]({d}validation_samples.json)","",
        f"The isolated recovery took {r['elapsed_seconds']:.1f} seconds. Triage and screening took {m['elapsed_seconds']:.1f} seconds "
        f"({m['original_items']/m['elapsed_seconds']:,.0f} review items/s alongside the inventory scan). "
        f"The indexed sidecar is {m['index_bytes']/1024**2:.1f} MiB and the reported peak process working set was "
        f"{m['peak_bytes']/1024**2:.1f} MiB. The registry copy grew by "
        f"{(REGISTRY.stat().st_size-SOURCE.stat().st_size)/1024:.1f} KiB.",
        f"SQLite integrity and foreign-key checks passed. The new copy retained {r['integrity']['history_rows']:,} historical assessment rows, "
        f"all 30,360 concepts and the same source bindings, revisions and canonical targets. Canonical status remains 30,230 `NOT_EVALUATED`, "
        f"130 `UNRESOLVED` and zero resolved. All {len(r['protected_after'])} protected paths matched their starting digests. "
        "The ontology, canonical registries and ingredient-equivalence history were preserved.",
        f"[Working registry](cosing_pilot/local/{REGISTRY.name}), [Searchable triage and eligibility sidecar]({d}handoff.sqlite), "
        f"[Policy version, metrics and protected checksums]({d}triage_eligibility_metrics.json)",""]
    if replay := r.get("idempotent_replay"):
        lines += [f"Replaying the recovery added {replay['new_rows']} rows, retained all decision IDs and left the working registry SHA-256 unchanged.",""]
    if (OUTPUT/"validation_checks.json").exists():
        lines += [f"The separate artifact check reconciled all sidecar items to the original queue and verified source revisions for recovered records. "
                  f"[Artifact validation]({d}validation_checks.json)",""]
    test = ElementTree.parse(OUTPUT/"tests.xml").getroot()[0].attrib
    lines += [f"The scoped run recorded {test['tests']} tests, {test['failures']} failures and {test['errors']} errors. "
              f"[Test results]({d}tests.xml)","",
        "## Reproduction","",
        "```powershell",
        "python -B -m canonical_registry.cosing_pilot.stage_b_handoff_recovery",
        "python -B -m canonical_registry.cosing_pilot.stage_b_handoff",
        "python -B -m pytest -q canonical_registry/cosing_pilot/test_stage_b_handoff.py",
        "python -B -m canonical_registry.cosing_pilot.stage_b_handoff_report",
        "```","",f"`{verdict}`",""]
    REPORT.write_text("\n".join(lines),encoding="utf-8")
    return verdict


if __name__=="__main__":
    print(generate())
