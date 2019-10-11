#!/usr/bin/env python3
from pathlib import Path, PosixPath
from typing import List, Sequence, Mapping

from my_configuration import paths
import my_configuration.repos.rexport.model as rexport


class CPath(PosixPath):
    def open(self, *args, **kwargs):
        # TODO FIXME use something else instead?
        from kython import kompress
        return kompress.open(str(self))


def get_backup_files() -> Sequence[Path]:
    export_dir = Path(paths.rexport.export_dir)
    res = list(map(CPath, sorted(export_dir.glob('*.json.xz'))))
    assert len(res) > 0
    return tuple(res)


def get_model():
    model = rexport.Model(get_backup_files())
    return model

import logging

def get_logger():
    return logging.getLogger('my.reddit')


Save = rexport.Save
Sid = rexport.Sid


def get_saves() -> List[Save]:
    return get_model().saved()


from typing import Dict, Union, Iterable, Iterator, NamedTuple, Any
from functools import lru_cache
import pytz
import re
from datetime import datetime
from multiprocessing import Pool

# TODO hmm. apparently decompressing takes quite a bit of time...

def reddit(suffix: str) -> str:
    return 'https://reddit.com' + suffix


# TODO for future events?
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


class SaveWithDt(NamedTuple):
    save: Save
    backup_dt: datetime

    def __getattr__(self, x):
        return getattr(self.save, x)


Url = str

def _get_bdate(bfile: Path) -> datetime:
    RE = re.compile(r'reddit-(\d{14})')
    match = RE.search(bfile.stem)
    assert match is not None
    bdt = pytz.utc.localize(datetime.strptime(match.group(1), "%Y%m%d%H%M%S"))
    return bdt


def _get_state(bfile: Path) -> Dict[Sid, SaveWithDt]:
    logger = get_logger()
    logger.debug('handling %s', bfile)

    bdt = _get_bdate(bfile)

    saves = [SaveWithDt(save, bdt) for save in rexport.Model([bfile]).saved()]
    from kython import make_dict
    return make_dict(
        sorted(saves, key=lambda p: p.save.created),
        key=lambda s: s.save.sid,
    )

# from cachew import cachew
# TODO hmm. how to combine cachew and lru_cache?....
# @cachew('/L/data/.cache/reddit-events.cache')

@lru_cache(1)
def _get_events(backups: Sequence[Path], parallel: bool) -> List[Event]:
    parallel = False # TODO FIXME
    logger = get_logger()

    events: List[Event] = []
    prev_saves: Mapping[Sid, Save] = {}
    # TODO suppress first batch??
    # TODO for initial batch, treat event time as creation time

    states: Iterable[Mapping[Sid, Save]]
    if parallel:
        with Pool() as p:
            states = p.map(_get_state, backups)
    else:
        # also make it lazy...
        states = map(_get_state, backups)

    for i, (bfile, saves) in enumerate(zip(backups, states)):
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
            else: # already in saves
                s = saves[key]
                last_saved = s.backup_dt
                events.append(Event(
                    dt=s.created if first else last_saved,
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
    backups = get_backup_files()
    if not all_:
        backups = backups[-1:]
    else:
        backup = backups
        # backups = backups[:40] # TODO FIXME NOCOMMIT
    return _get_events(backups=backups, parallel=parallel)



def test():
    get_events(all_=False)
    get_saves()


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
    # TODO not sure if this is necesasry anymore?
    saves = get_saves()
    # just check that they are unique..
    from kython import make_dict
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
