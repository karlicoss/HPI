#!/usr/bin/python3
"""
[[https://bluemaestro.com/products/product-details/bluetooth-environmental-monitor-and-logger][Bluemaestro]] temperature/humidity/pressure monitor
"""

# TODO eh, most of it belongs to DAL

import sqlite3
from datetime import datetime
from itertools import chain, islice
from pathlib import Path
from typing import Any, Dict, Iterable, NamedTuple, Set

from ..common import mcachew, LazyLogger, get_files


from my.config import bluemaestro as config


logger = LazyLogger('bluemaestro', level='debug')


def _get_exports():
    return get_files(config.export_path, glob='*.db')


class Measurement(NamedTuple):
    dt: datetime
    temp: float


@mcachew(cache_path=config.cache_path)
def _iter_measurements(dbs) -> Iterable[Measurement]:
    # I guess we can affort keeping them in sorted order
    points: Set[Measurement] = set()
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
                p = Measurement(
                    dt=dt,
                    temp=temp,
                    # TODO use pressure and humidity as well
                )
                if p in points:
                    continue
                points.add(p)
    # TODO make properly iterative?
    for p in sorted(points, key=lambda p: p.dt):
        yield p

    # logger.info('total items: %d', len(merged))
    # TODO assert frequency?
    # for k, v in merged.items():
    #     # TODO shit. quite a few of them have varying values... how is that freaking possible????
    #     # most of them are within 0.5 degree though... so just ignore?
    #     if isinstance(v, set) and len(v) > 1:
    #         print(k, v)
    # for k, v in merged.items():
    #     yield Point(dt=k, temp=v) # meh?

# TODO does it even have to be a dict?
# @dictify(key=lambda p: p.dt)
def measurements(exports=_get_exports()):
    yield from _iter_measurements(exports)


def dataframe():
    """
    %matplotlib gtk
    from my.bluemaestro import get_dataframe
    get_dataframe().plot()
    """
    import pandas as pd # type: ignore
    return pd.DataFrame(p._asdict() for p in measurements()).set_index('dt')


def main():
    ll = list(measurements(_get_exports()))
    print(len(ll))


if __name__ == '__main__':
    main()
