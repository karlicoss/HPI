"""
[[https://bluemaestro.com/products/product-details/bluetooth-environmental-monitor-and-logger][Bluemaestro]] temperature/humidity/pressure monitor

Comptatible with Android apps:
- https://play.google.com/store/apps/details?id=com.bluemaestro.bmLogger
- https://play.google.com/store/apps/details?id=com.bluemaestro.tempo_plus_2 (older app)
- com.bluemaestro.tempo_utility (even older app, not even on google play anymore)
"""

from __future__ import annotations

# todo most of it belongs to DAL... but considering so few people use it I didn't bother for now
import re
import sqlite3
from abc import abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

import pytz

from my.core import (
    Paths,
    Res,
    Stats,
    get_files,
    make_logger,
    stat,
    unwrap,
)
from my.core.cachew import mcachew
from my.core.pandas import DataFrameT, as_dataframe
from my.core.sqlite import sqlite_connect_immutable


class config(Protocol):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        raise NotImplementedError

    @property
    def tz(self) -> pytz.BaseTzInfo:
        # fixme: later, rely on the timezone provider
        # NOTE: the timezone should be set with respect to the export date!!!
        return pytz.timezone('Europe/London')
        # TODO when I change tz, check the diff


def make_config() -> config:
    from my.config import bluemaestro as user_config

    class combined_config(user_config, config): ...

    return combined_config()


logger = make_logger(__name__)


def inputs() -> Sequence[Path]:
    cfg = make_config()
    # FIXME hmmm, need to think how to avoid sorting by default when it's not needed
    # maybe only sort when we glob? and otherwise respect original order
    return get_files(cfg.export_path)


Celsius = float
Percent = float
mBar = float


@dataclass
class Measurement:
    dt: datetime  # todo aware/naive
    temp: Celsius
    humidity: Percent
    pressure: mBar
    dewpoint: Celsius


def is_bad_table(name: str) -> bool:
    # todo hmm would be nice to have a hook that can patch any module up to
    delegate = getattr(config, 'is_bad_table', None)
    return False if delegate is None else delegate(name)


@mcachew(depends_on=inputs)
def measurements() -> Iterable[Res[Measurement]]:
    cfg = make_config()
    tz = cfg.tz

    # todo ideally this would be via arguments... but needs to be lazy
    paths = inputs()
    total = len(paths)
    width = len(str(total))

    last: datetime | None = None

    # tables are immutable, so can save on processing..
    processed_tables: set[str] = set()
    # FIXME really need to be more defensive here...
    # it's fine to have missing data somewhere in the midddle
    for idx, path in enumerate(paths):
        logger.info(f'processing [{idx:>{width}}/{total:>{width}}] {path}')
        tot = 0
        new = 0
        # todo assert increasing timestamp?
        with sqlite_connect_immutable(path) as db:
            db_dt: datetime | None = None
            try:
                datas = db.execute(
                    f'SELECT "{path.name}" as name, Time, Temperature, Humidity, Pressure, Dewpoint FROM data ORDER BY log_index'
                )
                oldfmt = True
                [(db_dts,)] = db.execute('SELECT last_download FROM info')
                if db_dts == 'N/A':
                    # ??? happens for 20180923-20180928
                    continue
                if db_dts.endswith(':'):
                    db_dts += '00'  # wtf.. happens on some day
                db_dt = tz.localize(datetime.strptime(db_dts, '%Y-%m-%d %H:%M:%S'))
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
                # 'omnibus' appears in bmLogger app, but seems that it contains the same data that last export contains?
                # not sure what's the point :shrug:
                log_tables = [t for t in log_tables if 'omnibus' not in t]
                log_tables = [t for t in log_tables if t not in processed_tables]
                # NOTE: seems like it's possble to get empty log_tables; had exports which genuinely had _info table but no corresponding _log
                processed_tables |= set(log_tables)

                # todo use later?
                _frequencies = [list(db.execute(f'SELECT interval from {t.replace("_log", "_meta")}'))[0][0] for t in log_tables]  # noqa: RUF015

                # todo could just filter out the older datapoints?? dunno.

                # eh. a bit horrible, but seems the easiest way to do it?
                # note: for some reason everything in the new table multiplied by 10
                query = ' UNION '.join(
                    f'SELECT "{t}" AS name, unix, tempReadings / 10.0, humiReadings / 10.0, pressReadings / 10.0, dewpReadings / 10.0 FROM {t}'
                    for t in log_tables
                )
                if len(log_tables) > 0:  # ugh. otherwise end up with syntax error..
                    query = f'SELECT * FROM ({query}) ORDER BY name, unix'
                datas = db.execute(query)
                oldfmt = False
                db_dt = None

            for name, tsc, temp, hum, pres, dewp in datas:
                if is_bad_table(name):
                    continue

                # note: bluemaestro keeps local datetime
                if oldfmt:
                    tss = tsc.replace('Juli', 'Jul').replace('Aug.', 'Aug')
                    dt = datetime.strptime(tss, '%Y-%b-%d %H:%M')
                    dt = tz.localize(dt)
                    assert db_dt is not None
                else:
                    # todo cache?
                    m = re.search(r'_(\d+)_', name)
                    assert m is not None
                    export_ts = int(m.group(1))
                    db_dt = datetime.fromtimestamp(export_ts / 1000, tz=tz)
                    dt = datetime.fromtimestamp(tsc / 1000, tz=tz)

                ## sanity checks (todo make defensive/configurable?)
                # not sure how that happens.. but basically they'd better be excluded
                lower = timedelta(days=6000 / 24)  # ugh some time ago I only did it once in an hour.. in theory can detect from meta?
                upper = timedelta(days=10)  # kinda arbitrary
                if not (db_dt - lower < dt < db_dt + upper):
                    # todo could be more defenive??
                    yield RuntimeError('timestamp too far out', path, name, db_dt, dt)
                    continue

                # err.. sometimes my values are just interleaved with these for no apparent reason???
                if (temp, hum, pres, dewp) == (-144.1, 100.0, 1152.5, -144.1):
                    yield RuntimeError('the weird sensor bug')
                    continue

                assert -60 <= temp <= 60, (path, dt, temp)
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
        logger.debug(f'{path}: new {new}/{tot}')
    # logger.info('total items: %d', len(merged))
    # for k, v in merged.items():
    #     # TODO shit. quite a few of them have varying values... how is that freaking possible????
    #     # most of them are within 0.5 degree though... so just ignore?
    #     if isinstance(v, set) and len(v) > 1:
    #         print(k, v)
    # for k, v in merged.items():
    #     yield Point(dt=k, temp=v) # meh?


def stats() -> Stats:
    return stat(measurements)


def dataframe() -> DataFrameT:
    """
    %matplotlib gtk
    from my.bluemaestro import dataframe
    dataframe().plot()
    """
    df = as_dataframe(measurements(), schema=Measurement)
    # todo not sure how it would handle mixed timezones??
    # todo hmm, not sure about setting the index
    return df.set_index('dt')


def fill_influxdb() -> None:
    from my.core import influxdb

    influxdb.fill(measurements(), measurement=__name__)


def check() -> None:
    temps = list(measurements())
    latest = temps[:-2]

    prev = unwrap(latest[-2]).dt
    last = unwrap(latest[-1]).dt

    # todo stat should expose a dataclass?
    # TODO ugh. might need to warn about points past 'now'??
    # the default shouldn't allow points in the future...
    #
    # TODO also needs to be filtered out on processing, should be rejected on the basis of export date?

    POINTS_STORED = 6000  # on device?
    FREQ_SEC = 60
    HOURS_STORED = POINTS_STORED / (60 * 60 / FREQ_SEC)  # around 4 days
    NOW = datetime.now()
    assert NOW - last < timedelta(hours=HOURS_STORED / 2), f'old backup! {last}'

    assert last - prev < timedelta(minutes=3), f'bad interval! {last - prev}'
