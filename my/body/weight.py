'''
Weight data (manually logged)
'''

from datetime import datetime
from typing import NamedTuple, Iterator

from ..core import LazyLogger
from ..core.error import Res, set_error_datetime, extract_error_datetime

from .. import orgmode

from my.config import weight as config


log = LazyLogger('my.body.weight')


class Entry(NamedTuple):
    dt: datetime
    value: float
    # TODO comment??


Result = Res[Entry]


def from_orgmode() -> Iterator[Result]:
    orgs = orgmode.query()
    for o in orgmode.query().all():
        if 'weight' not in o.tags:
            continue
        try:
            # TODO can it throw? not sure
            created = o.created
            assert created is not None
        except Exception as e:
            log.exception(e)
            yield e
            continue
        try:
            w = float(o.heading)
        except Exception as e:
            set_error_datetime(e, dt=created)
            log.exception(e)
            yield e
            continue
        # FIXME use timezone provider
        created = config.default_timezone.localize(created)
        assert created is not None #??? somehow mypy wasn't happy?
        yield Entry(
            dt=created,
            value=w,
            # TODO add org note content as comment?
        )


def make_dataframe(data: Iterator[Result]):
    import pandas as pd # type: ignore
    def it():
        for e in data:
            if isinstance(e, Exception):
                dt = extract_error_datetime(e)
                yield {
                    'dt'    : dt,
                    'error': str(e),
                }
            else:
                yield {
                    'dt'    : e.dt,
                    'weight': e.value,
                }
    df = pd.DataFrame(it())
    df.set_index('dt', inplace=True)
    # TODO not sure about UTC??
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def dataframe():
    entries = from_orgmode()
    return make_dataframe(entries)

# TODO move to a submodule? e.g. my.body.weight.orgmode?
# so there could be more sources
# not sure about my.body thing though
