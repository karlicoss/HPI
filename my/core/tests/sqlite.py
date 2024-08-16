import shutil
import sqlite3
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

from ..sqlite import sqlite_connect_immutable, sqlite_copy_and_open


def test_sqlite_read_with_wal(tmp_path: Path) -> None:
    db = tmp_path / 'db.sqlite'
    # write a bit
    with sqlite3.connect(str(db)) as conn:
        conn.execute('CREATE TABLE testtable (col)')
        for i in range(5):
            conn.execute('INSERT INTO testtable (col) VALUES (?)', str(i))

    # write more in WAL mode
    with sqlite3.connect(str(db)) as conn_db:
        conn.execute('PRAGMA journal_mode=wal;')
        for i in range(5, 10):
            conn_db.execute('INSERT INTO testtable (col) VALUES (?)', str(i))
        conn_db.execute('COMMIT')

        # make sure it has unflushed stuff in wal
        wals = list(db.parent.glob('*-wal'))
        assert len(wals) == 1

        ## now run the tests in separate process to ensure there is no potential for reusing sqlite connections or something
        with ProcessPoolExecutor(1) as pool:
            # merely using it for ctx manager..
            # fmt: off
            pool.submit(_test_do_copy         , db).result()
            pool.submit(_test_do_immutable    , db).result()
            pool.submit(_test_do_copy_and_open, db).result()
            pool.submit(_test_open_asis       , db).result()
            # fmt: on


def _test_do_copy(db: Path) -> None:
    # from a copy without journal can only read previously committed stuff
    with TemporaryDirectory() as tdir:
        cdb = Path(tdir) / 'dbcopy.sqlite'
        shutil.copy(db, cdb)
        with sqlite3.connect(str(cdb)) as conn_copy:
            assert len(list(conn_copy.execute('SELECT * FROM testtable'))) == 5
        conn_copy.close()


def _test_do_immutable(db: Path) -> None:
    # in readonly mode doesn't touch
    with sqlite_connect_immutable(db) as conn_imm:
        assert len(list(conn_imm.execute('SELECT * FROM testtable'))) == 5
    conn_imm.close()


def _test_do_copy_and_open(db: Path) -> None:
    with sqlite_copy_and_open(db) as conn_mem:
        assert len(list(conn_mem.execute('SELECT * FROM testtable'))) == 10
    conn_mem.close()


def _test_open_asis(db: Path) -> None:
    # NOTE: this also works... but leaves some potential for DB corruption
    with sqlite3.connect(str(db)) as conn_db_2:
        assert len(list(conn_db_2.execute('SELECT * FROM testtable'))) == 10
    conn_db_2.close()
