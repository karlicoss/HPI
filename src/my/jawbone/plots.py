#!/usr/bin/env python3
# TODO this should be in dashboard
# from kython.plotting import *
from csv import DictReader
from pathlib import Path
from typing import Any, NamedTuple

import matplotlib.pylab as pylab  # type: ignore[import-not-found]

# sleep = []
# with open('2017.csv', 'r') as fo:
#     reader = DictReader(fo)
#     for line in islice(reader, 0, 10):
#         sleep
#         print(line)
import matplotlib.pyplot as plt  # type: ignore[import-not-found]
from numpy import genfromtxt

pylab.rcParams['figure.figsize'] = (32.0, 24.0)
pylab.rcParams['font.size'] = 10

jawboneDataFeatures = Path(__file__).parent / 'features.csv' # Data File Path
featureDesc: dict[str, str] = {}
for x in genfromtxt(jawboneDataFeatures, dtype='unicode', delimiter=','):
    featureDesc[x[0]] = x[1]

def _safe_float(s: str):
    if len(s) == 0:
        return None
    return float(s)

def _safe_int(s: str):
    if len(s) == 0:
        return None
    return int(float(s)) # TODO meh

def _safe_mins(s: float):
    if s is None:
        return None
    return s / 60

class SleepData(NamedTuple):
    date: str
    asleep_time: float
    awake_time: float
    total: float
    awake: float # 'awake for' from app, time awake duing sleep (seconds)
    awakenings: int
    light: float # 'light sleep' from app (seconds)
    deep: float  # 'deep sleep' from app (sec)
    quality: float # ???

    @classmethod
    def from_jawbone_dict(cls, d: dict[str, Any]):
        return cls(
            date=d['DATE'],
            asleep_time=_safe_mins(_safe_float(d['s_asleep_time'])),
            awake_time=_safe_mins(_safe_float(d['s_awake_time'])),
            total=_safe_mins(_safe_float(d['s_duration'])),
            light=_safe_mins(_safe_float(d['s_light'])),
            deep =_safe_mins(_safe_float(d['s_deep'])),
            awake=_safe_mins(_safe_float(d['s_awake'])),
            awakenings=_safe_int(d['s_awakenings']),
            quality=_safe_float(d['s_quality']),
        )

    def is_bad(self):
        return self.deep is None and self.light is None

    # @property
    # def total(self) -> float:
    #     return self.light + self.deep



def iter_useful(data_file: str):
    with Path(data_file).open() as fo:
        reader = DictReader(fo)
        for d in reader:
            dt = SleepData.from_jawbone_dict(d)
            if not dt.is_bad():
                yield dt

# TODO <<< hmm. these files do contain deep and light sleep??
# also steps stats??
from my.config import jawbone as config  # type: ignore[attr-defined]

p = config.export_dir / 'old_csv'
# TODO with_my?
files = [
    p / "2015.csv",
    p / "2016.csv",
    p / "2017.csv",
]

from kython import concat, parse_date  # type: ignore[import-not-found]

useful = concat(*(list(iter_useful(str(f))) for f in files))

# for u in useful:
#     print(f"{u.total} {u.asleep_time} {u.awake_time}")
#     # pprint(u.total)
#     pprint(u)
#     pprint("---")

dates = [parse_date(u.date, yearfirst=True, dayfirst=False) for u in useful]
# TODO filter outliers?

# TODO don't need this anymore? it's gonna be in dashboards package
from kython.plotting import plot_timestamped  # type: ignore[import-not-found]

for attr, lims, mavg, fig in [
        ('light', (0, 400), 5, None),
        ('deep', (0, 600), 5, None),
        ('total', (200, 600), 5, None),
        ('awake_time', (0, 1200), None, 1),
        ('asleep_time', (-100, 1000), None, 1),
        # ('awakenings', (0, 5)),
]:
    dates_wkd = [d for d in dates if d.weekday() < 5]
    dates_wke = [d for d in dates if d.weekday() >= 5]
    for dts, dn in [
            (dates, 'total'),
            (dates_wkd, 'weekday'),
            (dates_wke, 'weekend')
    ]:
        mavgs = []
        if mavg is not None:
            mavgs.append((mavg, 'green'))
        fig = plot_timestamped(
            dts,
            [getattr(u, attr) for u in useful],
            marker='.',
            ratio=(16, 4),
            mavgs=mavgs,
            ylimits=lims,
            ytick_size=60,
            # figure=1,
           )
        plt.savefig(f'{attr}_{dn}.png')

# TODO use proper names?
# plt.savefig('res.png')
# fig.show()
