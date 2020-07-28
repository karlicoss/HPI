#!/usr/bin/python3
"""
[[https://bluemaestro.com/products/product-details/bluetooth-environmental-monitor-and-logger][Bluemaestro]] temperature/humidity/pressure monitor
"""

# todo eh, most of it belongs to DAL

from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Iterable, NamedTuple, Sequence, Set

from ..common import mcachew, LazyLogger, get_files


from ..core.cachew import cache_dir
from my.config import bluemaestro as config


logger = LazyLogger('bluemaestro', level='debug')


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


class Measurement(NamedTuple):
    dt: datetime
    temp: float


@mcachew(cache_path=cache_dir() / 'bluemaestro.cache')
def measurements(dbs=inputs()) -> Iterable[Measurement]:
    emitted: Set[datetime] = set()
    for f in dbs:
        logger.debug('processing %s', f)
            # err = f'{f}: mismatch: {v} vs {value}'
            # if abs(v - value) > 0.4:
            #     logger.warning(err)
            #     # TODO mm. dunno how to mark errors properly..
            #     # raise AssertionError(err)
            # else:
            #     pass
            #         with sqlite3.connect(f'file:{db}?immutable=1', uri=True) as c:
        tot = 0
        new = 0
        # todo assert increasing timestamp?
        with sqlite3.connect(f'file:{f}?immutable=1', uri=True) as db:
            try:
                # try old format first
                # todo Humidity, Pressure, Dewpoint
                datas = db.execute('SELECT Time, Temperature FROM data ORDER BY log_index')
                oldfmt = True
            except sqlite3.OperationalError:
                # ok, must be new format?
                log_tables = list(c[0] for c in db.execute('SELECT name FROM sqlite_sequence WHERE name LIKE "%_log"'))
                # eh. a bit horrible, but seems the easiest way to do it?
                # todo could exclude logs that we already processed??
                # todo humiReadings, pressReadings, dewpReadings
                query = ' UNION '.join(f'SELECT unix, tempReadings FROM {t}' for t in log_tables) # todo order by?
                if len(log_tables) > 0: # ugh. otherwise end up with syntax error..
                    query = f'SELECT * FROM ({query}) ORDER BY unix'
                datas = db.execute(query)
                oldfmt = False

            # todo otherwise, union all dbs?... this is slightly insane...
            for tsc, tempc in datas:
                if oldfmt:
                    # TODO FIXME is that utc???
                    tss = tsc.replace('Juli', 'Jul').replace('Aug.', 'Aug')
                    dt = datetime.strptime(tss, '%Y-%b-%d %H:%M')
                    temp = tempc
                else:
                    dt = datetime.utcfromtimestamp(tsc / 1000) # todo not sure if utc?
                    temp = tempc / 10 # for some reason it's in tenths of degrees??

                # sanity check
                assert -40 <= temp <= 60, (f, dt, temp)

                tot += 1
                if dt in emitted:
                    continue
                emitted.add(dt)
                new += 1
                p = Measurement(
                    dt=dt,
                    temp=temp,
                    # TODO use pressure and humidity as well
                )
                yield p
        logger.debug('%s: new %d/%d', f, new, tot)
    # logger.info('total items: %d', len(merged))
    # TODO assert frequency?
    # for k, v in merged.items():
    #     # TODO shit. quite a few of them have varying values... how is that freaking possible????
    #     # most of them are within 0.5 degree though... so just ignore?
    #     if isinstance(v, set) and len(v) > 1:
    #         print(k, v)
    # for k, v in merged.items():
    #     yield Point(dt=k, temp=v) # meh?

def stats():
    from ..common import stat
    return stat(measurements)


def dataframe():
    """
    %matplotlib gtk
    from my.bluemaestro import dataframe
    dataframe().plot()
    """
    # todo not sure why x axis time ticks are weird...  df[:6269] works, whereas df[:6269] breaks...
    # either way, plot is not the best representation for the temperature I guess.. maybe also use bokeh?
    import pandas as pd # type: ignore
    return pd.DataFrame(p._asdict() for p in measurements()).set_index('dt')


def main():
    ll = list(measurements())
    print(len(ll))


if __name__ == '__main__':
    main()

# TODO copy a couble of databases (one old, one new) to my public data repository?
