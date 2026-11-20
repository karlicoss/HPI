"""
Endomondo exercise data

Reads workout JSON exports from [[https://github.com/karlicoss/endoexport][endoexport]].
"""

REQUIRES = [
    'endoexport[dal] @ git+https://github.com/karlicoss/endoexport',
]

import json
from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable, Sequence
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from typing import cast

# todo add a doctor check for pip endoexport module
from endoexport import dal

from my.core import Paths, Res, Stats, get_files, stat, warnings
from my.core.cfg import tmp_config
from my.core.pandas import DataFrameT, check_dataframe


class Config(ABC):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """Paths or globs pointing to endoexport workout JSON files."""
        raise NotImplementedError


def make_config() -> Config:
    from my.config import endomondo as user_config

    if hasattr(user_config, 'endoexport'):

        class combined_config(user_config.endoexport, Config):
            pass

        return combined_config()

    warnings.high('The flat Endomondo config is deprecated. Use my.config.endomondo.endoexport.export_path instead.')
    return cast(Config, user_config())


Point = dal.Point
Workout = dal.Workout


def inputs() -> Sequence[Path]:
    return get_files(make_config().export_path)


# todo cachew?
def workouts() -> Iterable[Res[Workout]]:
    _dal = dal.DAL(inputs())
    yield from _dal.workouts()


@check_dataframe
def dataframe(*, defensive: bool = True) -> DataFrameT:
    def it():
        for w in workouts():
            if isinstance(w, Exception):
                yield {'error': str(w)}
            else:
                try:
                    d = {
                        'id'            : w.id            ,
                        'start_time'    : w.start_time    ,
                        'duration'      : w.duration      ,
                        'sport'         : w.sport         ,
                        'heart_rate_avg': w.heart_rate_avg,
                        'speed_avg'     : w.speed_avg     ,
                        'kcal'          : w.kcal          ,
                    }  # fmt: skip
                except Exception as e:
                    # TODO use the trace? otherwise str() might be too short..
                    # r.g. for KeyError it only shows the missing key
                    # todo check for 'defensive'
                    d = {'error': f'{e} {w}'}
                yield d

    import pandas as pd

    df = pd.DataFrame(it())
    # pandas guesses integer, which is pointless for this field (might get coerced to float too)
    df['id'] = df['id'].astype(str)
    if 'error' not in df:
        df['error'] = None
    return df


def stats() -> Stats:
    return {
        # todo pretty print stats?
        **stat(workouts),
        **stat(dataframe),
    }


# TODO make sure it's possible to 'advise' functions and override stuff
@contextmanager
def fake_data(count: int = 100) -> Generator[ModuleType]:
    with TemporaryDirectory() as td:
        tdir = Path(td)
        fd = dal.FakeData()
        data = fd.generate(count=count)

        jf = tdir / 'data.json'
        jf.write_text(json.dumps(data))

        class override:
            class endomondo:
                class endoexport:
                    export_path = tdir

        with tmp_config(modules=__name__, config=override) as cfg:
            # todo would be nice to somehow expose the generator so it's possible to hack from the outside?
            yield cfg
