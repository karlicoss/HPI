import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from my.indico import export

ME = {'fullName': 'Viren, Brett', 'emailHash': 'a' * 32, 'affiliation': 'BNL'}
SOMEONE = {'fullName': 'Doe, Jane', 'emailHash': 'b' * 32}


def _day(date: str, time: str = '10:00:00', tz: str = 'America/Chicago') -> dict:
    return {'date': date, 'time': time, 'tz': tz}


def _file(number: int, name: str, **extra) -> dict:
    return {
        'id': number,
        'type': 'file',
        'title': name,
        'filename': name,
        'size': 5,
        'content_type': 'application/pdf',
        'checksum': 'c' * 32,
        'modified_dt': '2026-01-01T00:00:00+00:00',
        'download_url': f'https://i.example/{number}',
        **extra,
    }


def _event(number: int, title: str, **extra) -> dict:
    return {
        'id': str(number),
        'title': title,
        'description': 'about it',
        'startDate': _day('2026-03-04'),
        'endDate': _day('2026-03-05'),
        'timezone': 'America/Chicago',
        'type': 'meeting',
        'categoryId': 7,
        'category': 'Workshops',
        'url': f'https://i.example/event/{number}/',
        'chairs': [SOMEONE],
        'folders': [],
        **extra,
    }


def _contribution(number: int, title: str, speakers: list[dict], **extra) -> dict:
    return {
        'id': str(number),
        'title': title,
        'startDate': _day('2026-03-04', '11:00:00'),
        'endDate': _day('2026-03-04', '11:30:00'),
        'duration': 30,
        'session': 'Morning',
        'speakers': speakers,
        'primaryauthors': [],
        'coauthors': [],
        'folders': [],
        'subContributions': [],
        **extra,
    }


def _journal(name: str, fetched: str, events: list[tuple[str, dict]], files: list[dict] = (), **extra) -> dict:
    return {
        'format': 1,
        'fetched': fetched,
        'instance': name,
        'url': f'https://{name}.example',
        'view': 'v',
        'identity': {'email_hashes': ['a' * 32], 'names': ['viren, brett'], 'username': 'bv'},
        'categories': {'7': [{'id': 0, 'title': 'Home'}, {'id': 7, 'title': 'Workshops'}]},
        'events': [{'detail': detail, 'record': record} for detail, record in events],
        'files': list(files),
        **extra,
    }


@pytest.fixture
def journal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / 'slurp' / 'journal'
    directory.mkdir(parents=True)
    monkeypatch.setattr(export.config, 'export_path', directory)
    export._cached.cache_clear()
    return directory


def _write(directory: Path, stamp: str, instance: str, data: dict) -> None:
    (directory / f'{stamp}~{instance}~v.json').write_text(json.dumps(data))
    export._cached.cache_clear()


def _events() -> list:
    found = list(export.events())
    assert not [e for e in found if isinstance(e, Exception)]
    return found


def test_events_only(journal: Path) -> None:
    _write(journal, '20260601T000000Z', 'a', _journal('a', '2026-06-01T00:00:00+00:00', [('events', _event(1, 'Meeting'))]))
    [e] = _events()
    assert (e.instance, e.id, e.title, e.type) == ('a', 1, 'Meeting', 'meeting')
    assert e.start == datetime(2026, 3, 4, 10, tzinfo=e.start.tzinfo)
    assert e.start.utcoffset().total_seconds() == -6 * 3600  # Chicago, before the clocks change
    assert (e.has_agenda, e.contributions, e.sessions) == (False, (), ())
    assert e.category.path == ((0, 'Home'), (7, 'Workshops'))
    assert e.chairs[0].name == 'Doe, Jane'
    assert not e.mine
    assert e.url == 'https://i.example/event/1/'
    [site] = export.instances()
    assert (site.name, site.url, site.username) == ('a', 'https://a.example', 'bv')


def test_an_agenda_is_kept_when_a_later_view_fetches_only_events(journal: Path) -> None:
    talk = _contribution(10, 'My talk', [ME], folders=[{'title': 'Slides', 'attachments': [_file(100, 'talk.pdf')]}])
    agenda = _event(1, 'Meeting', contributions=[talk], sessions=[{'id': 5, 'title': 'Morning', 'contributions': []}])
    _write(journal, '20260601T000000Z', 'a', _journal('a', '2026-06-01T00:00:00+00:00', [('sessions', agenda)]))
    newer = _event(1, 'Meeting, renamed')
    _write(journal, '20260701T000000Z', 'a', _journal('a', '2026-07-01T00:00:00+00:00', [('events', newer)]))
    [e] = _events()
    assert e.title == 'Meeting, renamed'  # the newest observation of the event
    assert e.has_agenda  # the agenda is from the older
    assert [c.title for c in e.contributions] == ['My talk']
    assert e.observed == datetime(2026, 7, 1, tzinfo=UTC)
    assert e.agenda_observed == datetime(2026, 6, 1, tzinfo=UTC)
    assert [s.title for s in e.sessions] == ['Morning']


def test_a_newer_agenda_replaces_an_older(journal: Path) -> None:
    old = _event(1, 'M', contributions=[_contribution(10, 'Old', [SOMEONE])])
    new = _event(1, 'M', contributions=[_contribution(11, 'New', [SOMEONE])])
    _write(journal, '20260601T000000Z', 'a', _journal('a', '2026-06-01T00:00:00+00:00', [('sessions', old)]))
    _write(journal, '20260701T000000Z', 'a', _journal('a', '2026-07-01T00:00:00+00:00', [('sessions', new)]))
    [e] = _events()
    assert [c.title for c in e.contributions] == ['New']


def test_sites_do_not_mix_even_with_the_same_numbers(journal: Path) -> None:
    for site in 'ab':
        _write(journal, f'2026060{ord(site) - 96}T000000Z', site, _journal(site, '2026-06-01T00:00:00+00:00', [('events', _event(1, f'Event of {site}'))]))
    assert sorted((e.instance, e.title) for e in _events()) == [('a', 'Event of a'), ('b', 'Event of b')]


def test_mine(journal: Path) -> None:
    mine = _event(1, 'Mine', contributions=[_contribution(10, 'T', [ME]), _contribution(11, 'U', [SOMEONE])])
    chair = _event(2, 'Chaired', chairs=[ME])
    other = _event(3, 'Other', contributions=[_contribution(12, 'V', [SOMEONE])])
    by_name = _event(4, 'By name', contributions=[_contribution(13, 'W', [{'fullName': 'Viren, Brett'}])])
    sub = _contribution(14, 'Parent', [SOMEONE], subContributions=[{'id': 1, 'title': 'Part', 'speakers': [ME]}])
    nested = _event(5, 'Nested', contributions=[sub])
    _write(
        journal,
        '20260601T000000Z',
        'a',
        _journal('a', '2026-06-01T00:00:00+00:00', [('sessions', x) for x in (mine, chair, other, by_name, nested)]),
    )
    assert sorted(e.title for e in export.my_events() if not isinstance(e, Exception)) == ['By name', 'Chaired', 'Mine', 'Nested']
    assert sorted(c.title for c in export.my_contributions() if not isinstance(c, Exception)) == ['Parent', 'T', 'W']


def test_contributions_in_sessions_are_found_once(journal: Path) -> None:
    loose = _contribution(10, 'Loose', [SOMEONE])
    inner = _contribution(11, 'Inner', [SOMEONE])
    event = _event(1, 'M', contributions=[loose, inner], sessions=[{'id': 1, 'title': 'S', 'contributions': [inner]}])
    _write(journal, '20260601T000000Z', 'a', _journal('a', '2026-06-01T00:00:00+00:00', [('sessions', event)]))
    [e] = _events()
    assert [c.title for c in e.contributions] == ['Loose', 'Inner']


def test_files_are_found_where_they_were_put(journal: Path) -> None:
    pdf = journal.parent / 'files' / 'a' / 'e1' / 'a100-ccc' / 'talk.pdf'
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b'12345')
    talk = _contribution(10, 'T', [ME], folders=[{'title': 'Slides', 'attachments': [_file(100, 'talk.pdf'), _file(101, 'gone.pdf')]}])
    link = {'id': 102, 'type': 'link', 'title': 'Photos', 'link_url': 'https://photos.example/x'}
    event = _event(1, 'M', contributions=[talk], folders=[{'title': None, 'attachments': [link]}])
    entries = [
        {'attachment': 100, 'status': 'ok', 'path': 'files/a/e1/a100-ccc/talk.pdf'},
        {'attachment': 101, 'status': 'ok', 'path': 'files/a/e1/a101-ccc/gone.pdf'},  # said ok, but is not there
    ]
    _write(journal, '20260601T000000Z', 'a', _journal('a', '2026-06-01T00:00:00+00:00', [('sessions', event)], entries))
    found = {a.title: a for a in export.attachments() if not isinstance(a, Exception)}
    assert found['talk.pdf'].path == pdf
    assert found['talk.pdf'].downloaded
    assert found['talk.pdf'].folder == 'Slides'
    assert (found['talk.pdf'].contribution, found['talk.pdf'].event) == (10, 1)
    assert found['gone.pdf'].path is None
    assert found['gone.pdf'].status == 'ok'
    assert (found['Photos'].kind, found['Photos'].url, found['Photos'].contribution) == ('link', 'https://photos.example/x', None)


def test_a_later_view_that_did_not_download_does_not_lose_the_copy(journal: Path) -> None:
    pdf = journal.parent / 'files' / 'a' / 'e1' / 'a100-ccc' / 'talk.pdf'
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b'12345')
    talk = _contribution(10, 'T', [ME], folders=[{'title': 'S', 'attachments': [_file(100, 'talk.pdf')]}])
    event = _event(1, 'M', contributions=[talk])
    first = [{'attachment': 100, 'status': 'ok', 'path': 'files/a/e1/a100-ccc/talk.pdf'}]
    later = [{'attachment': 100, 'status': 'skipped: too big', 'path': None}]
    _write(journal, '20260601T000000Z', 'a', _journal('a', '2026-06-01T00:00:00+00:00', [('sessions', event)], first))
    _write(journal, '20260701T000000Z', 'a', _journal('a', '2026-07-01T00:00:00+00:00', [('sessions', event)], later))
    [a] = [a for a in export.attachments() if not isinstance(a, Exception)]
    assert a.path == pdf


def test_categories(journal: Path) -> None:
    _write(journal, '20260601T000000Z', 'a', _journal('a', '2026-06-01T00:00:00+00:00', [('events', _event(1, 'M'))]))
    found = [c for c in export.categories() if not isinstance(c, Exception)]
    assert [(c.id, c.title, len(c.path)) for c in found] == [(0, 'Home', 1), (7, 'Workshops', 2)]


def test_a_bad_event_is_an_error_not_a_loss(journal: Path) -> None:
    broken = {'id': '2', 'title': 'Broken', 'categoryId': 7, 'url': 'u', 'contributions': [{'title': 'no number'}]}
    data = _journal('a', '2026-06-01T00:00:00+00:00', [('events', _event(1, 'Fine')), ('sessions', broken)])
    data['events'].append({'detail': 'events', 'record': {'title': 'no number either'}})
    _write(journal, '20260601T000000Z', 'a', data)
    found = list(export.events())
    assert [e.title for e in found if not isinstance(e, Exception)] == ['Fine']
    assert len([e for e in found if isinstance(e, Exception)]) == 2


def test_a_journal_of_another_format_is_refused_by_name(journal: Path) -> None:
    _write(journal, '20260601T000000Z', 'a', {'format': 99})
    with pytest.raises(RuntimeError, match='99'):
        list(export.events())


def test_no_journal_says_so(journal: Path) -> None:
    with pytest.raises(RuntimeError, match='no Indico journal'):
        list(export.events())


def test_a_replaced_file_is_read_again(journal: Path) -> None:
    import os

    _write(journal, '20260601T000000Z', 'a', _journal('a', '2026-06-01T00:00:00+00:00', [('events', _event(1, 'Before'))]))
    assert [e.title for e in _events()] == ['Before']
    path = next(journal.iterdir())
    path.write_text(json.dumps(_journal('a', '2026-06-01T00:00:00+00:00', [('events', _event(1, 'After'))])))
    os.utime(path, (1, 1_900_000_000))
    assert [e.title for e in _events()] == ['After']
