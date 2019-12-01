import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import NamedTuple, Dict, List, Set, Optional
from functools import lru_cache

from .common import get_files

# TODO get rid of it
from kython import group_by_cmp # type: ignore

from my_configuration import paths


def get_logger():
    return logging.getLogger("my.rescuetime")


def _get_exports() -> List[Path]:
    from my_configuration import paths
    return get_files(paths.rescuetime.export_path, '*.json')


import my_configuration.repos.rescuexport.model as rescuexport
Model = rescuexport.Model


# TODO cache?
def get_model(last=0) -> Model:
    return Model(_get_exports()[-last:])


def get_groups(gap=timedelta(hours=3)):
    model = get_model()
    it = model.iter_entries()
    lit = list(it) # TODO get rid of it...
    return group_by_cmp(lit, lambda a, b: (b.dt - a.dt) <= gap, dist=1)


def print_groups():
    for gr in get_groups():
         print(f"{gr[0].dt}--{gr[-1].dt}")
    # TODO merged db?
    # TODO ok, it summarises my sleep intervals pretty well. I guess should adjust it for the fact I don't sleep during the day, and it would be ok!


def check_backed_up(hours=24):
    model = get_model(last=1)
    last = list(model.iter_entries())[-1]
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
    model = get_model()
    jsons = [{
        "measurement": 'phone',
        "tags": {},
        "time": str(e.dt),
        "fields": {"name": e.activity},
    } for e in model.iter_entries()]
    client.write_points(jsons, database=db) # TODO??

