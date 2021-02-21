'''
TODO doesn't really belong to 'core' morally, but can think of moving out later
'''
from typing import Iterable, Any, Optional


from .common import LazyLogger, asdict, Json


logger = LazyLogger(__name__)


class config:
    db = 'db'


def fill(it: Iterable[Any], *, measurement: str, reset: bool=False) -> None:
    # todo infer dt column automatically, reuse in stat?
    # it doesn't like dots, ends up some syntax error?
    measurement = measurement.replace('.', '_')
    # todo autoinfer measurement?

    db = config.db

    from influxdb import InfluxDBClient # type: ignore
    client = InfluxDBClient()
    # todo maybe create if not exists?
    # client.create_database(db)

    # todo should be it be env variable?
    if reset:
        client.delete_series(database=db, measurement=measurement)

    def dit() -> Iterable[Json]:
        for i in it:
            d = asdict(i)
            tags: Optional[Json] = None
            tags = d.get('tags') # meh... handle in a more robust manner
            if tags is not None:
                del d['tags']

            # TODO what to do with exceptions??
            # todo handle errors.. not sure how? maybe add tag for 'error' and fill with emtpy data?
            dt = d['dt'].isoformat()
            del d['dt']
            fields = d
            yield dict(
                measurement=measurement,
                # TODO maybe good idea to tag with database file/name? to inspect inconsistencies etc..
                # hmm, so tags are autoindexed and might be faster?
                # not sure what's the big difference though
                # "fields are data and tags are metadata"
                tags=tags,
                time=dt,
                fields=d,
            )


    from more_itertools import chunked
    # "The optimal batch size is 5000 lines of line protocol."
    # some chunking is def necessary, otherwise it fails
    for chi in chunked(dit(), n=5000):
        chl = list(chi)
        logger.debug('writing next chunk %s', chl[-1])
        client.write_points(chl, database=db)
    # todo "Specify timestamp precision when writing to InfluxDB."?
