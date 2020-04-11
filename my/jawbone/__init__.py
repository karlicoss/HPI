#!/usr/bin/env python3
from typing import Dict, Any, List
import json
from functools import lru_cache
from datetime import datetime, date, time, timedelta
from pathlib import Path
import logging
import pytz

from my.config import jawbone as config


BDIR = config.export_dir
PHASES_FILE = BDIR / 'phases.json'
SLEEPS_FILE = BDIR / 'sleeps.json'
GRAPHS_DIR = BDIR / 'graphs'


def get_logger():
    return logging.getLogger('jawbone-provider')


XID = str # TODO how to shared with backup thing?

Phases = Dict[XID, Any]
@lru_cache(1)
def get_phases() -> Phases:
    return json.loads(PHASES_FILE.read_text())

# TODO use awakenings and quality
class SleepEntry:
    def __init__(self, js) -> None:
        self.js = js

    # TODO @memoize decorator?
    @property
    def date_(self) -> date:
        return self.sleep_end.date()

    def _fromts(self, ts: int) -> datetime:
        return pytz.utc.localize(datetime.utcfromtimestamp(ts)).astimezone(self._tz).astimezone(self._tz)
    @property
    def _tz(self):
        return pytz.timezone(self._details['tz'])

    @property
    def title(self) -> str:
        return self.js['title']

    @property
    def xid(self) -> XID:
        return self.js['xid']

    @property
    def _details(self):
        return self.js['details']

    # TODO figure out timezones..
    # not sure how.. I guess by the american ones
    @property
    def created(self) -> datetime:
        return self._fromts(self.js['time_created'])

    @property
    def completed(self) -> datetime:
        return self._fromts(self.js['time_completed'])

    @property
    def asleep(self) -> datetime:
        return self._fromts(self._details['asleep_time'])

    @property
    def sleep_start(self) -> datetime:
        return self.asleep # TODO careful, maybe use same logic as emfit

    @property
    def bed_time(self) -> int:
        return int((self.sleep_end - self.sleep_start).total_seconds()) // 60

    @property
    def sleep_end(self) -> datetime:
        return self._fromts(self._details['awake_time'])

    @property
    def graph(self) -> Path:
        return GRAPHS_DIR / (self.xid + ".png")

    # TODO might be useful to cache these??
    @property
    def phases(self) -> List[datetime]:
        # TODO make sure they are consistent with emfit?
        return [self._fromts(i['time']) for i in get_phases()[self.xid]]

    def __str__(self) -> str:
        return f"{self.date_.strftime('%a %d %b')} {self.title}"

    def __repr__(self) -> str:
        return str(self)


def load_sleeps() -> List[SleepEntry]:
    sleeps = json.loads(SLEEPS_FILE.read_text())
    return [SleepEntry(js) for js in sleeps]


import numpy as np # type: ignore
import matplotlib.pyplot as plt # type: ignore
from matplotlib.figure import Figure # type: ignore
from matplotlib.axes import Axes # type: ignore

# pip install imageio
from imageio import imread # type: ignore


def hhmm(time: datetime):
    return time.strftime("%H:%M")


# def xpos(time: datetime) -> float:
#     tick = span / width
#     fromstart = time - sleep.created
#     return fromstart / tick

import matplotlib.dates as mdates # type: ignore
from matplotlib.ticker import MultipleLocator, FixedLocator # type: ignore

def plot_one(sleep: SleepEntry, fig: Figure, axes: Axes, xlims=None, showtext=True):
    span = sleep.completed - sleep.created
    print(f"{sleep.xid} span: {span}")

    img = imread(sleep.graph)
    # all of them are 300x300 images apparently
    # span for image
    xspan = [sleep.created, sleep.completed]
    xspan = [mdates.date2num(i) for i in xspan]
    if xlims is None:
        tt = sleep.created
        hour = tt.hour
        # TODO maybe assert that hour is somewhere between 20 and 8 or something
        start: datetime
        starttime = time(23, 00)
        if hour >= 20:
            # went to bed before midnight
            start = datetime.combine(tt.date(), starttime)
        elif hour <= 8:
            # went to bed after midnight
            start = datetime.combine(tt.date() - timedelta(days=1), starttime)
        else:
            print("wtf??? weird time for sleep...")
            # choosing at random
            start = datetime.combine(tt.date(), starttime)
        end = start + timedelta(hours=10)
        xlims = [start, end]

    # axes.figure(figsize=(10, 5))
    axes.set_xlim(xlims)
    hhmm_fmt = mdates.DateFormatter('%H:%M')
    axes.xaxis.set_major_formatter(hhmm_fmt)
    ticks = sleep.phases if showtext else []
    axes.xaxis.set_ticks(ticks)
    axes.yaxis.set_ticks([])
    axes.tick_params(
        axis='both',
        which='major',
        length=0,
        labelsize=7,
        rotation=30,
        pad=-14, # err... hacky
    )

    ylims = [0, 50]
    axes.set_ylim(ylims)

    axes.imshow(
        img,
        zorder=0,
        extent=[
            xspan[0], xspan[1],
            ylims[0], ylims[1],
        ],
        aspect='auto',
    )
    # axes.set_title(str(sleep))
    # axes.title.set_size(10)

    if showtext:
        axes.text(xlims[1] - timedelta(hours=1.5), 20, str(sleep),)
    # plt.text(sleep.asleep(), 0, hhmm(sleep.asleep()))

from ..common import group_by_key

def sleeps_by_date() -> Dict[date, SleepEntry]:
    logger = get_logger()

    sleeps = load_sleeps()
    sleeps = [s for s in sleeps if s.graph.exists()] # TODO careful..
    res = {}
    for dd, group in group_by_key(sleeps, key=lambda s: s.date_).items():
        if len(group) == 1:
            res[dd] = group[0]
        else:
            # TODO short ones I can ignore I guess. but won't bother now
            logger.error('multiple sleeps on %s: %s', dd, group)
    return res

# sleeps_count = 35 # len(sleeps) # apparently MPL fails at 298 with outofmemory or something
# start = 40
# 65 is arount 1 july
# sleeps = sleeps[start: start + sleeps_count]
# sleeps = sleeps[:sleeps_count]
# dt = {k: v for k, v in dt.items() if v is not None}

# TODO not really sure it belongs here...
# import melatonin
# dt = melatonin.get_data()

def predicate(sleep: SleepEntry):
    """
       Filter for comparing similar sleep sesssions
    """
    start = sleep.created.time()
    end = sleep.completed.time()
    if (time(23, 0) <= start <= time(23, 30)) and (time(5, 30) <= end <= time(6, 30)):
        return True
    return False


def plot():
    # TODO FIXME melatonin data
    melatonin_data = {} # type: ignore[var-annotated]

    # TODO ??
    sleeps = list(filter(predicate, load_sleeps()))
    sleeps_count = len(sleeps)
    print(sleeps_count)

    fig: Figure = plt.figure(figsize=(15, sleeps_count * 1))

    axarr = fig.subplots(nrows=len(sleeps))
    for i, (sleep, axes) in enumerate(zip(sleeps, axarr)):
        plot_one(sleep, fig, axes, showtext=True)
        used = melatonin_data.get(sleep.date_, None)
        sused: str
        color: str
        # used = True if used is None else False # TODO?
        if used is True:
            sused = "YES"
            color = 'green'
        elif used is False:
            sused = "NO"
            color = 'red'
        else:
            sused = "??"
            color = 'white'
        axes.text(axes.get_xlim()[0], 20, sused)
        axes.patch.set_alpha(0.5)
        axes.set_facecolor(color)


    plt.tight_layout()
    plt.subplots_adjust(hspace=0.0)
    # er... this saves with a different aspect ratio for some reason.
    # tap 'ctrl-s' on mpl plot window to save..
    # plt.savefig('res.png', asp)
    plt.show()

import pandas as pd # type: ignore
def get_dataframe():
    sleeps = sleeps_by_date()
    items = []
    for dd, s in sleeps.items():
        items.append({
            'date'       : dd, # TODO not sure... # TODO would also be great to sync column names...
            'sleep_start': s.sleep_start,
            'sleep_end'  : s.sleep_end,
            'bed_time'   : s.bed_time,
        })
        # TODO tz is in sleeps json
    res = pd.DataFrame(items)
    return res


def test_tz():
    sleeps = sleeps_by_date()
    for s in sleeps.values():
        assert s.sleep_start.tzinfo is not None
        assert s.sleep_end.tzinfo is not None

    for dd, exp in [
            (date(year=2015, month=8 , day=28), time(hour=7, minute=20)),
            (date(year=2015, month=9 , day=15), time(hour=6, minute=10)),
    ]:
        sleep = sleeps[dd]
        end = sleep.sleep_end

        assert end.time() == exp

        # TODO fuck. on 0909 I woke up at around 6 according to google timeline
        # but according to jawbone, it was on 0910?? eh. I guess it's jus shitty tracking.


def main():
    # TODO eh. vendorize klogging already?
    from kython.klogging import setup_logzero
    setup_logzero(get_logger())
    test_tz()
    # print(get_dataframe())


if __name__ == '__main__':
    main()
