import sqlite3
from pathlib import Path
p=Path(__file__).resolve().parent/'run/candidates.sqlite'
c=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True)
print('Processed records:',c.execute("select count(*) from candidate where diagnostic != 'Frozen source input'").fetchone()[0])
c.close()
