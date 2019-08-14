#!/usr/bin/python3
import logging
import sqlite3
from datetime import datetime
from itertools import chain, islice
from pathlib import Path
from typing import Any, Dict, Iterable, NamedTuple, Set

from cachew import cachew
from kython import dictify
from kython.klogging import LazyLogger


CACHE = Path('/L/data/.cache/bluemaestro.cache')

DIR = Path("/L/zzz_syncthing_backups/bluemaestro/")
# TODO how to move them back?
DIR2 = Path("/L/zzz_syncthing_phone/phone-syncthing/backups/bluemaestro/")

logger = LazyLogger('bluemaestro', level=logging.DEBUG)


def get_backup_files():
    return list(sorted(chain(
            DIR.glob('*.db'),
            DIR2.glob('*.db'),
    )))


class Point(NamedTuple):
    dt: datetime
    temp: float


@cachew(cache_path=CACHE)
def iter_points(dbs) -> Iterable[Point]:
    # I guess we can affort keeping them in sorted order
    points: Set[Point] = set()
    # TODO do some sanity check??
    for f in dbs:
            # err = f'{f}: mismatch: {v} vs {value}'
            # if abs(v - value) > 0.4:
            #     logger.warning(err)
            #     # TODO mm. dunno how to mark errors properly..
            #     # raise AssertionError(err)
            # else:
            #     pass
        with sqlite3.connect(str(f)) as db:
            datas = list(db.execute('select * from data'))
            for _, tss, temp, hum, pres, dew in datas:
                # TODO is that utc???
                tss = tss.replace('Juli', 'Jul').replace('Aug.', 'Aug')
                dt = datetime.strptime(tss, '%Y-%b-%d %H:%M')
                p = Point(
                    dt=dt,
                    temp=temp,
                )
                if p in points:
                    continue
                points.add(p)
    for p in sorted(points, key=lambda p: p.dt):
        yield p

    # logger.info('total items: %d', len(merged))
    # TODO assert frequency?
    # for k, v in merged.items():
    #     # TODO shit. quite a few of them have varying values... how is that freaking possible????
    #     # most of them are withing 0.5 degree though... so just ignore?
    #     if isinstance(v, set) and len(v) > 1:
    #         print(k, v)
    # for k, v in merged.items():
    #     yield Point(dt=k, temp=v) # meh?

# TODO does it even have to be a dict?
# @dictify(key=lambda p: p.dt)
def get_temperature(backups=get_backup_files()):
    return list(iter_points(backups))


def test():
    get_temperature(get_backup_files()[-1:])

def main():
    ll = list(iter_points(get_backup_files()))
    print(len(ll))
    # print(get_temperature(get_backup_files()[-1:]))
        # print(type(t))


if __name__ == '__main__':
    main()
