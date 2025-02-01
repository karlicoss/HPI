from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytz

from my.core import make_logger

logger = make_logger(__name__)

from my.config import jawbone as config  # type: ignore[attr-defined]

BDIR = config.export_dir
PHASES_FILE = BDIR / 'phases.json'
SLEEPS_FILE = BDIR / 'sleeps.json'
GRAPHS_DIR = BDIR / 'graphs'



XID = str # TODO how to shared with backup thing?

Phases = dict[XID, Any]
@lru_cache(1)
def get_phases() -> Phases:
    return json.loads(PHASES_FILE.read_text())

# TODO use awakenings and quality
class SleepEntry:
    def __init__(self, js) -> None:
        self.js = js

    @property
    def date_(self) -> date:
        return self.sleep_end.date()

    def _fromts(self, ts: int) -> datetime:
        return datetime.fromtimestamp(ts, tz=self._tz)

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
    def phases(self) -> list[datetime]:
        # TODO make sure they are consistent with emfit?
        return [self._fromts(i['time']) for i in get_phases()[self.xid]]

    def __str__(self) -> str:
        return f"{self.date_.strftime('%a %d %b')} {self.title}"

    def __repr__(self) -> str:
        return str(self)


def load_sleeps() -> list[SleepEntry]:
    sleeps = json.loads(SLEEPS_FILE.read_text())
    return [SleepEntry(js) for js in sleeps]


from ..core.error import Res, extract_error_datetime, set_error_datetime


def pre_dataframe() -> Iterable[Res[SleepEntry]]:
    from more_itertools import bucket

    sleeps = load_sleeps()
    # todo emit error if graph doesn't exist??
    sleeps = [s for s in sleeps if s.graph.exists()] # TODO careful..

    bucketed = bucket(sleeps, key=lambda s: s.date_)

    for dd in bucketed:
        group = list(bucketed[dd])
        if len(group) == 1:
            yield group[0]
        else:
            err = RuntimeError(f'Multiple sleeps per night, not supported yet: {group}')
            dt = datetime.combine(dd, time.min)
            set_error_datetime(err, dt=dt)
            logger.exception(err)
            yield err


def dataframe():
    dicts: list[dict[str, Any]] = []
    for s in pre_dataframe():
        d: dict[str, Any]
        if isinstance(s, Exception):
            dt = extract_error_datetime(s)
            d = {
                'date' : dt,
                'error': str(s),
            }
        else:
            d = {
                # TODO make sure sleep start/end are consistent with emfit? add to test as well..
                # I think it makes sense to be end date as 99% of time
                # or maybe I shouldn't care about this at all?
                'date'       : s.date_,
                'sleep_start': s.sleep_start,
                'sleep_end'  : s.sleep_end,
                'bed_time'   : s.bed_time,
            }
        dicts.append(d)

    import pandas as pd
    return pd.DataFrame(dicts)
    # TODO tz is in sleeps json


def stats():
    from ..core import stat
    return stat(pre_dataframe)


#### NOTE: most of the stuff below is deprecated and remnants of my old code!
#### sorry for it, feel free to remove if you don't need it


def hhmm(time: datetime):
    return time.strftime("%H:%M")


# def xpos(time: datetime) -> float:
#     tick = span / width
#     fromstart = time - sleep.created
#     return fromstart / tick


def plot_one(sleep: SleepEntry, fig, axes, xlims=None, *, showtext=True):
    import matplotlib.dates as mdates  # type: ignore[import-not-found]

    span = sleep.completed - sleep.created
    print(f"{sleep.xid} span: {span}")

    # pip install imageio
    from imageio import imread  # type: ignore[import-not-found]

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
        axes.text(xlims[1] - timedelta(hours=1.5), 20, str(sleep))
    # plt.text(sleep.asleep(), 0, hhmm(sleep.asleep()))


# TODO not really sure it belongs here...
# import melatonin
# dt = melatonin.get_data()

def predicate(sleep: SleepEntry):
    """
       Filter for comparing similar sleep sessions
    """
    start = sleep.created.time()
    end = sleep.completed.time()
    if (time(23, 0) <= start <= time(23, 30)) and (time(5, 30) <= end <= time(6, 30)):
        return True
    return False


# TODO move to dashboard
def plot() -> None:
    import matplotlib.pyplot as plt  # type: ignore[import-not-found]
    from matplotlib.figure import Figure  # type: ignore[import-not-found]

    # TODO FIXME melatonin data
    melatonin_data = {} # type: ignore[var-annotated]

    # TODO ??
    sleeps = list(filter(predicate, load_sleeps()))
    sleeps_count = len(sleeps)
    print(sleeps_count)

    fig: Figure = plt.figure(figsize=(15, sleeps_count * 1))

    axarr = fig.subplots(nrows=len(sleeps))
    for (sleep, axes) in zip(sleeps, axarr):
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

