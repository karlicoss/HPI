"""
Jawbone UP sleep data from saved API responses.

Reads ``sleeps.json``, ``phases.json``, and ``graphs/<xid>.png`` from ``my.config.jawbone.export_dir``.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import UTC, date, datetime, time
from functools import cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from more_itertools import bucket

from my.core import Json, Res, Stats, make_logger, stat
from my.core.error import extract_error_datetime, set_error_datetime
from my.core.pandas import DataFrameT

logger = make_logger(__name__)


class config(ABC):
    @property
    @abstractmethod
    def export_dir(self) -> Path | str:
        """Directory containing sleeps.json, phases.json, and graphs/."""
        raise NotImplementedError


def make_config() -> config:
    from my.config import jawbone as user_config

    class combined_config(user_config, config):
        pass

    return combined_config()


def _export_dir() -> Path:
    return Path(make_config().export_dir).expanduser()


XID = str  # TODO how to shared with backup thing?

Phases = dict[XID, list[Json]]


def get_phases() -> Phases:
    return _get_phases((_export_dir() / 'phases.json').resolve())


@cache
def _get_phases(path: Path) -> Phases:
    return json.loads(path.read_text())


# TODO use awakenings and quality
class SleepEntry:
    def __init__(self, js: Json) -> None:
        self.js = js

    @property
    def date_(self) -> date:
        return self.sleep_end.date()

    def _fromts(self, ts: int) -> datetime:
        return datetime.fromtimestamp(ts, tz=self._tz)

    @property
    def _tz(self) -> ZoneInfo:
        return ZoneInfo(self._details['tz'])

    @property
    def title(self) -> str:
        return self.js['title']

    @property
    def xid(self) -> XID:
        return self.js['xid']

    @property
    def _details(self) -> Json:
        return self.js['details']

    @property
    def created(self) -> datetime:
        return self._fromts(self.js['time_created'])

    @property
    def completed(self) -> datetime:
        return self._fromts(self.js['time_completed'])

    @property
    def asleep(self) -> datetime:
        return self._fromts(self._details['asleep_time'])

    @property
    def sleep_start(self) -> datetime:
        return self.asleep  # TODO careful, maybe use same logic as emfit

    @property
    def bed_time(self) -> int:
        # Subtract UTC instants so DST changes do not alter elapsed sleep duration.
        duration = self.sleep_end.astimezone(UTC) - self.sleep_start.astimezone(UTC)
        return int(duration.total_seconds()) // 60

    @property
    def sleep_end(self) -> datetime:
        return self._fromts(self._details['awake_time'])

    @property
    def graph(self) -> Path:
        return _export_dir() / 'graphs' / (self.xid + '.png')

    @property
    def phases(self) -> list[datetime]:
        # TODO make sure they are consistent with emfit?
        return [self._fromts(i['time']) for i in get_phases()[self.xid]]

    def __str__(self) -> str:
        return f"{self.date_.strftime('%a %d %b')} {self.title}"

    def __repr__(self) -> str:
        return str(self)


def load_sleeps() -> list[SleepEntry]:
    sleeps = json.loads((_export_dir() / 'sleeps.json').read_text())
    return [SleepEntry(js) for js in sleeps]


def pre_dataframe() -> Iterable[Res[SleepEntry]]:
    sleeps = load_sleeps()
    # todo emit error if graph doesn't exist??
    sleeps = [s for s in sleeps if s.graph.exists()]  # TODO careful..

    bucketed = bucket(sleeps, key=lambda s: s.date_)

    for dd in bucketed:
        group = list(bucketed[dd])
        if len(group) == 1:
            yield group[0]
        else:
            err = RuntimeError(f'Multiple sleeps per night, not supported yet: {group}')
            dt = datetime.combine(dd, time.min)
            set_error_datetime(err, dt=dt)
            logger.error(err, exc_info=err)
            yield err


def dataframe() -> DataFrameT:
    import pandas as pd

    dicts: list[dict[str, Any]] = []
    for s in pre_dataframe():
        d: dict[str, Any]
        if isinstance(s, Exception):
            dt = extract_error_datetime(s)
            d = {
                'date': dt,
                'error': str(s),
            }
        else:
            d = {
                # TODO make sure sleep start/end are consistent with emfit? add to test as well..
                # I think it makes sense to be end date as 99% of time
                # or maybe I shouldn't care about this at all?
                'date'       : s.date_,
                'sleep_start': s.sleep_start,
                'sleep_end'  : s.sleep_end,
                'bed_time'   : s.bed_time,
            }  # fmt: skip
        dicts.append(d)

    return pd.DataFrame(dicts)


def stats() -> Stats:
    return stat(pre_dataframe)
