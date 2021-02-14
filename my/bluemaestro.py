#!/usr/bin/python3
"""
[[https://bluemaestro.com/products/product-details/bluetooth-environmental-monitor-and-logger][Bluemaestro]] temperature/humidity/pressure monitor
"""

# todo most of it belongs to DAL... but considering so few people use it I didn't bother for now
from datetime import datetime, timedelta
from pathlib import Path
import re
import sqlite3
from typing import Iterable, Sequence, Set, Optional

from .core import get_files, LazyLogger, dataclass

from my.config import bluemaestro as config


# todo control level via env variable?
# i.e. HPI_LOGGING_MY_BLUEMAESTRO_LEVEL=debug
logger = LazyLogger(__name__, level='debug')


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


Celsius = float
Percent = float
mBar    = float

@dataclass
class Measurement:
    dt: datetime # todo aware/naive
    temp    : Celsius
    humidity: Percent
    pressure: mBar
    dewpoint: Celsius


# fixme: later, rely on the timezone provider
# NOTE: the timezone should be set with respect to the export date!!!
import pytz # type: ignore
tz = pytz.timezone('Europe/London')
# TODO when I change tz, check the diff


def is_bad_table(name: str) -> bool:
    # todo hmm would be nice to have a hook that can patch any module up to
    delegate = getattr(config, 'is_bad_table', None)
    return False if delegate is None else delegate(name)


from .core.cachew import cache_dir
from .core.common import mcachew
@mcachew(depends_on=lambda: inputs(), cache_path=cache_dir() / 'bluemaestro.cache')
def measurements() -> Iterable[Measurement]:
    # todo ideally this would be via arguments... but needs to be lazy
    dbs = inputs()

    last: Optional[datetime] = None

    # tables are immutable, so can save on processing..
    processed_tables: Set[str] = set()
    for f in dbs:
        logger.debug('processing %s', f)
        tot = 0
        new = 0
        # todo assert increasing timestamp?
        with sqlite3.connect(f'file:{f}?immutable=1', uri=True) as db:
            db_dt: Optional[datetime] = None
            try:
                datas = db.execute(f'SELECT "{f.name}" as name, Time, Temperature, Humidity, Pressure, Dewpoint FROM data ORDER BY log_index')
                oldfmt = True
                db_dts = list(db.execute(f'SELECT last_download FROM info'))[0][0]
                if db_dts == 'N/A':
                    # ??? happens for 20180923-20180928
                    continue
                if db_dts.endswith(':'):
                    db_dts += '00' # wtf.. happens on some day
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
                db_dt = None

            for i, (name, tsc, temp, hum, pres, dewp) in enumerate(datas):
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
                lower = timedelta(days=6000 / 24) # ugh some time ago I only did it once in an hour.. in theory can detect from meta?
                upper = timedelta(days=10) # kinda arbitrary
                if not (db_dt - lower < dt < db_dt + timedelta(days=10)):
                    # todo could be more defenive??
                    raise RuntimeError('timestamp too far out', f, name, db_dt, dt)

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
    # for k, v in merged.items():
    #     # TODO shit. quite a few of them have varying values... how is that freaking possible????
    #     # most of them are within 0.5 degree though... so just ignore?
    #     if isinstance(v, set) and len(v) > 1:
    #         print(k, v)
    # for k, v in merged.items():
    #     yield Point(dt=k, temp=v) # meh?

from .core import stat, Stats
def stats() -> Stats:
    return stat(measurements)


from .core.pandas import DataFrameT, as_dataframe
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
    from itertools import islice
    from .core.common import asdict

    from influxdb import InfluxDBClient # type: ignore
    client = InfluxDBClient()
    db = 'db'
    mname = __name__.replace('.', '_')
    client.delete_series(database=db,  measurement=mname)
    def dissoc(d, k):
        del d[k]
        return d # meh
    jsons = ({
        'measurement': mname,
        # todo maybe good idea to tags with database file/name? to inspect inconsistencies etc..
        # 'tags': {'activity': e.activity},
        'time': e.dt.isoformat(),
        'fields': dissoc(asdict(e), 'dt'),
    } for e in measurements())
    from more_itertools import chunked
    # "The optimal batch size is 5000 lines of line protocol."
    # some chunking is def necessary, otherwise it fails
    for chunk in chunked(jsons, n=5000):
        cl = list(chunk)
        logger.debug('writing next chunk %s', cl[-1])
        client.write_points(cl, database=db)
    # todo "Specify timestamp precision when writing to InfluxDB."?


def check() -> None:
    temps = list(measurements())
    latest = temps[:-2]

    prev = latest[-2].dt
    last = latest[-1].dt

    # todo stat should expose a dataclass?
    # TODO ugh. might need to warn about points past 'now'??
    # the default shouldn't allow points in the future...
    #
    # TODO also needs to be filtered out on processing, should be rejected on the basis of export date?

    POINTS_STORED = 6000 # on device?
    FREQ_SEC = 60
    SECS_STORED = POINTS_STORED * FREQ_SEC
    HOURS_STORED = POINTS_STORED / (60 * 60 / FREQ_SEC) # around 4 days
    NOW = datetime.now()
    assert NOW - last < timedelta(hours=HOURS_STORED / 2), f'old backup! {last}'

    assert last - prev  < timedelta(minutes=3), f'bad interval! {last - prev}'
    single = (last - prev).seconds
