#!/usr/bin/env python3.6
from kython import *

from backup_config import SLEEPS_FILE, GRAPHS_DIR, PHASES_FILE

from datetime import datetime
from datetime import date

fromtimestamp = datetime.fromtimestamp

XID = str # TODO how to shared with backup thing?
Phases = Dict[XID, Any]

phases: Phases
with open(PHASES_FILE, 'r') as fo:
    phases = json_load(fo)

class SleepEntry:
    def __init__(self, js) -> None:
        self.js = js

    # TODO @memoize decorator?
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
    def graph(self) -> str:
        return os.path.join(GRAPHS_DIR, self.xid + ".png")

    @property
    def phases(self) -> List[datetime]:
        return [fromtimestamp(i['time']) for i in phases[self.xid]]

    def __str__(self) -> str:
        return f"{self.date_} {self.title}"

    def __repr__(self) -> str:
        return str(self)

def load_sleeps() -> List[SleepEntry]:
    with open(SLEEPS_FILE, 'r') as fo:
        sleeps = json_load(fo)
        return [SleepEntry(js) for js in sleeps]
import numpy as np # type: ignore
import matplotlib.pyplot as plt # type: ignore
# pip install imageio
from imageio import imread # type: ignore
from scipy.misc import imresize # type: ignore


def hhmm(time: datetime):
    return time.strftime("%H:%M")


# def xpos(time: datetime) -> float:
#     tick = span / width
#     fromstart = time - sleep.created
#     return fromstart / tick

import matplotlib.dates as mdates # type: ignore
from matplotlib.figure import Figure # type: ignore
from matplotlib.axes import Axes # type: ignore
from matplotlib.ticker import MultipleLocator, FixedLocator # type: ignore

def plot_one(sleep: SleepEntry, fig: Figure, axes: Axes):
    span = sleep.completed - sleep.created
    print(f"span: {span}")

    img = imread(sleep.graph)
    # all of them are 300x300 images apparently
    # size = img.shape
    # (height, width, depth) = size
    # size = (height, width * 5, depth)
    # (height, width, depth) = size
    # img = imresize(img, size)

    xlims = [sleep.created, sleep.completed]
    xlims = [mdates.date2num(i) for i in xlims]
    # axes.figure(figsize=(10, 5))
    axes.set_xlim(xlims)

    ylims = [0, 50]
    axes.set_ylim(ylims)
    # axes.set_xlim((sleep.created(), sleep.completed()))

    hhmm_fmt = mdates.DateFormatter('%H:%M')
    axes.xaxis.set_major_formatter(hhmm_fmt)
    ticks = [
        # sleep.created,
        # sleep.asleep,
        # sleep.completed,
       ] + sleep.phases
    axes.xaxis.set_ticks(ticks)
    # axes.set_
    # plt.gca().xaxis.set_major_formatter(myFmt)
    # plt.gca().xaxis_date()

    # axes.imshow(img, zorder=0)
    # plt.figure(figsize=(10, 5))
    axes.imshow(
        img,
        zorder=0,
        extent=[
            xlims[0], xlims[1],
            ylims[0], ylims[1],
        ],
        aspect='auto',
    )
    axes.set_title(str(sleep))
    
    # plt.text(sleep.asleep(), 0, hhmm(sleep.asleep()))

fig: Figure = plt.figure(figsize=(15, 5))
axes: Axes = fig.add_subplot(1,1,1)

sleeps = load_sleeps()
# TODO use map?
sleep = sleeps[0]
# pprint(sleeps[:2])


plot_one(sleep, fig, axes)
plt.show()

