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


def save_locs(db_path: Path):
    db = sa.create_engine(f'sqlite:///{db_path}')
    engine = db.connect() # TODO do I need to tear anything down??
    meta = sa.MetaData(engine)
    schema = make_schema(xx_obj())
    sa.Table('locations', meta, *schema)
    meta.create_all()
    table = sa.table('locations', *schema)


    with Path('/L/tmp/loc/LocationHistory.json').open('r') as fo:
        # locs = list(_load_locations(fo))
        # TODO fuck. do I really need to split myself??
        # sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) too many SQL variables
        # TODO err wtf?? jsust 80000???
        for chunk in ichunks(_load_locations(fo), 10000):
            engine.execute(table.insert().values(chunk))

    # TODO maintain order during insertion?

def load_locs(db_path: Path):
    db = sa.create_engine(f'sqlite:///{db_path}')
    engine = db.connect() # TODO do I need to tear anything down??
    meta = sa.MetaData(engine)
    schema = make_schema(xx_obj())
    sa.Table('locations', meta, *schema)
    meta.create_all()
    table = sa.table('locations', *schema)

    return engine.execute(table.select()).fetchall()


def main():
    from kython import setup_logzero
    setup_logzero(get_logger(), level=logging.DEBUG)

    db_path = Path('test2.sqlite')
    # if db_path.exists():
    #     db_path.unlink()

    locs = [Location(**d) for d in load_locs(db_path)][:10]
    print(locs)


    # TODO is it quicker to insert anyway? needs unique policy

    # ok, very nice. the whold db is just 4mb now

if __name__ == '__main__':
    main()
