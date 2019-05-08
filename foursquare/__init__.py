#!/usr/bin/env python3
from datetime import datetime, timezone, timedelta
from typing import List, Dict, NamedTuple, Union, Any, Tuple, Set
import json
from pathlib import Path

# TODO pytz for timezone???

from kython import safe_get, flatten

# TODO actually i'm parsing FSQ in my gmaps thing
_BPATH = Path('/L/backups/4sq')

def get_logger():
    import logging
    return logging.getLogger("fsq-provider")


class Checkin:
    def __init__(self, j) -> None:
        self.j = j

    @property
    def summary(self) -> str:
        return "checked into " + safe_get(self.j, 'venue', 'name', default="NO_NAME") + " " + self.j.get('shout', "") # TODO should should be bold...
    # TODO maybe return htmlish? if not html, interpret as string

    @property
    def dt(self) -> datetime:
        created = self.j['createdAt']  # this is local time
        offset = self.j['timeZoneOffset']
        tz = timezone(timedelta(minutes=offset))
        # a bit meh, but seems to work..
        # TODO localize??
        return datetime.fromtimestamp(created, tz=tz)

    @property
    def cid(self) -> str:
        return self.j['id']

def get_raw(fname=None):
    if fname is None:
        fname = max(_BPATH.glob('*.json'))
    with Path(fname).open() as fo:
        j = json.load(fo)

    assert isinstance(j, list)
    for chunk in j:
        del chunk['meta']
        del chunk['notifications']
    assert chunk.keys() == {'response'}
    assert chunk['response'].keys() == {'checkins'}

    return flatten([x['response']['checkins']['items'] for x in j])


# TODO not sure how to make it generic..
def get_checkins(*args, **kwargs):
    everything = get_raw(*args, **kwargs)
    checkins = sorted([Checkin(i) for i in everything], key=lambda c: c.dt)
    return checkins


# TODO do I need this??
def get_cid_map(bfile: str):
    raw = get_raw(bfile)
    return {i['id']: i for i in raw}


def test():
    assert len(get_checkins()) > 100
    # TODO cid_map??


def main():
    print(get_checkins())

if __name__ == '__main__':
    main()
