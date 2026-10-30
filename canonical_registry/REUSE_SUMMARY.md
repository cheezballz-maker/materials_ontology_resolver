# Legacy component reuse

Reviewed the Chemical Parser App `app.py` OPSIN/direct parser functions, Small Organics `small_organics_resolver.py` structure/OPSIN/PubChem functions, `chemical_resolver_reuse_review.md`, `FIELD_PROFILE.md`, `REPORT.md`, actual CUMA workbook and current ontology 0.2.0. Legacy applications and ontology remain unchanged.

| Component | Treatment |
|---|---|
| Existing local OPSIN 3.0-SNAPSHOT JAR | Reused as-is |
| CPA subprocess transport concept | Refactored into bounded persistent JVM bridge; exact query, structured status/message and JAR hash retained; no first-line-success guessing |
| RDKit MolFromSmiles/MolToSmiles/InChI helpers | Reused APIs, replaced wrapper: explicit types, no suffix consumption, strict sanitization, preservation of all components/stereo/isotopes/charge |
| Text normalization | Replaced with NFC and whitespace only; never used on structures |
| PubChem PUG REST adapter and URL-keyed caching pattern | Modified: current SMILES response field, every returned candidate checked, identifier consistency required, fixed request budget, timeout, rate spacing and saved failures |
| Identity acceptance, fallback chain and text-as-canonical output | Discarded; separate explicit policy module |
| Formula lookup/first CID, salt rewrites, LLM identity proposals | Discarded |
| SQLite InChIKey-as-ID cache | Replaced with five-table registry and fresh SUB namespace; graph-plus-key exact clustering |
| Bulk alias enrichment | Discarded; each CUMA alias separately parsed and gated |
| MolStandardize comparisons and JNA reference InChI check | Added; comparisons are diagnostic only |
| Crystal/conformer/reactivity/xTB/LLM/UI paths | Excluded from this task |
| ChEBI/UniChem/CompTox/CAS/ChEMBL adapters | Deferred; PubChem supplies the bounded corroboration needed for this POC |

No legacy cache output was trusted as a canonical seed. Reuse is of installed engines, API primitives and adapter patterns, not a wholesale copy of application code or its acceptance policy.
