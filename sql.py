#!/usr/bin/env python3
from pathlib import Path
import functools
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
    # in theory could use something more effecient? e.g. blob for encoded datetime and tz?
    # but practically, the difference seems to be pretty small, so perhaps fine for now
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

from kython.ktyping import PathIsh

# TODO what if we want dynamic path??
# dbcache = make_dbcache('/L/tmp/test.db', hashf=lambda p: p) # TODO FIXME?

Hash = str

# TODO hash is a bit misleading
# TODO perhaps another table is the way to go...

# TODO careful about concurrent access?
def read_hash(db_path: Path) -> Optional[Hash]:
    hash_file = db_path.with_suffix('.hash')
    if not hash_file.exists():
        return None
    return hash_file.read_text()

# TODO not sure if there is any way to guarantee atomic reading....
# unless it happens automatically due to unlink logic?
# TODO need to know entry type?
# TODO or, we can just encode that in names. that way no need for atomic stuff

# TODO give a better name
class Alala:
    def __init__(self, db_path: Path, type_) -> None:
        self.db = sa.create_engine(f'sqlite:///{db_path}')
        self.engine = self.db.connect() # TODO do I need to tear anything down??
        self.meta = sa.MetaData(self.engine)
        self.table_hash = sa.Table('hash' , self.meta, sa.Column('value', sa.types.String))

        schema = make_schema(type_)
        self.table_data = sa.Table('table', self.meta, *schema)
        self.meta.create_all()


def get_dbcache_logger():
    return logging.getLogger('dbcache')

# TODO ugh. there should be a nicer way to wrap that...
def make_dbcache(db_path: PathIsh, hashf, type_):
    logger = get_dbcache_logger()
    db_path = Path(db_path)
    def dec(func):
        @functools.wraps(func)
        def wrapper(key):
            # TODO FIXME make sure we have exclusive write lock

            alala = Alala(db_path, type_)
            engine = alala.engine

            prev_hashes = engine.execute(alala.table_hash.select()).fetchall()
            if len(prev_hashes) > 1:
                raise RuntimeError(f'Multiple hashes! {prev_hashes}')

            prev_hash: Optional[Hash]
            if len(prev_hashes) == 0:
                prev_hash = None
            else:
                prev_hash = prev_hashes[0][0] # TODO ugh, returns a tuple...
            logger.debug('previous hash: %s', prev_hash)

            h = hashf(key)
            logger.debug('current hash: %s', h)
            assert h is not None # just in case

            with engine.begin() as transaction:
                if h == prev_hash:
                    rows = engine.execute(alala.table_data.select()).fetchall()
                    return [type_(**row) for row in rows]
                else:
                    datas = func(key)
                    if len(datas) > 0:
                        engine.execute(alala.table_data.insert().values(datas)) # TODO chunks??

                    # TODO FIXME insert and replace instead
                    engine.execute(alala.table_hash.delete())
                    engine.execute(alala.table_hash.insert().values([{'value': h}]))
                    return datas
        return wrapper

    # TODO FIXME engine is leaking??
    return dec


def hashf(path: Path) -> Hash:
    mt = int(path.stat().st_mtime)
    return f'{path}.{mt}'

dbcache = make_dbcache('test.sqlite', hashf=hashf, type_=Location)

@dbcache
def _xxx_locations(path: Path):
    with path.open('r') as fo:
        return list(islice(_load_locations(fo), 0, 100))


def xxx_locations():
    test_src = Path('/L/tmp/LocationHistory.json')
    return _xxx_locations(test_src)


def main():
    from kython import setup_logzero
    setup_logzero(get_logger(), level=logging.DEBUG)
    setup_logzero(get_dbcache_logger(), level=logging.DEBUG)

    src_path = Path('hi')

    db_path = Path('test.sqlite')
    # if db_path.exists():
    #     db_path.unlink()

    res = xxx_locations()
    # new_wrapped = dbcache_worker(db_path=db_path, hashf=hashf, type_=Location, wrapped=wrapped)
    # res = new_wrapped(src_path)
    print(res)

    # cache_locs(source=Path('/L/tmp/LocationHistory.json'), db_path=db_path)
    # locs = iter_db_locs(db_path)
    # print(len(list(locs)))

if __name__ == '__main__':
    main()
