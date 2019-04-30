#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
from itertools import islice
from typing import Type, NamedTuple, Union, Optional
import logging

from location import _load_locations, Location, get_logger
import sqlalchemy # type: ignore
import sqlalchemy as sa # type: ignore

from kython import ichunks


from kython.py37 import fromisoformat

# TODO move to some common thing?
class IsoDateTime(sqlalchemy.TypeDecorator):
    # TODO can we use something more effecient? e.g. blob for encoded datetime and tz? not sure if worth it
    impl = sqlalchemy.types.String

    # TODO optional?
    def process_bind_param(self, value: Optional[datetime], dialect) -> Optional[str]:
        if value is None:
            return None
        return value.isoformat()

    def process_result_value(self, value: Optional[str], dialect) -> Optional[datetime]:
        if value is None:
            return None
        return fromisoformat(value)


def _map_type(cls):
    tmap = {
        str: sa.String,
        float: sa.Float,
        datetime: IsoDateTime,
    }
    r = tmap.get(cls, None)
    if r is not None:
        return r


    if getattr(cls, '__origin__', None) == Union:
        elems = cls.__args__
        elems = [e for e in elems if e != type(None)]
        if len(elems) == 1:
            return _map_type(elems[0]) # meh..
    raise RuntimeError(f'Unexpected type {cls}')

# TODO to strart with, just assert utc when serializing, deserializing
# TODO how to use timestamp as key? just round it?

def make_schema(cls: Type[NamedTuple]): # TODO covariant?
    res = []
    for name, ann in cls.__annotations__.items():
        res.append(sa.Column(name, _map_type(ann)))
    return res


def get_table(db_path: Path, type_, name='table'):
    db = sa.create_engine(f'sqlite:///{db_path}')
    engine = db.connect() # TODO do I need to tear anything down??
    meta = sa.MetaData(engine)
    schema = make_schema(type_)
    sa.Table(name, meta, *schema)
    meta.create_all()
    table = sa.table(name, *schema)
    return engine, table

def cache_locs(source: Path, db_path: Path, limit=None):
    engine, table = get_table(db_path=db_path, type_=Location)

    with source.open('r') as fo:
        # TODO fuck. do I really need to split myself??
        # sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) too many SQL variables
        # TODO count deprecated??
        # print(engine.execute(table.count()).fetchone())
        for chunk in ichunks(islice(_load_locations(fo), 0, limit), 10000):
            engine.execute(table.insert().values(chunk))

    # TODO maintain order during insertion?

def iter_db_locs(db_path: Path):
    engine, table = get_table(db_path, type_=Location)
    datas = engine.execute(table.select()).fetchall()
    yield from (Location(**d) for d in datas)

def test(tmp_path):
    tdir = Path(tmp_path)
    tdb = tdir / 'test.sqlite'
    test_limit = 100
    test_src = Path('/L/tmp/LocationHistory.json')

    # TODO meh, double loading, but for now fine
    with test_src.open('r') as fo:
        real_locs = list(islice(_load_locations(fo), 0, test_limit))

    cache_locs(source=test_src, db_path=tdb, limit=test_limit)
    cached_locs = list(iter_db_locs(tdb))
    assert len(cached_locs) == test_limit
    assert real_locs == cached_locs

def main():
     

    from kython import setup_logzero
    setup_logzero(get_logger(), level=logging.DEBUG)

    db_path = Path('test3.sqlite')
    # if db_path.exists():
    #     db_path.unlink()

    locs = iter_db_locs(db_path)
    print(len(list(locs)))


    # TODO is it quicker to insert anyway? needs unique policy

    # ok, very nice. the whold db is just 20mb now
    # nice, and loads in seconds basically
    # TODO FIXME just need to check timezone

if __name__ == '__main__':
    main()
