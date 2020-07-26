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


from my.config import bluemaestro as config


logger = LazyLogger('bluemaestro', level='debug')


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


class Measurement(NamedTuple):
    dt: datetime
    temp: float


@mcachew(cache_path=config.cache_path)
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
        with sqlite3.connect(f'file:{f}?immutable=1', uri=True) as db:
            # todo assert increasing timestamp?
            datas = db.execute('SELECT * FROM data ORDER BY log_index')
            for _, tss, temp, hum, pres, dew in datas:
                tot += 1
                # TODO FIXME is that utc???
                tss = tss.replace('Juli', 'Jul').replace('Aug.', 'Aug')
                dt = datetime.strptime(tss, '%Y-%b-%d %H:%M')
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

# TODO does it even have to be a dict?

def stats():
    from ..common import stat
    return stat(measurements)


def dataframe():
    """
    %matplotlib gtk
    from my.bluemaestro import get_dataframe
    get_dataframe().plot()
    """
    import pandas as pd # type: ignore
    return pd.DataFrame(p._asdict() for p in measurements()).set_index('dt')


def main():
    ll = list(measurements())
    print(len(ll))


if __name__ == '__main__':
    main()
