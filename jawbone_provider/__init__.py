#!/usr/bin/env python3
from typing import Dict, Any, List
import json
from datetime import datetime, date, time
from pathlib import Path

BDIR = Path('/L/backups/jawbone')
PHASES_FILE = BDIR / 'phases.json'
SLEEPS_FILE = BDIR / 'sleeps.json'
GRAPHS_DIR = BDIR / 'graphs'


fromtimestamp = datetime.fromtimestamp # TODO careful

XID = str # TODO how to shared with backup thing?


Phases = Dict[XID, Any]


phases: Phases = json.loads(PHASES_FILE.read_text())

# TODO namedtuple, cproperty?
# TODO cache?
class SleepEntry:
    def __init__(self, js) -> None:
        self.js = js

    # TODO @memoize decorator?
    # date is going to be the date of the day you mostly slept on
    # e.g. if you went to bed at 01:30 24 august and work up at 8AM, date is gonna be 24 august
    @property
    def date_(self) -> date:
        dates = str(self.js['date'])
        return datetime.strptime(dates, "%Y%m%d").date()

    @property
    def title(self) -> str:
        return self.js['title']

    @property
    def xid(self) -> XID:
        return self.js['xid']

    def _details(self):
        return self.js['details']

    @property
    def created(self) -> datetime:
        return fromtimestamp(self.js['time_created'])

    @property
    def completed(self) -> datetime:
        return fromtimestamp(self.js['time_completed'])

    @property
    def asleep(self) -> datetime:
        return fromtimestamp(self._details()['asleep_time'])

    @property
    def graph(self) -> Path:
        return GRAPHS_DIR / (self.xid + ".png")

    @property
    def phases(self) -> List[datetime]:
        return [fromtimestamp(i['time']) for i in phases[self.xid]]

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
# from imageio import imread # type: ignore
from scipy.misc import imresize # type: ignore


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

from kython import make_dict
def sleeps_by_date() -> Dict[date, SleepEntry]:
    sleeps = load_sleeps()
    sleeps = [s for s in sleeps if s.graph.exists()] # TODO careful..
    return make_dict(sleeps, key=SleepEntry.date_)

# sleeps_count = 35 # len(sleeps) # apparently MPL fails at 298 with outofmemory or something
# start = 40
# 65 is arount 1 july
# sleeps = sleeps[start: start + sleeps_count]
# sleeps = sleeps[:sleeps_count]
# dt = {k: v for k, v in dt.items() if v is not None}

# TODO ??
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
    # TODO ??
    sleeps = lfilter(predicate, sleeps)
    sleeps_count = len(sleeps)
    print(sleeps_count)

    fig: Figure = plt.figure(figsize=(15, sleeps_count * 1))

    axarr = fig.subplots(nrows=len(sleeps))
    for i, (sleep, axes) in enumerate(zip(sleeps, axarr)):
        plot_one(sleep, fig, axes, showtext=True)
        used = dt.get(sleep.date_, None)
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

