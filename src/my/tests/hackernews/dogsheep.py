from datetime import UTC, datetime
from pathlib import Path
from typing import assert_type, get_type_hints

import pytest

from my.core.datetime import AwareDateTime, aware
from my.core.sqlite import sqlite_connection
from my.hackernews import dogsheep


def test_dogsheep_items(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / 'hackernews.sqlite'
    with sqlite_connection(db) as conn:
        conn.execute('CREATE TABLE items (id TEXT, type TEXT, time INTEGER, title TEXT, text TEXT, url TEXT)')
        conn.executemany(
            'INSERT INTO items VALUES (?, ?, ?, ?, ?, ?)',
            [
                ('2', 'story', 1704067200, 'A story', None, 'https://example.com/story'),
                ('1', 'comment', 0, None, '<p>A comment</p>', None),
            ],
        )

    monkeypatch.setattr(dogsheep.config, 'export_path', db)
    results = list(dogsheep.items())
    assert results == [
        dogsheep.Item(
            id='1',
            type='comment',
            created=aware(datetime(1970, 1, 1, tzinfo=UTC)),
            title=None,
            text_html='<p>A comment</p>',
            url=None,
        ),
        dogsheep.Item(
            id='2',
            type='story',
            created=aware(datetime(2024, 1, 1, tzinfo=UTC)),
            title='A story',
            text_html=None,
            url='https://example.com/story',
        ),
    ]
    for item in results:
        assert not isinstance(item, Exception)
        assert_type(item.created, AwareDateTime)
        assert item.created.tzinfo is UTC
        assert item.permalink == f'https://news.ycombinator.com/item?id={item.id}'
    assert get_type_hints(dogsheep.Item)['created'] is datetime
