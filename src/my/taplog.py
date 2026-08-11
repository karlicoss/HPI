'''
[[https://play.google.com/store/apps/details?id=com.waterbear.taglog][Taplog]] app data
'''

from __future__ import annotations

import json
from abc import abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from my.core import Paths, Stats, datetime_aware, get_files, stat
from my.core.sqlite import sqlite_connection


class Config(Protocol):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        raise NotImplementedError


def make_config() -> Config:
    from my.config import taplog as user_config

    class combined_config(user_config, Config): ...

    return combined_config()


@dataclass(frozen=True, kw_only=True)
class Address:
    street: str
    city: str
    state: str
    zip: str
    country: str


@dataclass(frozen=True, kw_only=True)
class GPS:
    lat: float
    lon: float
    dt: datetime_aware
    accuracy: float
    elevation: float
    bearing: float
    speed: float
    address: Address | None


@dataclass(frozen=True, kw_only=True)
class Entry:
    row: dict

    @property
    def id(self) -> str:
        # IDs are opaque; keep their public type independent of SQLite storage.
        return str(self.row['_id'])

    @property
    def number(self) -> float | None:
        return self.row['number']

    @property
    def note(self) -> str:
        return self.row['note']

    @property
    def button(self) -> str:
        return self.row['cat1']

    @property
    def timestamp(self) -> datetime_aware:
        return datetime.fromisoformat(self.row['timestamp'])

    @property
    def gps(self) -> GPS | None:
        raw = self.row['gps']
        if raw is None:
            return None

        data = json.loads(raw)
        assert data['version'] == 1, data['version']

        address_data = data.get('address')
        address = None if address_data is None else Address(**address_data)

        gps = data['gps']
        return GPS(
            lat=gps['latitude'],
            lon=gps['longitude'],
            dt=datetime.fromisoformat(gps['gpsTime']),
            accuracy=gps['accuracy'],
            elevation=gps['altitude'],
            bearing=gps['bearing'],
            speed=gps['speed'],
            address=address,
        )


def entries() -> Iterable[Entry]:
    cfg = make_config()
    last = max(get_files(cfg.export_path))
    with sqlite_connection(last, immutable=True, row_factory='dict') as db:
        for row in db.execute('SELECT * FROM Log ORDER BY Milliseconds, _id'):
            yield Entry(row=row)


# I guess worth having as top level considering it would be quite common?
def by_button(button: str) -> Iterable[Entry]:
    for e in entries():
        if e.button == button:
            yield e


def stats() -> Stats:
    return stat(entries)
