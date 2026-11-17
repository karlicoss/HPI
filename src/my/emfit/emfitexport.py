"""
[[https://shop-eu.emfit.com/products/emfit-qs][Emfit QS]] sleep tracker

Consumes data exported by https://github.com/karlicoss/emfitexport
"""

from __future__ import annotations

REQUIRES = [
    'emfitexport @ git+https://github.com/karlicoss/emfitexport',
]

import dataclasses
import inspect
from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime, time, timedelta, tzinfo
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zoneinfo import ZoneInfo

import emfitexport.dal as dal

from my.core import (
    Res,
    Stats,
    get_files,
    stat,
)
from my.core.cachew import cache_dir, mcachew
from my.core.error import extract_error_datetime, set_error_datetime
from my.core.pandas import DataFrameT


class config(ABC):
    @property
    @abstractmethod
    def export_path(self) -> Path | str:
        """Directory containing Emfit QS JSON exports."""
        raise NotImplementedError

    @property
    @abstractmethod
    def timezone(self) -> tzinfo:
        """Timezone used to assign sleep sessions to local dates."""
        raise NotImplementedError

    excluded_sids: Sequence[str] = ()


def make_config() -> config:
    from my.config import emfit as user_config

    class combined_config(user_config, config):
        pass

    return combined_config()


Emfit = dal.Emfit


def dir_hash(path: Path) -> tuple[tuple[Path, int, int], ...]:
    files = []
    for p in get_files(path, glob='*.json'):
        st = p.stat()
        files.append((p.resolve(), st.st_mtime_ns, st.st_size))
    return tuple(files)


def _cachew_depends_on() -> tuple[Path, tuple[tuple[Path, int, int], ...], tzinfo, tuple[str, ...]]:
    cfg = make_config()
    path = Path(cfg.export_path).expanduser().resolve()
    return path, dir_hash(path), cfg.timezone, tuple(cfg.excluded_sids)


# TODO take __file__ into account somehow?
@mcachew(cache_path=cache_dir() / 'emfit.cache', depends_on=_cachew_depends_on)
def datas() -> Iterable[Res[Emfit]]:
    cfg = make_config()
    # Emfit timestamps are in UTC, but local dates matter for sleep analysis.
    # TODO consider the local UTC offset recorded in each export.
    emfit_tz = cfg.timezone
    export_path = Path(cfg.export_path).expanduser()

    ## backwards compatibility (old DAL didn't have cpu_pool argument)
    cpu_pool_arg = 'cpu_pool'
    pass_cpu_pool = cpu_pool_arg in inspect.signature(dal.DAL).parameters
    if pass_cpu_pool:
        from my.core._cpu_pool import get_cpu_pool

        kwargs = {cpu_pool_arg: get_cpu_pool()}
    else:
        kwargs = {}
    ##

    for x in dal.DAL(export_path, **kwargs).sleeps():
        if isinstance(x, Exception):
            yield x
        else:
            if x.sid in cfg.excluded_sids:
                # TODO should be responsibility of export_path (similar to HPI?)
                continue
            # TODO maybe have a helper to 'patch up' all dattetimes in a namedtuple/dataclass?
            # TODO do the same for jawbone data?
            x = dataclasses.replace(
                x,
                start      =x.start      .astimezone(emfit_tz),
                end        =x.end        .astimezone(emfit_tz),
                sleep_start=x.sleep_start.astimezone(emfit_tz),
                sleep_end  =x.sleep_end  .astimezone(emfit_tz),
            )  # fmt: skip
            yield x


# TODO should be used for jawbone data as well?
def pre_dataframe() -> Iterable[Res[Emfit]]:
    # TODO shit. I need some sort of interrupted sleep detection?
    g: list[Emfit] = []

    def flush() -> Iterable[Res[Emfit]]:
        if len(g) == 0:
            return
        elif len(g) == 1:
            r = g[0]
            g.clear()
            yield r
        else:
            err = RuntimeError(f'Multiple sleeps per night, not supported yet: {g}')
            set_error_datetime(err, dt=datetime.combine(g[0].date, time.min))
            g.clear()
            yield err

    for x in datas():
        if isinstance(x, Exception):
            yield x
            continue
        # otherwise, Emfit
        if len(g) != 0 and g[-1].date != x.date:
            yield from flush()
        g.append(x)
    yield from flush()


def _elapsed(*, start: datetime, end: datetime) -> timedelta:
    """Measure elapsed time even when local timestamps cross a DST transition."""
    # Subtraction with a shared tzinfo object ignores changes in UTC offset.
    # TODO use emfitexport's time_in_bed once it accounts for this with ZoneInfo.
    return end.astimezone(UTC) - start.astimezone(UTC)


def dataframe() -> DataFrameT:
    dicts: list[dict[str, Any]] = []
    last: Emfit | None = None
    for s in pre_dataframe():
        d: dict[str, Any]
        if isinstance(s, Exception):
            edt = extract_error_datetime(s)
            d = {
                'date': edt,
                'error': str(s),
            }
        else:
            dd = s.date
            pday = dd - timedelta(days=1)
            if last is None or last.date != pday:
                hrv_change = None
            else:
                # todo it's change during the day?? dunno if reasonable metric
                hrv_change = s.hrv_evening - last.hrv_morning
            # todo maybe changes need to be handled in a more generic way?

            # todo ugh. get rid of hardcoding, just generate the schema automatically
            # TODO use 'workdays' provider....
            # fmt: off
            d = {
                'date'       : dd,

                'sleep_start': s.sleep_start,
                'sleep_end'  : s.sleep_end,
                'bed_time'   : int(_elapsed(start=s.sleep_start, end=s.sleep_end).total_seconds()) // 60,

                # these are emfit specific
                'coverage'   : s.sleep_hr_coverage,
                'avg_hr'     : s.measured_hr_avg,
                'hrv_evening': s.hrv_evening,
                'hrv_morning': s.hrv_morning,
                'recovery'   : s.recovery,
                'hrv_change' : hrv_change,
                'respiratory_rate_avg': s.respiratory_rate_avg,
            }
            # fmt: on
            last = s  # meh
        dicts.append(d)

    import pandas as pd

    return pd.DataFrame(dicts)


def stats() -> Stats:
    return stat(pre_dataframe)


@contextmanager
def fake_data(nights: int = 500) -> Generator[Any]:
    from emfitexport.tests.test_dal import FakeData

    from my.core.cfg import tmp_config

    with TemporaryDirectory() as td:
        tdir = Path(td)
        gen = FakeData()
        gen.fill(tdir, count=nights)

        class override:
            class emfit:
                export_path = tdir
                excluded_sids = ()
                timezone = ZoneInfo('Europe/London')

        with tmp_config(modules=__name__, config=override) as cfg:
            yield cfg


# TODO move away old entries if there is a diff??
