from typing import List, Dict, Union, Iterable, Iterator, NamedTuple
import json
from pathlib import Path
import pytz

BPATH = "/L/backups/reddit"


import re
RE = re.compile(r'reddit-(\d{14}).json.xz')

def iter_backups() -> Iterator[str]:
    import os
    for f in sorted(os.listdir(BPATH)):
        if RE.match(f):
            yield os.path.join(BPATH, f)


from datetime import datetime

class Save(NamedTuple):
    dt: datetime
    title: str
    url: str
    sid: str

class Misc(NamedTuple):
    pass

EventKind = Union[Save, Misc]

class Event(NamedTuple):
    dt: datetime
    text: str
    kind: EventKind
    eid: str
    title: str
    url: str

from kython import JSONType, load_json_file

def get_some(d, *keys):
    for k in keys:
        v = d.get(k, None)
        if v is not None:
            return v
    else:
        return None


def get_state(bfile: str):
    saves: Dict[str, Save] = {}
    with Path(bfile).open() as fo:
        jj = json.load(fo)

    saved = jj['saved']
    for s in saved:
        dt = pytz.utc.localize(datetime.utcfromtimestamp(s['created_utc']))
        url = get_some(s, 'link_permalink', 'url')
        title = get_some(s, 'link_title', 'title')
        save = Save(
            dt=dt,
            title=title,
            url=url,
            sid=s['id'],
        )
        saves[save.url] = save

        # "created_utc": 1535055017.0,
        # link_title
        # link_text 
    return saves


def get_events():
    backups = list(iter_backups())
    assert len(backups) > 0

    events: List[Event] = []
    prev_saves: Dict[str, Save] = {}
    # TODO suppress first batch??
    # TODO for initial batch, treat event time as creation time

    for i, b in enumerate(backups): # TODO when date...
        match = RE.search(b)
        assert match is not None
        btime = pytz.utc.localize(datetime.strptime(match.group(1), "%Y%m%d%H%M%S"))

        first = i == 0
        saves = get_state(b)

        def etime(dt: datetime):
            if first:
                return dt
            else:
                return btime

        for l in set(prev_saves.keys()).symmetric_difference(set(saves.keys())):
            if l in prev_saves:
                s = prev_saves[l]
                # TODO use backup date, that is more precise...
                events.append(Event(
                    dt=etime(s.dt),
                    text=f"unfavorited",
                    kind=s,
                    eid=f'unf-{s.sid}',
                    url=s.url,
                    title=s.title,
                ))
            else: # in saves
                s = saves[l]
                events.append(Event(
                    dt=etime(s.dt),
                    text=f"favorited {' [initial]' if first else ''}",
                    kind=s,
                    eid=f'fav-{s.sid}',
                    url=s.url,
                    title=s.title,
                ))
        prev_saves = saves

    return list(sorted(events, key=lambda e: e.dt))


