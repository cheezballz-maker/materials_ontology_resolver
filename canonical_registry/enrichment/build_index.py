"""Build the derived chemistry index once before interactive use."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from time import perf_counter
from .development import open_development
from registry_identity_adapter import RegistrySnapshot
from constitution_index import ConstitutionIndex

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry",type=Path,help="Read-only source. Defaults to the development Substance registry.")
    args=parser.parse_args()
    path=args.registry or open_development()[0].path
    started=perf_counter()
    with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        snapshot=RegistrySnapshot.from_connection(db)
        index=ConstitutionIndex(snapshot)
        snapshot.assert_unchanged()
        print(json.dumps({"registry":str(path),"canonical_snapshot":snapshot.sha256,
            "records":len(snapshot.entries),"indexed_records":len(index.safe),
            "fallback_records":len(index.fallback),"cache":index.cache_statistics,
            "snapshot_timings":snapshot.timings,"seconds":perf_counter()-started},indent=2))
if __name__=="__main__":main()
