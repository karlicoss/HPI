#!/usr/bin/env python3
"""
[[https://shop-eu.emfit.com/products/emfit-qs][Emfit QS]] sleep tracker

Consumes data exported by https://github.com/karlicoss/emfitexport
"""
from datetime import date
from pathlib import Path
from typing import Dict, List, Iterable

from ..core import get_files
from ..core.common import mcachew
from ..core.cachew import cache_dir
from ..core.error import Res
from ..core.types import DataFrameT

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
@mcachew(cache_path=cache_dir() / 'emfit.cache', hashf=dir_hash, logger=dal.log)
def datas(path: Path=config.export_path) -> Iterable[Res[Emfit]]:
    import dataclasses

    # data from emfit is coming in UTC. There is no way (I think?) to know the 'real' timezone, and local times matter more for sleep analysis
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
    dicts: List[Dict] = []
    last = None
    for s in pre_dataframe():
        if isinstance(s, Exception):
            # todo date would be nice too?
            d = {'error': str(s)}
        else:
            dd = s.date
            pday = dd - timedelta(days=1)
            if last is None or last.date != pday:
                hrv_change = None
            else:
                # todo it's change during the day?? dunno if reasonable metric
                hrv_change = s.hrv_evening - last.hrv_morning

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
            }
            last = s # meh
        dicts.append(d)


    import pandas # type: ignore
    return pandas.DataFrame(dicts)

# TODO add dataframe support to stat()
def stats():
    from ..core import stat
    return stat(pre_dataframe)


# TODO remove/deprecate it? I think used by timeline
def get_datas() -> List[Emfit]:
    # todo ugh. run lint properly
    return list(sorted(datas(), key=lambda e: e.start))
# TODO move away old entries if there is a diff??
