"""
Tinder data from Android app database (in =/data/data/com.tinder/databases/tinder-3.db=)
"""
from __future__ import annotations

REQUIRES = ['dataset']

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import chain
from pathlib import Path
from typing import Sequence, Iterator, Union, Dict, List, Mapping

from more_itertools import unique_everseen

from my.core import Paths, get_files, Res, assert_never, stat, Stats, datetime_aware
from my.core.dataset import connect_readonly, DatabaseT


from my.config import tinder as user_config
@dataclass
class config(user_config.android):
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


@dataclass
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


@dataclass
class _Message(_BaseMessage):
    match_id: str
    from_id: str
    to_id: str


@dataclass
class Message(_BaseMessage):
    match: Match
    from_: Person
    to: Person


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


_Entity = Union[Person, _Match, _Message]
Entity  = Union[Person,  Match,  Message]


def _entities() -> Iterator[Res[_Entity]]:
    for db_file in inputs():
        with connect_readonly(db_file) as db:
            yield from _handle_db(db)


def _handle_db(db: DatabaseT) -> Iterator[Res[_Entity]]:
    # profile_user_view contains our own user id
    for row in chain(db['profile_user_view'], db['match_person']):
        try:
            yield _parse_person(row)
        except Exception as e:
            # todo attach error contex?
            yield e

    for row in db['match']:
        try:
            yield _parse_match(row)
        except Exception as e:
            yield e

    for row in db['message']:
        try:
            yield _parse_msg(row)
        except Exception as e:
            yield e


def _parse_person(row) -> Person:
    return Person(
        id=row['id'],
        name=row['name'],
    )


def _parse_match(row) -> _Match:
    return _Match(
        id=row['id'],
        person_id=row['person_id'],
        when=datetime.fromtimestamp(row['creation_date'] / 1000, tz=timezone.utc),
    )


def _parse_msg(row) -> _Message:
    # note it also has raw_message_data -- not sure which is best to use..
    sent    = row['sent_date']
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
    id2person: Dict[str, Person] = {}
    id2match : Dict[str, Match ] = {}
    for x in unique_everseen(_entities()):
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
                to    = id2person[x.to_id]
            except Exception as e:
                yield e
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
    res: Dict[Match, List[Message]] = defaultdict(list)
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
                yield e
                continue
            ml.append(x)
            continue
    yield res
# TODO maybe a more natural return type is Iterator[Res[Tuple[Key, Value]]]
# but this doesn't work straight away because the key might have no corresponding values


def stats() -> Stats:
    return stat(messages)
