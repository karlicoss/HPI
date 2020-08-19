#!/usr/bin/env python3
"""
[[https://shop-eu.emfit.com/products/emfit-qs][Emfit QS]] sleep tracker

Consumes data exported by https://github.com/karlicoss/emfitexport
"""
from datetime import date
from pathlib import Path
from typing import Dict, List, Iterator

from ..core import get_files
from ..core.common import mcachew
from ..core.cachew import cache_dir
from ..core.error import Res

from my.config import emfit as config


import emfitexport.dal as dal
Emfit = dal.Emfit


# TODO move to common?
def dir_hash(path: Path):
    mtimes = tuple(p.stat().st_mtime for p in get_files(path, glob='*.json'))
    return mtimes


# TODO take __file__ into account somehow?
@mcachew(cache_path=cache_dir() / 'emfit.cache', hashf=dir_hash, logger=dal.log)
def iter_datas(path: Path=config.export_path) -> Iterator[Res[Emfit]]:
    # TODO FIMXE excluded_sids
    yield from dal.sleeps(config.export_path)


def get_datas() -> List[Emfit]:
    return list(sorted(iter_datas(), key=lambda e: e.start))
# TODO move away old entries if there is a diff??


# TODO merge with jawbone data first
def by_night() -> Dict[date, Emfit]:
    res: Dict[date, Emfit] = {}
    # TODO shit. I need some sort of interrupted sleep detection?
    from more_itertools import bucket
    grouped = bucket(get_datas(), key=lambda s: s.date)
    for dd in grouped:
        sleeps = list(grouped[dd])
        if len(sleeps) > 1:
            dal.log.warning("multiple sleeps per night, not handled yet: %s", sleeps)
            continue
        [s] = sleeps
        res[s.date] = s
    return res


def stats():
    return {
        'nights': len(by_night()),
    }


def main():
    for k, v in by_night().items():
        print(k, v.start, v.end)


if __name__ == '__main__':
    main()
