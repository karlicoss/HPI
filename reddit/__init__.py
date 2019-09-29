#!/usr/bin/env python3
from typing import List, Dict, Union, Iterable, Iterator, NamedTuple, Any, Sequence
import json
from functools import lru_cache
from collections import OrderedDict
from pathlib import Path
import pytz
import re
from datetime import datetime
import logging
from multiprocessing import Pool

from kython import kompress, cproperty, make_dict, numbers
from kython.klogging import setup_logzero

# TODO hmm. apparently decompressing takes quite a bit of time...

BPATH = Path("/L/backups/reddit")


def get_logger():
    return logging.getLogger('reddit-provider')

def reddit(suffix: str) -> str:
    return 'https://reddit.com' + suffix


def _get_backups(all_=True) -> Sequence[Path]:
    bfiles = tuple(sorted(BPATH.glob('reddit-*.json.xz'))) # TODO switch to that new compression format?
    if all_:
        return bfiles
    else:
        return bfiles[-1:]

Sid = str

class Save(NamedTuple):
    created: datetime
    backup_dt: datetime
    title: str
    sid: Sid
    json: Any = None
    # TODO ugh. not sure how to support this in cachew... could try serializing dicts of simple types automatically.. but json can't be properly typed
    # TODO why would json be none?

    def __hash__(self):
        return hash(self.sid)

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


# class Misc(NamedTuple):
#     pass

# EventKind = Union[Save, Misc]

EventKind = Save

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

def _get_bdate(bfile: Path) -> datetime:
    RE = re.compile(r'reddit-(\d{14})')
    match = RE.search(bfile.stem)
    assert match is not None
    bdt = pytz.utc.localize(datetime.strptime(match.group(1), "%Y%m%d%H%M%S"))
    return bdt


def _get_state(bfile: Path) -> Dict[Sid, Save]:
    logger = get_logger()
    logger.debug('handling %s', bfile)

    bdt = _get_bdate(bfile)

    saves: List[Save] = []
    with kompress.open(bfile) as fo:
        jj = json.load(fo)

    saved = jj['saved']
    for s in saved:
        created = pytz.utc.localize(datetime.utcfromtimestamp(s['created_utc']))
        # TODO need permalink
        # url = get_some(s, 'link_permalink', 'url') # this was original url...
        title = get_some(s, 'link_title', 'title')
        save = Save(
            created=created,
            backup_dt=bdt,
            title=title,
            sid=s['id'],
            json=s,
        )
        saves.append(save)

    return make_dict(
        sorted(saves, key=lambda p: p.created),
        key=lambda s: s.sid,
    )
    return OrderedDict()

# from cachew import cachew
# TODO hmm. how to combine cachew and lru_cache?....
# @cachew('/L/data/.cache/reddit-events.cache')

@lru_cache(1)
def _get_events(backups: Sequence[Path], parallel: bool) -> List[Event]:
    logger = get_logger()

    events: List[Event] = []
    prev_saves: Dict[Sid, Save] = {}
    # TODO suppress first batch??
    # TODO for initial batch, treat event time as creation time

    states: Iterable[Dict[Sid, Save]]
    if parallel:
        with Pool() as p:
            states = p.map(_get_state, backups)
    else:
        # also make it lazy...
        states = map(_get_state, backups)

    for i, bfile, saves in zip(numbers(), backups, states):
        bdt = _get_bdate(bfile)

        first = i == 0

        for key in set(prev_saves.keys()).symmetric_difference(set(saves.keys())):
            ps = prev_saves.get(key, None)
            if ps is not None:
                # TODO use backup date, that is more precise...
                # eh. I guess just take max and it will always be correct?
                assert not first
                events.append(Event(
                    dt=bdt, # TODO average wit ps.save_dt? 
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

def get_events(*args, all_=True, parallel=True):
    backups = _get_backups(all_=all_)
    assert len(backups) > 0
    return _get_events(backups=backups, parallel=parallel)

def get_saves(**kwargs) -> List[Save]:
    logger = get_logger()

    events = get_events(**kwargs)
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


def test_disappearing():
    # eh. so for instance, 'metro line colors' is missing from reddit-20190402005024.json for no reason
    # but I guess it was just a short glitch... so whatever
    saves = get_events(all_=True)
    favs = [s.kind for s in saves if s.text == 'favorited']
    [deal_with_it] = [f for f in favs if f.title == '"Deal with it!"']
    assert deal_with_it.backup_dt == datetime(2019, 4, 1, 23, 10, 25, tzinfo=pytz.utc)


def test_unfavorite():
    events = get_events(all_=True)
    unfavs = [s for s in events if s.text == 'unfavorited']
    [xxx] = [u for u in unfavs if u.eid == 'unf-19ifop']
    assert xxx.dt == datetime(2019, 1, 28, 8, 10, 20, tzinfo=pytz.utc)


def main():
    setup_logzero(get_logger(), level=logging.DEBUG)
    # TODO eh. not sure why but parallel on seems to mess glumov up and cause OOM...
    events = get_events(parallel=False)
    print(len(events))
    for e in events:
        print(e.text, e.url)
    # for e in get_
    # 509 with urls..
    # for e in get_events():
    #     print(e)


if __name__ == '__main__':
    main()
