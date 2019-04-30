#!/usr/bin/env python3
from pathlib import Path
from itertools import islice
import logging

from location import _load_locations, Location, get_logger
import sqlalchemy as sa # type: ignore

from kython import ichunks


# TODO wonder if possible to extract schema automatically?
def xx_obj():
    return Location(
        dt=sa.types.TIMESTAMP(timezone=True), # TODO tz?
        # TODO FIXME utc seems to be lost.. doesn't sqlite support it or what?
        lat=sa.Float,
        lon=sa.Float,
        alt=sa.Float, # TODO nullable
        tag=sa.String,
    )

def make_schema(obj):
    return [sa.Column(col, tp) for col, tp in obj._asdict().items()]


def cache_locs(source: Path, db_path: Path, limit=None):
    db = sa.create_engine(f'sqlite:///{db_path}')
    engine = db.connect() # TODO do I need to tear anything down??
    meta = sa.MetaData(engine)
    schema = make_schema(xx_obj())
    sa.Table('locations', meta, *schema)
    meta.create_all()
    table = sa.table('locations', *schema)


    with source.open('r') as fo:
        # TODO fuck. do I really need to split myself??
        # sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) too many SQL variables
        # TODO count deprecated??
        # print(engine.execute(table.count()).fetchone())
        for chunk in ichunks(islice(_load_locations(fo), 0, limit), 10000):
            engine.execute(table.insert().values(chunk))

    # TODO maintain order during insertion?

def iter_db_locs(db_path: Path):
    db = sa.create_engine(f'sqlite:///{db_path}')
    engine = db.connect() # TODO do I need to tear anything down??
    meta = sa.MetaData(engine)
    schema = make_schema(xx_obj())
    sa.Table('locations', meta, *schema)
    meta.create_all()
    table = sa.table('locations', *schema)

    datas = engine.execute(table.select()).fetchall()
    yield from (Location(**d) for d in datas)

def test(tmp_path):
    tdir = Path(tmp_path)
    tdb = tdir / 'test.sqlite'

    test_src = Path('/L/tmp/loc/LocationHistory.json')
    test_limit = 100
    cache_locs(source=test_src, db_path=tdb, limit=test_limit)

    locs = list(iter_db_locs(tdb))
    assert len(locs) == test_limit

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
