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
        with sqlite3.connect(tdir / dp.name) as conn:
            conn.backup(dest)
    return dest


def test_sqlite_read_with_wal(tmp_path: Path) -> None:
    db = tmp_path / 'db.sqlite'
    # write a bit
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE testtable (col)')
        for i in range(5):
            conn.execute('INSERT INTO testtable (col) VALUES (?)', str(i))

    # write more in WAL mode
    with sqlite3.connect(db) as conn_db:
        conn.execute('PRAGMA journal_mode=wal;')
        for i in range(5, 10):
            conn_db.execute('INSERT INTO testtable (col) VALUES (?)', str(i))
        conn_db.execute('COMMIT')

        # make sure it has unflushed stuff in wal
        wals = list(db.parent.glob('*-wal'))
        assert len(wals) == 1

        ## now run the tests in separate process to ensure there is no potential for reusing sqlite connections or something
        from concurrent.futures import ProcessPoolExecutor as Pool
        with Pool(1) as pool:
            # merely using it for ctx manager..
            pool.submit(_test_do_copy         , db).result()
            pool.submit(_test_do_immutable    , db).result()
            pool.submit(_test_do_copy_and_open, db).result()
            pool.submit(_test_open_asis       , db).result()


def _test_do_copy(db: Path) -> None:
    # from a copy without journal can only read previously committed stuff
    with TemporaryDirectory() as tdir:
        cdb = Path(tdir) / 'dbcopy.sqlite'
        shutil.copy(db, cdb)
        with sqlite3.connect(cdb) as conn_copy:
            assert len(list(conn_copy.execute('SELECT * FROM testtable'))) == 5


def _test_do_immutable(db: Path) -> None:
    # in readonly mode doesn't touch
    with sqlite_connect_immutable(db) as conn_imm:
        assert len(list(conn_imm.execute('SELECT * FROM testtable'))) == 5


def _test_do_copy_and_open(db: Path) -> None:
    with sqlite_copy_and_open(db) as conn_mem:
        assert len(list(conn_mem.execute('SELECT * FROM testtable'))) == 10


def _test_open_asis(db: Path) -> None:
    # NOTE: this also works... but leaves some potential for DB corruption
    with sqlite3.connect(db) as conn_db_2:
        assert len(list(conn_db_2.execute('SELECT * FROM testtable'))) == 10
