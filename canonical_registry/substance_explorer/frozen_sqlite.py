"""Read-only SQLite access for frozen snapshots and live development registries."""

from pathlib import Path
import sqlite3

from canonical_registry.chemistry import normalize_name


class FrozenSQLite:
    """Use immutable reads only for frozen files; live reads use SQLite transactions."""

    def __init__(self, path, *, live=False):
        self.live = live
        path = Path(path)
        self.path = path.expanduser().resolve(strict=True)
        self._check_file()

    def _check_file(self):
        if not self.path.is_file():
            raise ValueError("Select a standalone SQLite registry file.")
        for suffix in (() if self.live else ("-wal", "-journal")):
            if Path(str(self.path) + suffix).exists():
                raise ValueError("Select a closed, checkpointed snapshot without a WAL or journal.")

    def connect(self):
        self._check_file()
        db = sqlite3.connect(self.path.as_uri() + ("?mode=ro" if self.live else "?mode=ro&immutable=1"), uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.create_function("fold", 1, lambda value: normalize_name(value).casefold(), deterministic=True)
        if self.live:
            db.execute("BEGIN")
        return db

    def snapshot_token(self):
        self._check_file()
        stat = self.path.stat()
        token = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        if self.live:
            wal = Path(str(self.path) + "-wal")
            try:
                wal_stat = wal.stat()
                return (*token, wal_stat.st_size, wal_stat.st_mtime_ns)
            except FileNotFoundError:
                return (*token, None, None)
        return token
