from typing import List, Dict, Union, Iterable, Iterator, NamedTuple
import json
from pathlib import Path
import pytz
import re
from datetime import datetime

from kython import kompress


BPATH = Path("/L/backups/reddit")


def _get_backups(all_=True) -> List[Path]:
    bfiles = list(sorted(BPATH.glob('reddit-*.json.xz')))
    if all_:
        return bfiles
    else:
        return bfiles[-1:]


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


# TODO kython?
def get_some(d, *keys):
    for k in keys:
        v = d.get(k, None)
        if v is not None:
            return v
    else:
        return None


def get_state(bfile: Path):
    saves: Dict[str, Save] = {}
    with kompress.open(bfile) as fo:
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


def get_events(all_=True):
    backups = _get_backups(all_=all_)
    assert len(backups) > 0

    events: List[Event] = []
    prev_saves: Dict[str, Save] = {}
    # TODO suppress first batch??
    # TODO for initial batch, treat event time as creation time

    RE = re.compile(r'reddit-(\d{14})')
    for i, b in enumerate(backups): # TODO when date...
        match = RE.search(b.stem)
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


def test():
    get_events(all_=False)


def main():
    for e in get_events():
        print(e)


if __name__ == '__main__':
    main()
