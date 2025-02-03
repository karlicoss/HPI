'''
Weight data (manually logged)
'''

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from my import orgmode
from my.core import make_logger
from my.core.error import Res, extract_error_datetime, set_error_datetime

config = Any


def make_config() -> config:
    from my.config import weight as user_config  # type: ignore[attr-defined]

    return user_config()


log = make_logger(__name__)


@dataclass
class Entry:
    dt: datetime
    value: float
    # TODO comment??


Result = Res[Entry]


def from_orgmode() -> Iterator[Result]:
    cfg = make_config()

    orgs = orgmode.query()
    for o in orgs.all():
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
        created = cfg.default_timezone.localize(created)
        assert created is not None  # ??? somehow mypy wasn't happy?
        yield Entry(
            dt=created,
            value=w,
            # TODO add org note content as comment?
        )


def make_dataframe(data: Iterator[Result]):
    import pandas as pd

    def it():
        for e in data:
            if isinstance(e, Exception):
                dt = extract_error_datetime(e)
                yield {
                    'dt': dt,
                    'error': str(e),
                }
            else:
                yield {
                    'dt': e.dt,
                    'weight': e.value,
                }

    df = pd.DataFrame(it())
    df = df.set_index('dt')
    # TODO not sure about UTC??
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def dataframe():
    entries = from_orgmode()
    return make_dataframe(entries)


# TODO move to a submodule? e.g. my.body.weight.orgmode?
# so there could be more sources
# not sure about my.body thing though
