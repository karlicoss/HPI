#!/usr/bin/env python3
from typing import List, Dict, Union, Iterable, Iterator, NamedTuple, Any
import json
from collections import OrderedDict
from pathlib import Path
import pytz
import re
from datetime import datetime
import logging
from multiprocessing import Pool

from kython import kompress, cproperty, make_dict

# TODO hmm. apparently decompressing takes quite a bit of time...

BPATH = Path("/L/backups/reddit")

def get_logger():
    return logging.getLogger('reddit-provider')

def reddit(suffix: str) -> str:
    return 'https://reddit.com' + suffix


def _get_backups(all_=True) -> List[Path]:
    bfiles = list(sorted(BPATH.glob('reddit-*.json.xz')))
    if all_:
        return bfiles
    else:
        return bfiles[-1:]

Sid = str

class Save(NamedTuple):
    dt: datetime # TODO misleading name... this is creation dt, not saving dt
    backup_dt: datetime
    title: str
    sid: Sid
    json: Any = None

    def __hash__(self):
        return hash(self.sid)

    @cproperty
    def created(self) -> datetime:
        return self.dt

    @cproperty
    def save_dt(self) -> datetime:
        # TODO not exactly precise... but whatever I guess
        return self.backup_dt

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
# TODO do it in multiple threads??
def get_state(bfile: Path) -> Dict[Sid, Save]:
    logger = get_logger()
    logger.debug('handling %s', bfile)

    RE = re.compile(r'reddit-(\d{14})')
    match = RE.search(bfile.stem)
    assert match is not None
    bdt = pytz.utc.localize(datetime.strptime(match.group(1), "%Y%m%d%H%M%S"))

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
            backup_dt=bdt,
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


def get_events(all_=True, parallel=True) -> List[Event]:
    backups = _get_backups(all_=all_)
    assert len(backups) > 0

    events: List[Event] = []
    prev_saves: Dict[Sid, Save] = {}
    # TODO suppress first batch??
    # TODO for initial batch, treat event time as creation time

    states: Iterable[Dict[Sid, Save]]
    if parallel:
        with Pool() as p:
            states = p.map(get_state, backups)
    else:
        # also make it lazy...
        states = map(get_state, backups)

    for i, saves in enumerate(states): # TODO when date...

        first = i == 0

        for key in set(prev_saves.keys()).symmetric_difference(set(saves.keys())):
            ps = prev_saves.get(key, None)
            if ps is not None:
                # TODO use backup date, that is more precise...
                # eh. I guess just take max and it will always be correct?
                events.append(Event(
                    dt=ps.created if first else ps.save_dt,
                    text=f"unfavorited",
                    kind=ps,
                    eid=f'unf-{ps.sid}',
                    url=ps.url,
                    title=ps.title,
                ))
            else: # in saves
                s = saves[key]
                events.append(Event(
                    dt=s.created if first else s.save_dt,
                    text=f"favorited{' [initial]' if first else ''}",
                    kind=s,
                    eid=f'fav-{s.sid}',
                    url=s.url,
                    title=s.title,
                ))
        prev_saves = saves

    # TODO a bit awkward, favorited should compare lower than unfavorited?
    return list(sorted(events, key=lambda e: e.cmp_key))

def get_saves(all_=True) -> List[Save]:
    logger = get_logger()

    events = get_events(all_=all_)
    saves: Dict[Sid, Save] = OrderedDict()
    for e in events:
        if e.text.startswith('favorited'):
            ss = e.kind
            assert isinstance(ss, Save)
            if ss.sid in saves:
                # apparently we can get duplicates if we saved/unsaved multiple times...
                logger.warning(f'ignoring duplicate save %s, title %s, url %s', ss.sid, ss.title, ss.url)
            else:
                saves[ss.sid] = ss
    assert len(saves) > 0

    return list(saves.values())


def test():
    get_events(all_=False)
    get_saves(all_=False)


# TODO fuck. pytest is broken??
# right, apparently I need pytest.ini file...
def test_unfav():
    events = get_events(all_=True)
    url = 'https://reddit.com/r/QuantifiedSelf/comments/acxy1v/personal_dashboard/'
    uevents = [e for e in events if e.url == url]
    assert len(uevents) == 2
    ff = uevents[0]
    assert ff.text == 'favorited'
    uf = uevents[1]
    assert uf.text == 'unfavorited'

def test_get_all_saves():
    saves = get_saves(all_=True)
    # just check that they are unique..
    make_dict(saves, key=lambda s: s.sid)


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
