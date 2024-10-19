'''
Foursquare/Swarm checkins
'''

import json
from datetime import datetime, timedelta, timezone
from itertools import chain

from my.config import foursquare as config

# TODO pytz for timezone???
from my.core import get_files, make_logger

logger = make_logger(__name__)


def inputs():
    return get_files(config.export_path)


class Checkin:
    def __init__(self, j) -> None:
        self.j = j

    @property
    def summary(self) -> str:
        name = self.j.get('venue', {}).get('name', 'NO_NAME')
        return "checked into " + name + " " + self.j.get('shout', "") # TODO should should be bold...

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

    def __repr__(self):
        return repr(self.j)


class Place:
    def __init__(self, j) -> None:
        self.j = j


# TODO ugh. I'm not backing up lists, apparently...
# def test_places():
#     raise RuntimeError()


# TODO need json type

def get_raw(fname=None):
    if fname is None:
        fname = max(inputs())
    j = json.loads(fname.read_text())
    assert isinstance(j, list)

    for chunk in j:
        del chunk['meta']
        del chunk['notifications']
    assert chunk.keys() == {'response'}
    assert chunk['response'].keys() == {'checkins'}

    return chain.from_iterable(x['response']['checkins']['items'] for x in j)


# TODO not sure how to make it generic..
def get_checkins(*args, **kwargs):
    everything = get_raw(*args, **kwargs)
    checkins = sorted([Checkin(i) for i in everything], key=lambda c: c.dt)
    return checkins


# TODO do I need this??
def get_cid_map(bfile: str):
    raw = get_raw(bfile)
    return {i['id']: i for i in raw}


def print_checkins():
    print(get_checkins())


def stats():
    from more_itertools import ilen
    return {
        'checkins': ilen(get_checkins()),
    }
