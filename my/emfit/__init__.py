#!/usr/bin/env python3
"""
[[https://shop-eu.emfit.com/products/emfit-qs][Emfit QS]] sleep tracker

Consumes data exported by https://github.com/karlicoss/emfitexport
"""
from pathlib import Path
from typing import Dict, List, Iterable, Any, Optional

from ..core import get_files
from ..core.common import mcachew
from ..core.cachew import cache_dir
from ..core.error import Res, set_error_datetime, extract_error_datetime
from ..core.pandas import DataFrameT

from my.config import emfit as config


import emfitexport.dal as dal
# todo ugh. need to make up my mind on log vs logger naming... I guessl ogger makes more sense
logger = dal.log
Emfit  = dal.Emfit


# TODO move to common?
def dir_hash(path: Path):
    mtimes = tuple(p.stat().st_mtime for p in get_files(path, glob='*.json'))
    return mtimes


# TODO take __file__ into account somehow?
@mcachew(cache_path=cache_dir() / 'emfit.cache', hashf=lambda: dir_hash(config.export_path), logger=dal.log)
def datas() -> Iterable[Res[Emfit]]:
    import dataclasses

    # data from emfit is coming in UTC. There is no way (I think?) to know the 'real' timezone, and local times matter more for sleep analysis
    # TODO actully this is wrong?? check this..
    emfit_tz = config.timezone

    for x in dal.sleeps(config.export_path):
        if isinstance(x, Exception):
            yield x
        else:
            if x.sid in config.excluded_sids:
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
            )
            yield x


# TODO should be used for jawbone data as well?
def pre_dataframe() -> Iterable[Res[Emfit]]:
    # TODO shit. I need some sort of interrupted sleep detection?
    g: List[Emfit] = []

    def flush() -> Iterable[Res[Emfit]]:
        if len(g) == 0:
            return
        elif len(g) == 1:
            r = g[0]
            g.clear()
            yield r
        else:
            err = RuntimeError(f'Multiple sleeps per night, not supported yet: {g}')
            set_error_datetime(err, dt=g[0].date)
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
    from datetime import timedelta
    dicts: List[Dict[str, Any]] = []
    last: Optional[Emfit] = None
    for s in pre_dataframe():
        d: Dict[str, Any]
        if isinstance(s, Exception):
            edt = extract_error_datetime(s)
            d = {
                'date' : edt,
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
            last = s # meh
        dicts.append(d)


    import pandas # type: ignore
    return pandas.DataFrame(dicts)


from ..core import stat, Stats
def stats() -> Stats:
    return stat(pre_dataframe)


from contextlib import contextmanager
from typing import Iterator
@contextmanager
def fake_data(nights: int=500) -> Iterator[None]:
    from ..core.cfg import override_config
    from tempfile import TemporaryDirectory
    with override_config(config) as cfg, TemporaryDirectory() as td:
        tdir = Path(td)
        cfg.export_path = tdir

        gen = dal.FakeData()
        gen.fill(tdir, count=nights)
        yield


# TODO remove/deprecate it? I think used by timeline
def get_datas() -> List[Emfit]:
    # todo ugh. run lint properly
    return list(sorted(datas(), key=lambda e: e.start)) # type: ignore
# TODO move away old entries if there is a diff??
