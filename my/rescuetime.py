'''
Rescuetime (activity tracking) data
'''

from pathlib import Path
from datetime import datetime, timedelta
from typing import NamedTuple, Dict, List, Set, Optional

from .common import get_files, LazyLogger
from .error import Res, split_errors

# TODO get rid of it
from kython import group_by_cmp # type: ignore

from my.config import rescuetime as config


log = LazyLogger(__package__, level='info')


def inputs():
    return get_files(config.export_path, '*.json')


import my.config.repos.rescuexport.model as rescuexport
Model = rescuexport.Model


# TODO cache?
def get_model(last=0) -> Model:
    return Model(inputs()[-last:])


def _without_errors():
    model = get_model()
    it = model.iter_entries()
    vit, eit = split_errors(it, ET=Exception)
    # TODO FIXME handle eit somehow?
    yield from vit



def get_groups(gap=timedelta(hours=3)):
    vit = _without_errors()
    lit = list(vit) # TODO get rid of it...
    return group_by_cmp(lit, lambda a, b: (b.dt - a.dt) <= gap, dist=1)


def print_groups():
    for gr in get_groups():
         print(f"{gr[0].dt}--{gr[-1].dt}")
    # TODO merged db?
    # TODO ok, it summarises my sleep intervals pretty well. I guess should adjust it for the fact I don't sleep during the day, and it would be ok!


def check_backed_up(hours=24):
    vit = _without_errors()
    # TODO use some itertools stuff to get a window only?
    last = list(vit)[-1]
    latest_dt = last.dt

    assert (datetime.now() - latest_dt) < timedelta(hours=hours)
    # TODO move this to backup checker??


def fill_influxdb():
    from influxdb import InfluxDBClient # type: ignore
    client = InfluxDBClient()
    # client.delete_series(database='lastfm', measurement='phone')
    db = 'test'
    client.drop_database(db)
    client.create_database(db)
    vit = _without_errors()
    jsons = [{
        "measurement": 'phone',
        "tags": {},
        "time": str(e.dt),
        "fields": {"name": e.activity},
    } for e in vit]
    client.write_points(jsons, database=db) # TODO??

