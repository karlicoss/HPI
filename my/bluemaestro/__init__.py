#!/usr/bin/python3
"""
[[https://bluemaestro.com/products/product-details/bluetooth-environmental-monitor-and-logger][Bluemaestro]] temperature/humidity/pressure monitor
"""

# todo eh, most of it belongs to DAL

from datetime import datetime, timedelta
from pathlib import Path
import re
import sqlite3
from typing import Iterable, NamedTuple, Sequence, Set, Optional


from ..core.common import mcachew, LazyLogger, get_files
from ..core.cachew import cache_dir
from my.config import bluemaestro as config


logger = LazyLogger('bluemaestro', level='debug')


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


class Measurement(NamedTuple):
    dt: datetime
    temp    : float # Celsius
    humidity: float # percent
    pressure: float # mBar
    dewpoint: float # Celsius


# fixme: later, rely on the timezone provider
# NOTE: the timezone should be set with respect to the export date!!!
import pytz # type: ignore
tz = pytz.timezone('Europe/London')
# TODO when I change tz, check the diff


@mcachew(cache_path=cache_dir() / 'bluemaestro.cache')
def measurements(dbs=inputs()) -> Iterable[Measurement]:
    last: Optional[datetime] = None

    # tables are immutable, so can save on processing..
    processed_tables: Set[str] = set()
    for f in dbs:
        logger.debug('processing %s', f)
        tot = 0
        new = 0
        # todo assert increasing timestamp?
        with sqlite3.connect(f'file:{f}?immutable=1', uri=True) as db:
            try:
                datas = db.execute(f'SELECT "{f.name}" as name, Time, Temperature, Humidity, Pressure, Dewpoint FROM data ORDER BY log_index')
                oldfmt = True
            except sqlite3.OperationalError:
                # Right, this looks really bad.
                # The device doesn't have internal time & what it does is:
                # 1. every X seconds, record a datapoint, store it in the internal memory
                # 2. on sync, take the phone's datetime ('now') and then ASSIGN the timestamps to the collected data
                #    as now, now - X, now - 2X, etc
                #
                # that basically means that for example, hourly timestamps are completely useless? because their error is about 1h
                # yep, confirmed on some historic exports. seriously, what the fuck???
                #
                # The device _does_ have an internal clock, but it's basically set to 0 every time you update settings
                # So, e.g. if, say, at 17:15 you set the interval to 3600, the 'real' timestamps would be
                # 17:15, 18:15, 19:15, etc
                # But depending on when you export, you might get
                # 17:35, 18:35, 19:35; or 17:55, 18:55, 19:55, etc
                # basically all you guaranteed is that the 'correct' interval is within the frequency
                # it doesn't seem to keep the reference time in the database
                #
                # UPD: fucking hell, so you can set the reference date in the settings (calcReferenceUnix field in meta db)
                # but it's not set by default.

                log_tables = [c[0] for c in db.execute('SELECT name FROM sqlite_sequence WHERE name LIKE "%_log"')]
                log_tables = [t for t in log_tables if t not in processed_tables]
                processed_tables |= set(log_tables)

                # todo use later?
                frequencies = [list(db.execute(f'SELECT interval from {t.replace("_log", "_meta")}'))[0][0] for t in log_tables]

                # todo could just filter out the older datapoints?? dunno.

                # eh. a bit horrible, but seems the easiest way to do it?
                # note: for some reason everything in the new table multiplied by 10
                query = ' UNION '.join(
                    f'SELECT "{t}" AS name, unix, tempReadings / 10.0, humiReadings / 10.0, pressReadings / 10.0, dewpReadings / 10.0 FROM {t}'
                    for t in log_tables
                )
                if len(log_tables) > 0: # ugh. otherwise end up with syntax error..
                    query = f'SELECT * FROM ({query}) ORDER BY name, unix'
                datas = db.execute(query)
                oldfmt = False

            for i, (name, tsc, temp, hum, pres, dewp) in enumerate(datas):
                # note: bluemaestro keeps local datetime
                if oldfmt:
                    tss = tsc.replace('Juli', 'Jul').replace('Aug.', 'Aug')
                    dt = datetime.strptime(tss, '%Y-%b-%d %H:%M')
                    dt = tz.localize(dt)
                else:
                    m = re.search(r'_(\d+)_', name)
                    assert m is not None
                    export_ts = int(m.group(1))
                    edt = datetime.fromtimestamp(export_ts / 1000, tz=tz)

                    dt = datetime.fromtimestamp(tsc / 1000, tz=tz)

                ## sanity checks (todo make defensive/configurable?)
                # not sure how that happens.. but basically they'd better be excluded
                assert dt.year >= 2015, (f, name, dt)
                assert -60 <= temp <= 60, (f, dt, temp)
                ##

                tot += 1
                if last is not None and last >= dt:
                    continue
                # todo for performance, pass 'last' to sqlite instead?
                last = dt
                new += 1
                p = Measurement(
                    dt=dt,
                    temp=temp,
                    pressure=pres,
                    humidity=hum,
                    dewpoint=dewp,
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

from ..core import stat, Stats
def stats() -> Stats:
    return stat(measurements)


from ..core.pandas import DataFrameT, check_dataframe as cdf
@cdf
def dataframe() -> DataFrameT:
    """
    %matplotlib gtk
    from my.bluemaestro import dataframe
    dataframe().plot()
    """
    # todo not sure why x axis time ticks are weird...  df[:6269] works, whereas df[:6269] breaks...
    # either way, plot is not the best representation for the temperature I guess.. maybe also use bokeh?
    import pandas as pd # type: ignore
    df = pd.DataFrame(
        (p._asdict() for p in measurements()),
        # todo meh. otherwise fails on empty inputs...
        columns=list(Measurement._fields),
    )
    # todo not sure how it would handle mixed timezones??
    return df.set_index('dt')

# todo test against an older db?
