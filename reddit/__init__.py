from typing import List, Dict, Union, Iterable, Iterator, NamedTuple

BPATH = "/L/backups/reddit"

def iter_backups() -> Iterator[str]:
    import os
    for f in sorted(os.listdir(BPATH)):
        if f.endswith('.json'):
            yield os.path.join(BPATH, f)


from datetime import datetime

class Save(NamedTuple):
    dt: datetime
    link: str

class Misc(NamedTuple):
    pass

EventKind = Union[Save, Misc]

class Event(NamedTuple):
    dt: datetime
    text: str
    kind: EventKind

from kython import JSONType, json_load

def get_some(d, *keys):
    for k in keys:
        v = d.get(k, None)
        if v is not None:
            return v
    else:
        return None


def get_state(bfile: str):
    saves: Dict[str, Save] = {}
    json: JSONType
    with open(bfile, 'r') as fo:
        json = json_load(fo)

    saved = json['saved']
    for s in saved:
        dt = datetime.utcfromtimestamp(s['created_utc'])
        link = get_some(s, 'link_permalink', 'url') # TODO link title or title
        save = Save(dt=dt, link=link)
        saves[save.link] = save

        # "created_utc": 1535055017.0,
        # link_title
        # link_text 
    return saves


def get_events():
    backups = list(iter_backups())

    events: List[Event] = []
    prev_saves: Dict[str, Save] = {}
    # TODO suppress first batch??

    for b in backups: # TODO when date...
        saves = get_state(b)
        for l in set(prev_saves.keys()).symmetric_difference(set(saves.keys())):
            if l in prev_saves:
                s = prev_saves[l]
                # TODO use backup date, that is more precise...
                events.append(Event(
                    dt=s.dt,
                    text=f"Unfavorited {s.link}",
                    kind=s,
                ))
            else: # in saves
                s = saves[l]
                events.append(Event(
                    dt=s.dt,
                    text=f"Favorited {s.link}",
                    kind=s,
                ))
        prev_saves = saves

    return list(sorted(events, key=lambda e: e.dt))


