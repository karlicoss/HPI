from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import OperationalError
from typing import assert_type

import pytest
from hpikit.datetime import AwareDateTime

from my.core.sqlite import sqlite_connection


def test_materialistic_saves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from my.hackernews import materialistic

    first = tmp_path / 'z.db'
    second = tmp_path / 'a.db'
    for path, rows in [
        (
            first,
            [
                ('1', 2000, 'Original title', 'https://example.com/one'),
                ('2', 0, 'Earlier save', 'https://example.com/two'),
            ],
        ),
        (
            second,
            [
                ('1', 1000, 'Updated title', 'https://example.com/updated'),
                ('3', 500, 'New save', 'https://example.com/three'),
            ],
        ),
    ]:
        with sqlite_connection(path) as conn:
            conn.execute('CREATE TABLE saved (itemid TEXT, time INTEGER, title TEXT, url TEXT)')
            conn.executemany('INSERT INTO saved VALUES (?, ?, ?, ?)', rows)

    # Explicit input order wins over filenames, with timestamp ordering only within each database.
    monkeypatch.setattr(materialistic.config, 'export_path', [first, second], raising=False)
    results = list(materialistic.saves())
    assert [item.uid for item in results] == ['2', '1', '3']
    assert [item.title for item in results] == ['Earlier save', 'Original title', 'New save']
    assert [item.url for item in results] == [
        'https://example.com/two',
        'https://example.com/one',
        'https://example.com/three',
    ]
    assert [item.when for item in results] == [
        datetime(1970, 1, 1, tzinfo=UTC),
        datetime(1970, 1, 1, second=2, tzinfo=UTC),
        datetime(1970, 1, 1, microsecond=500_000, tzinfo=UTC),
    ]
    for item in results:
        assert_type(item.when, AwareDateTime)
        assert item.when.tzinfo is UTC
        assert item.hackernews_link == f'https://news.ycombinator.com/item?id={item.uid}'


def test_materialistic_saves_raises_database_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from my.hackernews import materialistic

    broken = tmp_path / 'broken.db'
    with sqlite_connection(broken) as conn:
        conn.execute('CREATE TABLE unrelated (id TEXT)')
    monkeypatch.setattr(materialistic.config, 'export_path', broken, raising=False)

    with pytest.raises(OperationalError, match='no such table: saved') as raised:
        list(materialistic.saves())
    assert f'^ while processing {broken}' in raised.value.__notes__
