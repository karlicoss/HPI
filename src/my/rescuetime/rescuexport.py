"""
RescueTime activity data

Reads activity JSON exports from [[https://github.com/karlicoss/rescuexport][rescuexport]].
"""

REQUIRES = [
    'rescuexport @ git+https://github.com/karlicoss/rescuexport',
]

import json
from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable, Sequence
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from typing import cast

from more_itertools import split_when
from rescuexport import dal

from my.core import Paths, Res, Stats, get_files, make_logger, stat, warnings
from my.core.cachew import disabled_cachew, mcachew
from my.core.cfg import tmp_config
from my.core.error import split_errors
from my.core.pandas import DataFrameT, as_dataframe

logger = make_logger(__name__)


class Config(ABC):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """Paths or globs pointing to rescuexport JSON files."""
        raise NotImplementedError


def make_config() -> Config:
    from my.config import rescuetime as user_config

    if hasattr(user_config, 'rescuexport'):

        class combined_config(user_config.rescuexport, Config):
            pass

        return combined_config()

    warnings.high('The flat RescueTime config is deprecated. Use my.config.rescuetime.rescuexport.export_path instead.')
    return cast(Config, user_config())


DAL = dal.DAL
Entry = dal.Entry


def inputs() -> Sequence[Path]:
    return get_files(make_config().export_path)


@mcachew(depends_on=inputs)
def entries() -> Iterable[Res[Entry]]:
    dal = DAL(inputs())
    yield from dal.entries()


def groups(gap: timedelta = timedelta(hours=3)) -> Iterable[Res[Sequence[Entry]]]:
    vit, eit = split_errors(entries(), ET=Exception)
    yield from eit
    yield from split_when(vit, lambda a, b: (b.dt - a.dt) > gap)


# todo automatic dataframe interface?
def dataframe() -> DataFrameT:
    return as_dataframe(entries())


def stats() -> Stats:
    return {
        **stat(groups),
        **stat(entries),
    }


# todo take seed, or what?
@contextmanager
def fake_data(rows: int = 1000) -> Generator[ModuleType]:
    """Temporarily read generated RescueTime entries with caching disabled."""
    with disabled_cachew(), TemporaryDirectory() as td:
        tdir = Path(td)
        f = tdir / 'rescuetime.json'
        f.write_text(json.dumps(dal.fake_data_generator(rows=rows)))

        class override:
            class rescuetime:
                class rescuexport:
                    export_path = tdir

        with tmp_config(modules=__name__, config=override) as cfg:
            yield cfg


# TODO let doctor use fake_data() for a basic module check.


def fill_influxdb() -> None:
    from my.core import influxdb

    it = (
        {
            'dt': e.dt,
            'duration_d': e.duration_s,
            'tags': {'activity': e.activity},
        }
        for e in entries()
        if isinstance(e, Entry)
    )  # TODO handle errors in core.influxdb
    influxdb.fill(it, measurement=__name__)


# TODO lots of garbage in dir()? maybe need to del the imports...
