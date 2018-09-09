from datetime import datetime, timezone, timedelta
# TODO pytz for timezone???
from typing import List, Dict, NamedTuple, Union, Any

from kython import safe_get, flatten
from kython.data import get_last_file

# TODO actually i'm parsing FSQ in my gmaps thing
_BPATH = '/L/backups/4sq'

class Checkin:
    def __init__(self, j) -> None:
        self.j = j

    @property
    def _summary(self) -> str:
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

def get_checkins():
    j = get_last_file(_BPATH)
    everything = flatten([x['response']['checkins']['items'] for x in j])
    checkins = sorted([Checkin(i) for i in everything], key=lambda c: c.dt)
    return checkins
