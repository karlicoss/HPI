'''
Rescuetime (activity tracking) data
'''

from pathlib import Path
from datetime import datetime, timedelta
from typing import Sequence, Iterable

from .core import get_files, LazyLogger
from .core.common import mcachew
from .core.error import Res, split_errors

import more_itertools

from my.config import rescuetime as config


log = LazyLogger(__package__, level='info')


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


import my.config.repos.rescuexport.dal as dal
DAL = dal.DAL
Entry = dal.Entry


# todo needs to be cumulative cache
@mcachew
def entries(files=inputs()) -> Iterable[Entry]:
    dal = DAL(files)
    it = dal.iter_entries()
    vit, eit = split_errors(it, ET=Exception)
    # todo handle errors, I guess initially I didn't because it's unclear how to easily group?
    yield from vit


def groups(gap=timedelta(hours=3)):
    vit = entries()
    from more_itertools import split_when
    yield from split_when(vit, lambda a, b: (b.dt - a.dt) > gap)


def stats():
    from .core import stat
    return {
        **stat(groups),
        **stat(entries),
    }


# todo not sure if I want to keep these here? vvv


def print_groups():
    for gr in groups():
         print(f"{gr[0].dt}--{gr[-1].dt}")
    # TODO merged db?
    # TODO ok, it summarises my sleep intervals pretty well. I guess should adjust it for the fact I don't sleep during the day, and it would be ok!


def fill_influxdb():
    from influxdb import InfluxDBClient # type: ignore
    client = InfluxDBClient()
    # client.delete_series(database='lastfm', measurement='phone')
    db = 'test'
    client.drop_database(db)
    client.create_database(db)
    vit = entries()
    jsons = [{
        "measurement": 'phone',
        "tags": {},
        "time": str(e.dt),
        "fields": {"name": e.activity},
    } for e in vit]
    client.write_points(jsons, database=db) # TODO??

