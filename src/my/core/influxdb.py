'''
TODO doesn't really belong to 'core' morally, but can think of moving out later
'''

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import click

from .logging import make_logger
from .types import Json, asdict

logger = make_logger(__name__)


class config:
    db = 'db'


RESET_DEFAULT = False


def fill(it: Iterable[Any], *, measurement: str, reset: bool = RESET_DEFAULT, dt_col: str = 'dt') -> None:
    # todo infer dt column automatically, reuse in stat?
    # it doesn't like dots, ends up some syntax error?
    measurement = measurement.replace('.', '_')
    # todo autoinfer measurement?

    db = config.db

    from influxdb import InfluxDBClient  # type: ignore[import-not-found]

    client = InfluxDBClient()
    # todo maybe create if not exists?
    # client.create_database(db)

    # todo should be it be env variable?
    if reset:
        logger.warning('deleting measurements: %s:%s', db, measurement)
        client.delete_series(database=db, measurement=measurement)

    # TODO need to take schema here...
    cache: dict[str, bool] = {}

    def good(f, v) -> bool:
        c = cache.get(f)
        if c is not None:
            return c
        t = type(v)
        r = t in {str, int}
        cache[f] = r
        if not r:
            logger.warning('%s: filtering out %s=%s because of type %s', measurement, f, v, t)
        return r

    def filter_dict(d: Json) -> Json:
        return {f: v for f, v in d.items() if good(f, v)}

    def dit() -> Iterable[Json]:
        for i in it:
            d = asdict(i)
            tags: Json | None = None
            tags_ = d.get('tags')  # meh... handle in a more robust manner
            if tags_ is not None and isinstance(tags_, dict):  # FIXME meh.
                del d['tags']
                tags = tags_

            # TODO what to do with exceptions??
            # todo handle errors.. not sure how? maybe add tag for 'error' and fill with empty data?
            dt = d[dt_col].isoformat()
            del d[dt_col]

            fields = filter_dict(d)

            yield {
                'measurement': measurement,
                # TODO maybe good idea to tag with database file/name? to inspect inconsistencies etc..
                # hmm, so tags are autoindexed and might be faster?
                # not sure what's the big difference though
                # "fields are data and tags are metadata"
                'tags': tags,
                'time': dt,
                'fields': fields,
            }

    from more_itertools import chunked

    # "The optimal batch size is 5000 lines of line protocol."
    # some chunking is def necessary, otherwise it fails
    inserted = 0
    for chi in chunked(dit(), n=5000):
        chl = list(chi)
        inserted += len(chl)
        logger.debug('writing next chunk %s', chl[-1])
        client.write_points(chl, database=db)

    logger.info('inserted %d points', inserted)
    # todo "Specify timestamp precision when writing to InfluxDB."?


def magic_fill(it, *, name: str | None = None, reset: bool = RESET_DEFAULT) -> None:
    if name is None:
        assert callable(it)  # generators have no name/module
        name = f'{it.__module__}:{it.__name__}'
    assert name is not None

    if callable(it):
        it = it()

    from itertools import tee

    from more_itertools import first, one

    it, x = tee(it)
    f = first(x, default=None)
    if f is None:
        logger.warning('%s has no data', name)
        return

    # TODO can we reuse pandas code or something?
    #
    from .pandas import _as_columns

    schema = _as_columns(type(f))

    from datetime import datetime

    dtex = RuntimeError(f'expected single datetime field. schema: {schema}')
    dtf = one((f for f, t in schema.items() if t == datetime), too_short=dtex, too_long=dtex)

    fill(it, measurement=name, reset=reset, dt_col=dtf)


@click.group()
def main() -> None:
    pass


@main.command(name='populate', short_help='populate influxdb')
@click.option('--reset', is_flag=True, help='Reset Influx measurements before inserting', show_default=True)
@click.argument('FUNCTION_NAME', type=str, required=True)
def populate(*, function_name: str, reset: bool) -> None:
    from .__main__ import _locate_functions_or_prompt

    [provider] = list(_locate_functions_or_prompt([function_name]))
    # todo could have a non-interactive version which populates from all data sources for the provider?
    magic_fill(provider, reset=reset)


# todo later just add to hpi main?
# not sure if want to couple
if __name__ == '__main__':
    main()
