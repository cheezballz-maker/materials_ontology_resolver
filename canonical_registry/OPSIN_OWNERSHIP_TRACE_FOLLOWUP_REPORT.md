# OPSIN ownership-trace follow-up

**Production adapter: not yet justified.** A reproducible source-built diagnostic can capture candidate fragments before R/S assignment and identify a successful parse's selected atom in its final CML. It establishes a unique OPSIN-scoped source assignment for CUMA 48695, but does not resolve that case's existing graph correspondence or tautomer conflict. CUMA 41891 still lacks original-descriptor-to-clone lineage. Production resolver behavior and admissions were not changed.

## Build identity and trace

The local OPSIN source has **no Git metadata or identified commit**. Its 226 Java/resource/POM files were frozen by [content manifest](opsin_ownership_followup_final/SOURCE_SNAPSHOT.json), SHA-256 `9e5d834ed0f78bd10475565c4398ff3035f8f97e98bce401edb55311d77c0971`; its POM says `3.0-SNAPSHOT`. Both builds compile all 84 core Java sources from that same frozen snapshot using `javac 17.0.12 --release 8`, source resources, and `project.version=3.0-SNAPSHOT`. The installed shaded jar, SHA-256 `a2cdde821c35352496e7f658b32d8619f851aa774cbcdf41d801fd3af5a021d3`, supplies dependencies. Core classes and resources precede it on the runtime classpath; the baseline contains all 144 class names present in the installed core jar.

The uninstrumented source-built core jar SHA-256 is `46c2772e2c1fb0b03216a51a83720bab3e3bc7ae280f4c2e7ad2c008c7413e54`; the diagnostic jar is `d85f86f1935bef0c13e4c6d68831a06ca3d0cb45a00815be4c623d7184158e05`. An independent rebuild on the same machine and JDK reproduced both hashes. Only `NameToStructure` and `StereochemistryHandler` class bytes differ between the source builds, plus a diagnostic helper. The source build is **not proven equivalent** to the installed jar: 139 of 144 core class files have different bytes, which could include compiler differences; the exact snapshot revision is unknown. This does not establish a code difference or a match. [Build identity](opsin_ownership_followup_final/BUILD_IDENTITY.json), [class coverage](opsin_ownership_followup_final/CLASS_COVERAGE.json), [rebuild check](opsin_ownership_followup_final/REPRODUCIBILITY.json).

The isolated [patch](opsin_ownership_followup_final/diagnostic.patch) and [helper](opsin_ownership_followup_final/OwnershipTrace.java) buffer records per parse attempt and emit them only after a successful `OpsinResult` is constructed. Records contain temporary attempt, node, scope and fragment IDs; descriptor and scope XML; each primary and possible fallback fragment; its locant, potential-stereocentre and unassigned status **before assignment**; previously assigned atom IDs; the selected path and atom; and the final CML atom from that same result. Warnings and public status are captured separately. A synthetic [lifecycle test](opsin_ownership_followup_final/TRACE_ISOLATION_TEST.json) confirms that buffered events from an abandoned attempt are not emitted after a later successful attempt; all observed successful cases happened to select attempt 1. WARNING-only results deliberately have no associated trace, so that path is not demonstrated.

The trace is captured at [OPSIN's R/S application point](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/StereochemistryHandler.java#L301), after source parse and fragment construction. No raw source offsets or original-token lineage are invented. CML correspondence is the internal atom ID written by OPSIN as `a<ID>` from the same returned result; atom parity is checked as output consistency, not used to choose ownership. IDs are temporary and not comparable across parses.

## Classification rule

`UNIQUELY_SCOPED` requires one distinct potential `(fragment, atom)` pair across OPSIN's complete pre-assignment primary and applicable fallback candidate lists, that pair unassigned, a primary-path selection of it, and same-result CML correspondence. Candidate lists are recorded before the handler's first successful selection; potential centres already assigned earlier remain counted, so they cannot create a false appearance of uniqueness. Duplicate locants elsewhere do not invalidate a single syntactically reachable pair. This is uniqueness **within OPSIN's enumerated scope**, not proof that every plausible chemical interpretation was enumerated.

`ORDERED_OR_FALLBACK_SELECTION` means more than one potential pair exists or the actual fallback path was used. It does not assert that OPSIN's selection is chemically wrong. `PROVENANCE_INCOMPLETE` means the selected-result trace, CML link, or required descriptor lineage is inadequate. Cloned or repeated processed nodes that outnumber visible original descriptor tokens are treated as lineage-incomplete; no source spans are assigned. The diagnostic does not modify the parser's selection. E/Z, canonical-SMILES and RDKit atom mapping were not implemented.

## Five diagnostic names

All five names are existing project or OPSIN fixtures. Baseline and diagnostic outputs were identical for **status, message, warnings, ambiguity flags, SMILES and CML in 5/5 cases**; the source-built baseline also matched the installed jar's public output in these five cases. Four succeeded with selected-parse traces; one failed and yielded no trace. The complete structured candidates and results are in [observations.json](opsin_ownership_followup_final/observations.json).

| Case | Trace and scope result | Disposition |
| --- | --- | --- |
| `(2R,3S)-2-bromo-3-chloropentane` | `2R` → `pent` / `a4`; `3S` → `pent` / `a5`. Each has one potential scoped fragment/atom pair before its assignment. `3S` records prior assignment of `a4`, which is not a competitor for locant 3. Both `UNIQUELY_SCOPED`. | Control; temporary CML correspondence verified. |
| OPSIN flavonoids fixture: two nested `2S` chroman descriptors | First `2S` → fragment/`a13`: one potential pair, `UNIQUELY_SCOPED`. Second `2S` → fragment/`a30`: potential pairs include `a13` and `a30`; `a13` was already assigned. `ORDERED_OR_FALLBACK_SELECTION` despite only `a30` being unassigned at that point. | The trace does not independently establish a unique scope for the second descriptor; it does not declare the name chemically ambiguous. |
| CUMA 41891: `Succinic acid - (2S)-…-2-propanol (1:2)` | OPSIN SUCCESS; selected trace has two separately scoped `2S` nodes → `a48` and `a16`, each locally unique before selection. There is only one visible original `2S` token. | **PROVENANCE_INCOMPLETE** for both: the source-to-processed-node/clone linkage is not established. The previous resolver reason was `MULTICOMPONENT_SEMANTICS_UNKNOWN`; `GRAPH_MAPPING_AMBIGUOUS` also remains. No safe full resolution is demonstrated. |
| CUMA 48695: `3-Pyridinecarboxamide, …[(3R)-3-hydroxy-1-pyrrolidinyl]…` | OPSIN SUCCESS; `3R` node → one potential scoped `pyrrolidin` fragment/`a13`, selected on the primary path; same-result CML correspondence verified. `UNIQUELY_SCOPED`. | The source ownership ambiguity is addressed **at OPSIN/CML level**. The previous resolver still has `GRAPH_MAPPING_AMBIGUOUS` for CML-to-RDKit correspondence and a separate `TAUTOMER_CONFLICT`; no admission recovery is claimed. |
| `1-N-BOC-1,2-TRANS-CYCLOHEXYLDIAMINE` | OPSIN FAILURE; no successful selected-parse trace. | No stereo ownership or CML mapping claimed. |

For the 1:2 case, [StructureBuilder](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/StructureBuilder.java#L1794) can clone elements during stoichiometry processing before stereo application, and [cloneElement](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/FragmentManager.java#L509) copies groups and fragments. The trace observes two processed nodes but does not record which clone operation created them or their common original-token lineage. A general lineage system was deliberately not added. No case exercises an actual fallback selection; its candidate path is captured but remains empirically untested.

## Reproduction and next decision

[Build script](opsin_ownership_followup_final/build.py), [runner](opsin_ownership_followup_final/run_cases.py), [trace patch](opsin_ownership_followup_final/diagnostic.patch), and [observations](opsin_ownership_followup_final/observations.json) are retained. From the workspace root in Windows PowerShell, build into a **new** directory; the script intentionally refuses to overwrite a prior build:

```powershell
$src = 'canonical_registry/opsin_ownership_followup_final'
$dst = 'canonical_registry/opsin_ownership_reproduce'
New-Item -ItemType Directory -Path $dst | Out-Null
Copy-Item -LiteralPath "$src/source_snapshot" -Destination "$dst/source_snapshot" -Recurse
Copy-Item -LiteralPath "$src/SOURCE_SNAPSHOT.json", "$src/build.py", "$src/OwnershipTrace.java", "$src/Runner.java", "$src/run_cases.py", "$src/TraceIsolationProbe.java" -Destination $dst
python "$dst/build.py"
New-Item -ItemType Directory -Path "$dst/runner_classes", "$dst/probe_classes" | Out-Null
$deps = 'opsin-master/opsin-cli/target/opsin-cli-3.0-SNAPSHOT-jar-with-dependencies.jar'
javac --release 8 -encoding UTF-8 -cp "$dst/baseline_core.jar;$deps" -d "$dst/runner_classes" "$dst/Runner.java"
javac --release 8 -encoding UTF-8 -cp "$dst/diagnostic_core.jar;$deps" -d "$dst/probe_classes" "$dst/TraceIsolationProbe.java"
java -cp "$dst/probe_classes;$dst/diagnostic_core.jar;$deps" uk.ac.cam.ch.wwmm.opsin.TraceIsolationProbe
python "$dst/run_cases.py"
```

A production adapter would still need pinned, provenance-matched OPSIN source; robust warning/alternative-parse handling; a defensible original-node/clone lineage contract; and source CML-to-resolver graph correspondence that abstains under symmetry. It must also separately address E/Z if required. Those are nontrivial maintenance and policy boundaries around private internals. Given that neither outstanding case is fully resolved by this trace, do not integrate it into admissions now. A separate bounded graph-correspondence study may be worthwhile if the 48695-style use case justifies it; clone lineage would be a distinct study.

The production resolver runtime and test files still match the prior frozen implementation hashes. No provider, registry, ontology, or admission behavior was changed; no 400-record replay was run.

OPSIN_OWNERSHIP_ADAPTER_NOT_YET_JUSTIFIED
