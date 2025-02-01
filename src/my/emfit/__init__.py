"""
[[https://shop-eu.emfit.com/products/emfit-qs][Emfit QS]] sleep tracker

Consumes data exported by https://github.com/karlicoss/emfitexport
"""

from __future__ import annotations

REQUIRES = [
    'git+https://github.com/karlicoss/emfitexport',
]

import dataclasses
import inspect
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

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

from my.config import emfit as config  # isort: skip


Emfit = dal.Emfit


# TODO move to common?
def dir_hash(path: Path):
    mtimes = tuple(p.stat().st_mtime for p in get_files(path, glob='*.json'))
    return mtimes


def _cachew_depends_on():
    return dir_hash(config.export_path)


# TODO take __file__ into account somehow?
@mcachew(cache_path=cache_dir() / 'emfit.cache', depends_on=_cachew_depends_on)
def datas() -> Iterable[Res[Emfit]]:
    # data from emfit is coming in UTC. There is no way (I think?) to know the 'real' timezone, and local times matter more for sleep analysis
    # TODO actually this is wrong?? there is some sort of local offset in the export
    emfit_tz = config.timezone

    ## backwards compatibility (old DAL didn't have cpu_pool argument)
    cpu_pool_arg = 'cpu_pool'
    pass_cpu_pool = cpu_pool_arg in inspect.signature(dal.sleeps).parameters
    if pass_cpu_pool:
        from my.core._cpu_pool import get_cpu_pool

        kwargs = {cpu_pool_arg: get_cpu_pool()}
    else:
        kwargs = {}
    ##

    for x in dal.sleeps(config.export_path, **kwargs):
        if isinstance(x, Exception):
            yield x
        else:
            if x.sid in config.excluded_sids:
                # TODO should be responsibility of export_path (similar to HPI?)
                continue
            # TODO maybe have a helper to 'patch up' all dattetimes in a namedtuple/dataclass?
            # TODO do the same for jawbone data?
            # fmt: off
            x = dataclasses.replace(
                x,
                start      =x.start      .astimezone(emfit_tz),
                end        =x.end        .astimezone(emfit_tz),
                sleep_start=x.sleep_start.astimezone(emfit_tz),
                sleep_end  =x.sleep_end  .astimezone(emfit_tz),
            )
            # fmt: on
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
                'bed_time'   : s.time_in_bed, # eh, this is derived frop sleep start / end. should we compute it on spot??

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
def fake_data(nights: int = 500) -> Iterator:
    from tempfile import TemporaryDirectory

    import pytz

    from my.core.cfg import tmp_config

    with TemporaryDirectory() as td:
        tdir = Path(td)
        gen = dal.FakeData()
        gen.fill(tdir, count=nights)

        class override:
            class emfit:
                export_path = tdir
                excluded_sids = ()
                timezone = pytz.timezone('Europe/London')  # meh

        with tmp_config(modules=__name__, config=override) as cfg:
            yield cfg


# TODO remove/deprecate it? I think used by timeline
def get_datas() -> list[Emfit]:
    # todo ugh. run lint properly
    return sorted(datas(), key=lambda e: e.start)  # type: ignore[arg-type]


# TODO move away old entries if there is a diff??
