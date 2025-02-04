"""
Tinder data from Android app database (in =/data/data/com.tinder/databases/tinder-3.db=)
"""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import chain
from pathlib import Path
from typing import Union

from my.core import Paths, Res, Stats, datetime_aware, get_files, make_logger, stat
from my.core.common import unique_everseen
from my.core.compat import add_note, assert_never
from my.core.sqlite import sqlite_connection

import my.config  # isort: skip


logger = make_logger(__name__)


@dataclass
class config(my.config.tinder.android):
    # paths[s]/glob to the exported sqlite databases
    export_path: Paths


@dataclass(unsafe_hash=True)
class Person:
    id: str
    name: str
    # todo bio? it might change, not sure what do we want here


@dataclass(unsafe_hash=True)
class _BaseMatch:
    # for android, checked directly shortly after a match
    when: datetime_aware
    id: str


@dataclass(unsafe_hash=True)
class _Match(_BaseMatch):
    person_id: str


@dataclass(unsafe_hash=True)
class Match(_BaseMatch):
    person: Person


# todo again, not sure what's the 'optimal' field order? perhaps the one which gives the most natural sort?
# so either match id or datetime
@dataclass
class _BaseMessage:
    # looks like gdpr takeout does contain GMT (compared against google maps data)
    sent: datetime_aware
    id: str
    text: str


@dataclass(unsafe_hash=True)
class _Message(_BaseMessage):
    match_id: str
    from_id: str
    to_id: str


@dataclass
class Message(_BaseMessage):
    match: Match
    from_: Person
    to: Person


# todo hmm I have a suspicion it might be cumulative?
# although still possible that the user might remove/install app back, so need to keep that in mind
def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


_Entity = Union[Person, _Match, _Message]
Entity = Union[Person, Match, Message]


def _entities() -> Iterator[Res[_Entity]]:
    paths = inputs()
    total = len(paths)
    width = len(str(total))
    for idx, path in enumerate(paths):
        logger.info(f'processing [{idx:>{width}}/{total:>{width}}] {path}')
        with sqlite_connection(path, immutable=True, row_factory='row') as db:
            try:
                yield from _handle_db(db)
            except Exception as e:
                add_note(e, f'^ while processing {path}')
                yield e


def _handle_db(db: sqlite3.Connection) -> Iterator[Res[_Entity]]:
    # profile_user_view contains our own user id
    user_profile_rows = list(db.execute('SELECT * FROM profile_user_view'))

    if len(user_profile_rows) == 0:
        # shit, sometime in 2023 profile_user_view stopped containing user profile..
        # presumably the most common from_id/to_id would be our own username
        counter = Counter([id_ for (id_,) in db.execute('SELECT from_id FROM message UNION ALL SELECT to_id FROM message')])
        if len(counter) > 0:  # this might happen if db is empty (e.g. user got logged out)
            [(you_id, _)] = counter.most_common(1)
            yield Person(id=you_id, name='you')

    for row in chain(
        user_profile_rows,
        db.execute('SELECT * FROM match_person'),
    ):
        try:
            yield _parse_person(row)
        except Exception as e:
            add_note(e, f'^ while parsing {dict(row)}')
            yield e

    for row in db.execute('SELECT * FROM match'):
        try:
            yield _parse_match(row)
        except Exception as e:
            add_note(e, f'^ while parsing {dict(row)}')
            yield e

    for row in db.execute('SELECT * FROM message'):
        try:
            yield _parse_msg(row)
        except Exception as e:
            add_note(e, f'^ while parsing {dict(row)}')
            yield e


def _parse_person(row: sqlite3.Row) -> Person:
    return Person(
        id=row['id'],
        name=row['name'],
    )


def _parse_match(row: sqlite3.Row) -> _Match:
    return _Match(
        id=row['id'],
        person_id=row['person_id'],
        when=datetime.fromtimestamp(row['creation_date'] / 1000, tz=timezone.utc),
    )


def _parse_msg(row: sqlite3.Row) -> _Message:
    # note it also has raw_message_data -- not sure which is best to use..
    sent = row['sent_date']
    return _Message(
        sent=datetime.fromtimestamp(sent / 1000, tz=timezone.utc),
        id=row['id'],
        text=row['text'],
        match_id=row['match_id'],
        from_id=row['from_id'],
        to_id=row['to_id'],
    )


# todo maybe it's rich_entities method?
def entities() -> Iterator[Res[Entity]]:
    id2person: dict[str, Person] = {}
    id2match: dict[str, Match] = {}
    for x in unique_everseen(_entities):
        if isinstance(x, Exception):
            yield x
            continue
        if isinstance(x, Person):
            id2person[x.id] = x
            yield x
            continue
        if isinstance(x, _Match):
            try:
                person = id2person[x.person_id]
            except Exception as e:
                add_note(e, f'^ while processing {x}')
                yield e
                continue
            m = Match(
                id=x.id,
                when=x.when,
                person=person,
            )
            id2match[x.id] = m
            yield m
            continue
        if isinstance(x, _Message):
            try:
                match = id2match[x.match_id]
                from_ = id2person[x.from_id]
                to = id2person[x.to_id]
            except Exception as e:
                add_note(e, f'^ while processing {x}')
                continue
            yield Message(
                sent=x.sent,
                match=match,
                id=x.id,
                text=x.text,
                from_=from_,
                to=to,
            )
            continue
        assert_never(x)


def messages() -> Iterator[Res[Message]]:
    for x in entities():
        if isinstance(x, (Exception, Message)):
            yield x
            continue


# todo not sure, maybe it's not fundamental enough to keep here...
def match2messages() -> Iterator[Res[Mapping[Match, Sequence[Message]]]]:
    res: dict[Match, list[Message]] = defaultdict(list)
    for x in entities():
        if isinstance(x, Exception):
            yield x
            continue
        if isinstance(x, Match):
            # match might happen without messages so makes sense to handle here
            res[x]  # just trigger creation
            continue
        if isinstance(x, Message):
            try:
                ml = res[x.match]
            except Exception as e:
                add_note(e, f'^ while processing {x}')
                yield e
                continue
            ml.append(x)
            continue
    yield res


# TODO maybe a more natural return type is Iterator[Res[Tuple[Key, Value]]]
# but this doesn't work straight away because the key might have no corresponding values


def stats() -> Stats:
    return stat(messages)
