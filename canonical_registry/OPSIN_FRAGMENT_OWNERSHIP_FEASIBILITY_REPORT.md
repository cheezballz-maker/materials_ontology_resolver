# OPSIN fragment-ownership feasibility

A narrow trace is feasible for the installed OPSIN build: isolated instrumentation observed two distinct source parse nodes with the same `2S` locant applied to different structural fragments and carried their atom IDs into the same parse's final CML. Both locant-2 atoms were potential stereocentres. This demonstrates access to **OPSIN's own assignment**, not independent proof that every assignment expresses the intended chemical name or is safe for admission.

## Version, entry point and provenance

The project [Bridge](providers.py) launches [RegistryBridge.java](RegistryBridge.java) against `opsin-cli-3.0-SNAPSHOT-jar-with-dependencies.jar`; `NameToStructure.parseChemicalName` returns `OpsinResult`, from which it obtains SMILES or CML. The runtime reports **3.0-SNAPSHOT**, with jar SHA-256 `a2cdde821c35352496e7f658b32d8619f851aa774cbcdf41d801fd3af5a021d3`. The local source POM also says `3.0-SNAPSHOT`. Four inspected classes in the CLI jar are byte-identical to those in the local core *jar*, but the checkout is not pinned to a recorded source commit and its `target/classes` files have different class hashes. Source-to-jar byte identity is therefore unproven. For all six cases, the instrumented source compiled against the installed jar produced the same public status, message, SMILES and CML as the unmodified jar; this is bounded behavioral evidence, not proof of full source equivalence.

## Where the link exists

- [NameToStructure.java:138](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/NameToStructure.java#L138) parses the name, then runs component generation and processing to attach fragments before structure construction. `OpsinResult` publicly exposes CML and SMILES, but [getStructure()](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/OpsinResult.java#L74) is package-private; the public result does not expose descriptor/fragment ownership.
- [StructureBuilder.java:65](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/StructureBuilder.java#L65) handles stoichiometry, makes hydrogens explicit, creates the unified fragment, then applies stereo. The [stereo handler](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/StereochemistryHandler.java#L301) holds the current stereo XML element and its parent scope, searches parse-derived accessible fragments, obtains the locant within the chosen fragment and applies R/S to its atom. The descriptor node is subsequently [detached](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/StereochemistryHandler.java#L188).
- OPSIN's [fragment search](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/StructureBuildingMethods.java#L2255) accounts for brackets and returns an **ordered** list; the handler returns at the first eligible assignment, including a fallback across words. That is OPSIN's own source-parse decision, not a general uniqueness guarantee. The diagnostic separately recorded all considered local candidates before application and the global potential-stereocentre IDs; it did not select a match itself or use a provider, reference structure, or expected identity.
- The internal selected atom's temporary ID is written directly as `a<ID>` by [CmlWriter.java:117](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/CmlWriter.java#L117). On these cases each selected ID appeared in the CML from the **same** `OpsinResult`, with the expected locant and an atom-parity element. That is a direct internal-atom → final CML link. It is not a demonstrated stable mapping to canonical SMILES or to RDKit atom indices.

## Diagnostic observations

The isolated shadow-class patch records the descriptor node, its current parent XML, candidate/selected fragment token and temporary object identity, fragment-local locant lookup, global potential stereocentres with that locant, selected atom ID and final CML atom. It also marks parse attempts. `CONSIDER` eligibility is measured before assignment; the selected atom is removed from OPSIN's unassigned set after assignment, so its later `SELECT` eligibility flag is false. Full names and traces are in [observations.json](opsin_fragment_feasibility/observations.json).

| Source case | Observed source parse → fragment → final CML | Limit |
| --- | --- | --- |
| Project simple control `(2R,3S)-2-bromo-3-chloropentane` | `2R`, `3S` nodes → `pent` fragment → `a4`, `a5`; one global potential centre per locant. | Source character spans are not exposed. |
| Project bridgehead control `(3aR,4S,5R,6aS)-…cyclopenta[b]furan-2-one` | Four nodes → same `pent[b]furan` fragment → `a18`, `a13`, `a14`, `a17`. | Fragment and atom IDs are temporary; this traces OPSIN output, not resolver admission. |
| Prior CUMA 23002, `(2S)-amino[2-(trifluoromethyl)phenyl]ethanoic acid` | `2S` node → `eth` fragment → `a11`; only `a11` was globally a potential stereocentre with locant 2. | Duplicate global labels alone do not demonstrate ownership when only one is stereo-eligible. |
| OPSIN's [flavonoids fixture, line 262](../opsin-master/opsin-inchi/src/test/resources/uk/ac/cam/ch/wwmm/opsin/flavonoids.txt#L262): `(2S)…[(2S)…chroman-2-yl]…chroman-4-one` | Two distinct `2S` nodes, under a `substituent locant=5` and a `bracket locant=2`, were applied to distinct `chroman` fragments → `a13` and `a30`. Both `a13` and `a30` were in OPSIN's global potential-stereocentre map with locant 2; each node's considered list had one eligible fragment at application. Both IDs and parity are present in final CML. | The node and its then-current scope are recorded, not raw source offsets. The trace observes OPSIN's ordered algorithm and is not an independent nomenclature validation. |
| Prior CUMA 41891, succinic acid with `(2S)…propanol (1:2)` | One visible source descriptor produced two distinct processed `2S` nodes; different `prop` fragment objects → `a48` and `a16`, both stereo-eligible and present in CML. | The trace does not retain original-span or clone lineage; it cannot prove how each processed node relates back to the single original occurrence. |
| Prior relative-stereo input `1-N-BOC-1,2-TRANS-CYCLOHEXYLDIAMINE` | OPSIN returned FAILURE; no application trace. | No ownership or atom assignment was demonstrated. |

The nested fixture's parse-node scopes and fragment objects, rather than CML label order or a matching external candidate, distinguish the two assignments. The test does not establish a unique atom correspondence when the final graph is symmetric. E/Z was not instrumented; [OPSIN's bond path](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/StereochemistryHandler.java#L397) is analogous in outline, but no bond-ownership claim is made.

## Transformations, access and follow-up

[FragmentManager](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/FragmentManager.java#L99) unifies fragments using the existing atoms; original fragments retain their atom collections even though atoms' current fragment pointers change. Fragment incorporation, [cloning and relabelling](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/FragmentManager.java#L353), and [atom replacement](../opsin-master/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin/FragmentManager.java#L556) occur in construction and can alter identities or locants. Capturing at stereo application observes the IDs **after** those transformations and before final CML in the demonstrated cases; it does not establish lineage through every prior transformation, cloning, alternative parse, warning, or later radical/polymer processing. Mutable XML scopes and temporary IDs must not be treated as stable provenance.

The working extraction uses a small **isolated source patch** to two OPSIN classes: parse-attempt markers in `NameToStructure` and logging immediately around R/S application in `StereochemistryHandler`. The diagnostic classes shadow the jar only for the harness; neither the installed jar nor production resolver is modified. [Exact patch](opsin_fragment_feasibility/diagnostic.patch), [harness](opsin_fragment_feasibility/run.py), and [recorded observations](opsin_fragment_feasibility/observations.json). To reproduce from the workspace root on Windows with Java 17 and Python:

```powershell
$jar = 'opsin-master/opsin-cli/target/opsin-cli-3.0-SNAPSHOT-jar-with-dependencies.jar'
$h = 'canonical_registry/opsin_fragment_feasibility'
javac -cp $jar -d "$h/classes" "$h/src/uk/ac/cam/ch/wwmm/opsin/NameToStructure.java" "$h/src/uk/ac/cam/ch/wwmm/opsin/StereochemistryHandler.java"
javac -cp $jar -d "$h/baseline_classes" "$h/src/InspectOpsin.java"
javac -cp $jar -d "$h/classes" "$h/src/InspectOpsin.java"
python "$h/run.py"
```

A small follow-up to expose a typed trace at the application point is justified, but integration risk is **moderate to high**: the useful objects and methods are internal/private, the public API does not offer a hook, snapshot-version source provenance is not pinned, and selected-parse/warning handling, clone lineage, output graph correspondence, symmetry, and E/Z require explicit design and tests. A production adapter would need a pinned matching source build or a supported upstream API; these six diagnostic names do not justify changing the resolver or its admission policy.

OPSIN_FRAGMENT_OWNERSHIP_FEASIBLE_NARROWLY
