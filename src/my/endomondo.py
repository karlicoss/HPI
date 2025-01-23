'''
Endomondo exercise data
'''

REQUIRES = [
    'git+https://github.com/karlicoss/endoexport',
]
# todo use ast in setup.py or doctor to extract the corresponding pip packages?

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from my.config import endomondo as user_config

from .core import Paths, get_files


@dataclass
class endomondo(user_config):
    '''
    Uses [[https://github.com/karlicoss/endoexport][endoexport]] outputs
    '''

    # paths[s]/glob to the exported JSON data
    export_path: Paths


def inputs() -> Sequence[Path]:
    return get_files(endomondo.export_path)


# todo add a doctor check for pip endoexport module
import endoexport.dal as dal
from endoexport.dal import Point, Workout  # noqa: F401

from .core import Res


# todo cachew?
def workouts() -> Iterable[Res[Workout]]:
    _dal = dal.DAL(inputs())
    yield from _dal.workouts()


from .core.pandas import DataFrameT, check_dataframe


@check_dataframe
def dataframe(*, defensive: bool=True) -> DataFrameT:
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
                    }
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


from .core import Stats, stat


def stats() -> Stats:
    return {
        # todo pretty print stats?
        **stat(workouts),
        **stat(dataframe),
    }


# TODO make sure it's possible to 'advise' functions and override stuff

from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def fake_data(count: int=100) -> Iterator:
    import json
    from tempfile import TemporaryDirectory

    from my.core.cfg import tmp_config
    with TemporaryDirectory() as td:
        tdir = Path(td)
        fd = dal.FakeData()
        data = fd.generate(count=count)

        jf = tdir / 'data.json'
        jf.write_text(json.dumps(data))

        class override:
            class endomondo:
                export_path = tdir

        with tmp_config(modules=__name__, config=override) as cfg:
            # todo would be nice to somehow expose the generator so it's possible to hack from the outside?
            yield cfg
