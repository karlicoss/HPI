from .common import assert_subpackage; assert_subpackage(__name__)

import sqlite3

from .common import PathIsh

def sqlite_connect_immutable(db: PathIsh) -> sqlite3.Connection:
    # https://www.sqlite.org/draft/uri.html#uriimmutable
    return sqlite3.connect(f'file:{db}?immutable=1', uri=True)


from pathlib import Path
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
