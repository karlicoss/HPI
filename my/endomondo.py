'''
Endomondo exercise data
'''

REQUIRES = [
    'git+https://github.com/karlicoss/endoexport',
]
# todo use ast in setup.py or doctor to extract the corresponding pip packages?

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Iterable

from .core.common import Paths, get_files
from .core.error import Res

from my.config import endomondo as user_config

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
import endoexport.dal
from endoexport.dal import Point, Workout


# todo cachew?
def workouts() -> Iterable[Res[Workout]]:
    dal = endoexport.dal.DAL(inputs())
    yield from dal.workouts()


def dataframe(defensive=True):
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
    import pandas as pd # type: ignore
    df = pd.DataFrame(it())
    # pandas guesses integer, which is pointless for this field (might get coerced to float too)
    df['id'] = df['id'].astype(str)
    return df



def stats():
    from .core import stat
    return stat(workouts)


# TODO make sure it's possible to 'advise' functions and override stuff
