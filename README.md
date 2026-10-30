# Materials Ontology Resolver

Canonical molecular Substance resolution, read-only registry matching, and controlled source-concept association experiments.

Start with:

- [Controlled identity reuse](canonical_registry/CONTROLLED_CANONICAL_IDENTITY_REUSE_V1_REPORT.md)
- [Read-only canonical matching](canonical_registry/CANONICAL_REGISTRY_MATCHING_V1_REPORT.md)
- [Chemical correspondence hardening](canonical_registry/CHEMICAL_CORRESPONDENCE_HARDENING_AND_VALIDATION_V1_REPORT.md)
- [Resolver setup](canonical_registry/README.md)
- [Ontology](ontology/substance_ontology.ttl)
- [Publication and local-data notes](PUBLICATION_NOTES.md)

The latest association implementation is fixture-only. It does not authorize production writes or create canonical Substance identities.

## Local setup

Install the Python packages in `canonical_registry/requirements.txt` and provide JDK 17 and Maven. Build the bundled OPSIN source to obtain the local OPSIN/InChI bridge dependencies; binary JARs are not committed. Keep credentials in an ignored `.env.local`, using `.env.example` as a template.

The source-only checkout omits the local databases, caches and evaluation assets used in historical validation. See the publication notes before attempting complete replay.
