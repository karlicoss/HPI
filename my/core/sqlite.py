from .common import assert_subpackage; assert_subpackage(__name__)


from pathlib import Path
import shutil
import sqlite3
from tempfile import TemporaryDirectory


from .common import PathIsh


def sqlite_connect_immutable(db: PathIsh) -> sqlite3.Connection:
    # https://www.sqlite.org/draft/uri.html#uriimmutable
    return sqlite3.connect(f'file:{db}?immutable=1', uri=True)


def test_sqlite_connect_immutable(tmp_path: Path) -> None:
    db = str(tmp_path / 'db.sqlite')
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE testtable (col)')

    import pytest  # type: ignore
    with pytest.raises(sqlite3.OperationalError, match='readonly database'):
        with sqlite_connect_immutable(db) as conn:
            conn.execute('DROP TABLE testtable')

    # succeeds without immutable
    with sqlite3.connect(db) as conn:
        conn.execute('DROP TABLE testtable')


# TODO come up with a better name?
# NOTE: this is tested by tests/sqlite.py::test_sqlite_read_with_wal
def sqlite_copy_and_open(db: PathIsh) -> sqlite3.Connection:
    """
    'Snapshots' database and opens by making a deep copy of it including journal/WAL files
    """
    dp = Path(db)
    # TODO make atomic/check mtimes or something
    dest = sqlite3.connect(':memory:')
    with TemporaryDirectory() as td:
        tdir = Path(td)
        # shm should be recreated from scratch -- safer not to copy perhaps
        tocopy = [dp] + [p for p in dp.parent.glob(dp.name + '-*') if not p.name.endswith('-shm')]
        for p in tocopy:
            shutil.copy(p, tdir / p.name)
        with sqlite3.connect(str(tdir / dp.name)) as conn:
            from .compat import sqlite_backup
            sqlite_backup(source=conn, dest=dest)
        conn.close()
    return dest
