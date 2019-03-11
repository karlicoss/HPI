#!/usr/bin/python3
import sqlite3
# ugh, dataset stumpled over date format
from itertools import islice, chain
from typing import Dict, Any

from datetime import datetime
import logging
from kython import setup_logzero
from pathlib import Path

DIR = Path("/L/zzz_syncthing_backups/bluemaestro/")

# TODO how to move them back?
DIR2 = Path("/L/zzz_syncthing_phone/phone-syncthing/backups/bluemaestro/")

def get_logger():
    return logging.getLogger('bluemaestro')


def get_temperature():
    logger = get_logger()
    merged: Dict[datetime, Any] = {}

    for f in list(sorted(chain(
            DIR.glob('*.db'),
            DIR2.glob('*.db'),
    ))):
        def reg(dt: datetime, value):
            v = merged.get(dt, None)
            if v is None:
                merged[dt] = value
                return
            if value == v or (isinstance(v, set) and value in v):
                return
            if isinstance(v, set):
                v.add(value)
            else:
                merged[dt] = {v, value}
            # err = f'{f}: mismatch: {v} vs {value}'
            # if abs(v - value) > 0.4:
            #     logger.warning(err)
            #     # TODO mm. dunno how to mark errors properly..
            #     # raise AssertionError(err)
            # else:
            #     pass

        db = sqlite3.connect(str(f))

        datas = list(db.execute('select * from data'))

        for _, tss, temp, hum, pres, dew in datas:
            # TODO is that utc???
            tss = tss.replace('Juli', 'Jul').replace('Aug.', 'Aug')


            dt = datetime.strptime(tss, '%Y-%b-%d %H:%M')
            reg(dt, temp)

        db.close()

    logger.info('total items: %d', len(merged))
    # TODO assert frequency?
    # for k, v in merged.items():
    #     # TODO shit. quite a few of them have varying values... how is that freaking possible????
    #     # most of them are withing 0.5 degree though... so just ignore?
    #     if isinstance(v, set) and len(v) > 1:
    #         print(k, v)
    return merged

def main():
    setup_logzero(get_logger(), level=logging.DEBUG)
    get_temperature()


if __name__ == '__main__':
    main()
