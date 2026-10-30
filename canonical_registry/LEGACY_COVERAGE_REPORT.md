# Legacy-table candidate-presence coverage

Read-only database-side aggregates, 27 October 2026. No legacy records downloaded or reconciled.

Matched by at least one channel: **102 / 112 (91.1%)**. Not matched: **10**.

| Measure | Result |
|---|---:|
| coverage | 0.9107142857142857 |
| multiple_channel_match | 82 |
| not_matched | 10 |
| matched_any_channel | 102 |
| inchikey_match | 91 |
| alias_match | 93 |
| canonical_substances | 112 |
| cas_identifier_match | 0 |

Channel counts are non-exclusive. Alias matching means candidate presence, not canonical equivalence. InChIKey matches also do not override this registry’s graph-specific identity policy. CAS channel is zero eligible identifiers in this POC, not evidence of legacy CAS absence. Alias scope: exact literals in substance_name_all plus English master, IUPAC, JChem, compound and scientific names. No case/whitespace folding.

SQL: `output/legacy_coverage.sql`. Canonical input is restricted to the accepted registry; aggregation occurs in Trino against the source table.

Successful query ID: `2114922003525357569` (SUCCEEDED; one aggregate row). Initial query `2114921724801273858` failed with an array-constructor argument limit. Its SQL is preserved in `output/legacy_coverage_failed_array_limit.sql`; the corrected query concatenates smaller arrays with identical matching semantics.
