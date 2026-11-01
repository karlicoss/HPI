import json
from collections.abc import Iterator, Sequence
from datetime import datetime
from pathlib import Path
from sqlite3 import OperationalError
from typing import assert_type

import pytest
from hpikit.datetime import NaiveDateTime
from hpikit.json import Json

from my.core.cfg import tmp_config
from my.core.sqlite import sqlite_connection


@pytest.fixture(autouse=True)
def _config(tmp_path: Path) -> Iterator[None]:
    class user_config:
        class instagram:
            class android:
                export_path = tmp_path
                username = 'owner'
                full_name = 'Owner Name'

    with tmp_config(modules='my.instagram.android', config=user_config):
        yield


def _make_db(path: Path, *, threads: Sequence[Json], messages: Sequence[Json]) -> None:
    with sqlite_connection(path) as db:
        db.executescript('''
            CREATE TABLE session (user_id INTEGER);
            INSERT INTO session VALUES (1);
            CREATE TABLE threads (thread_info TEXT);
            CREATE TABLE messages (message TEXT, timestamp INTEGER);
        ''')
        db.executemany('INSERT INTO threads VALUES (?)', [(json.dumps(thread),) for thread in threads])
        db.executemany(
            'INSERT INTO messages VALUES (?, ?)',
            [(json.dumps(message), int(message['timestamp'])) for message in messages],
        )


def _message(*, id_: str, timestamp: int, item_type: str = 'text', **payload: object) -> Json:
    return {
        'item_id': id_,
        'item_type': item_type,
        'timestamp': str(timestamp),
        'thread_key': {'thread_id': 'local'},
        'user_id': '2',
        'text': 'A message',
        **payload,
    }


def test_messages_merge_snapshots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from my.instagram import android

    first = tmp_path / 'z.db'
    second = tmp_path / 'a.db'
    thread = {
        'thread_id': 'local',
        'thread_v2_id': 'server',
        'recipients': [{'id': 2, 'username': 'alice', 'full_name': 'Alice'}],
    }
    one = _message(id_='1', timestamp=1_000_123, text='Hello')
    _make_db(
        first,
        threads=[thread],
        messages=[
            _message(
                id_='2', timestamp=2_000_000, item_type='action_log', action_log={'description': 'Liked a message'}
            ),
            one,
            _message(id_='missing-thread', timestamp=3_000_000, thread_key={'thread_id': 'unknown'}),
        ],
    )
    updated_thread = {
        **thread,
        'recipients': [{'pk_id': 2, 'username': 'alice_new', 'full_name': 'Alice Updated'}],
    }
    _make_db(
        second,
        threads=[updated_thread],
        messages=[
            one,
            _message(id_='3', timestamp=3_000_000, item_type='reel_share', reel_share={'text': 'Shared a reel'}),
            _message(id_='4', timestamp=4_000_000, user_id='1', text='My reply'),
        ],
    )
    monkeypatch.setattr(android.config, 'export_path', [first, second])

    messages = []
    for item in android.messages():
        assert isinstance(item, android.Message), item
        assert_type(item.created, NaiveDateTime)
        assert item.created.tzinfo is None
        assert item.thread_id == 'server'
        messages.append(item)
    assert [message.id for message in messages] == ['1', '2', '3', '4']
    assert [message.text for message in messages] == ['Hello', 'Liked a message', 'Shared a reel', 'My reply']
    assert [message.user.username for message in messages[:3]] == ['alice', 'alice', 'alice_new']
    assert messages[2].user.full_name == 'Alice Updated'
    assert messages[3].user.full_name == 'Owner Name'
    assert messages[0].created == datetime.fromtimestamp(1.000123)


def test_messages_keep_partial_results_and_deduplicate_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from my.instagram import android

    first = tmp_path / 'first.db'
    second = tmp_path / 'second.db'
    thread = {
        'thread_id': 'local',
        'thread_v2_id': 'server',
        'recipients': [{'id': 2, 'username': 'alice', 'full_name': 'Alice'}],
    }
    _make_db(
        first,
        threads=[thread],
        messages=[
            _message(id_='1', timestamp=1_000_000),
            _message(id_='photo-1', timestamp=2_000_000, item_type='photo'),
            _message(id_='photo-2', timestamp=3_000_000, item_type='photo'),
        ],
    )
    with sqlite_connection(first) as db:
        db.execute('INSERT INTO messages VALUES (?, ?)', ('{', 4_000_000))
    # The later database needs user information emitted before the first database's JSON error.
    _make_db(
        second,
        threads=[{**thread, 'recipients': []}],
        messages=[
            _message(id_='2', timestamp=5_000_000),
            _message(id_='photo-3', timestamp=6_000_000, item_type='photo'),
        ],
    )
    monkeypatch.setattr(android.config, 'export_path', [first, second])

    one, unsupported, malformed, two = list(android.messages())
    assert isinstance(one, android.Message)
    assert isinstance(two, android.Message)
    assert [one.id, two.id] == ['1', '2']
    assert one.user == two.user
    assert isinstance(unsupported, android.MessageError)
    assert unsupported.args == ('photo-1', "photo isn't handled yet")
    assert isinstance(malformed, ValueError)
    for error in (unsupported, malformed):
        assert f'^ while processing {first}' in error.__notes__
    assert any(note.startswith('^ while parsing ') for note in unsupported.__notes__)


def test_messages_continue_after_database_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from my.instagram import android

    broken = tmp_path / 'broken.db'
    later = tmp_path / 'later.db'
    with sqlite_connection(broken) as db:
        db.execute('CREATE TABLE unrelated (id INTEGER)')
    thread = {'thread_id': 'local', 'thread_v2_id': 'server', 'recipients': []}
    _make_db(later, threads=[thread], messages=[_message(id_='1', timestamp=1_000_000, user_id='1')])
    monkeypatch.setattr(android.config, 'export_path', [broken, later])

    error, message = list(android.messages())
    assert isinstance(error, OperationalError)
    assert 'no such table: session' in str(error)
    assert f'^ while processing {broken}' in error.__notes__
    assert isinstance(message, android.Message)
    assert message.id == '1'
