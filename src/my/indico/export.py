"""
Events, agendas and files from [[https://getindico.io][Indico]] sites, kept as a journal by [[https://github.com/brettviren/orgface][orgface]] (=orgface slurp indico=)
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, tzinfo
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from my.core import Paths, Res, Stats, get_files, make_config, make_logger, stat

from .common import (
    Attachment,
    Category,
    Contribution,
    Event,
    Instance,
    Person,
    Session,
    SubContribution,
)

import my.config  # isort: skip


@dataclass
class indico(my.config.indico):
    '''
    Uses the journal of JSON files that =orgface slurp indico= writes: one for each run of a view on a site.
    '''

    # path[s]/glob to the journal, i.e. its directory ('journal' under the slurp directory).
    # The downloaded files are found beside it, in 'files'.
    export_path: Paths


config = make_config(indico)

logger = make_logger(__name__)

# the journal format this reads
FORMAT = 1


def inputs() -> Sequence[Path]:
    try:
        return tuple(p for p in get_files(config.export_path) if p.suffix == '.json')
    except (AssertionError, OSError):  # get_files insists that the path exists
        return ()


# -- reading the journal


@dataclass
class _Seen:
    """What the journal has said about one event, put together."""

    meta: dict  # the newest observation of the event itself
    observed: datetime
    agenda: dict | None = None  # the newest observation that has the agenda
    agenda_observed: datetime | None = None


@dataclass(frozen=True)
class _Identity:
    hashes: frozenset[str] = frozenset()
    names: frozenset[str] = frozenset()

    def is_person(self, person: dict) -> bool:
        return (person.get('emailHash') in self.hashes) or (str(person.get('fullName', '')).strip().lower() in self.names)


@dataclass(frozen=True)
class _State:
    instances: dict[str, Instance]
    identities: dict[str, _Identity]
    events: dict[tuple[str, int], _Seen]
    categories: dict[tuple[str, int], list[dict]]
    files: dict[tuple[str, int], dict]
    problems: tuple[Exception, ...] = field(default=())


def _when(text: str) -> datetime:
    return datetime.fromisoformat(text).astimezone(UTC)


def _load(paths: Sequence[Path]) -> _State:
    """
    The journal, oldest first so that what is newer replaces what is older.

    An event is the newest observation of the event itself, and the agenda of the newest observation that has one,
    so a view that fetched only events does not hide an agenda that an earlier one fetched.
    A file is the newest entry that has a copy on this computer, else the newest entry.
    """
    instances: dict[str, Instance] = {}
    identities: dict[str, _Identity] = {}
    events: dict[tuple[str, int], _Seen] = {}
    categories: dict[tuple[str, int], list[dict]] = {}
    files: dict[tuple[str, int], dict] = {}
    problems: list[Exception] = []

    for path in sorted(paths, key=lambda p: p.name):  # the names start with the time
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as e:
            raise RuntimeError(f'{path}: {e}') from e
        fmt = data.get('format') if isinstance(data, dict) else None
        if fmt != FORMAT:
            raise RuntimeError(f'{path}: journal format {fmt!r}, but this reads {FORMAT}; is HPI or orgface out of date?')
        name = data['instance']
        fetched = _when(data['fetched'])
        ident = data.get('identity') or {}
        instances[name] = Instance(name=name, url=data['url'], username=ident.get('username') or None)
        identities[name] = _Identity(frozenset(ident.get('email_hashes', ())), frozenset(ident.get('names', ())))

        for cid, steps in (data.get('categories') or {}).items():
            categories[(name, int(cid))] = steps
        for item in data.get('events', ()):
            try:
                record = item['record']
                key = (name, int(record['id']))
                seen = events.get(key)
                if seen is None:
                    seen = events[key] = _Seen(meta=record, observed=fetched)
                else:
                    seen.meta, seen.observed = record, fetched
                if item.get('detail') == 'sessions':
                    seen.agenda, seen.agenda_observed = record, fetched
            except (KeyError, TypeError, ValueError) as e:
                problems.append(RuntimeError(f'{path}: an event that has no number: {e!r}'))
        for entry in data.get('files', ()):
            try:
                key = (name, int(entry['attachment']))
            except (KeyError, TypeError, ValueError):
                problems.append(RuntimeError(f'{path}: a file that has no number'))
                continue
            local = path.parent.parent / entry['path'] if entry.get('path') else None
            entry = {**entry, 'local': local}
            earlier = files.get(key)
            if earlier is not None and local is None and earlier.get('local') is not None and earlier['local'].is_file():
                continue  # a newer view did not download what an earlier one did; keep the copy
            files[key] = entry

    return _State(instances, identities, events, categories, files, tuple(problems))


@lru_cache(maxsize=4)
def _cached(paths: tuple[Path, ...], stamp: tuple[float, ...]) -> _State:
    return _load(paths)


def _state() -> _State:
    paths = tuple(inputs())
    if len(paths) == 0:
        raise RuntimeError(f'no Indico journal found in {config.export_path}')
    # the modification times make a file that was replaced in place be read again
    return _cached(paths, tuple(p.stat().st_mtime for p in paths))


# -- small helpers


def _number(record: dict) -> int:
    """
    The number a talk has in the site's URLs, which is unique on the site.
    The 'id' is only unique in its event, and is what the site calls the 'friendly' one.
    """
    return int(record.get('db_id') or record['id'])


def _friendly(record: dict) -> int | None:
    found = record.get('friendly_id', record.get('id'))
    return int(found) if found is not None else None


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _day(spec: Any, fallback_zone: str | None = None) -> datetime | None:
    """A date, time and zone as Indico writes them: {'date': '2026-03-04', 'time': '10:00:00', 'tz': 'UTC'}."""
    if not isinstance(spec, dict) or not spec.get('date'):
        return None
    zone: tzinfo
    try:
        zone = ZoneInfo(spec.get('tz') or fallback_zone or 'UTC')
    except (KeyError, ValueError, OSError):
        zone = UTC
    try:
        return datetime.fromisoformat(f"{spec['date']}T{spec.get('time') or '00:00:00'}").replace(tzinfo=zone)
    except ValueError:
        return None


def _stamp(text: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(text) if text else None
    except (TypeError, ValueError):
        return None


def _people(items: Any, identity: _Identity) -> tuple[Person, ...]:
    return tuple(
        Person(
            name=str(p.get('fullName') or f"{p.get('last_name', '')}, {p.get('first_name', '')}".strip(', ')),
            affiliation=_text(p.get('affiliation')),
            email_hash=_text(p.get('emailHash')),
            mine=identity.is_person(p),
        )
        for p in items or ()
        if isinstance(p, dict)
    )


@dataclass(frozen=True)
class _Where:
    """What an attachment is attached to, and how to find its file."""

    state: _State
    instance: str
    event: int
    contribution: int | None = None
    subcontribution: int | None = None


def _attachments(holder: dict, where: _Where) -> tuple[Attachment, ...]:
    found = []
    for folder in holder.get('folders') or ():
        for a in folder.get('attachments') or ():
            number = int(a['id'])
            entry = where.state.files.get((where.instance, number), {})
            local = entry.get('local')
            kind = a.get('type') or 'file'
            found.append(
                Attachment(
                    instance=where.instance,
                    id=number,
                    event=where.event,
                    contribution=where.contribution,
                    subcontribution=where.subcontribution,
                    folder=_text(folder.get('title')),
                    title=str(a.get('title') or a.get('filename') or number),
                    kind=kind,
                    filename=_text(a.get('filename')),
                    content_type=_text(a.get('content_type')),
                    size=a.get('size') if isinstance(a.get('size'), int) else None,
                    checksum=_text(a.get('checksum')),
                    modified=_stamp(a.get('modified_dt')),
                    url=_text(a.get('link_url') if kind == 'link' else a.get('download_url')),
                    status=_text(entry.get('status')),
                    path=local if local is not None and local.is_file() else None,
                )
            )
    return tuple(found)


def _contribution(c: dict, event: dict, where: _Where, identity: _Identity, zone: str | None) -> Contribution:
    number = _number(c)
    here = _Where(where.state, where.instance, where.event, number)
    subs = tuple(
        SubContribution(
            instance=where.instance,
            event=where.event,
            contribution=number,
            id=_number(s),
            friendly_id=_friendly(s),
            title=str(s.get('title') or ''),
            description=str(s.get('description') or ''),
            duration=s.get('duration') if isinstance(s.get('duration'), int) else None,
            speakers=_people(s.get('speakers'), identity),
            attachments=_attachments(s, _Where(where.state, where.instance, where.event, number, _number(s))),
        )
        for s in c.get('subContributions') or ()
    )
    speakers = _people(c.get('speakers'), identity)
    authors = _people(c.get('primaryauthors'), identity)
    coauthors = _people(c.get('coauthors'), identity)
    return Contribution(
        instance=where.instance,
        event=where.event,
        id=number,
        friendly_id=_friendly(c),
        title=str(c.get('title') or '(untitled)'),
        description=str(c.get('description') or ''),
        start=_day(c.get('startDate'), zone),
        end=_day(c.get('endDate'), zone),
        duration=c.get('duration') if isinstance(c.get('duration'), int) else None,
        session=_text(c.get('session')),
        track=_text(c.get('track')),
        type=_text(c.get('type')),
        location=_text(c.get('location')),
        room=_text(c.get('roomFullname') or c.get('room')),
        url=_text(c.get('url')),
        speakers=speakers,
        authors=authors,
        coauthors=coauthors,
        attachments=_attachments(c, here),
        subcontributions=subs,
        mine=any(p.mine for p in (*speakers, *authors, *coauthors)) or any(p.mine for s in subs for p in s.speakers),
    )


def _category(state: _State, instance: str, record: dict) -> Category:
    number = int(record['categoryId'])
    steps = state.categories.get((instance, number))
    path = tuple((int(s['id']), str(s['title'])) for s in steps or ())
    title = str(record.get('category') or (path[-1][1] if path else number))
    if not path or path[-1][0] != number:
        path = (*path, (number, title))
    return Category(instance=instance, id=number, title=title, path=path)


def _event(state: _State, instance: str, seen: _Seen) -> Event:
    meta = seen.meta
    number = int(meta['id'])
    identity = state.identities.get(instance, _Identity())
    zone = _text(meta.get('timezone'))
    where = _Where(state, instance, number)
    chairs = _people(meta.get('chairs'), identity)

    sessions: tuple[Session, ...] = ()
    contributions: tuple[Contribution, ...] = ()
    if seen.agenda is not None:
        agenda = seen.agenda
        sessions = tuple(
            Session(
                instance=instance,
                event=number,
                id=int(s['id']),
                title=str(s.get('title') or s.get('slotTitle') or ''),
                description=str(s.get('description') or ''),
                start=_day(s.get('startDate'), zone),
                end=_day(s.get('endDate'), zone),
                location=_text(s.get('location')),
                room=_text(s.get('roomFullname') or s.get('room')),
                conveners=_people(s.get('conveners'), identity),
                mine=any(p.mine for p in _people(s.get('conveners'), identity)),
            )
            for s in agenda.get('sessions') or ()
        )
        seen_contributions: dict[int, dict] = {}
        for holder in (agenda, *(agenda.get('sessions') or ())):
            for c in holder.get('contributions') or ():
                seen_contributions.setdefault(_number(c), c)
        contributions = tuple(
            sorted(
                (_contribution(c, agenda, where, identity, zone) for c in seen_contributions.values()),
                key=lambda c: (c.start or datetime.min.replace(tzinfo=UTC), c.id),
            )
        )

    creator = meta.get('creator')
    return Event(
        instance=instance,
        id=number,
        title=str(meta.get('title') or '(untitled)'),
        description=str(meta.get('description') or ''),
        type=_text(meta.get('type')),
        start=_day(meta.get('startDate'), zone),
        end=_day(meta.get('endDate'), zone),
        timezone=zone,
        location=_text(meta.get('location')),
        room=_text(meta.get('roomFullname') or meta.get('room')),
        address=_text(meta.get('address')),
        url=str(meta.get('url') or f'{state.instances[instance].url}/event/{number}/'),
        category=_category(state, instance, meta),
        keywords=tuple(str(k) for k in meta.get('keywords') or ()),
        created=_day(meta.get('creationDate')),
        creator=_text(creator.get('fullName')) if isinstance(creator, dict) else None,
        chairs=chairs,
        attachments=_attachments(meta, where),
        sessions=sessions,
        contributions=contributions,
        has_agenda=seen.agenda is not None,
        observed=seen.observed,
        agenda_observed=seen.agenda_observed,
        mine=any(p.mine for p in chairs) or any(s.mine for s in sessions) or any(c.mine for c in contributions),
    )


# -- the public functions


def instances() -> Iterator[Res[Instance]]:
    yield from sorted(_state().instances.values(), key=lambda i: i.name)


def events() -> Iterator[Res[Event]]:
    """
    Every event any view has fetched, newest first.
    """
    state = _state()
    yield from state.problems
    found: list[Event] = []
    for (instance, number), seen in state.events.items():
        try:
            found.append(_event(state, instance, seen))
        except (KeyError, TypeError, ValueError) as e:
            yield RuntimeError(f'{instance} event {number}: {e!r}')
    far = datetime.min.replace(tzinfo=UTC)
    found.sort(key=lambda e: (e.start or far, e.instance, e.id), reverse=True)
    yield from found


def categories() -> Iterator[Res[Category]]:
    """
    The categories of the events, and those above them as far as the journal knows.
    """
    seen: dict[tuple[str, int], Category] = {}
    for e in events():
        if isinstance(e, Exception):
            yield e
            continue
        steps = e.category.path
        for i, (number, title) in enumerate(steps):
            key = (e.instance, number)
            if key not in seen:
                seen[key] = Category(e.instance, number, title, steps[: i + 1])
    yield from sorted(seen.values(), key=lambda c: (c.instance, c.path))


def contributions() -> Iterator[Res[Contribution]]:
    for e in events():
        if isinstance(e, Exception):
            yield e
        else:
            yield from e.contributions


def attachments() -> Iterator[Res[Attachment]]:
    """
    Every file and link whose event has been fetched with its agenda, or that is attached to an event.
    """
    for e in events():
        if isinstance(e, Exception):
            yield e
            continue
        yield from e.attachments
        for c in e.contributions:
            yield from c.all_attachments


def my_events() -> Iterator[Res[Event]]:
    """
    The events the user chairs, convenes, speaks at or is an author at.
    """
    for e in events():
        if isinstance(e, Exception) or e.mine:
            yield e


def my_contributions() -> Iterator[Res[Contribution]]:
    for c in contributions():
        if isinstance(c, Exception) or c.mine:
            yield c


def stats() -> Stats:
    return {
        **stat(instances),
        **stat(events),
        **stat(contributions),
        **stat(attachments),
        **stat(my_events),
    }
