from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import OperationalError
from struct import error as StructError
from typing import assert_type

import pytest
from hpikit.datetime import AwareDateTime

from my.core.sqlite import sqlite_connection


def _make_db(path: Path, *, rows: Sequence[tuple[object, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite_connection(path) as db:
        db.executescript('''
            CREATE TABLE statuses (
                status_id INTEGER, author_id INTEGER, created INTEGER, content BLOB, quoted_tweet_id INTEGER,
                bookmarked INTEGER, favorited INTEGER, retweeted INTEGER,
                in_r_user_id INTEGER DEFAULT 0, in_r_status_id INTEGER DEFAULT 0, conversation_id INTEGER DEFAULT 1
            );
            CREATE TABLE users (
                user_id INTEGER, username TEXT, is_active_creator INTEGER,
                is_graduated INTEGER, profile_highlights_info TEXT
            );
            INSERT INTO users (user_id, username) VALUES (42, 'me'), (7, 'other');
            CREATE TABLE list_mapping (list_mapping_user_id INTEGER);
            CREATE TABLE cursors (owner_id INTEGER);
            CREATE TABLE status_groups (owner_id INTEGER);
            INSERT INTO status_groups VALUES (42);
        ''')
        db.executemany(
            '''
            INSERT INTO statuses (
                status_id, author_id, created, content, quoted_tweet_id, bookmarked, favorited, retweeted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
            rows,
        )


def test_tweets_likes_and_bookmarks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from my.twitter import android

    first = tmp_path / 'z' / '42-66.db'
    second = tmp_path / 'a' / '42-66.db'
    empty = tmp_path / 'empty.db'
    shared = [
        (2, 7, 2000, b'J\x03B\x06quotedI\x08', 0, 0, 0, 0),
        (3, 7, 3000, b'J\x03B\x06repostI\x08', 0, 1, 1, 1),
        (4, 7, 4000, b'J\x03B\x05likedI\x08', 0, 0, 1, 0),
        (5, 7, 5000, b'J\x03B\x08bookmarkI\x08', 0, 1, 0, 0),
    ]
    _make_db(first, rows=[(1, 42, 1000, b'J\x03B\x03ownI\x08', 2, 0, 0, 0), *shared])
    _make_db(
        second,
        rows=[
            (1, 42, 1000, b'J\x03B\x06editedI\x08', 2, 0, 0, 0),
            *shared,
            (6, 42, 6000, b'J\x03B\x05laterI\x08', 0, 1, 1, 0),
        ],
    )
    _make_db(empty, rows=[])

    # Explicit input order wins over filenames, and the filename supplies the otherwise missing owner ID.
    monkeypatch.setattr(android.config, 'export_path', [first, empty, second], raising=False)
    for provider, expected in [
        (android.tweets, [('1', 'own'), ('3', 'repost'), ('2', 'quoted'), ('1', 'edited'), ('6', 'later')]),
        (android.likes, [('3', 'repost'), ('4', 'liked'), ('6', 'later')]),
        (android.bookmarks, [('3', 'repost'), ('5', 'bookmark'), ('6', 'later')]),
    ]:
        tweets = []
        for item in provider():
            assert isinstance(item, android.Tweet), item
            assert_type(item.created_at, AwareDateTime)
            assert item.created_at == datetime(1970, 1, 1, second=int(item.id_str), tzinfo=UTC)
            assert item.permalink == f'https://twitter.com/{item.screen_name}/status/{item.id_str}'
            tweets.append((item.id_str, item.text))
        assert tweets == expected


def test_bookmarks_preserve_parse_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from my.twitter import android

    path = tmp_path / '42-66.db'
    _make_db(
        path,
        rows=[
            (1, 7, 1000, b'', 0, 1, 0, 0),
            (2, 7, 2000, b'J\x03B\x02okI\x08', 0, 1, 0, 0),
        ],
    )
    monkeypatch.setattr(android.config, 'export_path', path, raising=False)

    error, tweet = list(android.bookmarks())
    assert isinstance(error, StructError)
    assert isinstance(tweet, android.Tweet)
    assert tweet.id_str == '2'
    assert tweet.text == 'ok'


def test_bookmarks_raise_database_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from my.twitter import android

    path = tmp_path / 'broken.db'
    with sqlite_connection(path) as db:
        db.execute('CREATE TABLE unrelated (id INTEGER)')
    monkeypatch.setattr(android.config, 'export_path', path, raising=False)

    with pytest.raises(OperationalError, match='no such table: statuses') as raised:
        list(android.bookmarks())
    assert f'^ while processing {path}' in raised.value.__notes__
