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


@pytest.mark.parametrize('with_cached_story', [False, True])
def test_harmonic_saved_yields_missing_cache_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    with_cached_story: bool,
) -> None:
    pytest.importorskip('lxml')
    from my.hackernews import harmonic

    prefix = 'com.simon.harmonichackernews.KEY_SHARED_PREFERENCES'
    cached = ''
    if with_cached_story:
        cached = f'''
            <string name="{prefix}_CACHED_STORY1">
                {{"id": 1, "created_at_i": 0, "title": "A story", "url": "https://example.com/story"}}
            </string>
        '''
    xml = f'''
        <map>
            <set name="{prefix}_CACHED_STORIES_STRINGS">
                <string>1-1000</string>
                <string>2-2000</string>
            </set>
            {cached}
            <string name="{prefix}_BOOKMARKS">2q2000-1q1000-3q3000</string>
        </map>
    '''
    for name in ['first.xml', 'second.xml']:
        (tmp_path / name).write_text(xml)
    # A later snapshot can contain metadata for an ID that already produced an error.
    later_cached = f'''
        <string name="{prefix}_CACHED_STORY2">
            {{"id": 2, "created_at_i": 0, "title": "Recovered story", "url": "https://example.com/recovered"}}
        </string>
    '''
    (tmp_path / 'third.xml').write_text(xml.replace('</map>', f'{later_cached}</map>'))
    monkeypatch.setattr(harmonic.harmonic, 'export_path', tmp_path)

    results = list(harmonic.saved())
    saved = [item for item in results if isinstance(item, harmonic.Saved)]
    errors = [item for item in results if isinstance(item, Exception)]
    if with_cached_story:
        first, later = saved
        assert first.uid == '1'
        assert first.hackernews_link == 'https://news.ycombinator.com/item?id=1'
        assert first.when == datetime(1970, 1, 1, tzinfo=UTC)
        assert first.title == 'A story'
        assert first.url == 'https://example.com/story'
        assert isinstance(results[0], RuntimeError)
        assert results[1] is first
        missing_ids = ['2', '3']
    else:
        (later,) = saved
        missing_ids = ['2', '1', '3']
    assert later.uid == '2'
    assert later.title == 'Recovered story'
    assert later.url == 'https://example.com/recovered'
    assert all(isinstance(error, RuntimeError) for error in errors)
    assert [str(error) for error in errors] == [
        f'{tmp_path / "first.xml"}: no cached story for bookmark {uid}' for uid in missing_ids
    ]
