'''
[[https://github.com/jonasoreland/runnerup][Runnerup]] exercise data (TCX format)
'''

REQUIRES = [
    'python-tcxparser',
]

from collections.abc import Iterable
from datetime import timedelta
from pathlib import Path

import tcxparser  # type: ignore[import-untyped]

from my.config import runnerup as config
from my.core import Json, Res, get_files
from my.core.compat import fromisoformat

# TODO later, use a proper namedtuple?
Workout = Json


def _parse(f: Path) -> Workout:
    tcx = tcxparser.TCXParser(str(f))

    sport = f.stem.split('_')[-1] # todo not sure how reliable...
    hr_avg = tcx.hr_avg

    distance_m = tcx.distance
    duration_s = tcx.duration
    # kmh to match endomondo.. should probably be CI
    speed_avg_kmh = (distance_m / 1000) / (duration_s / 3600)

    # eh. not sure if there is a better way
    # for now use this to be compatible with Endomondo
    # https://beepb00p.xyz/heartbeats_vs_kcals.html
    # filtered for Endomondo running:
    reg_coeff = 0.0993
    intercept = -11.0739
    total_beats = hr_avg * (duration_s / 60)
    kcal_estimate = total_beats * reg_coeff + intercept

    return {
        'id'            : f.name, # not sure?
        'start_time'    : fromisoformat(tcx.started_at),
        'duration'      : timedelta(seconds=tcx.duration),
        'sport'         : sport,
        'heart_rate_avg': tcx.hr_avg,
        'speed_avg'     : speed_avg_kmh,
        'kcal'          : kcal_estimate,
    }
    # from more_itertools import zip_equal
    # for ts, latlon, hr in zip_equal(
    #         tcx.time_values(),
    #         tcx.position_values(),
    #         tcx.hr_values(),
    #         # todo cadence?
    # ):
    #     t = fromisoformat(ts)


def workouts() -> Iterable[Res[Workout]]:
    for f in get_files(config.export_path):
        try:
            yield _parse(f)
        except Exception as e:
            yield e


from .core.pandas import DataFrameT, check_dataframe, error_to_row


@check_dataframe
def dataframe() -> DataFrameT:
    def it():
        for w in workouts():
            if isinstance(w, Exception):
                yield error_to_row(w)
            else:
                yield w
    import pandas as pd
    df = pd.DataFrame(it())
    if 'error' not in df:
        df['error'] = None
    return df


from .core import Stats, stat


def stats() -> Stats:
    return stat(dataframe)
