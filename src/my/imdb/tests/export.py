from datetime import datetime
from pathlib import Path

import pytest

import my.config
import my.imdb.export as imdb
from my.core import __NOT_HPI_MODULE__  # noqa: F401


def test_latest_export_preserves_row_order(*, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Read the latest named CSV and parse ratings and timestamps in the original row order."""
    header = 'Title,You rated,created\n'
    (tmp_path / '20150101.csv').write_text(header + 'Old snapshot,1,Thu Jan 01 00:00:00 2015\n')
    (tmp_path / '20150102.csv').write_text(
        header + '"Later, Film",8,Fri Jan 02 12:34:56 2015\nEarlier Film,7,Thu Jan 01 08:00:00 2015\n'
    )

    class user_config:
        export_path = str(tmp_path / '*.csv')

    monkeypatch.setattr(my.config, 'imdb', user_config)
    later = imdb.Movie(created=datetime(2015, 1, 2, 12, 34, 56), title='Later, Film', rating=8)
    earlier = imdb.Movie(created=datetime(2015, 1, 1, 8), title='Earlier Film', rating=7)

    assert list(imdb.iter_movies()) == [later, earlier]
