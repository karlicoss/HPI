#!/usr/bin/env python3
from typing import List, Dict, Union, Iterable, Iterator, NamedTuple, Any
import json
from collections import OrderedDict
from pathlib import Path
import pytz
import re
from datetime import datetime

from kython import kompress, cproperty, make_dict

# TODO hmm. apparently decompressing takes quite a bit of time...

BPATH = Path("/L/backups/reddit")

def reddit(suffix: str) -> str:
    return 'https://reddit.com' + suffix


def _get_backups(all_=True) -> List[Path]:
    bfiles = list(sorted(BPATH.glob('reddit-*.json.xz')))
    if all_:
        return bfiles
    else:
        return bfiles[-1:]


class Save(NamedTuple):
    dt: datetime
    title: str
    sid: str
    json: Any = None

    def __hash__(self):
        return hash(self.sid)

    @cproperty
    def url(self) -> str:
        # pylint: disable=unsubscriptable-object
        pl = self.json['permalink']
        return reddit(pl)

    @cproperty
    def text(self) -> str:
        bb = self.json.get('body', None)
        st = self.json.get('selftext', None)
        if bb is not None and st is not None:
            raise RuntimeError(f'wtf, both body and selftext are not None: {bb}; {st}')
        return bb or st

    @cproperty
    def subreddit(self) -> str:
        assert self.json is not None
        # pylint: disable=unsubscriptable-object
        return self.json['subreddit']['display_name']


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

    @property
    def cmp_key(self):
        return (self.dt, (1 if 'unfavorited' in self.text else 0))


# TODO kython?
def get_some(d, *keys):
    # TODO only one should be non None??
    for k in keys:
        v = d.get(k, None)
        if v is not None:
            return v
    else:
        return None


Url = str

# TODO shit. there does seem to be a difference...
def get_state(bfile: Path) -> Dict[Url, Save]:
    saves: List[Save] = []
    with kompress.open(bfile) as fo:
        jj = json.load(fo)

    saved = jj['saved']
    for s in saved:
        dt = pytz.utc.localize(datetime.utcfromtimestamp(s['created_utc']))
        # TODO need permalink
        # url = get_some(s, 'link_permalink', 'url') # this was original url...
        title = get_some(s, 'link_title', 'title')
        save = Save(
            dt=dt,
            title=title,
            sid=s['id'],
            json=s,
        )
        saves.append(save)

    return make_dict(
        sorted(saves, key=lambda p: p.dt), # TODO make helper to create lambda from property?
        key=lambda s: s.sid,
    )
    return OrderedDict()


def get_events(all_=True) -> List[Event]:
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

        for key in set(prev_saves.keys()).symmetric_difference(set(saves.keys())):
            ps = prev_saves.get(key, None)
            if ps is not None:
                # TODO use backup date, that is more precise...
                events.append(Event(
                    dt=etime(ps.dt),
                    text=f"unfavorited",
                    kind=ps,
                    eid=f'unf-{ps.sid}',
                    url=ps.url,
                    title=ps.title,
                ))
            else: # in saves
                s = saves[key]
                events.append(Event(
                    dt=etime(s.dt),
                    text=f"favorited {'[initial]' if first else ''}",
                    kind=s,
                    eid=f'fav-{s.sid}',
                    url=s.url,
                    title=s.title,
                ))
        prev_saves = saves

    # TODO a bit awkward, favorited should compare lower than unfavorited?
    return list(sorted(events, key=lambda e: e.cmp_key))

def get_saves(all_=True) -> List[Save]:
    # TODO hmm.... do we want ALL reddit saves I ever had?
    # TODO for now even last ones would be ok
    assert all_ is False, 'all saves are not supported yet...'
    backups = _get_backups(all_=all_)
    [backup] = backups

    saves = get_state(backup)
    return list(saves.values())


def test():
    get_events(all_=False)
    get_saves(all_=False)


# TODO fuck. pytest is broken??
def test_unfav():
    events = get_events(all_=True)
    url = 'https://reddit.com/r/QuantifiedSelf/comments/acxy1v/personal_dashboard/'
    uevents = [e for e in events if e.url == url]
    assert len(uevents) == 2
    ff = uevents[0]
    assert ff.text == 'favorited [initial]'
    uf = uevents[1]
    assert uf.text == 'unfavorited'


def main():
    events = get_events()
    print(len(events))
    for e in events:
        print(e.text, e.url)
    # for e in get_
    # 509 with urls..
    # for e in get_events():
    #     print(e)


if __name__ == '__main__':
    main()
