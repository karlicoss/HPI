'''
EightSleep data
'''

REQUIRES = [
    'git+https://github.com/hpi/eight-sleep',
]

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Iterable

from .core import Paths, get_files

from my.config import eightsleep as user_config

@dataclass
class eightsleep(user_config):
    # paths[s]/glob to the exported JSON data
    export_path: Paths


def inputs() -> Sequence[Path]:
    return get_files(eightsleep.export_path)


import eightsleep.dal as dal


def sessions():
    _dal = dal.DAL(inputs())
    yield from _dal.sessions()


from .core.pandas import check_dataframe, DataFrameT

@check_dataframe
def dataframe(defensive: bool=True) -> DataFrameT:
    def it():
        for s in sessions():
            try:
                d = {
                    'ts': s['ts'],
                    'score'      : s['score'],
                    'stages': pd.DataFrame(s['stages']),
                    'tossAndTurns': pd.DataFrame(s['tossAndTurns']),
                    'tempRoomC': pd.DataFrame(s['tempRoomC']),
                    'tempBedC': pd.DataFrame(s['tempBedC']),
                    'respiratoryRate': pd.DataFrame(s['respiratoryRate']),
                    'heartRate': pd.DataFrame(s['heartRate']),
                    'hrv': pd.DataFrame(s['hrv']),
                    'rmssd': pd.DataFrame(s['rmssd']),
                    'stages': pd.DataFrame(s['stages']),
                    'presenceDuration': s['presenceDuration'] if 'presenceDuration' in s else 0,
                    'sleepDuration': s['sleepDuration'] if 'sleepDuration' in s else 0,
                    'deepPercent': s['deepPercent'] if 'deepPercent' in s else 0,
                    'presenceStart': s['presenceStart'] if 'presenceStart' in s else 0,
                    'presenceEnd': s['presenceEnd'] if 'presenceEnd' in s else 0,
                    'sleepStart': s['sleepStart'] if 'sleepStart' in s else 0,
                    'sleepEnd': s['sleepEnd'] if 'sleepEnd' in s else 0,
                    'totalTossAndTurns': s['tnt'] if 'tnt' in s else 0,
                    'incomplete': s['incomplete'] if 'incomplete' in s else False
                }
            except Exception as e:
                # TODO use the trace? otherwise str() might be too short..
                # r.g. for KeyError it only shows the missing key
                # todo check for 'defensive'
                d = {'error': f'{e} {s}'}
            yield d
    import pandas as pd # type: ignore
    df = pd.DataFrame(it())
    print(df)
    if 'error' not in df:
        df['error'] = None
    return df

from .core import stat, Stats
def stats() -> Stats:
    return {
        # todo pretty print stats?
        **stat(dataframe),
    }
