"""Explicit additive migration for a marked development ChemicalConcept registry."""
import argparse
from contextlib import closing
import sqlite3
from canonical_registry.enrichment import development
from .registry import fixture_path
from .identity_contract import migrate

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database")
    args = parser.parse_args()
    path = fixture_path(args.database)
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, isolation_level=None)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        if db.execute("SELECT marker FROM fixture_marker").fetchall() != [("CHEMICAL_CONCEPT_POC_V1",)]:
            raise PermissionError("FIXTURE_MARKER_REQUIRED")
        migrate(db)
        print(db.execute("SELECT status, count(*) FROM concept_alignment GROUP BY status ORDER BY status").fetchall())

if __name__ == "__main__":
    main()
